---
name: node-upgrade
description: >
  Upgrade Node.js to the next LTS version across an entire project — .nvmrc, Dockerfiles,
  serverless.yml runtime, package.json engines, CI workflows, and related dependencies like
  @types/node. Validates the upgrade with lint and tests. Use this skill whenever the user
  wants to update Node.js, bump the Node version, migrate to a newer Node, update the
  runtime, or mentions things like "update node", "upgrade node", "atualizar node",
  "subir versão do node", "next LTS". Also use when the user is reviewing a Dependabot PR
  that bumps a Node.js Docker base image and wants to align the rest of the project.
---

# Node.js LTS Upgrade

Upgrades a project's Node.js version to the **next LTS release**, updating every file that
references the Node version and validating that the project still builds, lints, and passes
tests afterward.

The guiding principle: **.nvmrc is the source of truth** for the development Node.js version.
Everything else (Docker, Lambda runtime, CI, engines) should be consistent with it.

## Prerequisites

Before starting, verify:
- You're in the root of a Node.js project (has `package.json`)
- The git working tree is clean (`git status` shows no uncommitted changes)

If the working tree is dirty, stop and ask the user to commit or stash first.

## Step 1: Determine Current and Target Versions

### Find the current version

Read `.nvmrc` (the source of truth). If it doesn't exist, check `package.json` engines,
Dockerfile `FROM` lines, or ask the user.

### Determine the next LTS

Node.js LTS releases follow a predictable pattern: even-numbered major versions become LTS
(18, 20, 22, 24, 26...). The target is always the **next even-numbered major** after the
current one.

Examples:
- Current v18 -> Target v20
- Current v20 -> Target v22
- Current v22 -> Target v24
- Current v24 -> Target v26

If the current version is odd (e.g., v19, v21), the next LTS is the next even number
(v20, v22 respectively).

To confirm the target version is actually released as LTS and get the latest patch, run:

```bash
curl -s https://nodejs.org/dist/index.json | node -e "
  const data = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
  const target = process.argv[1];
  const latest = data.find(v => v.version.startsWith('v' + target + '.') && v.lts);
  if (latest) console.log(latest.version, '(LTS:', latest.lts + ')');
  else { const current = data.find(v => v.version.startsWith('v' + target + '.')); console.log(current ? current.version + ' (Current, not yet LTS)' : 'Not released yet'); }
" TARGET_MAJOR
```

### Hard stop: next LTS not yet released

If the target LTS version is not yet released or not yet in LTS status (only in "Current"),
you MUST stop and ask the user before making any changes. Do not fall back to a non-LTS
"Current" version (odd-numbered releases like v25 are never LTS). Present the situation:

