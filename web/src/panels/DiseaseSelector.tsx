import { useAppStore } from "../store";
import type { DiseaseCode, SignatureData } from "../data/schema";

const ORDER: DiseaseCode[] = ["PD", "SCZ", "AD"];

interface Props {
  data: SignatureData;
}

/** Frontend.md §6.1 — the global driver. A proper radio group (§11 a11y:
 * "segmented control is a proper radio group"), arrow keys move selection. */
export default function DiseaseSelector({ data }: Props) {
  const selected = useAppStore((s) => s.selectedDisease);
  const setDisease = useAppStore((s) => s.setDisease);

  function handleKeyDown(e: React.KeyboardEvent) {
    const idx = ORDER.indexOf(selected);
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      setDisease(ORDER[(idx + 1) % ORDER.length]);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      setDisease(ORDER[(idx - 1 + ORDER.length) % ORDER.length]);
    }
  }

  return (
    <div role="radiogroup" aria-label="Disease" className="flex gap-1" onKeyDown={handleKeyDown}>
      {ORDER.map((code) => (
        <button
          key={code}
          role="radio"
          aria-checked={selected === code}
          tabIndex={selected === code ? 0 : -1}
          onClick={() => setDisease(code)}
          className={`rounded px-3 py-1.5 text-[13px] transition-colors ${
            selected === code
              ? "bg-accent text-white"
              : "text-ink-muted hover:text-ink"
          }`}
        >
          {data.diseases[code].label}
        </button>
      ))}
    </div>
  );
}
