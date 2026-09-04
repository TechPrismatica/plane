import { readFileSync, writeFileSync } from "node:fs";

export class AnchorMissError extends Error {}

/**
 * Replace `find` with `insert` in `file`, once.
 *
 * Idempotent via `marker`: if the file already contains it, this is a no-op,
 * so re-running after a partial failure is safe.
 *
 * Throws AnchorMissError when `find` is absent. That is the point -- an
 * upstream bump that moves the anchor must break the build loudly rather than
 * quietly produce an image with no Microsoft sign-in button.
 */
export function applyEdit({ file, find, insert, marker }) {
  const source = readFileSync(file, "utf8");
  if (marker && source.includes(marker)) return false;
  if (!source.includes(find)) {
    throw new AnchorMissError(`anchor not found in ${file}\n  looking for: ${JSON.stringify(find)}`);
  }
  writeFileSync(file, source.replace(find, insert));
  return true;
}
