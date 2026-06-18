---
name: flux-my-cards
description: Lista os cards do usuário em todos os boards do Flux a que ele tem acesso, agrupados por board e stage, destacando os que precisam de ação. Use sempre que o usuário pedir "meus cards no flux", "status dos meus cards", "como estão minhas publicações", "o que falta nos meus cards", "cards no flux", ou variações.
---

# flux-my-cards

Lista os cards do usuário autenticado em **todos os boards (pipes) do Flux/Isengard** a que ele tem acesso, agrupando por board e stage, e destacando os que precisam de ação.

## Quando usar

- Usuário pergunta sobre o status dos próprios cards no Flux.
- Usuário quer saber o que falta pra publicar / o que está parado.
- Usuário acabou de criar um card e quer ver o quadro geral.

## Pré-requisitos

- MCP `claude.ai FluxControl Custom [Production]` autenticado. Se não estiver, peça ao usuário pra autenticar via `mcp__claude_ai_FluxControl_Custom_Production__authenticate`.

## Fluxo

### 1. Buscar cards do usuário em todos os boards

Use o MCP `list_own_cards` **sem filtrar por `pipeId`** — assim a API retorna cards de todos os pipes a que o usuário pertence:

```
mcp__claude_ai_FluxControl_Custom_Production__list_own_cards
  filters:
    status: notConcluded
    archived: false
  includeCurrentStage: true
  includeCreatedBy: true
  take: 100
  skip: 0
  sort: [{ field: "updated_at", order: "desc" }]
```

**Importante:** o campo de ordenação é `updated_at` (snake_case), não `updatedAt` — a API retorna erro de Prisma se for camelCase.

Se `totalCount > take`, faça novas chamadas com `skip` crescente até buscar tudo.

### 2. Variações

- **Se o usuário pedir um board específico** (ex: "meus cards no de publicações"): adicione `pipeId` ao filtro. Boards conhecidos:
  - Produto FSM - Publicações: `ac4db338-c7eb-452e-b75a-978abe03c8b6`
- **Se o usuário pedir concluídos também:** troque `status: notConcluded` por `status: all` (ou `concluded` se quiser só os finalizados). Por padrão, mostre só os não concluídos.
- **Se o usuário pedir cards arquivados:** remova o filtro `archived: false`.

### 3. Formatar a resposta

Agrupe por board (`pipe.name`) e dentro de cada board liste os cards com: nome, stage atual (com emoji de cor), data de atualização.

Mapeie `currentStage.color` para emojis:
- `red` → 🔴 (geralmente "Changes requested" / devolvido — precisa de ação do usuário)
- `yellow` → 🟡 (esperando / aguardando)
- `green` → 🟢 (em andamento avançado)
- `cyan` → 🔵 (triagem / verificação)
- `blue` → 🔷
- `purple` → 🟣
- `orange` → 🟠
- `gray` → ⚪

Depois das tabelas, faça um **resumo curto** destacando:
- Quantos precisam de ação imediata (stages vermelhos).
- Quantos estão esperando ação de terceiros.
- Total por board.

### 4. Links dos cards

Para cada card, monte o link no formato:

```
https://app.fluxcontrol.com.br/#/fluxo/<pipeId>?view_mode=board&panel=card-detail&card-tab=0&cardId=<cardId>
```

Use o `pipe.id` retornado em cada card. **Não** use `https://app.fluxcontrol.com.br/cards/<id>` — não funciona.

## Referência rápida

- **Board Produto FSM - Publicações:** `ac4db338-c7eb-452e-b75a-978abe03c8b6`
- Stages finais (cards aí não aparecem em `notConcluded`): Publicação, Concluido, Cancelado.
