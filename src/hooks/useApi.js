import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Hook générique pour les requêtes GET.
 * Retourne { data, loading, error, refetch }.
 *
 * @param {() => Promise<any>} fetcher  Fonction qui appelle l'API
 * @param {any[]} deps  Dépendances qui déclenchent un refetch
 */
export function useQuery(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current();
      setData(result);
    } catch (err) {
      setError(err.message ?? "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { data, loading, error, refetch: run };
}

/**
 * Hook générique pour les mutations (POST / PATCH / DELETE).
 * Retourne { mutate, loading, error }.
 *
 * @param {(args: any) => Promise<any>} mutationFn
 */
export function useMutation(mutationFn) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mutationFnRef = useRef(mutationFn);
  mutationFnRef.current = mutationFn;

  const mutate = useCallback(async (args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await mutationFnRef.current(args);
      return result;
    } catch (err) {
      setError(err.message ?? "Erreur inconnue");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []); // stable — mutationFnRef.current toujours à jour

  return { mutate, loading, error };
}
