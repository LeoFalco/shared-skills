---
name: flux-publish
description: Cria um card no board "Produto FSM - Publicações" no Flux a partir do PR da branch atual. Use sempre que o usuário pedir "cria card de publicação", "vira esse PR em card no Flux", "manda esse PR pro flux", "abre publicação", "fluxa esse PR", ou variações — incluindo logo depois de mergear um PR, quando faz sentido publicar.
---

# flux-publish

Cria um card no board **Produto FSM - Publicações** (Flux/Isengard) a partir do PR aberto na branch atual.

## Quando usar

- O usuário pede explicitamente para abrir card de publicação no Flux para um PR.
- Logo depois de mergear um PR, se o usuário sinalizar que quer publicar.

## Pré-requisitos

- Repositório git ativo com PR aberto (a skill usa `gh pr view`).
- Variável de ambiente `FLUX_JWT` exportada com um JWT válido do Flux. Se não estiver setada, o script falha com mensagem clara — peça ao usuário para pegar o token no DevTools do app web (qualquer request → header `authorization`) e exportar:
  ```bash
  export FLUX_JWT='eyJhbGciOiJI...'
  ```
  O token expira em ~3 dias.

## Resolução do caminho do script

A skill pode estar instalada em `$HOME/.claude/skills/flux-publish` (global) ou `.claude/skills/flux-publish` (project-local). Antes do primeiro uso na conversa, descubra o caminho real do `flux_api.py`:

```bash
SCRIPT="$(find "$HOME/.claude/skills" .claude/skills -name flux_api.py -path '*/flux-publish/*' 2>/dev/null | head -1)"
```

Use `"$SCRIPT"` nos comandos abaixo. Se não encontrar nada, a skill não está instalada — diga ao usuário pra rodar `npx skills add LeoFalco/shared-skills -g -y`.

## Fluxo

### 1. Coleta dos dados do PR

Use `gh pr view --json number,title,url,headRefName` para a branch atual. Se não houver PR, diga ao usuário e pare — a skill não cria card sem PR.

O **título do card** é o título do PR exatamente como está no GitHub. Não invente, não traduza, não tire prefixos.

### 2. Busca de opções dos campos de escolha

Rode o script para baixar o formulário inicial com as opções:

```bash
python3 "$SCRIPT" options
```

A saída é o form com `questions[].options[]` resolvido. Os campos relevantes:

| Campo | Tipo | Comportamento |
|---|---|---|
| Projeto | checkboxes | Pergunte ao usuário qual projeto (lista de repos). Tente inferir do `headRefName` ou do nome do repo (`gh repo view --json name`) — se houver match exato com algum `options[].value` (case-insensitive), pré-selecione. |
| Área | multipleChoice | Pergunte: Correção / Implementação / Melhoria. Inferir do prefixo do título do PR: `fix:` → Correção, `feat:` → Implementação, `chore:`/`docs:`/`refactor:` → Melhoria. Confirme antes de prosseguir. |
| Rollback | checkboxes | Default: não marcar nenhuma opção (significa "Não"). Pergunte só se o usuário sinalizar que é rollback ou incidente. |
| Equipe Responsável | checkboxes | Pergunte: Projetos / Sustentação. Se você não tem certeza, deixe o usuário escolher. |

**Importante:** os IDs de opção podem mudar — sempre resolva via o script `options`, nunca hardcode UUIDs no payload. A skill já sabe os `questionId`s de cada campo (eles são estáveis no board, ver tabela abaixo), mas os `optionId`s vêm da chamada acima.

### 3. Escolha de etiquetas

Antes da confirmação, liste as etiquetas disponíveis no board via MCP:

```
mcp__claude_ai_FluxControl_Custom_Production__list_labels
  pipeId: ac4db338-c7eb-452e-b75a-978abe03c8b6
```

