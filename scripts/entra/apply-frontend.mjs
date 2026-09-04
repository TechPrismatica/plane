import { copyFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { applyEdit, AnchorMissError } from "./anchors.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const p = (rel) => resolve(root, rel);

const LOGO_TARGETS = [
  "apps/web/app/assets/logos/microsoft-logo.svg",
  "apps/space/app/assets/logos/microsoft-logo.svg",
  "apps/admin/app/assets/logos/microsoft-logo.svg",
];

function copyAssets() {
  const source = p("scripts/entra/assets/microsoft-logo.svg");
  for (const target of LOGO_TARGETS) {
    mkdirSync(dirname(p(target)), { recursive: true });
    copyFileSync(source, p(target));
  }
}

const TEMPLATES = [
  ["scripts/entra/templates/microsoft-config.tsx", "apps/admin/components/authentication/microsoft-config.tsx"],
  ["scripts/entra/templates/admin-page.tsx", "apps/admin/app/(all)/(dashboard)/authentication/microsoft/page.tsx"],
  ["scripts/entra/templates/admin-form.tsx", "apps/admin/app/(all)/(dashboard)/authentication/microsoft/form.tsx"],
];

function writeTemplates() {
  for (const [source, target] of TEMPLATES) {
    mkdirSync(dirname(p(target)), { recursive: true });
    copyFileSync(p(source), p(target));
  }
}

export const edits = [
  {
    file: p("packages/types/src/instance/auth.ts"),
    find: `  | "gitea";\n\nexport type TInstanceAuthenticationModeKeys`,
    insert: `  | "gitea"\n  | "microsoft";\n\nexport type TInstanceAuthenticationModeKeys`,
    // Invariant: a marker must not be a substring of any *other* edit's
    // insert in the same file -- otherwise this edit silently stops applying
    // forever the moment that other edit runs first, and the outcome depends
    // on array order. (See the invariant test in test/run-tests.mjs, which
    // checks this mechanically across the whole `edits` array.)
    //
    // Tightened to the newline-separated form this edit's own insert produces.
    // The plain `| "microsoft";` form is also a substring of edit 5's insert
    // (`"gitea" | "microsoft";`), so a bare marker here would silently skip
    // this edit forever once edit 5 has run -- regardless of edits order.
    marker: `"gitea"\n  | "microsoft";`,
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
    // Tightened with the trailing " =" that only this edit's own insert
    // produces (the type declaration line). The bare type name is also a
    // substring of the next edit's insert (`| TInstanceMicrosoft...Keys;`,
    // a union member reference ending in `;` not ` =`), which is the same
    // collision class as the edit above -- see that comment.
    marker: "TInstanceMicrosoftAuthenticationConfigurationKeys =",
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

  // apps/web and apps/space oauth hooks -- structurally identical.
  ...["apps/web/core/hooks/oauth/core.tsx", "apps/space/hooks/oauth/core.tsx"].flatMap((rel) => [
    {
      file: p(rel),
      find: `import googleLogo from "@/app/assets/logos/google-logo.svg?url";`,
      insert:
        `import googleLogo from "@/app/assets/logos/google-logo.svg?url";\n` +
        `import microsoftLogo from "@/app/assets/logos/microsoft-logo.svg?url";`,
      marker: "microsoft-logo.svg",
    },
    {
      file: p(rel),
      find: `        config?.is_gitea_enabled)) ||`,
      insert: `        config?.is_gitea_enabled ||\n        config?.is_microsoft_enabled)) ||`,
      marker: "config?.is_microsoft_enabled)) ||",
    },
    {
      file: p(rel),
      find: `      enabled: config?.is_gitea_enabled,\n    },\n  ];`,
      insert:
        `      enabled: config?.is_gitea_enabled,\n    },\n` +
        `    {\n      id: "microsoft",\n` +
        `      text: \`\${oauthActionText} with Microsoft\`,\n` +
        `      icon: <img src={microsoftLogo} height={18} width={18} alt="Microsoft Logo" />,\n` +
        `      onClick: () => {\n` +
        `        window.location.assign(\`\${API_BASE_URL}/auth/microsoft/\${next_path ? \`?next_path=\${next_path}\` : \`\`}\`);\n` +
        `      },\n      enabled: config?.is_microsoft_enabled,\n    },\n  ];`,
      marker: `id: "microsoft"`,
    },
  ]),

  // apps/admin -- registers the Microsoft auth mode + its route.
  {
    file: p("apps/admin/hooks/oauth/core.tsx"),
    find: `import googleLogo from "@/app/assets/logos/google-logo.svg?url";\n// components`,
    insert:
      `import googleLogo from "@/app/assets/logos/google-logo.svg?url";\n` +
      `import microsoftLogo from "@/app/assets/logos/microsoft-logo.svg?url";\n// components`,
    marker: "microsoft-logo.svg?url",
  },
  {
    file: p("apps/admin/hooks/oauth/core.tsx"),
    find:
      `import { GoogleConfiguration } from "@/components/authentication/google-config";\n` +
      `import { PasswordLoginConfiguration } from "@/components/authentication/password-config-switch";`,
    insert:
      `import { GoogleConfiguration } from "@/components/authentication/google-config";\n` +
      `import { MicrosoftConfiguration } from "@/components/authentication/microsoft-config";\n` +
      `import { PasswordLoginConfiguration } from "@/components/authentication/password-config-switch";`,
    marker: `MicrosoftConfiguration } from "@/components/authentication/microsoft-config"`,
  },
  {
    file: p("apps/admin/hooks/oauth/core.tsx"),
    find: `    enabledConfigKey: "IS_GITEA_ENABLED",\n  },\n});`,
    insert:
      `    enabledConfigKey: "IS_GITEA_ENABLED",\n  },\n` +
      `  microsoft: {\n    key: "microsoft",\n    name: "Microsoft",\n` +
      `    description: "Allow members to log in or sign up for Plane with their Microsoft accounts.",\n` +
      `    icon: <img src={microsoftLogo} height={20} width={20} alt="Microsoft Logo" />,\n` +
      `    config: <MicrosoftConfiguration disabled={disabled} updateConfig={updateConfig} />,\n` +
      `    enabledConfigKey: "IS_MICROSOFT_ENABLED",\n  },\n});`,
    marker: `microsoft: {\n    key: "microsoft",`,
  },
  {
    file: p("apps/admin/hooks/oauth/index.ts"),
    find: `    authenticationModes["gitea"],\n  ];`,
    insert: `    authenticationModes["gitea"],\n    authenticationModes["microsoft"],\n  ];`,
    marker: `authenticationModes["microsoft"]`,
  },
  {
    file: p("apps/admin/app/routes.ts"),
    find:
      `    route("authentication/gitea", "./(all)/(dashboard)/authentication/gitea/page.tsx"),\n` +
      `    route("ai", "./(all)/(dashboard)/ai/page.tsx"),`,
    insert:
      `    route("authentication/gitea", "./(all)/(dashboard)/authentication/gitea/page.tsx"),\n` +
      `    route("authentication/microsoft", "./(all)/(dashboard)/authentication/microsoft/page.tsx"),\n` +
      `    route("ai", "./(all)/(dashboard)/ai/page.tsx"),`,
    marker: `authentication/microsoft", "./(all)/(dashboard)/authentication/microsoft/page.tsx"`,
  },

  // packages/types -- instance config surface.
  {
    file: p("packages/types/src/instance/base.ts"),
    find: `  is_gitea_enabled: boolean;\n  is_magic_login_enabled: boolean;`,
    insert: `  is_gitea_enabled: boolean;\n  is_microsoft_enabled: boolean;\n  is_magic_login_enabled: boolean;`,
    marker: `is_microsoft_enabled: boolean;`,
  },

  // apps/web and apps/space auth helpers -- error codes.
  //
  // The committed original used MICROSOFT_NOT_CONFIGURED = "5113" and
  // MICROSOFT_OAUTH_PROVIDER_ERROR = "5126", which collided with upstream's
  // own 5000-5190 band (RATE_LIMIT_EXCEEDED = "5900" etc). The plugin now
  // reserves 6900/6901/6902, so these edits produce those numbers instead
  // and add a third code, MICROSOFT_TENANT_INVALID = "6902", that never
  // existed in the original commit.
  //
  // Markers below key on the enum member / error-code *name*, not its
  // string value: the current tree (pre Task 10 revert) already carries
  // these members under the stale 5113/5126 numbers, so a value-specific
  // marker would neither match (already-present) nor find its pure-upstream
  // anchor (the member sits between the anchor's two halves) -- it would
  // throw AnchorMissError on today's tree. A name-based marker recognizes
  // "this concept already exists here" and safely no-ops today; run fresh
  // against upstream (no Microsoft code at all, as Task 10 restores) the
  // marker is absent, the anchor is found, and the correct 6900/6901/6902
  // text is produced.
  ...["apps/web/helpers/authentication.helper.tsx", "apps/space/helpers/authentication.helper.tsx"].flatMap(
    (rel) => [
      {
        file: p(rel),
        find: `  GITLAB_NOT_CONFIGURED = "5111",\n  GOOGLE_OAUTH_PROVIDER_ERROR = "5115",`,
        insert:
          `  GITLAB_NOT_CONFIGURED = "5111",\n  MICROSOFT_NOT_CONFIGURED = "6900",\n` +
          `  GOOGLE_OAUTH_PROVIDER_ERROR = "5115",`,
        marker: `MICROSOFT_NOT_CONFIGURED = "`,
      },
      {
        file: p(rel),
        find: `  GITLAB_OAUTH_PROVIDER_ERROR = "5121",\n  // Reset Password`,
        insert:
          `  GITLAB_OAUTH_PROVIDER_ERROR = "5121",\n  MICROSOFT_OAUTH_PROVIDER_ERROR = "6901",\n` +
          `  MICROSOFT_TENANT_INVALID = "6902",\n  // Reset Password`,
        marker: `MICROSOFT_OAUTH_PROVIDER_ERROR = "`,
      },
      {
        file: p(rel),
        find:
          `  [EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED]: {\n` +
          "    title: `GitLab not configured`,\n" +
          "    message: () => `GitLab not configured. Please contact your administrator.`,\n" +
          `  },\n  [EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR]: {`,
        insert:
          `  [EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED]: {\n` +
          "    title: `GitLab not configured`,\n" +
          "    message: () => `GitLab not configured. Please contact your administrator.`,\n" +
          `  },\n  [EAuthenticationErrorCodes.MICROSOFT_NOT_CONFIGURED]: {\n` +
          "    title: `Microsoft not configured`,\n" +
          "    message: () => `Microsoft not configured. Please contact your administrator.`,\n" +
          `  },\n  [EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR]: {`,
        marker: `EAuthenticationErrorCodes.MICROSOFT_NOT_CONFIGURED]: {`,
      },
      {
        file: p(rel),
        find:
          `  [EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR]: {\n` +
          "    title: `GitLab OAuth provider error`,\n" +
          "    message: () => `GitLab OAuth provider error. Please try again.`,\n" +
          `  },\n\n  // Reset Password`,
        insert:
          `  [EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR]: {\n` +
          "    title: `GitLab OAuth provider error`,\n" +
          "    message: () => `GitLab OAuth provider error. Please try again.`,\n" +
          `  },\n  [EAuthenticationErrorCodes.MICROSOFT_OAUTH_PROVIDER_ERROR]: {\n` +
          "    title: `Microsoft OAuth provider error`,\n" +
          "    message: () => `Microsoft OAuth provider error. Please try again.`,\n" +
          `  },\n  [EAuthenticationErrorCodes.MICROSOFT_TENANT_INVALID]: {\n` +
          "    title: `Microsoft tenant invalid`,\n" +
          "    message: () => `Your Microsoft tenant is not configured correctly. Contact your instance admin.`,\n" +
          `  },\n\n  // Reset Password`,
        marker: `EAuthenticationErrorCodes.MICROSOFT_OAUTH_PROVIDER_ERROR]: {`,
      },
      {
        file: p(rel),
        find:
          `    EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED,\n` +
          `    EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR,`,
        insert:
          `    EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED,\n` +
          `    EAuthenticationErrorCodes.MICROSOFT_NOT_CONFIGURED,\n` +
          `    EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR,`,
        marker: `EAuthenticationErrorCodes.MICROSOFT_NOT_CONFIGURED,`,
      },
      {
        file: p(rel),
        find:
          `    EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR,\n` +
          `    EAuthenticationErrorCodes.INVALID_PASSWORD_TOKEN,`,
        insert:
          `    EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR,\n` +
          `    EAuthenticationErrorCodes.MICROSOFT_OAUTH_PROVIDER_ERROR,\n` +
          `    EAuthenticationErrorCodes.MICROSOFT_TENANT_INVALID,\n` +
          `    EAuthenticationErrorCodes.INVALID_PASSWORD_TOKEN,`,
        marker: `EAuthenticationErrorCodes.MICROSOFT_OAUTH_PROVIDER_ERROR,`,
      },
    ]
  ),
];

// Guard so importing this module (e.g. from the test suite, to reach the
// exported `edits` array) never runs the CLI's file-mutating side effects --
// only running it directly (`node apply-frontend.mjs`) does.
const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  copyAssets();
  writeTemplates();

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
}
