import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { applyEdit, AnchorMissError } from "../anchors.mjs";
import { edits } from "../apply-frontend.mjs";

const dir = mkdtempSync(join(tmpdir(), "entra-codemod-"));
const file = join(dir, "sample.ts");
const original = `export type T =\n  | "google"\n  | "gitea";\n`;

// 1. inserts after the anchor
writeFileSync(file, original);
applyEdit({ file, find: `  | "gitea";`, insert: `  | "gitea"\n  | "microsoft";`, marker: "microsoft" });
assert.match(readFileSync(file, "utf8"), /\| "microsoft";/);

// 2. idempotent -- second run changes nothing
const afterFirst = readFileSync(file, "utf8");
applyEdit({ file, find: `  | "gitea";`, insert: `  | "gitea"\n  | "microsoft";`, marker: "microsoft" });
assert.equal(readFileSync(file, "utf8"), afterFirst, "second run must be a no-op");

// 3. a missing anchor throws AnchorMissError naming the file
writeFileSync(file, original);
assert.throws(
  () => applyEdit({ file, find: `NOT PRESENT`, insert: "x", marker: "zzz" }),
  (e) => e instanceof AnchorMissError && e.message.includes("sample.ts"),
);

// 4. invariant: within a single file, no edit's marker may be a substring of
// any *other* edit's insert. If it is, that other edit's insert makes this
// edit's idempotency check look satisfied even when its own find/insert has
// never run -- so it silently, permanently no-ops the moment the other edit
// runs first. This makes the class of bug fixed for edit 0 (vs edit 5) and
// edit 2 (vs edit 3) in apply-frontend.mjs structurally impossible to
// reintroduce, whatever order edits end up in or however many are added.
{
  const violations = [];
  for (let i = 0; i < edits.length; i++) {
    for (let j = 0; j < edits.length; j++) {
      if (i === j) continue;
      if (edits[i].file !== edits[j].file) continue;
      if (!edits[i].marker) continue;
      if (edits[j].insert.includes(edits[i].marker)) {
        violations.push(
          `edit ${i}'s marker ${JSON.stringify(edits[i].marker)} is a substring of edit ${j}'s insert ` +
            `(file: ${edits[i].file})`
        );
      }
    }
  }
  assert.equal(
    violations.length,
    0,
    `marker/insert collisions found -- these edits will silently skip once run out of order:\n${violations.join("\n")}`
  );
}

console.log("codemod harness: 4 passed");