Mostre as etiquetas pro usuário (nome + cor) e pergunte quais aplicar — pode ser nenhuma, uma ou várias. Guarde os `id`s das escolhidas pra usar no passo 6.

### 4. Confirmação antes de criar

Antes de criar o card, mostre ao usuário uma tabela resumo dos campos que vão ser preenchidos e peça confirmação. Algo curto, tipo:

```
Vou criar:
  Título: <título do PR>
  PR: <url>
  Projeto: <opção>
  Área: <opção>
  Equipe: <opção>
  Etiquetas: <nomes escolhidos, ou "nenhuma">
Confirma?
```

Em modo `--dry-run` (ver "Testes" abaixo), pule a confirmação e siga direto pro próximo passo.

### 5. Criação do card

Monte o payload no formato:

```json
{
  "fields": [
    {"questionId": "132a3167-d354-4085-a8f6-bb2adbe79114", "type": "shortAnswer", "value": "<título do PR>"},
    {"questionId": "bd561eeb-a8d7-4a0a-b7d2-74e88ee242c2", "type": "paragraph", "value": "<url do PR>"},
    {"questionId": "f34a1126-3c19-43fc-ac50-b4a8051a9273", "type": "url", "value": null},
    {"questionId": "28c0b446-ebf3-421d-9f87-acf35bf94499", "type": "url", "value": null},
    {"questionId": "dc16125d-b1e3-4964-9fd6-dfb3243e4d7c", "type": "checkboxes", "value": "<projetoOptionId>"},
    {"questionId": "c94fa92c-6360-4698-bd99-81cead4c7c83", "type": "multipleChoice", "value": "<areaOptionId>"},
    {"questionId": "86f9cc9a-b1ce-48f0-bdcb-f7bec64a4b11", "type": "checkboxes", "value": null},
    {"questionId": "3b7b1d2f-1b03-4f38-8c2a-19fa6b359d8c", "type": "checkboxes", "value": "<equipeOptionId>"},
    {"questionId": "54adb187-4861-428c-a1dd-0f1baa118446", "type": "numeric", "value": "0"}
  ]
}
```

Envia via stdin ao script:

```bash
echo '<payload>' | python3 "$SCRIPT" create
```

A resposta tem `id` e `url`. Mostre o link ao usuário no formato:

```
https://app.fluxcontrol.com.br/#/fluxo/ac4db338-...?view_mode=board&panel=card-detail&card-tab=0&cardId=<id>
```

Esse é o formato correto — **não** use `https://app.fluxcontrol.com.br/cards/<id>`, que não funciona.

### 6. Atribuir o Leo como responsável e aplicar etiquetas

O Leo sempre quer ser responsável pelos cards de publicação que cria. O `userId` está no payload do próprio `$FLUX_JWT` — não precisa chamar `get_me`.

1. Extrai o `id` do payload do JWT (segundo segmento, base64url):
   ```bash
   USER_ID="$(printf '%s' "$FLUX_JWT" | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
   ```
2. Adiciona como assignee no card recém-criado via MCP:
   ```
   mcp__claude_ai_FluxControl_Custom_Production__add_card_assignee
     cardId: <id do card criado no passo 5>
     assigneeId: <USER_ID extraído acima>
   ```
3. Para cada etiqueta escolhida no passo 3, aplica via MCP:
   ```
   mcp__claude_ai_FluxControl_Custom_Production__add_card_label
     input:
       cardId: <id do card criado no passo 5>
       labelId: <id da etiqueta>
   ```

Em modo `--dry-run`, pule esses passos e diga ao usuário que o Leo seria atribuído como responsável e quais etiquetas seriam aplicadas.

Se algum desses passos falhar (MCP não autenticado, etc), mostre o erro mas não falhe a skill — o card já foi criado, atribuição e etiquetas são só conveniência.

### 7. Comentário no PR com o link do card

