# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **shared Claude Code skills** repository — a collection of reusable skills installed into other projects via `npx skills add LeoFalco/shared-skills -g -y` and used within Claude Code sessions.

Each skill lives in its own directory with a `SKILL.md` (name, trigger description, runtime workflow) and optional supporting scripts under `scripts/`.

### Skills

| Skill | Purpose | Implementation |
|-------|---------|----------------|
| `gleap-analyzer` | Fetches a Gleap card and produces a structured N3 analysis in pt-BR | Gleap MCP (`mcp__gleap__get_ticket`, `get_ticket_messages`, `get_ticket_activity_log`) |
| `gleap-responder` | Posts an investigation report as an internal note on a Gleap card | Gleap MCP (`mcp__gleap__send_message` with `isNote: true`) |
| `angular-upgrade` | Upgrades an Angular project by one major version using `ng update` | — |

## Adding a New Skill

1. Create a directory with the skill name
2. Add a `SKILL.md` defining name, trigger description, and workflow
3. Add supporting scripts under `scripts/` only if MCPs / built-in tools are not enough
4. Update the skills table above

## Script Conventions (when scripts are needed)

- Zero external dependencies — Node.js built-ins only (`fetch`, `fs`, `path`)
- ESM imports with top-level `await` (requires Node 18+)
- `.env` loaded manually (no dotenv) — reads keys from consumer project's `.env`
- When installed as a skill, scripts are resolved dynamically via `find` across `$HOME/.claude/skills` and `.claude/skills`

## Gleap Skills — Architecture

Both Gleap skills delegate to the **Gleap MCP server**. The MCP handles authentication and project scoping, so the consumer project does not need a `GLEAP_API_KEY` or to know the `projectId` from the URL.

- `gleap-analyzer` parses the URL only to extract the `ticketId` (24-char hex), then calls `mcp__gleap__get_ticket`, `mcp__gleap__get_ticket_messages` (paginated, `limit: 200`), and `mcp__gleap__get_ticket_activity_log` in parallel.
- `gleap-responder` posts the report via `mcp__gleap__send_message` with `isNote: true`. The MCP accepts plain text/markdown — no TipTap conversion needed.

If the MCP is not authenticated, the skills instruct the user to authenticate the Gleap MCP server in Claude Code.
