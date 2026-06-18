# shared-skills

A collection of reusable [Claude Code](https://claude.ai/code) skills, installable globally or per-project.

## Installation

```bash
npx skills add LeoFalco/shared-skills -g -y
```

## Updating

Update by skill name (the `skills` CLI does not resolve repo slugs in `update`):

```bash
npx skills update gleap-analyzer gleap-responder angular-upgrade flux-publish flux-attach flux-my-cards merge cleanup-branches node-upgrade pin-dependencies -g -y
```

To check what's installed:

```bash
npx skills list -g
```

## Skills

### gleap-analyzer

Fetches a Gleap support card and produces a structured N3 analysis in pt-BR.

**Triggers:** "analyze gleap card", "review this ticket", "investigate this gleap", or any `app.gleap.io` URL.

**Output:** Resumo do Card, Linha do Tempo, Análise de Causa Raiz, Situação Atual, and Próximos Passos Sugeridos.

### gleap-responder

Posts an investigation report as an internal note on a Gleap card.

**Triggers:** "respond to the gleap card", "post a note", "send the relatório".

**Flow:** Gathers findings from the conversation, generates a structured report, shows it for approval, and posts it as an internal note.

### angular-upgrade

Upgrades an Angular project by exactly one major version using the Angular CLI.

**Triggers:** "upgrade angular", "update angular", "ng update", "subir versão do angular", "migrate angular", "atualizar angular".

**Flow:** Detects the current Angular version, checks the official update guide, runs `ng update` for core packages and ecosystem dependencies (Material, CDK, ESLint, TypeScript, etc.), then validates with lint, tests, and production build. Each package update is an individual commit.

### flux-publish

Creates a publication card on the Flux board "Produto FSM - Publicações" from the PR open in the current branch.

**Triggers:** "manda esse PR pro flux", "abre card de publicação", "fluxa esse PR", "cria publicação no flux", "vira esse PR em card no Flux", or variants — including right after merging a PR.

**Flow:** Reads the current PR with `gh pr view`, fetches the form options via the Flux GraphQL API (operation `Form`), infers Projeto/Área from repo name and PR title prefix, asks the user for ambiguous fields (Equipe Responsável, Rollback when relevant), confirms, then creates the card via `CreateCard` mutation. Includes a `--dry-run` mode that reads from a local fixture and prints the payload without calling the API.

### flux-attach

Uploads files (APK, AAB, images, PDFs, etc.) and links them as attachments to an existing Flux/Isengard card.

**Triggers:** "anexa esse apk no card", "sobe o apk pro card do flux", "manda esses arquivos pro card", "vincula anexo ao card" — including right after creating a publication card with `flux-publish`.

**Flow:** Resolves the bundled `flux_attach.py`, then uploads each file and links it to the given card via the Flux GraphQL API. Uses the same `$FLUX_JWT` token as `flux-publish`.

### flux-my-cards

Lists the user's cards across all Flux boards they have access to, grouped by board and stage, highlighting the ones that need action.

**Triggers:** "meus cards no flux", "status dos meus cards", "como estão minhas publicações", "o que falta nos meus cards".

**Flow:** Queries the Flux MCP for the authenticated user's cards and presents a grouped, action-oriented summary.

### merge

Automates the full PR merge workflow for the current branch.

**Triggers:** "merge this PR", "wait and merge", "approve and merge", "merge it".

**Flow:** Waits for CI checks to pass, approves the PR (if not authored by the current user), attempts the merge, and falls back to admin merge if needed.

### cleanup-branches

Cleans up stale git branches and merged/closed PR branches.

**Triggers:** "cleanup branches", "prune branches", "remove stale branches", "delete gone branches".

**Flow:** Deletes local branches whose remote tracking branch is gone, removes remote branches whose PRs are merged/closed, and ensures the repo has "delete branch on merge" enabled.

### node-upgrade

Upgrades Node.js to the next LTS version across an entire project.

**Triggers:** "upgrade node", "update node", "subir versão do node", "next LTS", "atualizar node".

**Flow:** Updates `.nvmrc`, Dockerfiles, `serverless.yml` runtime, `package.json` engines, CI workflows, and related deps like `@types/node`, then validates with lint and tests.

### pin-dependencies

Pins npm dependencies by removing `^` and `~` version prefixes across all `package.json` files (monorepo-aware).

**Triggers:** "pin dependencies", "lock versions", "exact versions", "make my deps exact", "stop version drift".

**Flow:** Resolves the bundled `pin-dependencies.js`, scans for workspaces, strips range prefixes, and runs install in each changed directory to update the lock file.

## Setup

The Gleap skills (`gleap-analyzer` and `gleap-responder`) use the **Gleap MCP server** for all API access. Make sure the Gleap MCP is connected and authenticated in Claude Code — no `GLEAP_API_KEY` or other env vars are required in the consumer project.

The `angular-upgrade` skill uses only the Angular CLI and standard Node.js (18+) tooling.

The `flux-publish` and `flux-attach` skills need `FLUX_JWT` exported (token from the Flux web app DevTools — refresh it if a request fails with an auth error) and `gh` CLI authenticated. The Flux MCP doesn't expose the form options, the `CreateCard` mutation, or file uploads today (see [FieldControl/isengard#2591](https://github.com/FieldControl/isengard/issues/2591)), so these skills use GraphQL directly. `flux-my-cards`, by contrast, runs entirely through the Flux MCP.

The `merge` and `cleanup-branches` skills require the `gh` CLI authenticated. `node-upgrade` and `pin-dependencies` use only standard Node.js tooling.

## License

MIT
