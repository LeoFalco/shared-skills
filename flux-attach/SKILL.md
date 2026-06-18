---
name: flux-attach
description: Faz upload de arquivos (APK, AAB, imagens, PDFs, etc.) e os vincula como anexo a um card existente no Flux/Isengard. Use sempre que o usuário pedir "anexa esse apk no card", "sobe o apk pro card do flux", "manda esses arquivos pro card", "vincula anexo ao card", "anexa no flux", ou variações — incluindo logo depois de criar um card de publicação com a skill flux-publish, quando faz sentido anexar o build.
---

# flux-attach

Sobe arquivos para o storage do Flux (Isengard) e os vincula como anexo a um card já existente. Pensada para anexar APKs/AABs de build e outros artefatos a cards do board **Produto FSM - Publicações**, mas funciona com qualquer card cujo `cardId` você conheça.

## Quando usar

- O usuário pede para anexar um ou mais arquivos a um card do Flux.
- Logo depois de criar um card com `flux-publish`, quando o usuário quer anexar o build (APK/AAB) ou outros artefatos.

## Pré-requisitos

- Variável de ambiente `FLUX_JWT` exportada com um JWT válido do Flux — **o mesmo token da skill `flux-publish`**. Se não estiver setada, o script falha com mensagem clara. Peça ao usuário para pegar o token no DevTools do app web (qualquer request → header `authorization`) e exportar:
  ```bash
  export FLUX_JWT='eyJhbGciOiJI...'
  ```
  Se algum request falhar com erro de autenticação, peça um token novo.

## Resolução do caminho do script

A skill pode estar instalada em vários lugares dependendo do harness. Antes do primeiro uso na conversa, descubra o caminho real do `flux_attach.py` filtrando apenas os diretórios que existem (senão o `find` aborta com exit≠0 e zera a variável):

```bash
SCRIPT=""
for d in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.cursor/skills" ".claude/skills" ".agents/skills"; do
  [ -d "$d" ] || continue
  found="$(find "$d" -name flux_attach.py -path '*/flux-attach/*' 2>/dev/null | head -1)"
  [ -n "$found" ] && { SCRIPT="$found"; break; }
done
```

Use `"$SCRIPT"` nos comandos abaixo. Se `$SCRIPT` ficar vazio, a skill não está instalada nesse harness — diga ao usuário pra rodar `npx skills add LeoFalco/shared-skills -g -y` (ou `npx skills update flux-attach -g -y` se já tiver outras skills do repo) e pare.

## Como funciona o upload (contexto)

O Flux **não** aceita upload por GraphQL multipart. O app web usa um fluxo de **presigned POST S3 em 3 passos**, que o script replica:

1. Query `GetPreSignedPost(pipeId, name, mimeType)` → `{ url, fields }`. O servidor já gera a `key` (path no storage) e a devolve em `fields["key"]` — não precisa parsear o XML do S3.
2. POST `multipart/form-data` na `url` com todos os `fields` + o arquivo no campo `file`. Sucesso = HTTP **201**.
3. Mutation `CreateCardAttachment(cardId, key, name, mimeType, size)` que registra o anexo no card.

O subcomando `upload` do script faz os 3 passos de uma vez. Você raramente precisa chamar `presign` separado.

## Fluxo

### 1. Descobrir os arquivos a anexar

O usuário aponta os caminhos. Se ele não especificar e o contexto for o app orc-3, **sugira** os artefatos de build mais prováveis (ex.: APK em `android/app/build/outputs/apk/**/*.apk` ou `*.aab`). Liste os arquivos encontrados (com tamanho) e confirme a lista antes de subir.

### 2. Escolher o card

**Pergunte ao usuário qual card usar, sugerindo com base no contexto atual.** Para sugerir:

1. Pegue o PR da branch atual: `gh pr view --json number,title,url` (silencioso se não houver PR/branch).
2. Se houver PR, procure no board de Publicações o card cujo campo "Link do(s) PR(s)" contém o número do PR, via MCP:
   ```
   mcp__claude_ai_FluxControl_Custom_Production__list_cards
     pipeId: ac4db338-c7eb-452e-b75a-978abe03c8b6
     includeCurrentStage: true
     filters: { filtersByForm: [{ questionTitle: "Link do(s) PR(s)", value: "<numero-do-PR>" }] }
   ```
3. Se achar **exatamente 1** card, sugira ele (mostre título + stage + link no formato `#/fluxo/...?...&cardId=<id>`) e peça confirmação.
4. Se achar vários, liste e peça pra escolher. Se achar nenhum (ou não houver PR), peça o **link do card** ou o `cardId` direto.

O usuário pode, em qualquer caso:
- **Confirmar** a sugestão.
- **Colar um link de card** — extraia o `cardId` do parâmetro `?cardId=<uuid>` (ou do final do hash). Use só o UUID.
- **Passar o `cardId` cru** (um UUID).

> O anexo vai para o card identificado pelo `cardId`. O `pipeId` default no script é o do board de Publicações; se o card for de outro board, passe `--pipe <pipeId>` (o presigned precisa do pipe correto para montar a key).

