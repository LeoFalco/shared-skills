# gleap-analyzer

Claude Code skills for fetching, analyzing, and responding to Gleap support cards as an N3 support analyst.

## Skills

| Skill | Description |
|-------|-------------|
| `gleap-analyzer` | Fetches and analyzes Gleap cards, producing a structured N3 analysis |
| `gleap-responder` | Posts a structured investigation report (relatório) as an internal note on the Gleap card |

## Installation

```bash
npx skills add LeoFalco/gleap-analyzer -g -y
```

## Updating

```bash
npx skills update LeoFalco/gleap-analyzer -g -y
```

## Setup

Add your Gleap API key to your project's `.env` file:

```
GLEAP_API_KEY=your_api_key_here
```

No additional dependencies required — the script uses only Node.js built-ins.

## Usage

Once installed, trigger the skill by asking Claude Code to:

- "analyze gleap card `<URL>`"
- "review this ticket `<URL>`"
- "investigate this gleap `<URL>`"

Or paste any Gleap URL (`https://app.gleap.io/projects/...`).

The skill will:

1. Extract the ticket and project IDs from the URL
2. Fetch card data, messages, and activity logs via the Gleap API
3. Generate a structured N3 support analysis in Portuguese (pt-BR)

## Output

The analysis includes:

- **Resumo do Card** — card metadata and assignment info
- **Linha do Tempo** — chronological event summary
- **Análise de Causa Raiz** — root cause investigation
- **Situação Atual** — current status and blockers
- **Próximos Passos Sugeridos** — actionable next steps

### gleap-responder

After analyzing a card, trigger the responder by asking Claude Code to:

- "respond to the gleap card"
- "post a note on the card"
- "send the relatório"

The skill will:

1. Gather investigation findings from the current conversation
2. Generate a structured report (Problema reportado → Causas → O que foi feito → Situação atual)
3. Show the report for your approval
4. Post it as an internal note on the Gleap card via the API

## License

MIT
