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
 *
 * Also throws AnchorMissError when `find` occurs more than once. A plain
 * existence check would let `source.replace(find, insert)` silently pick the
 * first occurrence the moment upstream introduces a second one -- fine for a
 * missing anchor, wrong for an ambiguous one. Several anchors here are short
 * enough (e.g. `"google" | "gitea";`) that a new upstream provider could
 * plausibly duplicate them.
 */
export function applyEdit({ file, find, insert, marker }) {
  const source = readFileSync(file, "utf8");
  if (marker && source.includes(marker)) return false;
  const occurrences = source.split(find).length - 1;
  if (occurrences === 0) {
    throw new AnchorMissError(`anchor not found in ${file}\n  looking for: ${JSON.stringify(find)}`);
  }
  if (occurrences > 1) {
    throw new AnchorMissError(
      `anchor is AMBIGUOUS (${occurrences} occurrences) in ${file}\n  looking for: ${JSON.stringify(find)}`
    );
  }
  // A function replacement (rather than a plain string) avoids String.replace
  // treating $&, $`, $', $1, $$ etc. in `insert` as substitution patterns.
  // No current insert contains one of those sequences, but a future template
  // literal easily could, and this closes the trap for free.
  writeFileSync(file, source.replace(find, () => insert));
  return true;
}
