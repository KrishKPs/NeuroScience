import { useMemo } from "react";
import { useSignatureData } from "./data/useSignatureData";
import { isWebgl2Available } from "./brain/useNiivue";
import { useAppStore } from "./store";
import BrainCanvas from "./brain/BrainCanvas";
import BrainFallback from "./brain/BrainFallback";
import DiseaseSelector from "./panels/DiseaseSelector";
import Controls from "./panels/Controls";
import RegionInspector from "./panels/RegionInspector";
import ValidationPanel from "./panels/ValidationPanel";
import ModelPanel from "./panels/ModelPanel";
import SpecificityMatrix from "./panels/SpecificityMatrix";
import ValidationScatter from "./panels/ValidationScatter";
import Colorbar from "./ui/Colorbar";

/** Frontend.md §11 responsive rule: "≥1200px = full workstation. Tablet =
 * brain on top, panels stack below, scatter last. Mobile = brain + disease
 * switch + a swipeable panel stack." Below the `wide` (1200px) breakpoint
 * this renders a single scrollable column in that same top-to-bottom order
 * instead of a true swipeable carousel — a documented simplification
 * (Frontend.md §16), not a silent gap: a scrollable stack keeps every
 * panel fully functional on mobile, a carousel gesture layer would be a
 * materially bigger feature on its own.
 */
export default function App() {
  const state = useSignatureData();
  const webglAvailable = useMemo(() => isWebgl2Available(), []);
  const overlayMode = useAppStore((s) => s.overlayMode);
  const selectedDisease = useAppStore((s) => s.selectedDisease);

  if (state.status === "loading") {
    return (
      <div className="flex h-full items-center justify-center bg-bg text-ink-muted" aria-live="polite">
        Loading brain model…
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 bg-bg text-center text-ink" role="alert">
        <p>Couldn&apos;t load the results file.</p>
        <p className="text-sm text-ink-muted">Check the data path: {state.message}</p>
      </div>
    );
  }

  const { data, regionIndex } = state;
  const colormap = data.colormaps[overlayMode];

  const brain = (
    <div className="relative h-[50vh] overflow-hidden wide:h-full" aria-label="3D brain viewer region">
      {webglAvailable ? (
        <>
          <BrainCanvas
            data={data}
            regionIndex={regionIndex}
            onNiivueError={(msg) => console.error("NiiVue error:", msg)}
          />
          <Colorbar domain={colormap.domain} units={colormap.units} />
          {/* Text alternative for the WebGL canvas (§11 a11y) — screen
              readers get the same information the visual colorbar carries. */}
          <p className="sr-only" aria-live="polite">
            Showing {data.diseases[selectedDisease].label} {overlayMode} on the 3D brain, colored from{" "}
            {colormap.domain[0].toFixed(2)} to {colormap.domain[1].toFixed(2)} {colormap.units}.
          </p>
        </>
      ) : (
        <BrainFallback data={data} reason="WebGL2 context unavailable in this browser/session." />
      )}
    </div>
  );

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-bg text-ink wide:grid wide:grid-cols-[260px_1fr_320px] wide:grid-rows-[auto_1fr_auto] wide:overflow-hidden">
      <header className="flex items-center justify-between border-b border-hairline px-4 py-2.5 wide:col-span-3">
        <h1 className="text-[15px] font-semibold">neuro-signatures</h1>
        <DiseaseSelector data={data} />
      </header>

      {/* Brain first on narrow screens (§11: "brain on top"); reordered into
          the center column on wide screens via `wide:order-none` + grid
          placement. */}
      <div className="wide:order-none wide:col-start-2 wide:row-start-2 wide:overflow-hidden">{brain}</div>

      <aside className="overflow-y-auto border-hairline wide:col-start-1 wide:row-start-2 wide:border-r">
        <Controls data={data} />
      </aside>

      <aside className="overflow-y-auto border-hairline wide:col-start-3 wide:row-start-2 wide:border-l">
        <RegionInspector data={data} />
        <ValidationPanel data={data} />
        <SpecificityMatrix data={data} />
        <ModelPanel data={data} />
      </aside>

      <footer className="overflow-x-auto border-t border-hairline wide:col-span-3">
        <ValidationScatter data={data} />
      </footer>
    </div>
  );
}
