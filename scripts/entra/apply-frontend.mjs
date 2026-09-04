import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { applyEdit, AnchorMissError } from "./anchors.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const p = (rel) => resolve(root, rel);

const edits = [
  {
    file: p("packages/types/src/instance/auth.ts"),
    find: `  | "gitea";\n\nexport type TInstanceAuthenticationModeKeys`,
    insert: `  | "gitea"\n  | "microsoft";\n\nexport type TInstanceAuthenticationModeKeys`,
    marker: `| "microsoft";`,
  },
  {
    file: p("packages/types/src/instance/auth.ts"),
    find: `  | "IS_GITEA_ENABLED";`,
    insert: `  | "IS_GITEA_ENABLED"\n  | "IS_MICROSOFT_ENABLED";`,
    marker: "IS_MICROSOFT_ENABLED",
  },
  {
    file: p("packages/types/src/instance/auth.ts"),
    find: `export type TInstanceAuthenticationConfigurationKeys =`,
    insert:
      `export type TInstanceMicrosoftAuthenticationConfigurationKeys =\n` +
      `  | "MICROSOFT_CLIENT_ID"\n  | "MICROSOFT_CLIENT_SECRET"\n` +
      `  | "MICROSOFT_TENANT_ID"\n  | "ENABLE_MICROSOFT_SYNC";\n\n` +
      `export type TInstanceAuthenticationConfigurationKeys =`,
    marker: "TInstanceMicrosoftAuthenticationConfigurationKeys",
  },
  {
    file: p("packages/types/src/instance/auth.ts"),
    find: `  | TInstanceGiteaAuthenticationConfigurationKeys;`,
    insert:
      `  | TInstanceGiteaAuthenticationConfigurationKeys\n` +
      `  | TInstanceMicrosoftAuthenticationConfigurationKeys;`,
    marker: "| TInstanceMicrosoftAuthenticationConfigurationKeys;",
  },
  {
    file: p("packages/types/src/instance/auth.ts"),
    find: `"google" | "gitea";`,
    insert: `"google" | "gitea" | "microsoft";`,
    marker: `"gitea" | "microsoft";`,
  },
  {
    file: p("packages/constants/src/auth/core.ts"),
    find: `  gitea: "Gitea",`,
    insert: `  gitea: "Gitea",\n  microsoft: "Microsoft",`,
    marker: `microsoft: "Microsoft"`,
  },
];

let applied = 0;
try {
  for (const edit of edits) if (applyEdit(edit)) applied++;
} catch (error) {
  if (error instanceof AnchorMissError) {
    console.error(`\n[entra codemod] FAILED\n${error.message}\n`);
    console.error("Upstream moved an anchor. Re-derive it against the current tree.\n");
    process.exit(1);
  }
  throw error;
}
console.log(`[entra codemod] ${applied} edit(s) applied, ${edits.length - applied} already present`);
