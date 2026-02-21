import { useCallback } from "react";
import { api } from "@/lib/api";
import { useQuery, useMutation } from "@/hooks/useApi";

// ── Comptes ───────────────────────────────────────────────────────────────────
export function useDefaultAccount() {
  return useQuery(() => api.accounts.getDefault());
}

export function useAccounts() {
  return useQuery(() => api.accounts.list());
}

// ── Personnages ───────────────────────────────────────────────────────────────
export function useCharacters(accountId) {
  return useQuery(
    () => (accountId ? api.characters.list(accountId) : Promise.resolve(null)),
    [accountId]
  );
}

export function useCreateCharacter(onSuccess) {
  const { mutate, loading, error } = useMutation((data) => api.characters.create(data));
  return {
    createCharacter: async (data) => {
      const result = await mutate(data);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useDeleteCharacter(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.characters.delete(id));
  return {
    deleteCharacter: async (id) => {
      await mutate(id);
      onSuccess?.();
    },
    loading,
    error,
  };
}

// ── Todos ─────────────────────────────────────────────────────────────────────
export function useTodos(characterId) {
  return useQuery(() => api.todos.list(characterId), [characterId]);
}

export function useAllTodos() {
  return useQuery(() => api.todos.list());
}

export function useAdvanceTodo(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.todos.advance(id));
  return {
    advanceTodo: async (id) => {
      const result = await mutate(id);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useCreateTodo(onSuccess) {
  const { mutate, loading, error } = useMutation((data) => api.todos.create(data));
  return {
    createTodo: async (data) => {
      const result = await mutate(data);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useDeleteTodo(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.todos.delete(id));
  return {
    deleteTodo: async (id) => {
      await mutate(id);
      onSuccess?.();
    },
    loading,
    error,
  };
}

// ── Guildes ───────────────────────────────────────────────────────────────────
export function useGuilds() {
  return useQuery(() => api.guilds.list());
}

// ── Auth Blizzard ─────────────────────────────────────────────────────────────
export function useAuthStatus(accountId) {
  return useQuery(
    () => (accountId ? api.auth.status(accountId) : Promise.resolve(null)),
    [accountId]
  );
}

export function useBlizzardLogin() {
  const { mutate, loading, error } = useMutation((accountId) => {
    // Redirige le navigateur vers le flow OAuth Blizzard
    window.location.href = api.auth.loginUrl(accountId);
    return Promise.resolve();
  });
  return { login: mutate, loading, error };
}

// ── Sync ──────────────────────────────────────────────────────────────────────
export function useSyncAccount(onSuccess) {
  const { mutate, loading, error } = useMutation(async (accountId) => {
    // Lance Blizzard + Raider.io en parallèle
    const [blizzard, raiderio] = await Promise.allSettled([
      api.sync.account(accountId),
      api.sync.raiderioAccount(accountId),
    ]);
    return {
      blizzard: blizzard.status === "fulfilled" ? blizzard.value : null,
      raiderio: raiderio.status === "fulfilled" ? raiderio.value : null,
      synced: blizzard.value?.synced ?? 0,
      total: blizzard.value?.total ?? 0,
    };
  });
  return {
    syncAccount: async (accountId) => {
      const result = await mutate(accountId);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

// ── Weekly ────────────────────────────────────────────────────────────────────
export function useWeeklyInfo() {
  return useQuery(() => api.weekly.info());
}

export function useWeekly(characterId, week) {
  return useQuery(
    () => api.weekly.list(characterId, week),
    [characterId, week]
  );
}

export function useAdvanceWeekly(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.weekly.advance(id));
  return {
    advanceWeekly: async (id) => {
      const result = await mutate(id);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useCreateWeekly(onSuccess) {
  const { mutate, loading, error } = useMutation((data) => api.weekly.create(data));
  return {
    createWeekly: async (data) => {
      const result = await mutate(data);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

// ── Crafting — commandes ──────────────────────────────────────────────────────

export function useCraftingOrders(filters = {}) {
  return useQuery(() => api.crafting.orders.list(filters), [
    filters.character_id,
    filters.profession,
    filters.status,
  ]);
}

export function useCreateCraftingOrder(onSuccess) {
  const { mutate, loading, error } = useMutation((data) => api.crafting.orders.create(data));
  return {
    createOrder: async (data) => {
      const result = await mutate(data);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useAdvanceCraftingOrder(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.crafting.orders.advance(id));
  return {
    advanceOrder: async (id) => {
      const result = await mutate(id);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useDeleteCraftingOrder(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.crafting.orders.delete(id));
  return {
    deleteOrder: async (id) => {
      await mutate(id);
      onSuccess?.();
    },
    loading,
    error,
  };
}

// ── Crafting — objectifs ──────────────────────────────────────────────────────

export function useCraftingGoals(filters = {}) {
  return useQuery(() => api.crafting.goals.list(filters), [
    filters.character_id,
    filters.profession,
  ]);
}

export function useCreateCraftingGoal(onSuccess) {
  const { mutate, loading, error } = useMutation((data) => api.crafting.goals.create(data));
  return {
    createGoal: async (data) => {
      const result = await mutate(data);
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useUpdateCraftingGoal(onSuccess) {
  const { mutate, loading, error } = useMutation(({ id, data }) =>
    api.crafting.goals.update(id, data)
  );
  return {
    updateGoal: async (id, data) => {
      const result = await mutate({ id, data });
      onSuccess?.(result);
      return result;
    },
    loading,
    error,
  };
}

export function useDeleteCraftingGoal(onSuccess) {
  const { mutate, loading, error } = useMutation((id) => api.crafting.goals.delete(id));
  return {
    deleteGoal: async (id) => {
      await mutate(id);
      onSuccess?.();
    },
    loading,
    error,
  };
}
