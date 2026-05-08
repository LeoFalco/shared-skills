# shared-skills

A collection of reusable [Claude Code](https://claude.ai/code) skills, installable globally or per-project.

## Installation

```bash
npx skills add LeoFalco/shared-skills -g -y
```

## Updating

```bash
npx skills update LeoFalco/shared-skills -g -y
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

## Setup

The Gleap skills (`gleap-analyzer` and `gleap-responder`) use the **Gleap MCP server** for all API access. Make sure the Gleap MCP is connected and authenticated in Claude Code — no `GLEAP_API_KEY` or other env vars are required in the consumer project.

The `angular-upgrade` skill uses only the Angular CLI and standard Node.js (18+) tooling.

## License

MIT
