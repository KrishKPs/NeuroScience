import { useMemo } from "react";
import { useSignatureData } from "./data/useSignatureData";
import { isWebgl2Available } from "./brain/useNiivue";
import BrainCanvas from "./brain/BrainCanvas";
import BrainFallback from "./brain/BrainFallback";

export default function App() {
  const state = useSignatureData();
  const webglAvailable = useMemo(() => isWebgl2Available(), []);

  if (state.status === "loading") {
    return (
      <div className="flex h-full items-center justify-center bg-bg text-ink-muted">
        Loading brain model…
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 bg-bg text-center text-ink">
        <p>Couldn&apos;t load the results file.</p>
        <p className="text-sm text-ink-muted">Check the data path: {state.message}</p>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-bg text-ink">
      {webglAvailable ? (
        <BrainCanvas
          data={state.data}
          regionIndex={state.regionIndex}
          onNiivueError={(msg) => console.error("NiiVue error:", msg)}
        />
      ) : (
        <BrainFallback data={state.data} reason="WebGL2 context unavailable in this browser/session." />
      )}
    </div>
  );
}
