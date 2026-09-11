import { useEffect, useState } from "react";
import type { RegionIndex, SignatureData } from "./schema";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: SignatureData; regionIndex: RegionIndex };

/** Fetch + schema-sanity-check the §9 JSON (Frontend.md §12 "bad/missing
 * data" state: a direction-giving error, not a raw fetch exception). */
export function useSignatureData(): LoadState {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [dataRes, indexRes] = await Promise.all([
          fetch("/data/signature.json"),
          fetch("/assets/dk_region_index.json"),
        ]);
        if (!dataRes.ok) {
          throw new Error(`/data/signature.json — HTTP ${dataRes.status}`);
        }
        if (!indexRes.ok) {
          throw new Error(`/assets/dk_region_index.json — HTTP ${indexRes.status}`);
        }
        const data = (await dataRes.json()) as SignatureData;
        const regionIndex = (await indexRes.json()) as RegionIndex;

        if (!data.diseases?.PD || !data.diseases?.SCZ || !data.diseases?.AD) {
          throw new Error("signature.json is missing one or more diseases (expected PD, SCZ, AD)");
        }

        if (!cancelled) setState({ status: "ready", data, regionIndex });
      } catch (err) {
        if (!cancelled) {
          setState({
            status: "error",
            message: err instanceof Error ? err.message : "Unknown error loading data",
          });
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
