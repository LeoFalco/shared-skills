# gleap-analyzer

Claude Code skill for fetching and analyzing Gleap support cards as an N2 support analyst.

## Installation

```bash
npx skills add LeoFalco/gleap-analyzer -g -y
```

## Setup

1. Add your Gleap API key to your project's `.env` file:

```
GLEAP_API_KEY=your_api_key_here
```

2. Install the required dependencies in the project where you'll use the skill:

```bash
npm install dotenv axios yaml
```

## Usage

Once installed, trigger the skill by asking Claude Code to:

- "analyze gleap card `<URL>`"
- "review this ticket `<URL>`"
- "investigate this gleap `<URL>`"

Or paste any Gleap URL (`https://app.gleap.io/projects/...`).

The skill will:

1. Extract the ticket and project IDs from the URL
2. Fetch card data, messages, and activity logs via the Gleap API
3. Generate a structured N2 support analysis in Portuguese (pt-BR)

## Output

The analysis includes:

- **Resumo do Card** — card metadata and assignment info
- **Linha do Tempo** — chronological event summary
- **Análise de Causa Raiz** — root cause investigation
- **Situação Atual** — current status and blockers
- **Próximos Passos Sugeridos** — actionable next steps

## License

MIT
