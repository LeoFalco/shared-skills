"""Cliente fino para a API GraphQL do Flux (Isengard).

Usado pela skill `flux-publish` para:
  - listar as opções (`Projeto`, `Área`, `Rollback`, `Equipe Responsável`) do
    formulário inicial do board "Produto FSM - Publicações"
  - criar um card no board

Autenticação via JWT lido de `$FLUX_JWT`. Esse token é o mesmo que o app web
do Flux usa — pega ele no DevTools (Network → qualquer request → header
`authorization`) e exporta no shell:

    export FLUX_JWT='eyJhbGciOiJI...'

O token expira em ~3 dias; quando expirar, refresh manual.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = "https://isengard.fluxcontrol.com.br/api/graphql"
PIPE_ID = "ac4db338-c7eb-452e-b75a-978abe03c8b6"  # Produto FSM - Publicações
START_FORM_ID = "c0a35ca9-aa15-49c5-a8c6-9b678e30003c"
START_STAGE_ID = "0b22730d-b591-47da-acde-b539a7c3b5db"  # Devbox

CREATE_CARD_PERSISTED_HASH = (
    "1bc4346cb4bd76f48de3df4067787eadac881719bb84578fed99afe7d24bbfab"
)


class FluxError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("FLUX_JWT", "").strip()
    if not token:
        raise FluxError(
            "FLUX_JWT não está exportado. Pegue o token no DevTools do app "
            "web do Flux e rode: export FLUX_JWT='<token>'"
        )
    return token


def _post(payload: dict) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "authorization": _token(),
            "content-type": "application/json",
            "x-graphql-client-name": "fluxcontrol:client:production",
            "x-graphql-client-version": "bb06e-20260511",
            "origin": "https://app.fluxcontrol.com.br",
            "referer": "https://app.fluxcontrol.com.br/",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise FluxError(f"HTTP {e.code}: {e.read().decode(errors='replace')}") from e
    except urllib.error.URLError as e:
        raise FluxError(f"Falha de rede: {e}") from e

    if body.get("errors"):
        msgs = "; ".join(err.get("message", "?") for err in body["errors"])
        raise FluxError(f"GraphQL: {msgs}")
    return body["data"]


def fetch_form_options() -> dict[str, Any]:
    """Retorna o form inicial com as opções resolvidas.

    O MCP `get_form` ainda não retorna `options` (ver
    https://github.com/FieldControl/isengard/issues/2591), por isso usamos a
    operation `Form` direto via GraphQL com query inline.

    Em modo `FLUX_PUBLISH_DRY_RUN=1`, lê de um fixture local — não chama a
    API. Isso permite rodar testes sem token/rede.
    """
    if os.environ.get("FLUX_PUBLISH_DRY_RUN") == "1":
        fixture = os.path.join(os.path.dirname(__file__), "form_fixture.json")
        with open(fixture) as f:
            return json.load(f)

    query = (
        "query Form($id: ID!) { form(id: $id) { id name questions { "
        "id title type required position "
        "options { id value position } "
        "} } }"
    )
    data = _post({
        "operationName": "Form",
        "query": query,
        "variables": {"id": START_FORM_ID},
    })
    return data["form"]


def create_card(fields: list[dict]) -> dict:
    """Cria um card na etapa Devbox do board de Publicações.

    `fields` é a lista no formato esperado pela mutation `CreateCard`:
        [{"questionId": "...", "type": "shortAnswer", "value": "..."}, ...]
    """
    data = _post({
        "operationName": "CreateCard",
        "variables": {
            "input": {
                "pipeId": PIPE_ID,
                "stageId": START_STAGE_ID,
                "fields": fields,
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": CREATE_CARD_PERSISTED_HASH,
            }
        },
    })
    return data["createCard"]


def card_url(card_id: str) -> str:
    return (
        f"https://app.fluxcontrol.com.br/#/fluxo/{PIPE_ID}"
        f"?view_mode=board&panel=card-detail&card-tab=0&cardId={card_id}"
    )


def _cli() -> None:
    """Pequena CLI: `flux_api.py options` ou `flux_api.py create <json>`.

    `options` imprime o form com opções em JSON.
    `create` lê um JSON `{"fields": [...]}` em stdin e cria o card; com
    `--dry-run` imprime o payload sem chamar a API.
    """
    args = sys.argv[1:]
    if not args:
        print("uso: flux_api.py [options|create [--dry-run]]", file=sys.stderr)
        sys.exit(2)

    cmd = args[0]
    if cmd == "options":
        print(json.dumps(fetch_form_options(), ensure_ascii=False, indent=2))
        return

    if cmd == "create":
        dry = "--dry-run" in args[1:]
        payload = json.loads(sys.stdin.read())
        fields = payload["fields"]
        if dry:
            print(json.dumps({"dry_run": True, "fields": fields}, ensure_ascii=False, indent=2))
            return
        card = create_card(fields)
        print(json.dumps({**card, "url": card_url(card["id"])}, ensure_ascii=False, indent=2))
        return

    print(f"comando desconhecido: {cmd}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        _cli()
    except FluxError as e:
        print(f"erro: {e}", file=sys.stderr)
        sys.exit(1)