> Node.js v{target} is not yet released (or not yet LTS). The project is currently on
> v{current} which is the latest available LTS. Options:
> 1. Stay on v{current} — no changes needed
> 2. Prepare configs for v{target} now (builds will break until it's released)
> 3. Update to a different version you specify
>
> What would you like to do?

Do NOT proceed with any file changes until the user responds. This is the most important
rule in this skill — upgrading to a non-LTS version defeats the entire purpose.

Tell the user:
> Upgrading Node.js from v{current} to v{target} (LTS)

## Step 1b: Detect Existing Version Mismatches

Before upgrading, check if the project already has inconsistent Node versions across files.
This is common when Dependabot bumps only one file (e.g., Dockerfile) while others remain
on the old version. Scan all version reference files and compare:

```bash
# Collect all Node version references
echo "=== .nvmrc files ===" && find . -name '.nvmrc' -not -path '*/node_modules/*' -exec echo -n "{}: " \; -exec cat {} \;
echo "=== Dockerfiles ===" && grep -rn 'FROM node:' --include='Dockerfile*' .
echo "=== serverless ===" && grep -rn 'nodejs[0-9]' --include='serverless.*' .
echo "=== engines ===" && grep -rn '"node"' --include='package.json' . | grep -v node_modules
```

If versions are inconsistent (e.g., Dockerfile says v25 but .nvmrc says v24), mention
this to the user before proceeding:

> I noticed a version mismatch: Dockerfile uses node:25-alpine but .nvmrc is on v24.
> I'll align everything to v{target} (the next LTS).

This context helps the user understand why certain files are changing.

## Step 2: Review Breaking Changes

Before making changes, check the Node.js release notes for breaking changes between
the current and target versions. Key things to watch for:

- Removed or deprecated APIs (e.g., `url.parse()`, `Buffer()` constructor)
- V8 engine changes that affect native modules
- Changes to `--experimental-*` flags
- Module system changes (ESM/CJS interop)
- OpenSSL version bumps that affect crypto behavior

Summarize anything relevant to the user before proceeding.

## Step 3: Update All Version References

Scan the project for every file that references the Node.js version. In FieldControl
projects, these are typically:

### 3a. `.nvmrc` files (source of truth)

Find all `.nvmrc` files in the project:
```bash
find . -name '.nvmrc' -not -path '*/node_modules/*'
```

Update each one to `v{target}` (matching the existing format — some use `v24`, others
`v24.x`, others `24.20.1`). Prefer the simple `v{target}` format unless there's a reason
for a specific patch version.

### 3b. Dockerfiles

Search for `FROM node:` lines:
```bash
grep -rn 'FROM node:' --include='Dockerfile*' .
```

Update the tag while preserving the variant (e.g., `node:24-alpine` -> `node:26-alpine`,
`node:24` -> `node:26`). Keep the same base image variant (alpine, slim, bullseye, etc.).

### 3c. `serverless.yml` / `serverless.ts` (Lambda runtime)

Search for `nodejs` runtime references:
```bash
grep -rn 'nodejs[0-9]' --include='serverless.*' .
```

Update `runtime: nodejs24.x` -> `runtime: nodejs26.x`.

**Important:** Verify the target runtime is supported by AWS Lambda. Check the AWS Lambda
runtimes documentation. If the runtime isn't available yet, warn the user — they may need
to wait or use a container image deployment instead.

### 3d. `package.json` engines field

Search for engines fields:
```bash
grep -rn '"engines"' --include='package.json' . | grep -v node_modules
```

Update the Node.js version range. Match the existing style:
- `">=18"` -> `">=26"`
- `"18.x"` -> `"26.x"`
- `"^18.0.0"` -> `"^26.0.0"`

### 3e. GitHub Actions workflows

Search for node-version in CI configs:
```bash
grep -rn 'node-version' .github/workflows/
```

Most FieldControl projects use `node-version-file` pointing to `.nvmrc` (which means CI
picks up the change automatically). If the workflow hardcodes a version, update it.

### 3f. Other files

Also check:
- `dependabot.yml` — if it has a `docker` ecosystem entry, no change needed (it manages
  Docker image updates separately)
- `.tool-versions` (asdf) — if present, update the `nodejs` line
- `Makefile` or shell scripts that reference node versions
- `tsconfig.json` target — newer Node versions support newer ES targets

## Step 4: Update Related Dependencies

Some dependencies are tightly coupled to the Node.js version:

| Dependency | Action |
|-----------|--------|
| `@types/node` | Update to match target major: `npm install -D @types/node@{target}` |
| `node-gyp` | May need update for native module compilation |
| `engines` in sub-packages | Keep consistent across the monorepo |

For monorepos, repeat dependency updates in each package directory.

Do NOT blindly update all dependencies — only those that are Node.js-version-sensitive.
Leave general dependency updates for Dependabot or a separate task.

## Step 5: Reinstall Dependencies

Clean install to ensure lockfiles are regenerated correctly:

```bash
rm -rf node_modules package-lock.json
npm install
```

For monorepos with a root `postinstall` that installs sub-packages, run from the root.
For yarn-based projects, use `yarn install` instead.

If there are peer dependency warnings or conflicts, report them to the user.

## Step 6: Run Lint

```bash
npm run lint
```

If lint fails:
1. Try `npm run lint:fix` first
2. If auto-fix resolves it, continue
3. If not, stop and report the remaining issues to the user

For monorepos, run lint in each package (or from root if it runs all).

## Step 7: Run Tests

```bash
npm test
```

If tests fail:
1. Read the error output carefully
2. Determine if failures are caused by the Node upgrade (API changes, timing issues,
   etc.) vs pre-existing failures
3. Try to fix upgrade-related failures
4. If you can't fix them, stop and report to the user with context about what changed

For monorepos, run tests in each package.

## Step 8: Summary

When all steps pass, provide a summary:

> Node.js upgrade from v{current} to v{target} (LTS) complete!
>
> **Files updated:**
> - .nvmrc: v{current} -> v{target}
> - Dockerfile: node:{current}-alpine -> node:{target}-alpine
> - (list all changed files)
>
> **Dependencies updated:**
> - @types/node: {old} -> {new}
> - (list all)
>
> **Validation:**
> - Lint: passing
> - Tests: passing

Remind the user the changes are local and not yet committed or pushed.

## Handling Monorepos

Many FieldControl projects are monorepos with multiple packages (e.g., `packages/server`,
`packages/cron`). For these:

1. Update version references in ALL packages, not just one
2. Run `npm install` from root (if root postinstall handles sub-packages)
3. Run lint and tests in EACH package independently
4. Some packages may use different module systems (ESM vs CJS) — test both

## When to Ask the User

Stop and ask if:
- The target LTS is not yet released
- The AWS Lambda runtime for the target version doesn't exist yet
- Tests or lint fail and you can't determine the fix
- There are peer dependency conflicts you're unsure about
- The project has native modules (`node-gyp`, `.node` files) that may need recompilation
- You find version references in unexpected places and aren't sure if they should be updated
