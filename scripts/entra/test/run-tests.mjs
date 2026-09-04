import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { applyEdit, AnchorMissError } from "../anchors.mjs";

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

console.log("codemod harness: 3 passed");
