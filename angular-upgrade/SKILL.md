---
name: angular-upgrade
description: >
  Upgrade an Angular project by exactly one major version using the Angular CLI.
  Handles @angular/* core packages, @angular/material, @angular/cdk, @angular-eslint,
  typescript, rxjs, zone.js, and other Angular-ecosystem dependencies found in package.json.
  Validates the upgrade with lint, tests, and production build.
  Use this skill whenever the user wants to upgrade Angular, bump Angular version,
  migrate to a newer Angular, or mentions "ng update". Also use when the user says
  things like "update angular", "subir versão do angular", "upgrade angular",
  "migrate angular", or "atualizar angular".
---

# Angular Upgrade (One Major Version)

This skill upgrades an Angular project by exactly **one** major version (e.g., 14 -> 15, not 14 -> 16).
It uses the Angular CLI's `ng update` with `--create-commits` so each package update is an individual commit,
runs validation (lint, tests, build), and stops to ask the user if anything fails.

## Prerequisites

Before starting, verify:
- You're in the root of an Angular project (has `angular.json` and `package.json`)
- The git working tree is clean (`git status` shows no uncommitted changes)
- `node_modules` exists (run the install command if needed)
- Detect the package manager: look for `yarn.lock` (yarn), `pnpm-lock.yaml` (pnpm), or default to npm.
  Use the detected package manager for all install/run commands throughout this workflow.

If the working tree is dirty, stop and ask the user to commit or stash first.

## Step 1: Detect Current and Target Versions

Read `package.json` and extract the current major version from `@angular/core`.
The target is always `current + 1`.

Example: if `@angular/core` is `14.3.0`, the target major is `15`.

Tell the user:
> Upgrading Angular from v{current} to v{target}

## Step 2: Check the Angular Update Guide

Visit `https://angular.dev/update-guide?v={current}.0-{target}.0&l=3` to review
breaking changes and required migration steps. Summarize the most impactful changes
for the user before proceeding.

For versions older than v17, use `https://update.angular.io/?v={current}.0-{target}.0&l=3` instead.

## Step 3: Update Core Angular Packages

Run `ng update` for the core Angular packages. Always use `--force` (to allow peer dependency
mismatches during the upgrade) and `--create-commits` (so each update is a discrete commit).

```bash
npx ng update @angular/core@{target} @angular/cli@{target} --force --create-commits
```

If this fails, stop and report the error to the user. Ask what they want to do.

## Step 4: Update Angular Material and CDK (if present)

Check if `@angular/material` or `@angular/cdk` are in `package.json`. If so:

```bash
npx ng update @angular/material@{target} --force --create-commits
```

This typically updates both `@angular/material` and `@angular/cdk` together.
If only `@angular/cdk` is present without `@angular/material`, update it directly:

```bash
npx ng update @angular/cdk@{target} --force --create-commits
```

## Step 5: Update Angular ESLint (if present)

Check if `@angular-eslint/schematics` (or any `@angular-eslint/*` package) is in `package.json`. If so:

```bash
npx ng update @angular-eslint/schematics@{target} --force --create-commits
```

This updates all `@angular-eslint/*` packages together.

Note: `@angular-eslint` versioning follows Angular major versions starting from v12.
If the project uses TSLint instead of ESLint (check for `tslint.json`), skip this step
as TSLint has no Angular-version-specific updates.

## Step 6: Update Other Angular-Ecosystem Dependencies

Scan `package.json` for other dependencies that are known to have Angular-version-specific
releases. For each one found, determine if it needs a version bump for the target Angular version.

Common ones to check:

| Package | Notes |
|---------|-------|
| `@angular/material-moment-adapter` | Must match `@angular/material` version |
| `@angular-devkit/build-angular` | Usually updated with `@angular/cli`, verify it matches |
| `@angular/compiler-cli` | Usually updated with `@angular/core`, verify it matches |
| `@angular/language-service` | Usually updated with `@angular/core`, verify it matches |
| `@angular/service-worker` | Usually updated with `@angular/core`, verify it matches |
| `typescript` | Each Angular version requires a specific TypeScript range — check Angular's `package.json` peerDependencies |
| `zone.js` | Check if the new Angular version requires a different zone.js range |
| `rxjs` | Major Angular upgrades sometimes require rxjs bumps |

Also scan for any `ngx-*` or other third-party libraries that declare Angular peer dependencies
(e.g., `ngx-mask`, `ngx-translate`, `@ngrx/*`, `@sentry/angular`). Check their changelogs or
npm pages to find compatible versions for the target Angular version.

For packages not updated by `ng update`, install the correct version directly.
After each install, commit with a descriptive message:

```bash
git add -A && git commit -m "chore: update <package> to v<version> for Angular {target} compatibility"
```

Do NOT blindly bump everything. Check actual compatibility. If unsure about a package,
search npm for its Angular compatibility or check its changelog/README.

## Step 7: Install and Verify Dependencies

Delete `node_modules` and the lockfile (`package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml`),
then run a clean install with the project's package manager.

Check for peer dependency warnings. If there are critical peer dependency conflicts,
report them to the user.

Commit the updated lockfile:

```bash
git add <lockfile> && git commit -m "chore: regenerate lockfile for Angular {target}"
```

## Step 8: Run Lint

Check `package.json` for a `lint` script. If it exists, run it.

If lint fails:
1. Check if a `lint:fix` (or similar auto-fix) script exists and try it first
2. If auto-fix resolves it, commit the fixes:
   ```bash
   git add -A && git commit -m "fix: resolve lint issues after Angular {target} upgrade"
   ```
3. If auto-fix doesn't fully resolve it, stop and report the remaining issues to the user

If the project has no lint script, skip this step.

## Step 9: Run Tests

Check `package.json` for a `test` script. If it exists, run it.

If tests fail, stop and report the failures to the user. Show the failing test names
and error messages. Ask what they want to do before proceeding.

If the project has no test script, skip this step.

## Step 10: Smoke Test Dev Server

Look in `package.json` for a `start` script (or a variant like `start:prod`, `serve`, etc.).
Start the dev server to verify the app boots correctly.

Wait for the compilation to finish and check the output for errors. Verify the app loads
without console errors or blank screens on the local URL shown in the terminal output.

If the app fails to start or shows runtime errors:
1. Check the terminal output for compilation errors
2. Check the browser console for runtime errors
3. Try to fix the issues (common problems: broken imports, changed APIs, missing modules)
4. If fixed, commit the changes:
   ```bash
   git add -A && git commit -m "fix: resolve runtime issues after Angular {target} upgrade"
   ```
5. If you can't fix it, stop and report the errors to the user

Stop the dev server before proceeding.

## Step 11: Run Production Build

Look in `package.json` for a production build script (common names: `build`, `build:prod`,
`build:production`). Run it with the production configuration. If no dedicated script exists,
use `npx ng build --configuration production`.

If the build fails, stop and report the error. Common issues after Angular upgrades:
- TypeScript strict mode changes
- Deprecated API removals
- Template type-checking changes
- Budget size violations

Report the specific errors and ask the user how to proceed.

## Step 12: Summary

When all steps pass, provide a summary:

> Angular upgrade from v{current} to v{target} complete!
>
> - Core packages: updated
> - Material/CDK: updated (or N/A)
> - ESLint: updated (or N/A)
> - Ecosystem deps: list what was updated
> - Lint: passing
> - Tests: passing
> - Build: passing
>
> Commits created: {count}

Remind the user that the changes are committed locally but not pushed.
If they want to create a PR, offer to help.
