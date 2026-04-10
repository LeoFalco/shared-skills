# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **shared Claude Code skills** repository — a collection of reusable skills installed into other projects via `npx skills add LeoFalco/shared-skills -g -y` and used within Claude Code sessions.

Each skill lives in its own directory with a `SKILL.md` (name, trigger description, runtime workflow) and a `scripts/` folder for any supporting scripts.

### Skills

| Skill | Purpose | Script |
|-------|---------|--------|
| `gleap-analyzer` | Fetches a Gleap card and produces a structured N3 analysis in pt-BR | `gleap-analyzer/scripts/fetch-gleap-card.js` |
| `gleap-responder` | Posts an investigation report as an internal note on a Gleap card | `gleap-responder/scripts/post-gleap-note.js` |
| `angular-upgrade` | Upgrades an Angular project by one major version using `ng update` | — |

## Adding a New Skill

1. Create a directory with the skill name
2. Add a `SKILL.md` defining name, trigger description, and workflow
3. Add supporting scripts under `scripts/` if needed
4. Update the skills table above

## Script Conventions

- Zero external dependencies — Node.js built-ins only (`fetch`, `fs`, `path`)
- ESM imports with top-level `await` (requires Node 18+)
- `.env` loaded manually (no dotenv) — reads keys from consumer project's `.env`
- When installed as a skill, scripts are resolved dynamically via `find` across `$HOME/.claude/skills` and `.claude/skills`

## Gleap Skills — Architecture

### Data Flow

1. User provides a Gleap URL → skill extracts `ticketId` and `projectId` (24-char hex each)
2. `fetch-gleap-card.js` calls Gleap API v3 (`https://api.gleap.io/v3`) for ticket, messages, and activities in parallel
3. Output is written to `gleap-card-<ticketId>.json` (heavily sanitized — many ticket/message fields are stripped)
4. Claude reads the JSON and produces analysis
5. Optionally, `post-gleap-note.js` posts a markdown report back as an internal note via `POST /v3/messages`

### Gleap-Specific Details

- Messages and activities are fetched with pagination (50 per page)
- Rich text (`doc` type content) is converted to plain text via `docToPlainText()`
- Default project ID fallback: `695d175e48ac2b20b647cbfe`

## Testing Scripts Locally

```bash
# fetch-gleap-card.js
GLEAP_API_KEY=<key> node gleap-analyzer/scripts/fetch-gleap-card.js <ticketId> [projectId]

# post-gleap-note.js
GLEAP_API_KEY=<key> node gleap-responder/scripts/post-gleap-note.js <ticketId> <projectId> <content-file.md>
```
