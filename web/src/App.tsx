import { useMemo } from "react";
import { useSignatureData } from "./data/useSignatureData";
import { isWebgl2Available } from "./brain/useNiivue";
import BrainCanvas from "./brain/BrainCanvas";
import BrainFallback from "./brain/BrainFallback";
import DiseaseSelector from "./panels/DiseaseSelector";
import Controls from "./panels/Controls";
import RegionInspector from "./panels/RegionInspector";
import ValidationPanel from "./panels/ValidationPanel";
import ModelPanel from "./panels/ModelPanel";
import SpecificityMatrix from "./panels/SpecificityMatrix";
import ValidationScatter from "./panels/ValidationScatter";

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

  const { data, regionIndex } = state;

  return (
    <div className="grid h-full grid-cols-[260px_1fr_320px] grid-rows-[auto_1fr_auto] bg-bg text-ink">
      {/* Top bar: title + disease switch (§3.6). */}
      <header className="col-span-3 flex items-center justify-between border-b border-hairline px-4 py-2.5">
        <h1 className="text-[15px] font-semibold">neuro-signatures</h1>
        <DiseaseSelector data={data} />
      </header>

      {/* Left: controls. */}
      <aside className="overflow-y-auto border-r border-hairline">
        <Controls data={data} />
      </aside>

      {/* Center: the brain — the hero. */}
      <main className="relative overflow-hidden">
        {webglAvailable ? (
          <BrainCanvas
            data={data}
            regionIndex={regionIndex}
            onNiivueError={(msg) => console.error("NiiVue error:", msg)}
          />
        ) : (
          <BrainFallback data={data} reason="WebGL2 context unavailable in this browser/session." />
        )}
      </main>

      {/* Right rail: readouts (§6). */}
      <aside className="overflow-y-auto border-l border-hairline">
        <RegionInspector data={data} />
        <ValidationPanel data={data} />
        <SpecificityMatrix data={data} />
        <ModelPanel data={data} />
      </aside>

      {/* Bottom strip: validation scatter, full width, linked. */}
      <footer className="col-span-3 overflow-x-auto border-t border-hairline">
        <ValidationScatter data={data} />
      </footer>
    </div>
  );
}
