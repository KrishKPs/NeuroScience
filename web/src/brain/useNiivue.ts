/** WebGL2 detection, separate from mounting NiiVue itself — NiiVue is
 * WebGL2-only (its own description: "minimal webgl2 nifti image viewer"),
 * and development hit a browser/session where WebGL was
 * disabled entirely. Detect before attempting to construct a Niivue
 * instance so the fallback is a clean branch, not a
 * caught exception from deep inside the library. */
export function isWebgl2Available(): boolean {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2");
    return !!gl;
  } catch {
    return false;
  }
}