Após criar o card com sucesso, **verifique se o PR já tem um comentário com link do Flux** — se não tiver, adicione um. Isso evita comentários duplicados quando a skill rodar mais de uma vez no mesmo PR (ex: usuário criou um card de teste antes).

```bash
# 1) Cheque se já existe comentário com link do Flux nesse PR
EXISTING="$(gh pr view <numero-do-pr> --json comments --jq '.comments[].body' | grep -c 'app.fluxcontrol.com.br' || true)"

# 2) Só comente se ainda não houver
if [ "$EXISTING" = "0" ]; then
  gh pr comment <numero-do-pr> --body "Card de publicação criado no Flux: <url do card>"
fi
```

Em modo `--dry-run`, **pule** este passo — não comente no PR, só diga ao usuário que o comentário seria postado (ou que já existe, se for o caso). Se o `gh pr comment` falhar (sem permissão, rate limit, etc), mostre o erro ao usuário mas não falhe a skill — o card já foi criado, o comentário é só conveniência.

## Modo dry-run (para testes)

Quando o usuário digitar `--dry-run` no prompt, **ou** o ambiente tiver `FLUX_PUBLISH_DRY_RUN=1`:

- O script `options` lê de `scripts/form_fixture.json` em vez de chamar a API — não precisa de `FLUX_JWT`. O fixture foi capturado no dia da criação da skill e contém o snapshot real do formulário.
- Use `create --dry-run` em vez de `create`. O script imprime o payload em JSON sem chamar a API.
- Mostre o payload final ao usuário e diga explicitamente "modo dry-run — nenhum card foi criado".

Use isso pra desenvolver/testar sem poluir o board de produção. Quando alguém adicionar uma opção nova no Flux (ex: um repo novo), o fixture vai ficar desatualizado — refresh com:

```bash
FLUX_JWT='<token>' python3 "$SCRIPT" options > "$(dirname "$SCRIPT")/form_fixture.json"
```

## Campos do formulário inicial — referência

| Campo | questionId | type | Valores |
|---|---|---|---|
| Título | `132a3167-d354-4085-a8f6-bb2adbe79114` | shortAnswer | título do PR |
| Link do(s) PR(s) | `bd561eeb-a8d7-4a0a-b7d2-74e88ee242c2` | paragraph | URL do PR |
| Link Movidesk | `f34a1126-3c19-43fc-ac50-b4a8051a9273` | url | null (a menos que usuário forneça) |
| Link Documentação | `28c0b446-ebf3-421d-9f87-acf35bf94499` | url | null (a menos que usuário forneça) |
| Projeto | `dc16125d-b1e3-4964-9fd6-dfb3243e4d7c` | checkboxes | optionId — resolver via script |
| Área | `c94fa92c-6360-4698-bd99-81cead4c7c83` | multipleChoice | optionId — resolver via script |
| Rollback | `86f9cc9a-b1ce-48f0-bdcb-f7bec64a4b11` | checkboxes | null (default), ou optionId se Sim/Incidente |
| Equipe Responsável | `3b7b1d2f-1b03-4f38-8c2a-19fa6b359d8c` | checkboxes | optionId — resolver via script |
| Quantidade de problemas encontrados | `54adb187-4861-428c-a1dd-0f1baa118446` | numeric | "0" (default) |

`questionId`s são estáveis no board. `optionId`s podem ser adicionados/renomeados pela equipe do produto — por isso a skill sempre busca via API antes de criar o card.

## Por que essa skill existe

O MCP do Flux não expõe nem as opções dos campos do formulário inicial, nem uma mutation `CreateCard`. A skill resolve isso usando GraphQL direto. Quando o MCP for atualizado (ver issue [FieldControl/isengard#2591](https://github.com/FieldControl/isengard/issues/2591)), a skill pode migrar para usar `mcp__claude_ai_FluxControl_Custom_Production__*` e remover o curl direto — mas isso ainda exige a mutation `CreateCard` no MCP, que hoje não existe.
