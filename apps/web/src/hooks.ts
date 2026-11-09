import { useEffect, useState, useCallback } from "react";
import { request } from "./api";
export function useResource<T>(path: string, epoch = 0) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const [reloadId, setReload] = useState(0);
  const reload = useCallback(() => setReload((v) => v + 1), []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setData(null);
    request<T>(path)
      .then((v) => {
        if (active) setData(v);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, epoch, reloadId]);
  return { data, error, loading, reload };
}
