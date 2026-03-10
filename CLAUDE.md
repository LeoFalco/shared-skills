# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Code skill** (`gleap-analyzer`) that fetches and analyzes Gleap support cards as an N2 support analyst. It's installed into other projects via `claude skill install --from LeoFalco/gleap-analyzer` and used within Claude Code sessions.

## Repository Structure

- `gleap-analyzer/SKILL.md` — Skill definition and workflow instructions consumed by Claude Code at runtime
- `gleap-analyzer/scripts/fetch-gleap-card.js` — Node.js script that calls the Gleap API (v3) to fetch ticket data, messages, and activity logs, then outputs a sanitized YAML file

## How the Skill Works

1. User provides a Gleap URL (`https://app.gleap.io/projects/{projectId}/{channel}/{ticketId}`)
2. The fetch script is invoked: `node .claude/skills/gleap-analyzer/gleap-analyzer/scripts/fetch-gleap-card.js <ticketId> <projectId>`
3. Script fetches ticket, messages, and activities in parallel from Gleap API v3
4. Output is written to `gleap-card-<ticketId>.json` in the current directory
5. Claude reads the YAML and produces a structured N2 analysis in Portuguese (pt-BR)

## Runtime Dependencies

Zero external dependencies — uses only Node.js built-ins (`fetch`, `fs`, `path`). Requires `GLEAP_API_KEY` in the consumer project's `.env`.

## Key Technical Details

- The script uses ESM imports (`import` syntax) and top-level `await`
- Uses native `fetch` (Node 18+) instead of axios
- Loads `.env` manually without dotenv
- Outputs JSON instead of YAML
- Messages and activities are fetched with pagination (50 per page)
- Rich text (`doc` type content) is converted to plain text via `docToPlainText()`
- Ticket data is heavily sanitized — many fields are stripped to reduce noise for analysis
- Default project ID is hardcoded as fallback: `695d175e48ac2b20b647cbfe`