### 3. Validar tamanho e tipo

Antes de subir, o script valida — mas adiante o aviso ao usuário:

- **Tamanho**: limite de **100 MB** por arquivo no Flux. APK de release costuma passar disso. Se algum arquivo exceder, avise e confirme: ou o usuário aceita tentar com `--force` (o servidor pode rejeitar), ou sobe um APK menor/dividido. Não force sem confirmação.
- **Tipo**: extensões aceitas (allowlist do Isengard): imagens, vídeo, áudio, documentos (pdf, docx, xlsx, csv, json, xml, md…), email (eml, msg), cad (dwg, dxf, rvt) e arquivos compactados (`zip, rar, 7z, tar, gz, **apk**`). `aab` **não** está explicitamente no allowlist — se o usuário quiser subir um AAB, avise que pode ser recusado pela extensão; alternativa é renomear/compactar como zip ou subir o APK.

### 4. Confirmação

Mostre uma tabela resumo e peça OK antes de subir:

```
Vou anexar ao card "<título>" (<link>):
  - app-release.apk     (84.2 MB)
  - mapping.txt         (3.1 MB)
Confirma?
```

Em modo `--dry-run`, pule a confirmação.

### 5. Upload

Para cada arquivo, rode:

```bash
python3 "$SCRIPT" upload <cardId> "<caminho-do-arquivo>"
```

Flags úteis:
- `--pipe <pipeId>` — se o card não for do board de Publicações.
- `--mime <mimeType>` — força o mimeType (o script já detecta `.apk` corretamente).
- `--force` — sobe mesmo acima de 100 MB (use só com confirmação do usuário).
- `--dry-run` — não chama API; imprime mimeType detectado, tamanho e o plano dos 3 passos.

Suba os arquivos **sequencialmente** (um comando por arquivo) e mostre o progresso. Cada chamada bem-sucedida imprime o attachment criado:

```json
{ "id": "...", "name": "app-release.apk", "path": "accounts/.../files/...-app-release.apk", "size": 88291234, "cardUrl": "https://app.fluxcontrol.com.br/#/fluxo/..." }
```

### 6. Resultado

Liste os anexos criados (nome + id) e o link do card. Se algum arquivo falhou, mostre o erro específico e continue com os demais (não aborte a leva inteira por causa de um arquivo).

## Tratamento de erro

- **`FLUX_JWT` ausente/expirado** → peça token novo (igual flux-publish).
- **S3 HTTP 401/403** → policy do presigned expirou ou o `Content-Type` não bate; normalmente é refazer (token novo / tentar de novo).
- **S3 HTTP 413** → arquivo acima do permitido; é caso de tamanho.
- **`CreateCardAttachment` falha depois do upload** → o arquivo já está no S3; o script informa a `key` na mensagem de erro. Dá pra registrar manualmente depois com essa key (rodando só o passo 3) — não re-suba o arquivo.

## Modo dry-run (para testes)

Quando o usuário digitar `--dry-run`:

- Use `upload <cardId> <arquivo> --dry-run`: o script valida tamanho/extensão e imprime o mimeType detectado, o tamanho e o plano dos 3 passos — **sem** chamar a API nem postar no S3. Não precisa de `FLUX_JWT`.
- Diga explicitamente "modo dry-run — nenhum arquivo foi enviado nem vinculado".

## Referência das operations

| Passo | Operation | Tipo | Input | Saída relevante |
|---|---|---|---|---|
| 1 | `GetPreSignedPost` | query | `CreatePreSignedPostInput { pipeId: ID!, name: String!, mimeType: String! }` | `{ url, fields }` (com `fields.key`) |
| 2 | (POST S3) | HTTP | `multipart/form-data`: todos os `fields` + `file` (último) | HTTP 201 |
| 3 | `CreateCardAttachment` | mutation | `CreateCardAttachmentInput { cardId: ID!, key: String!, name: String!, mimeType: String!, size: Int! }` | `CardAttachment { id, name, path, type, size, extension, createdAt }` |

`questionTitle` do campo de PR no board ("Link do(s) PR(s)") e `pipeId` (`ac4db338-...`) são estáveis. A `key`, `url` e `fields` vêm sempre da chamada do passo 1 — **nunca** hardcode.

## Por que essa skill existe

O MCP do Flux não expõe upload nem vínculo de anexos a cards — só leitura/movimentação. O app web faz presigned POST S3 em 3 passos, e a skill replica isso via GraphQL inline (mesma abordagem da `flux-publish`, que resolve a ausência de `CreateCard` no MCP). Quando/se o MCP passar a expor `getPreSignedPost` + `createCardAttachment`, o script pode ser substituído pelas tools do MCP.

Operations confirmadas no servidor do Isengard (`packages/apps/api/src/modules/cards/graphql/cards-attachments.resolver.ts`), validação de extensão/tamanho em `cards-attachments.service.ts` e `infra/presigned-url/presigned-url.service.ts`.
