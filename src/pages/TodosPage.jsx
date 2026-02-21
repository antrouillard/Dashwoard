import { useState, useMemo, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/warcraftcn/badge";
import { Button } from "@/components/ui/warcraftcn/button";
import { Skeleton } from "@/components/ui/warcraftcn/skeleton";
import {
  useDefaultAccount,
  useCharacters,
  useAllTodos,
  useAdvanceTodo,
  useCreateTodo,
  useDeleteTodo,
  useWeekly,
} from "@/hooks/useWow";

// Activités WoW récurrentes — suggestions rapides
const ACTIVITY_PRESETS = [
  "Vault M+",
  "Vault Raid",
  "Catalyseur",
  "World Boss",
  "Quêtes de métier",
  "Évènement hebdo",
  "Clé mythique +",
  "PvP hebdo",
  "Îles interdites",
  "Donjon héroïque x8",
];

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_LABEL = { a_faire: "À faire", en_cours: "En cours", termine: "Terminé" };
const STATUS_FILTERS = ["tous", "a_faire", "en_cours", "termine"];

const statusBadge = (status) => {
  switch (status) {
    case "termine":
      return { variant: "default", className: "text-emerald-100 border-emerald-500/40 bg-emerald-500/10" };
    case "en_cours":
      return { variant: "secondary", className: "text-amber-100 border-amber-500/40 bg-amber-500/10" };
    default:
      return { variant: "outline", className: "text-slate-300" };
  }
};

// ── Components ────────────────────────────────────────────────────────────────

function TodoRow({ todo, ownerName, onAdvance, onDelete }) {
  const [confirmDel, setConfirmDel] = useState(false);
  const badge = statusBadge(todo.status);

  return (
    <div className="flex items-center gap-3 rounded border border-border/20 bg-background/30 px-3 py-2 hover:bg-background/50 transition-colors">
      {/* Statut cliquable */}
      <button
        onClick={() => onAdvance(todo.id)}
        className="shrink-0"
        title="Changer le statut"
      >
        <Badge
          variant={badge.variant}
          className={`text-[10px] w-20 justify-center cursor-pointer ${badge.className}`}
        >
          {STATUS_LABEL[todo.status] ?? todo.status}
        </Badge>
      </button>

      {/* Contenu */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm truncate ${todo.status === "termine" ? "line-through text-muted-foreground" : "text-foreground"}`}>
          {todo.title}
        </p>
        {todo.description && (
          <p className="text-[10px] text-muted-foreground truncate">{todo.description}</p>
        )}
      </div>

      {/* Perso */}
      <span className="text-xs text-muted-foreground shrink-0 hidden sm:block">{ownerName}</span>

      {/* Priorité */}
      {todo.priority > 1 && (
        <span className="text-[10px] text-amber-400 shrink-0">P{todo.priority}</span>
      )}

      {/* Supprimer */}
      {!confirmDel ? (
        <button
          onClick={() => setConfirmDel(true)}
          className="text-muted-foreground hover:text-destructive text-xs shrink-0 w-5 text-center"
        >
          ✕
        </button>
      ) : (
        <span className="flex gap-1 shrink-0 text-[10px]">
          <button onClick={() => onDelete(todo.id)} className="text-destructive hover:underline">Suppr.</button>
          <button onClick={() => setConfirmDel(false)} className="text-muted-foreground hover:underline">Ann.</button>
        </span>
      )}
    </div>
  );
}

function AddTodoForm({ characters, weeklyActivities = [], initialTitle = "", onCreated }) {
  const [mode, setMode] = useState(initialTitle ? "free" : "preset");
  const [form, setForm] = useState({
    title: initialTitle,
    description: "",
    character_id: "",
    priority: 1,
  });
  const { createTodo, loading } = useCreateTodo(onCreated);

  // Si un titre initial arrive depuis l'URL, on passe en mode libre
  useEffect(() => {
    if (initialTitle) {
      setMode("free");
      setForm((f) => ({ ...f, title: initialTitle }));
    }
  }, [initialTitle]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // Sélection d'une activité hebdo (API) → auto-fill titre + personnage
  const handlePresetSelect = (e) => {
    const value = e.target.value;
    // Cherche si c'est une activité hebdo avec character_id
    const match = weeklyActivities.find(
      (a) => `${a.activity_type} — ${a.character_name}` === value
    );
    if (match) {
      setForm((f) => ({
        ...f,
        title: match.activity_type,
        character_id: String(match.character_id),
      }));
    } else {
      setForm((f) => ({ ...f, title: value === "" ? "" : value }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.character_id) return;
    await createTodo({
      title: form.title.trim(),
      description: form.description.trim() || undefined,
      character_id: parseInt(form.character_id, 10),
      priority: parseInt(form.priority, 10),
      status: "a_faire",
    });
    setForm({ title: "", description: "", character_id: form.character_id, priority: 1 });
  };

  return (
    <form onSubmit={handleSubmit} className="panel-frame">
      <div className="panel-header">
        <p className="panel-title">Ajouter une tâche</p>
      </div>
      <div className="panel-body space-y-3">
        {/* Toggle source */}
        <div className="flex rounded border border-border/30 overflow-hidden text-[10px]">
          <button
            type="button"
            onClick={() => setMode("preset")}
            className={`flex-1 px-2 py-1 transition-colors ${
              mode === "preset" ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Activité prédéfinie
          </button>
          <button
            type="button"
            onClick={() => setMode("free")}
            className={`flex-1 px-2 py-1 transition-colors ${
              mode === "free" ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Texte libre
          </button>
        </div>

        {/* Sélection activité ou texte libre */}
        {mode === "preset" ? (
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Activité</label>
            <select
              value={form.title}
              onChange={handlePresetSelect}
              required
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              <option value="">Choisir une activité...</option>
              {weeklyActivities.length > 0 && (
                <optgroup label="── Activités de la semaine">
                  {weeklyActivities.map((a, i) => (
                    <option
                      key={`weekly-${i}`}
                      value={`${a.activity_type} — ${a.character_name}`}
                    >
                      {a.activity_type} — {a.character_name}
                    </option>
                  ))}
                </optgroup>
              )}
              <optgroup label="── Activités courantes">
                {ACTIVITY_PRESETS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </optgroup>
            </select>
          </div>
        ) : (
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Titre</label>
            <input
              value={form.title}
              onChange={set("title")}
              placeholder="Faire le weekly M+"
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
              required
            />
          </div>
        )}

        <div>
          <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Description (optionnel)</label>
          <input
            value={form.description}
            onChange={set("description")}
            placeholder="Détails..."
            className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Personnage</label>
            <select
              value={form.character_id}
              onChange={set("character_id")}
              required
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              <option value="">Choisir...</option>
              {(characters ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Priorité</label>
            <select
              value={form.priority}
              onChange={set("priority")}
              className="mt-1 w-full rounded border border-border/40 bg-background/60 px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              <option value={1}>Normale</option>
              <option value={2}>Haute</option>
              <option value={3}>Urgente</option>
            </select>
          </div>
        </div>

        <Button type="submit" disabled={loading} className="w-full">
          {loading ? "Ajout..." : "Ajouter la tâche"}
        </Button>
      </div>
    </form>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function TodosPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("tous");
  const [charFilter, setCharFilter] = useState("tous");

  // Titre pré-rempli via URL (?title=...)
  const urlTitle = useMemo(() => {
    const p = new URLSearchParams(location.search);
    return p.get("title") ?? "";
  }, [location.search]);

  // Nettoie l'URL après lecture
  useEffect(() => {
    if (urlTitle) {
      navigate("/todos", { replace: true });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: account } = useDefaultAccount();
  const { data: characters } = useCharacters(account?.id);
  const { data: todos, loading, refetch } = useAllTodos();

  // Activités de la semaine courante — enrichies avec le nom du perso
  const { data: weeklyData } = useWeekly(null);
  const weeklyActivities = useMemo(() => {
    const activities = weeklyData?.activities ?? [];
    return activities.map((a) => ({
      ...a,
      character_name: characters?.find((c) => c.id === a.character_id)?.name ?? `Perso #${a.character_id}`,
    }));
  }, [weeklyData, characters]);

  const { advanceTodo } = useAdvanceTodo(refetch);
  const { deleteTodo } = useDeleteTodo(refetch);

  // Enrichit les todos avec le nom du perso
  const enriched = useMemo(() => {
    if (!todos) return [];
    return todos.map((t) => ({
      ...t,
      ownerName: characters?.find((c) => c.id === t.character_id)?.name ?? "—",
    }));
  }, [todos, characters]);

  // Filtrage
  const filtered = useMemo(() => {
    return enriched.filter((t) => {
      if (statusFilter !== "tous" && t.status !== statusFilter) return false;
      if (charFilter !== "tous" && String(t.character_id) !== charFilter) return false;
      return true;
    });
  }, [enriched, statusFilter, charFilter]);

  // Stats
  const stats = useMemo(() => {
    const total = enriched.length;
    const done = enriched.filter((t) => t.status === "termine").length;
    const inProgress = enriched.filter((t) => t.status === "en_cours").length;
    const todo = enriched.filter((t) => t.status === "a_faire").length;
    return { total, done, inProgress, todo };
  }, [enriched]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl text-foreground">Todos</h2>
          <p className="text-sm text-muted-foreground">
            {stats.done}/{stats.total} tâches terminées
            {stats.inProgress > 0 && ` · ${stats.inProgress} en cours`}
          </p>
        </div>

        {/* Barre de progression */}
        {stats.total > 0 && (
          <div className="w-40 h-1.5 rounded-full bg-border/30 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${(stats.done / stats.total) * 100}%` }}
            />
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-4">
          {/* Filtres */}
          <div className="flex flex-wrap gap-2">
            {/* Filtre statut */}
            <div className="flex rounded border border-border/30 overflow-hidden">
              {STATUS_FILTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1 text-xs transition-colors ${
                    statusFilter === s
                      ? "bg-primary/20 text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {s === "tous" ? "Tous" : STATUS_LABEL[s]}
                </button>
              ))}
            </div>

            {/* Filtre perso */}
            <select
              value={charFilter}
              onChange={(e) => setCharFilter(e.target.value)}
              className="rounded border border-border/30 bg-background/60 px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            >
              <option value="tous">Tous les persos</option>
              {(characters ?? []).map((c) => (
                <option key={c.id} value={String(c.id)}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Liste */}
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded border border-border/20 bg-background/20 py-8 text-center text-sm text-muted-foreground">
              {enriched.length === 0 ? "Aucune tâche. Ajoutes-en une à droite." : "Aucune tâche correspondant aux filtres."}
            </div>
          ) : (
            <div className="space-y-1.5">
              {filtered.map((todo) => (
                <TodoRow
                  key={todo.id}
                  todo={todo}
                  ownerName={todo.ownerName}
                  onAdvance={advanceTodo}
                  onDelete={deleteTodo}
                />
              ))}
            </div>
          )}
        </div>

        {/* Formulaire d'ajout */}
        <div>
          <AddTodoForm
            characters={characters}
            weeklyActivities={weeklyActivities}
            initialTitle={urlTitle}
            onCreated={refetch}
          />
        </div>
      </div>
    </div>
  );
}
