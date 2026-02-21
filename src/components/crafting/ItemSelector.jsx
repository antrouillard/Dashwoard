/**
 * ItemSelector — Combobox de sélection d'objet depuis les recettes Blizzard.
 *
 * Comportement :
 * - Charge les recettes de la profession choisie via l'API backend
 * - Filtre en temps réel
 * - Résout item_id via Blizzard static API → fallback Wowhead search public (pas de credentials)
 * - Affiche lien Wowhead : le script zamimg ajoute icône + couleur rareté + tooltip automatiquement
 * - Affiche les composants (réactifs) avec liens Wowhead iconisés, inspiré de T'asPas1Po
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

// ── Helpers Wowhead ───────────────────────────────────────────────────────────

function refreshWowheadTooltips() {
  setTimeout(() => window.WH?.Tooltips?.refreshLinks?.(), 80);
}

function whUrl(itemId) {
  return `https://www.wowhead.com/fr/item=${itemId}`;
}

// ── Hook : charge les recettes d'une profession ──────────────────────────────

function useProfessionRecipes(professionName) {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(false);
  const cacheRef = useRef({});

  useEffect(() => {
    if (!professionName) { setRecipes([]); return; }
    const key = professionName.toLowerCase().trim();
    if (cacheRef.current[key]) { setRecipes(cacheRef.current[key]); return; }

    let cancelled = false;
    setLoading(true);
    api.crafting.recipes.listByProfession(key)
      .then((data) => {
        if (cancelled) return;
        cacheRef.current[key] = data ?? [];
        setRecipes(data ?? []);
      })
      .catch(() => { if (!cancelled) setRecipes([]); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [professionName]);

  return { recipes, loading };
}

// ── Composant principal ───────────────────────────────────────────────────────

export function ItemSelector({
  profession,
  value,
  onChange,
  onResolving,
  placeholder = "Rechercher une recette…",
  inputClass = "",
}) {
  const [query, setQuery]         = useState(value?.item_name ?? "");
  const [open, setOpen]           = useState(false);
  const [resolving, setResolving] = useState(false);
  const [reagents, setReagents]   = useState([]);
  const containerRef              = useRef(null);

  const { recipes, loading } = useProfessionRecipes(profession);

  const filtered = query.length >= 1
    ? recipes.filter((r) => r.name.toLowerCase().includes(query.toLowerCase())).slice(0, 50)
    : recipes.slice(0, 50);

  // Sync depuis le parent (ex: reset du formulaire)
  useEffect(() => {
    setQuery(value?.item_name ?? "");
    if (!value?.item_name) setReagents([]);
  }, [value?.item_name]);

  // Active les tooltips Wowhead dès que item_id ou reagents sont disponibles
  useEffect(() => {
    if (value?.item_id) refreshWowheadTooltips();
  }, [value?.item_id]);

  useEffect(() => {
    if (reagents.length > 0) refreshWowheadTooltips();
  }, [reagents]);

  // Ferme sur clic extérieur
  useEffect(() => {
    function onOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  const handleSelect = useCallback((recipe) => {
    setQuery(recipe.name);
    setOpen(false);
    setResolving(true);
    setReagents([]);
    onResolving?.(true);
    onChange({ item_name: recipe.name, item_id: null, recipe_id: recipe.recipe_id });

    // Résolution item_id : backend essaie Blizzard static → fallback Wowhead search automatiquement
    api.crafting.recipes.getDetail(recipe.recipe_id, recipe.name)
      .then((detail) => {
        const itemId   = detail?.item_id ?? null;
        const itemName = detail?.item_name || recipe.name;
        const rList    = (detail?.reagents ?? []).filter((r) => r.item_id);
        setReagents(rList);
        onChange({ item_name: itemName, item_id: itemId, recipe_id: recipe.recipe_id });

        // Dernier recours : si item_id toujours null, on cherche directement par nom
        if (!itemId) {
          api.crafting.recipes.searchItem(recipe.name)
            .then((res) => {
              if (res?.item_id) onChange({ item_name: itemName, item_id: res.item_id, recipe_id: recipe.recipe_id });
            })
            .catch(() => {});
        }
      })
      .catch(() => {
        api.crafting.recipes.searchItem(recipe.name)
          .then((res) => {
            if (res?.item_id) onChange({ item_name: recipe.name, item_id: res.item_id, recipe_id: recipe.recipe_id });
          })
          .catch(() => {});
      })
      .finally(() => { setResolving(false); onResolving?.(false); });
  }, [onChange, onResolving]);

  const handleClear = useCallback(() => {
    setQuery(""); setReagents([]); setOpen(false);
    onChange({ item_name: "", item_id: null, recipe_id: null });
  }, [onChange]);

  const handleInputChange = useCallback((e) => {
    const v = e.target.value;
    setQuery(v);
    setOpen(true);
    if (!v) { onChange({ item_name: "", item_id: null, recipe_id: null }); setReagents([]); }
    else onChange({ item_name: v, item_id: null, recipe_id: null });
  }, [onChange]);

  return (
    <div ref={containerRef} className="relative space-y-1.5">

      {/* ── Champ de saisie ── */}
      <div className="flex items-center gap-1">
        <input
          className={`${inputClass} flex-1`}
          value={query}
          onChange={handleInputChange}
          onFocus={() => setOpen(true)}
          placeholder={loading ? "Chargement des recettes…" : placeholder}
          autoComplete="off"
        />
        {query && (
          <button type="button" onClick={handleClear}
            className="shrink-0 text-muted-foreground hover:text-foreground text-xs px-1.5"
            title="Effacer">✕</button>
        )}
      </div>

      {/* ── Résolution en cours ── */}
      {resolving && (
        <p className="text-[10px] text-muted-foreground animate-pulse">Résolution de l'objet…</p>
      )}

      {/* ── Lien Wowhead + composants ── */}
      {/* Le script zamimg (colorLinks+iconizeLinks) détecte les href wowhead.com et ajoute */}
      {/* automatiquement : icône à gauche, couleur de rareté, tooltip au survol.            */}
      {!resolving && value?.item_id && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <a
            key={value.item_id}
            href={whUrl(value.item_id)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs hover:underline"
          >
            {value.item_name}
          </a>

          {reagents.length > 0 && (
            <>
              <span className="text-[10px] text-muted-foreground/40">·</span>
              <span className="text-[10px] text-muted-foreground/60">Composants :</span>
              {reagents.map((r, i) => (
                <a
                  key={i}
                  href={whUrl(r.item_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] hover:underline"
                  title={r.item_name ?? ""}
                >
                  ×{r.quantity}
                </a>
              ))}
            </>
          )}
        </div>
      )}

      {/* ── Dropdown ── */}
      {open && !loading && filtered.length > 0 && (
        <ul className="absolute z-50 left-0 right-0 top-full mt-0.5 max-h-56 overflow-y-auto rounded-md border border-border/80 bg-card shadow-xl">
          {filtered.map((recipe) => (
            <li key={recipe.recipe_id}>
              <button
                type="button"
                className="w-full px-3 py-1.5 text-left text-xs text-foreground hover:bg-primary/10 flex items-baseline justify-between gap-2"
                onMouseDown={(e) => { e.preventDefault(); handleSelect(recipe); }}
              >
                <span>{recipe.name}</span>
                {recipe.category && (
                  <span className="text-[10px] text-muted-foreground shrink-0">{recipe.category}</span>
                )}
              </button>
            </li>
          ))}
          {recipes.length > 50 && query.length < 1 && (
            <li className="px-3 py-1 text-[10px] text-muted-foreground italic text-center">
              {recipes.length - 50} autres — affinez la recherche
            </li>
          )}
        </ul>
      )}

      {open && !loading && filtered.length === 0 && query.length >= 2 && (
        <div className="absolute z-50 left-0 right-0 top-full mt-0.5 rounded-md border border-border/80 bg-card px-3 py-2 text-xs text-muted-foreground shadow-xl">
          Aucune recette trouvée pour « {query} »
        </div>
      )}

      {open && !loading && recipes.length === 0 && !query && (
        <div className="absolute z-50 left-0 right-0 top-full mt-0.5 rounded-md border border-border/80 bg-card px-3 py-2 text-xs text-muted-foreground shadow-xl">
          Aucune recette disponible pour ce métier.<br />Saisie libre possible.
        </div>
      )}
    </div>
  );
}