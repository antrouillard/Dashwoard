/**
 * Client HTTP centralisé pour l'API FastAPI.
 * Toutes les fonctions retournent des données JSON déjà parsées.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
// Racine du serveur (sans /api) — pour les routes /auth/* montées hors préfixe
const SERVER_URL = BASE_URL.replace(/\/api$/, "");

async function request(pathOrUrl, options = {}) {
  const url = pathOrUrl.startsWith("http") ? pathOrUrl : `${BASE_URL}${pathOrUrl}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }

  // 204 No Content → pas de body
  if (res.status === 204) return null;
  return res.json();
}

// ── Comptes ──────────────────────────────────────────────────────────────────
export const api = {
  accounts: {
    list: () => request("/accounts"),
    getDefault: () => request("/accounts/default"),
    get: (id) => request(`/accounts/${id}`),
    create: (data) => request("/accounts", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) => request(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id) => request(`/accounts/${id}`, { method: "DELETE" }),
  },

  // ── Personnages ────────────────────────────────────────────────────────────
  characters: {
    list: (accountId) =>
      request(`/characters${accountId ? `?account_id=${accountId}` : ""}`),
    get: (id) => request(`/characters/${id}`),
    create: (data) => request("/characters", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) =>
      request(`/characters/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id) => request(`/characters/${id}`, { method: "DELETE" }),
  },

  // ── Todos ──────────────────────────────────────────────────────────────────
  todos: {
    list: (characterId) =>
      request(`/todos${characterId ? `?character_id=${characterId}` : ""}`),
    create: (data) => request("/todos", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) =>
      request(`/todos/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    advance: (id) => request(`/todos/${id}/advance`, { method: "PATCH" }),
    delete: (id) => request(`/todos/${id}`, { method: "DELETE" }),
  },

  // ── Guildes ────────────────────────────────────────────────────────────────
  guilds: {
    list: () => request("/guilds"),
    get: (id) => request(`/guilds/${id}`),
    create: (data) => request("/guilds", { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) =>
      request(`/guilds/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id) => request(`/guilds/${id}`, { method: "DELETE" }),
  },

  // ── Sync Blizzard ──────────────────────────────────────────────────────────
  sync: {
    account: (accountId) => request(`/sync/account/${accountId}`, { method: "POST" }),
    character: (characterId) => request(`/sync/character/${characterId}`, { method: "POST" }),
    raiderioAccount: (accountId) => request(`/sync/raiderio/account/${accountId}`, { method: "POST" }),
    raiderioCharacter: (characterId) => request(`/sync/raiderio/character/${characterId}`, { method: "POST" }),
  },

  // ── Weekly ────────────────────────────────────────────────────────────
  weekly: {
    list: (characterId, week) =>
      request(`/weekly${characterId ? `?character_id=${characterId}` : ""}${week ? `${characterId ? "&" : "?"}week=${week}` : ""}` ),
    info: () => request("/weekly/info"),
    create: (data) => request("/weekly", { method: "POST", body: JSON.stringify(data) }),
    advance: (id) => request(`/weekly/${id}/advance`, { method: "PATCH" }),
    update: (id, data) => request(`/weekly/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id) => request(`/weekly/${id}`, { method: "DELETE" }),
  },

  // ── Crafting ───────────────────────────────────────────────────────────────
  crafting: {
    orders: {
      list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.character_id) params.set("character_id", filters.character_id);
        if (filters.profession) params.set("profession", filters.profession);
        if (filters.status) params.set("status", filters.status);
        const qs = params.toString();
        return request(`/crafting/orders${qs ? `?${qs}` : ""}`);
      },
      get: (id) => request(`/crafting/orders/${id}`),
      create: (data) => request("/crafting/orders", { method: "POST", body: JSON.stringify(data) }),
      update: (id, data) => request(`/crafting/orders/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
      advance: (id) => request(`/crafting/orders/${id}/advance`, { method: "PATCH" }),
      delete: (id) => request(`/crafting/orders/${id}`, { method: "DELETE" }),
    },
    goals: {
      list: (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.character_id) params.set("character_id", filters.character_id);
        if (filters.profession) params.set("profession", filters.profession);
        const qs = params.toString();
        return request(`/crafting/goals${qs ? `?${qs}` : ""}`);
      },
      get: (id) => request(`/crafting/goals/${id}`),
      create: (data) => request("/crafting/goals", { method: "POST", body: JSON.stringify(data) }),
      update: (id, data) => request(`/crafting/goals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
      delete: (id) => request(`/crafting/goals/${id}`, { method: "DELETE" }),
      // Quantités posssédées par réactif (persistance DB)
      reagents: () => request("/crafting/goals/reagents"),
      saveReagent: (goalId, itemId, haveQty) =>
        request(`/crafting/goals/${goalId}/reagents/${itemId}`, {
          method: "PATCH",
          body: JSON.stringify({ have_qty: haveQty }),
        }),
    },
    recipes: {
      listByProfession: (professionName) =>
        request(`/crafting/professions/${encodeURIComponent(professionName.toLowerCase())}/recipes`),
      // item_name optionnel : permet le fallback Wowhead côté backend si Blizzard static indispo
      getDetail: (recipeId, itemName) => {
        const qs = itemName ? `?item_name=${encodeURIComponent(itemName)}` : "";
        return request(`/crafting/recipes/${recipeId}${qs}`);
      },
      // Charge tout le cache DB en une seule requête (montée du composant)
      loadCache: () => request("/crafting/recipes/cache"),
      // Recherche Wowhead directe (publique, sans credentials Blizzard)
      searchItem: (name) => request(`/crafting/search-item?q=${encodeURIComponent(name)}`),
    },
    backfillItemIds: () => request("/crafting/backfill-item-ids", { method: "POST" }),
    admin: {
      truncate: () => request("/crafting/admin/truncate", { method: "DELETE" }),
      clearRecipeCache: () => request("/crafting/admin/clear-recipe-cache", { method: "POST" }),
      debugRecipeRaw: (recipeId) => request(`/crafting/debug/recipe-raw/${recipeId}`),
    },
  },

  // ── Auth Blizzard ──────────────────────────────────────────────────────────
  // loginUrl déclenche une navigation navigateur, pas un fetch
  auth: {
    loginUrl: (accountId) => `${SERVER_URL}/auth/login?account_id=${accountId}`,
    status: (accountId) => request(`${SERVER_URL}/auth/status/${accountId}`),
    logout: (accountId) => request(`${SERVER_URL}/auth/logout/${accountId}`, { method: "DELETE" }),
  },
};
