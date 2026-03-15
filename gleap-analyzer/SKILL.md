---
name: gleap-analyzer
description: >
  Fetch and analyze Gleap support cards as an N2 support analyst. Use when asked to
  analyze a Gleap card, review a support ticket, investigate a Gleap issue, or when the
  user provides a Gleap URL (app.gleap.io). Triggers on: "analyze gleap card", "gleap card",
  "review this ticket", "investigate this gleap", or any Gleap URL.
---

# Gleap Card Analyzer (N2 Support)

## Workflow

### 1. Get the Gleap card URL

Ask the user for the Gleap card URL if not already provided.

URL format: `https://app.gleap.io/projects/{projectId}/{channel}/{ticketId}`

Extract IDs from URL:
- **ticketId**: last path segment (24-char hex)
- **projectId**: segment after `/projects/` (24-char hex)

### 2. Fetch card data

Run the fetch script. It may be installed locally or globally, so resolve the path first:

```bash
node "$HOME/.claude/skills/gleap-analyzer/scripts/fetch-gleap-card.js" <ticketId> <projectId>
```

This outputs a `gleap-card-<ticketId>.json` file in the current directory.

Requires `GLEAP_API_KEY` in `.env`. If missing, tell the user to add it.

### 3. Read and analyze the JSON

Read the generated `gleap-card-<ticketId>.json` file.

The file contains:
- `ticket`: card metadata (title, description, form data, assigned user, channel)
- `messages`: chronological conversation notes between support agents
- `activities`: activity log events

### 4. Produce the N2 analysis

Act as an **N2 (level 2) support analyst**. Write the analysis in **Portuguese (pt-BR)** since FieldControl is a Brazilian company.

Structure the output as:

#### Resumo do Card
- Título do card
- Canal (email, chat, etc.)
- Cliente/conta afetada
- Responsável atual
- Data de abertura → último update

#### Linha do Tempo
Chronological summary of key events from messages and activities. For each entry:
- Date, author, and what happened/was communicated
- Highlight escalations, blocks, and status changes

#### Análise de Causa Raiz
Based on the conversation, identify:
- What is the reported problem
- What was investigated
- What was found as root cause (or if still unknown)

#### Situação Atual
- Where does the card stand right now
- What was the last action taken and by whom
- Is it waiting on someone? Who?

#### Próximos Passos Sugeridos
Actionable next steps for N2 support, such as:
- Technical investigations to perform
- People to contact
- Scripts or queries to run
- Escalation recommendations if needed

### 5. Clean up

After presenting the analysis, ask the user if they want to keep the generated YAML file or delete it.
