import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/warcraftcn/badge";
import { Button } from "@/components/ui/warcraftcn/button";
import { Skeleton } from "@/components/ui/warcraftcn/skeleton";
import { mockData } from "@/data/mockData";
import { useDefaultAccount, useCharacters } from "@/hooks/useWow";
import { api } from "@/lib/api";
import { ItemSelector } from "@/components/crafting/ItemSelector";
import {
  useCraftingOrders,
  useCreateCraftingOrder,
  useAdvanceCraftingOrder,
  useDeleteCraftingOrder,
  useCraftingGoals,
  useCreateCraftingGoal,
  useDeleteCraftingGoal,
} from "@/hooks/useWow";

const Panel = ({ title, subtitle, actions, className = "", children }) => (
  <section className={`panel-frame ${className}`}>
    <div className="panel-header">
      <div>
        <p className="panel-title">{title}</p>
        {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
    <div className="panel-body">{children}</div>
  </section>
);

const ProgressBar = ({ value }) => (
  <div className="h-2 w-full rounded-full bg-muted/50">
    <div
      className="h-2 rounded-full bg-primary shadow-[0_0_10px_rgba(245,204,120,0.4)]"
      style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
    />
  </div>
);

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_LABEL = { a_faire: "A faire", en_cours: "En cours", termine: "Terminé" };
const STATUS_VARIANT = { a_faire: "outline", en_cours: "secondary", termine: "default" };

/** Formate un montant en gold (entier) → "+18k or" ou "+500 or" */
function formatGold(gold) {
  if (!gold) return "—";
  if (gold >= 1000) return `+${(gold / 1000).toFixed(gold % 1000 === 0 ? 0 : 1)}k or`;
  return `+${gold} or`;
}

const EMPTY_ORDER = { item_name: "", item_id: null, recipe_id: null, client: "", character_id: "", profession: "", profit_gold: 0 };
const EMPTY_GOAL  = { title: "", item_id: null, recipe_id: null, character_id: "", profession: "" };

// ── Page ──────────────────────────────────────────────────────────────────────

function CraftingPage() {
  const [viewMode, setViewMode]         = useState("profession");
  const [selectedKeys, setSelectedKeys] = useState([]); // [] = tout afficher

  // ── Données API ────────────────────────────────────────────────────────────
  const { data: account }                              = useDefaultAccount();
  const { data: characters, loading: charsLoading }   = useCharacters(account?.id);
  const { data: orders,  loading: ordersLoading, refetch: refetchOrders } = useCraftingOrders();
  const { data: goals,   loading: goalsLoading,  refetch: refetchGoals  } = useCraftingGoals();

  const { createOrder, loading: creatingOrder } = useCreateCraftingOrder(refetchOrders);
  const { advanceOrder }                        = useAdvanceCraftingOrder(refetchOrders);
  const { deleteOrder }                         = useDeleteCraftingOrder(refetchOrders);
  const { createGoal, loading: creatingGoal }   = useCreateCraftingGoal(refetchGoals);
  const { deleteGoal }                          = useDeleteCraftingGoal(refetchGoals);

  // ── Formulaires ────────────────────────────────────────────────────────────
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [newOrder, setNewOrder]           = useState(EMPTY_ORDER);
  const [orderResolving, setOrderResolving] = useState(false);
  const [showGoalForm, setShowGoalForm]   = useState(false);
  const [newGoal, setNewGoal]             = useState(EMPTY_GOAL);
  const [goalResolving, setGoalResolving]   = useState(false);

  // ── Réactifs des recettes ─────────────────────────────────────────────────
  // recipeDetails : { [recipe_id]: { reagents: [{item_id, item_name, quantity}] } }
  const [recipeDetails, setRecipeDetails] = useState({});
  // goalHaveQty  : { [`${goal.id}-${item_id}`]: qty } — quantités possédées (DB)
  const [goalHaveQty, setGoalHaveQty] = useState({});
  const reagentTimers    = useRef({});
  const loadingRecipeIds = useRef(new Set()); // évite les doublons de chargement
  const cacheInitialized = useRef(false);     // garantit un seul chargement du cache DB

  // ── Sélecteurs dérivés ────────────────────────────────────────────────────

  const byProfession = useMemo(() => {
    if (!characters) return [];
    const map = new Map();
    characters.forEach((char) => {
      char.professions?.forEach((prof) => {
        if (!map.has(prof.name)) map.set(prof.name, []);
        map.get(prof.name).push(char.name);
      });
    });
    return Array.from(map.entries()).map(([profession, owners]) => ({ profession, owners }));
  }, [characters]);

  const byCharacter = useMemo(() => {
    if (!characters) return [];
    return characters.map((c) => ({
      id: c.id,
      name: c.name,
      professions: c.professions?.map((p) => p.name) ?? [],
    }));
  }, [characters]);

  const handleViewMode = useCallback((mode) => { setViewMode(mode); setSelectedKeys([]); }, []);
  const toggleKey = useCallback((key) => {
    setSelectedKeys((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  }, []);

  /** Pré-remplit perso/métier selon le filtre actif (1 seule clé sélectionnée). */
  const buildPreFill = useCallback((empty) => {
    if (selectedKeys.length !== 1) return { ...empty };
    const pre = { ...empty };
    if (viewMode === "profession") {
      pre.profession = selectedKeys[0];
      const charsWithProf = byCharacter.filter((c) => c.professions.includes(selectedKeys[0]));
      if (charsWithProf.length === 1) pre.character_id = String(charsWithProf[0].id);
    } else {
      const char = byCharacter.find((c) => c.name === selectedKeys[0]);
      if (char) {
        pre.character_id = String(char.id);
        if (char.professions.length === 1) pre.profession = char.professions[0];
      }
    }
    return pre;
  }, [selectedKeys, viewMode, byCharacter]);

  /** Met à jour le personnage et préserve la profession si toujours valide. */
  const handleCharChange = useCallback((charId, setter) => {
    const char = (characters ?? []).find((c) => c.id === parseInt(charId, 10));
    const profs = char?.professions?.map((p) => p.name) ?? [];
    setter((p) => ({ ...p, character_id: charId, profession: profs.includes(p.profession) ? p.profession : "" }));
  }, [characters]);

  // ── Pré-remplissage des formulaires depuis le filtre actif ────────────────
  const openOrderForm = useCallback(() => {
    if (showOrderForm) { setShowOrderForm(false); return; }
    setNewOrder(buildPreFill(EMPTY_ORDER));
    setShowOrderForm(true);
  }, [showOrderForm, buildPreFill]);

  const openGoalForm = useCallback(() => {
    if (showGoalForm) { setShowGoalForm(false); return; }
    setNewGoal(buildPreFill(EMPTY_GOAL));
    setShowGoalForm(true);
  }, [showGoalForm, buildPreFill]);

  // Backfill automatique : résout item_id pour les items sauvegardés sans (migration)
  useEffect(() => {
    api.crafting.backfillItemIds()
      .then((res) => { if (res?.updated > 0) { refetchOrders(); refetchGoals(); } })
      .catch(() => {/* silencieux si Blizzard credentials absents */});
  // Une seule fois au montage du composant
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Chargement initial des quantités réactifs depuis la base de données
  useEffect(() => {
    api.crafting.goals.reagents()
      .then((rows) => {
        const map = {};
        rows.forEach((r) => { map[`${r.goal_id}-${r.item_id}`] = r.have_qty; });
        setGoalHaveQty(map);
      })
      .catch(console.error);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-scan tooltips Wowhead — données, filtres, réactifs, (re)montage
  useEffect(() => {
    const t = setTimeout(() => window.WH?.Tooltips?.refreshLinks?.(), 150);
    return () => clearTimeout(t);
  }, [orders, goals, selectedKeys, recipeDetails]);

  // Re-scan au (re)montage du composant (retour sur la page crafting)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const t = setTimeout(() => window.WH?.Tooltips?.refreshLinks?.(), 400);
    return () => clearTimeout(t);
  }, []);

  // Charge les détails de recette (réactifs).
  // Étape 1 (premier montage) — lit le cache DB en entier pour éviter N scrapes Wowhead.
  // Étape 2 — pour les recipe_id encore absents du cache, scrape Wowhead individuellement.
  useEffect(() => {
    const allItems  = [...(orders ?? []), ...(goals ?? [])];
    const recipeIds = [...new Set(allItems.map((i) => i.recipe_id).filter(Boolean))];
    if (recipeIds.length === 0) return;

    const fetchMissing = (knownDetails) => {
      const toLoad = recipeIds.filter(
        (rid) => !knownDetails[rid] && !loadingRecipeIds.current.has(rid)
      );
      if (toLoad.length === 0) return;
      toLoad.forEach((rid) => loadingRecipeIds.current.add(rid));
      Promise.allSettled(
        toLoad.map((rid) =>
          api.crafting.recipes.getDetail(rid)
            .then((detail) => {
              if (detail?.reagents?.length > 0) {
                setRecipeDetails((prev) => ({ ...prev, [rid]: detail }));
              }
            })
            .finally(() => { loadingRecipeIds.current.delete(rid); })
        )
      );
    };

    if (!cacheInitialized.current) {
      cacheInitialized.current = true;
      api.crafting.recipes.loadCache()
        .then((rows) => {
          const dbMap = {};
          (rows ?? []).forEach((r) => { if (r.reagents?.length) dbMap[r.recipe_id] = r; });
          if (Object.keys(dbMap).length > 0) {
            setRecipeDetails((prev) => ({ ...dbMap, ...prev }));
          }
          fetchMissing(dbMap);
        })
        .catch(() => fetchMissing({}));
    } else {
      fetchMissing(recipeDetails);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, goals]);

  // ── Filtres ───────────────────────────────────────────────────────────────

  const filteredOrders = useMemo(() => {
    if (!orders) return [];
    if (selectedKeys.length === 0) return orders;
    return viewMode === "profession"
      ? orders.filter((o) => selectedKeys.includes(o.profession))
      : orders.filter((o) => selectedKeys.includes(o.character?.name));
  }, [orders, viewMode, selectedKeys]);

  const filteredGoals = useMemo(() => {
    if (!goals) return [];
    if (selectedKeys.length === 0) return goals;
    return viewMode === "profession"
      ? goals.filter((g) => selectedKeys.includes(g.profession))
      : goals.filter((g) => selectedKeys.includes(g.character?.name));
  }, [goals, viewMode, selectedKeys]);

  /** KP depuis les professions réelles des personnages (API) */
  const filteredKp = useMemo(() => {
    if (!characters) return [];
    if (viewMode === "profession") {
      return characters.flatMap(
        (char) =>
          char.professions
            ?.filter((p) => selectedKeys.length === 0 || selectedKeys.includes(p.name))
            .map((p) => ({ profession: p.name, characterName: char.name, current: p.kp_current, max: p.kp_max })) ?? []
      );
    }
    const chars = selectedKeys.length === 0 ? characters : characters.filter((c) => selectedKeys.includes(c.name));
    return chars.flatMap((c) =>
      c.professions?.map((p) => ({ profession: p.name, characterName: c.name, current: p.kp_current, max: p.kp_max })) ?? []
    );
  }, [characters, viewMode, selectedKeys]);

  // Sections encore sur mockData (pas de modèle DB — niveau 2/3)
  const activeMockProfs = useMemo(() => {
    if (selectedKeys.length === 0) {
      if (viewMode === "profession") return byProfession.map((r) => r.profession);
      return mockData.characters.flatMap((c) => c.professions);
    }
    if (viewMode === "profession") return selectedKeys;
    return mockData.characters.filter((c) => selectedKeys.includes(c.name)).flatMap((c) => c.professions);
  }, [selectedKeys, viewMode, byProfession]);

  const filteredBestCrafts = useMemo(
    () => mockData.crafting.bestCrafts.filter((c) => activeMockProfs.includes(c.profession)),
    [activeMockProfs]
  );
  const filteredSkillTree  = useMemo(
    () => mockData.crafting.skillTree.filter((n) => activeMockProfs.includes(n.profession)),
    [activeMockProfs]
  );

  const buildMaterialsMap = useCallback((items) => {
    const map = new Map();
    items.forEach((item) => {
      if (!item.recipe_id || !recipeDetails[item.recipe_id]) return;
      recipeDetails[item.recipe_id].reagents.forEach((r) => {
        if (!r.item_id) return;
        if (map.has(r.item_id)) map.get(r.item_id).qty += r.quantity;
        else map.set(r.item_id, { item_id: r.item_id, item_name: r.item_name, qty: r.quantity });
      });
    });
    return Array.from(map.values()).sort((a, b) => (a.item_name ?? "").localeCompare(b.item_name ?? ""));
  }, [recipeDetails]);

  const materialsOrders = useMemo(() => buildMaterialsMap(filteredOrders), [filteredOrders, buildMaterialsMap]);
  const materialsGoals  = useMemo(() => buildMaterialsMap(filteredGoals),  [filteredGoals,  buildMaterialsMap]);

  // Professions disponibles dans les forms (selon le perso choisi)
  const orderFormProfs = useMemo(() => {
    if (!newOrder.character_id || !characters) return [];
    return characters.find((c) => c.id === parseInt(newOrder.character_id, 10))?.professions?.map((p) => p.name) ?? [];
  }, [newOrder.character_id, characters]);

  const goalFormProfs = useMemo(() => {
    if (!newGoal.character_id || !characters) return [];
    return characters.find((c) => c.id === parseInt(newGoal.character_id, 10))?.professions?.map((p) => p.name) ?? [];
  }, [newGoal.character_id, characters]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleSubmitOrder = useCallback(async (e) => {
    e.preventDefault();
    if (!newOrder.item_name || !newOrder.client || !newOrder.character_id || !newOrder.profession) return;
    // Si recipe_id connu mais item_id pas encore résolu, on le récupère maintenant
    let finalOrder = { ...newOrder };
    if (finalOrder.recipe_id && !finalOrder.item_id) {
      try {
        const detail = await api.crafting.recipes.getDetail(finalOrder.recipe_id);
        if (detail?.item_id) {
          finalOrder.item_id = detail.item_id;
          finalOrder.item_name = detail.item_name || finalOrder.item_name;
          setNewOrder((prev) => ({ ...prev, item_id: detail.item_id }));
        }
      } catch (_) { /* continue sans item_id */ }
    }
    await createOrder({ ...finalOrder, character_id: parseInt(finalOrder.character_id, 10), profit_gold: parseInt(finalOrder.profit_gold, 10) || 0 });
    setNewOrder(EMPTY_ORDER);
    setShowOrderForm(false);
  }, [newOrder, createOrder]);

  const handleSubmitGoal = useCallback(async (e) => {
    e.preventDefault();
    if (!newGoal.title || !newGoal.character_id || !newGoal.profession) return;
    let finalGoal = { ...newGoal };
    if (finalGoal.recipe_id && !finalGoal.item_id) {
      try {
        const detail = await api.crafting.recipes.getDetail(finalGoal.recipe_id);
        if (detail?.item_id) {
          finalGoal.item_id = detail.item_id;
          setNewGoal((prev) => ({ ...prev, item_id: detail.item_id }));
        }
      } catch (_) { /* continue sans item_id */ }
    }
    await createGoal({ ...finalGoal, character_id: parseInt(finalGoal.character_id, 10) });
    setNewGoal(EMPTY_GOAL);
    setShowGoalForm(false);
  }, [newGoal, createGoal]);

  // ── Styles communs ────────────────────────────────────────────────────────
  const inputClass  = "w-full rounded-md border border-border/60 bg-background/60 px-2 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/60";
  const labelClass  = "block text-[10px] uppercase tracking-widest text-muted-foreground mb-1";
  const actionClass = "px-4 py-2 text-xs leading-none";

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="dashboard-grid">

      {/* ── Sélecteur ─────────────────────────────────────────────────────── */}
      <Panel
        title="Metiers & personnages"
        subtitle="Vue par metier ou par personnage"
        className="md:col-span-12"
        actions={
          <div className="flex items-center gap-2">
            {["profession", "character"].map((mode) => (
              <button key={mode} type="button" onClick={() => handleViewMode(mode)}
                className={`rounded-md border px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${
                  viewMode === mode ? "border-primary/60 bg-card/80 text-foreground" : "border-border/60 text-muted-foreground"
                }`}
              >
                {mode === "profession" ? "Metiers" : "Persos"}
              </button>
            ))}
          </div>
        }
      >
        {charsLoading ? (
          <div className="flex gap-2">{[1,2,3].map((i) => <Skeleton key={i} className="h-7 w-24 rounded-full" />)}</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {/* Bouton "Tout" */}
            <button type="button" onClick={() => setSelectedKeys([])}
              className={`rounded-full border px-3 py-1 text-xs ${
                selectedKeys.length === 0 ? "border-primary/60 bg-card/90 text-foreground" : "border-border/60 text-muted-foreground"
              }`}
            >
              Tout
            </button>

            {viewMode === "profession"
              ? byProfession.map((row) => (
                  <button key={row.profession} type="button" onClick={() => toggleKey(row.profession)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      selectedKeys.includes(row.profession) ? "border-primary/60 bg-card/90 text-foreground" : "border-border/60 text-muted-foreground"
                    }`}
                  >
                    {row.profession}
                    <span className="ml-2 text-[10px] text-muted-foreground">{row.owners.length}</span>
                  </button>
                ))
              : byCharacter.map((row) => (
                  <button key={row.name} type="button" onClick={() => toggleKey(row.name)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      selectedKeys.includes(row.name) ? "border-primary/60 bg-card/90 text-foreground" : "border-border/60 text-muted-foreground"
                    }`}
                  >
                    {row.name}
                    <span className="ml-2 text-[10px] text-muted-foreground">{row.professions.length}</span>
                  </button>
                ))
            }
            {viewMode === "profession" && byProfession.length === 0 && (
              <p className="text-xs text-muted-foreground italic">Aucun métier — synchronise tes personnages.</p>
            )}
          </div>
        )}
      </Panel>

      {/* ── Commandes (API) ───────────────────────────────────────────────── */}
      <Panel
        title="Commandes"
        subtitle="Priorite et statut"
        className="md:col-span-6"
        actions={
          <Button variant="frame" className={actionClass} onClick={openOrderForm}>
            {showOrderForm ? "Annuler" : "Nouvelle commande"}
          </Button>
        }
      >
        {showOrderForm && (
          <form onSubmit={handleSubmitOrder} className="mb-4 rounded-md border border-border/60 bg-card/60 p-3 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelClass}>Personnage *</label>
                <select className={inputClass} value={newOrder.character_id} required
                  onChange={(e) => handleCharChange(e.target.value, setNewOrder)}
                >
                  <option value="">Choisir…</option>
                  {(characters ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Metier *</label>
                <select className={inputClass} value={newOrder.profession} required disabled={orderFormProfs.length === 0}
                  onChange={(e) => setNewOrder((p) => ({ ...p, profession: e.target.value }))}
                >
                  <option value="">Choisir…</option>
                  {orderFormProfs.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div className="col-span-2">
                <label className={labelClass}>Objet *</label>
                <ItemSelector
                  profession={newOrder.profession}
                  value={{ item_name: newOrder.item_name, item_id: newOrder.item_id, recipe_id: newOrder.recipe_id }}
                  onChange={(sel) => setNewOrder((p) => ({ ...p, ...sel }))}
                  onResolving={setOrderResolving}
                  inputClass={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Client *</label>
                <input className={inputClass} placeholder="Pseudo" value={newOrder.client} required
                  onChange={(e) => setNewOrder((p) => ({ ...p, client: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Marge (gold)</label>
                <input type="number" min="0" className={inputClass} placeholder="0" value={newOrder.profit_gold}
                  onChange={(e) => setNewOrder((p) => ({ ...p, profit_gold: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit" variant="frame" className={actionClass} disabled={creatingOrder || orderResolving}>
                {orderResolving ? "Résolution…" : creatingOrder ? "Ajout…" : "Ajouter"}
              </Button>
            </div>
          </form>
        )}

        {ordersLoading ? (
          <div className="space-y-2">{[1,2,3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
        ) : filteredOrders.length === 0 ? (
          <p className="text-xs text-muted-foreground italic py-2">Aucune commande pour cette sélection.</p>
        ) : (
          <table className="dense-table">
            <thead><tr><th>Client</th><th>Objet</th><th>Perso</th><th>Statut</th><th>Marge</th><th></th></tr></thead>
            <tbody>
              {filteredOrders.map((order) => (
                <tr key={order.id}>
                  <td className="text-foreground">{order.client}</td>
                  <td>
                    {order.item_id ? (
                      <a
                        href={`https://www.wowhead.com/fr/item=${order.item_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[13px]"
                      >
                        {order.item_name}
                      </a>
                    ) : (
                      order.item_name
                    )}
                  </td>
                  <td className="text-muted-foreground">{order.character?.name ?? "—"}</td>
                  <td>
                    <button type="button" title="Cliquer pour avancer le statut" onClick={() => advanceOrder(order.id)}>
                      <Badge size="sm" variant={STATUS_VARIANT[order.status] ?? "outline"}>
                        {STATUS_LABEL[order.status] ?? order.status}
                      </Badge>
                    </button>
                  </td>
                  <td className="text-primary">{formatGold(order.profit_gold)}</td>
                  <td>
                    <button type="button" onClick={() => deleteOrder(order.id)}
                      className="text-muted-foreground hover:text-destructive text-xs transition-colors" title="Supprimer">
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {/* ── Objectifs (API — nouveau panel) ───────────────────────────────── */}
      <Panel
        title="Objectifs de craft"
        subtitle="Suivi de progression"
        className="md:col-span-6"
        actions={
          <Button variant="frame" className={actionClass} onClick={openGoalForm}>
            {showGoalForm ? "Annuler" : "Nouvel objectif"}
          </Button>
        }
      >
        {showGoalForm && (
          <form onSubmit={handleSubmitGoal} className="mb-4 rounded-md border border-border/60 bg-card/60 p-3 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelClass}>Personnage *</label>
                <select className={inputClass} value={newGoal.character_id} required
                  onChange={(e) => handleCharChange(e.target.value, setNewGoal)}
                >
                  <option value="">Choisir…</option>
                  {(characters ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Metier *</label>
                <select className={inputClass} value={newGoal.profession} required disabled={goalFormProfs.length === 0}
                  onChange={(e) => setNewGoal((p) => ({ ...p, profession: e.target.value }))}
                >
                  <option value="">Choisir…</option>
                  {goalFormProfs.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div className="col-span-2">
                <label className={labelClass}>Objet (recette optionnelle)</label>
                <ItemSelector
                  profession={newGoal.profession}
                  value={{ item_name: newGoal.title, item_id: newGoal.item_id, recipe_id: newGoal.recipe_id }}
                  onChange={(sel) => setNewGoal((p) => ({ ...p, title: sel.item_name, item_id: sel.item_id, recipe_id: sel.recipe_id }))}
                  onResolving={setGoalResolving}
                  inputClass={inputClass}
                  placeholder="Ex: 500 flacons / semaine (ou choisir une recette)"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit" variant="frame" className={actionClass} disabled={creatingGoal || goalResolving}>
                {goalResolving ? "Résolution…" : creatingGoal ? "Ajout…" : "Ajouter"}
              </Button>
            </div>
          </form>
        )}

        {goalsLoading ? (
          <div className="space-y-3">{[1,2,3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
        ) : filteredGoals.length === 0 ? (
          <p className="text-xs text-muted-foreground italic py-2">Aucun objectif pour cette sélection.</p>
        ) : (
          <div className="space-y-3">
            {filteredGoals.map((goal) => {
              const reagents = goal.recipe_id ? (recipeDetails[goal.recipe_id]?.reagents ?? []) : [];
              return (
                <div key={goal.id} className="rounded-md border border-border/60 bg-card/70 px-3 py-2 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      {goal.item_id ? (
                        <a
                          href={`https://www.wowhead.com/fr/item=${goal.item_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[13px] leading-tight block hover:underline"
                        >
                          {goal.title}
                        </a>
                      ) : (
                        <p className="text-sm text-foreground leading-tight">{goal.title}</p>
                      )}
                      {goal.character && (
                        <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                          {goal.character.name} · {goal.profession}
                        </p>
                      )}
                    </div>
                    <button type="button" onClick={() => deleteGoal(goal.id)}
                      className="ml-1 text-muted-foreground hover:text-destructive text-xs transition-colors shrink-0" title="Supprimer">✕</button>
                  </div>

                  {/* Réactifs de la recette */}
                  {reagents.length > 0 && (
                    <div className="space-y-1 pt-1 border-t border-border/30">
                      {reagents.map((r) => {
                        const qKey = `${goal.id}-${r.item_id ?? r.item_name}`;
                        const have = goalHaveQty[qKey] ?? 0;
                        const pct  = r.quantity > 0 ? Math.min(100, Math.round((have / r.quantity) * 100)) : 0;
                        return (
                          <div key={qKey} className="flex items-center gap-2 text-xs">
                            {r.item_id ? (
                              <a href={`https://www.wowhead.com/fr/item=${r.item_id}`}
                                target="_blank" rel="noopener noreferrer"
                                className="flex-1 min-w-0 truncate text-muted-foreground hover:underline">
                                {r.item_name}
                              </a>
                            ) : (
                              <span className="flex-1 min-w-0 truncate text-muted-foreground">{r.item_name}</span>
                            )}
                            <div className="flex items-center gap-1 shrink-0">
                              <input
                                type="number" min="0" max={r.quantity} value={have}
                                onChange={(e) => {
                                  const qty = parseInt(e.target.value) || 0;
                                  setGoalHaveQty((prev) => ({ ...prev, [qKey]: qty }));
                                  // Sauvegarde debounced en base
                                  clearTimeout(reagentTimers.current[qKey]);
                                  reagentTimers.current[qKey] = setTimeout(() => {
                                    api.crafting.goals.saveReagent(goal.id, r.item_id, qty).catch(console.error);
                                  }, 600);
                                }}
                                className="w-12 rounded border border-border/60 bg-background/60 px-1 py-0.5 text-[10px] text-center focus:outline-none"
                              />
                              <span className="text-[10px] text-muted-foreground">/ {r.quantity}</span>
                              <span className={`text-[10px] w-8 text-right ${pct >= 100 ? "text-green-500" : "text-muted-foreground/60"}`}>
                                {pct}%
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* ── Knowledge Points (API — professions des personnages) ──────────── */}
      <Panel title="Knowledge Points" subtitle="KP recoltés / KP max" className="md:col-span-4">
        {charsLoading ? (
          <div className="space-y-3">{[1,2,3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}</div>
        ) : filteredKp.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">Aucun KP — synchronise tes personnages.</p>
        ) : (
          <div className="space-y-3">
            {filteredKp.map((track, i) => {
              const percent = track.max > 0 ? Math.round((track.current / track.max) * 100) : 0;
              return (
                <div key={i} className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      {track.profession}
                      {viewMode === "profession" && (
                        <span className="ml-1 text-[10px] text-muted-foreground/60">({track.characterName})</span>
                      )}
                    </span>
                    <span>{track.current}/{track.max}</span>
                  </div>
                  <ProgressBar value={percent} />
                </div>
              );
            })}
          </div>
        )}
      </Panel>

      {/* ── Arbre de compétence (MOCK — skill_tree Blizzard non peuplé) ──── */}
      <Panel title="Arbre de competence" subtitle="Noeuds a debloquer" className="md:col-span-4"
        actions={<Badge size="sm">Mock</Badge>}
      >
        <div className="space-y-3">
          {filteredSkillTree.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">Aucun nœud pour cette sélection.</p>
          ) : filteredSkillTree.map((node) => (
            <div key={node.name} className="rounded-md border border-border/60 bg-card/70 px-3 py-2">
              <div className="flex items-center justify-between">
                <p className="text-sm text-foreground">{node.name}</p>
                <Badge size="sm" variant="outline">{node.level}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">{node.detail}</p>
            </div>
          ))}
        </div>
      </Panel>

      {/* ── Matières nécessaires (commandes + objectifs) ──────────────── */}
      <Panel title="Matieres necessaires" subtitle="Reactifs — commandes et objectifs" className="md:col-span-4">
        <div className="h-80 overflow-y-auto pr-1">

        {/* Section commandes */}
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Commandes</p>
        {materialsOrders.length === 0 ? (
          <p className="text-xs text-muted-foreground italic mb-2">
            {filteredOrders.some((o) => o.recipe_id) ? "Chargement des réactifs…" : "Aucune commande avec recette."}
          </p>
        ) : (
          <table className="dense-table mb-2">
            <tbody>
              {materialsOrders.map((mat) => (
                <tr key={mat.item_id}>
                  <td>
                    <a href={`https://www.wowhead.com/fr/item=${mat.item_id}`}
                      target="_blank" rel="noopener noreferrer" className="text-[13px]">
                      {mat.item_name}
                    </a>
                  </td>
                  <td className="text-right text-primary font-medium">{mat.qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <hr className="border-border/40 my-3" />

        {/* Section objectifs */}
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Objectifs</p>
        {materialsGoals.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">
            {filteredGoals.some((g) => g.recipe_id) ? "Chargement des réactifs…" : "Aucun objectif avec recette."}
          </p>
        ) : (
          <table className="dense-table">
            <tbody>
              {materialsGoals.map((mat) => (
                <tr key={mat.item_id}>
                  <td>
                    <a href={`https://www.wowhead.com/fr/item=${mat.item_id}`}
                      target="_blank" rel="noopener noreferrer" className="text-[13px]">
                      {mat.item_name}
                    </a>
                  </td>
                  <td className="text-right text-primary font-medium">{mat.qty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        </div>
      </Panel>

      {/* ── Crafts rentables (MOCK — nécessite données AH niveau 2) ─────── */}
      <Panel title="Crafts rentables" subtitle="Top marges — données AH a venir" className="md:col-span-12"
        actions={<Badge size="sm">Mock</Badge>}
      >
        <table className="dense-table">
          <thead><tr><th>Objet</th><th>Metier</th><th>Marge estimée</th><th>Temps</th></tr></thead>
          <tbody>
            {filteredBestCrafts.map((craft) => (
              <tr key={craft.item}>
                <td className="text-foreground">{craft.item}</td>
                <td>{craft.profession}</td>
                <td className="text-primary">{craft.profit}</td>
                <td>{craft.time}</td>
              </tr>
            ))}
            {filteredBestCrafts.length === 0 && (
              <tr><td colSpan={4} className="text-center text-muted-foreground italic text-xs py-2">Aucune donnée pour cette sélection.</td></tr>
            )}
          </tbody>
        </table>
      </Panel>

    </div>
  );
}

export default CraftingPage;
