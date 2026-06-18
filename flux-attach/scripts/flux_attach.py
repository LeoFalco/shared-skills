"""Cliente fino para upload de anexos a um card do Flux (Isengard).

Usado pela skill `flux-attach` para subir arquivos (APKs, AABs, imagens,
PDFs, etc.) e vinculá-los a um card já existente no Flux.

O upload NÃO é GraphQL — o app web do Flux usa um fluxo de presigned POST
S3 em 3 passos, replicado aqui:

  1. query `GetPreSignedPost(pipeId, name, mimeType)` -> { url, fields }
     (o servidor já gera a `key` e a devolve em `fields["key"]`)
  2. POST multipart do arquivo na `url` do S3/CloudFront com os `fields`
     + o binário no campo `file` (sucesso = HTTP 201)
  3. mutation `CreateCardAttachment(cardId, key, name, mimeType, size)`
     que registra o anexo no card

Autenticação via JWT lido de `$FLUX_JWT` — o mesmo token usado pela skill
`flux-publish`. Pega ele no DevTools do app web do Flux (Network ->
qualquer request -> header `authorization`) e exporta:

    export FLUX_JWT='eyJhbGciOiJI...'

Se algum request falhar com erro de autenticação, exporte um token novo.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any

ENDPOINT = "https://isengard.fluxcontrol.com.br/api/graphql"
PIPE_ID = "ac4db338-c7eb-452e-b75a-978abe03c8b6"  # Produto FSM - Publicações

# Limite padrão do servidor para anexos não-CAD (presigned-url.service.ts).
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

# Extensões aceitas pelo servidor (upload.service.ts ALLOWED_EXTENSIONS_GROUPED).
ALLOWED_EXTENSIONS = {
    # image
    "gif", "bmp", "tiff", "jpeg", "jpg", "png", "svg", "webp", "heic", "heif",
    # video
    "mp4", "avi", "mov", "mkv", "webm",
    # audio
    "mp3", "wav", "ogg", "flac", "aac", "m4a",
    # document
    "txt", "csv", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "rft", "odt", "ods", "odp", "md", "xml", "json",
    # email
    "eml", "msg",
    # cad
    "rvt", "dwg", "dxf",
    # archive (apk incluído)
    "zip", "rar", "7z", "tar", "gz", "apk",
}

# Overrides de mimeType para extensões que o `mimetypes` da stdlib não acerta.
MIME_OVERRIDES = {
    "apk": "application/vnd.android.package-archive",
    "aab": "application/octet-stream",
}


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
    """POST GraphQL no Isengard. Mesmo padrão da skill flux-publish."""
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


def guess_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def get_presigned_post(pipe_id: str, name: str, mime_type: str) -> dict[str, Any]:
    """Passo 1: pede a URL assinada e os campos do form S3.

    Query inline (não persisted) — mesmo motivo da flux-publish: o servidor
    responde `PersistedQueryNotFound` para hashes não registrados em cache.
    O retorno traz `url` e `fields`; `fields["key"]` é o path no storage.
    """
    query = (
        "query GetPreSignedPost($input: CreatePreSignedPostInput!) {"
        " getPreSignedPost(input: $input) { url fields } }"
    )
    data = _post({
        "operationName": "GetPreSignedPost",
        "query": query,
        "variables": {
            "input": {"pipeId": pipe_id, "name": name, "mimeType": mime_type}
        },
    })
    return data["getPreSignedPost"]


def _encode_multipart(fields: dict[str, Any], file_path: str, file_field: str = "file") -> tuple[bytes, str]:
    """Monta o corpo multipart/form-data.

    Os `fields` vão na ordem recebida e o arquivo é o ÚLTIMO campo — o S3
    exige que o binário venha depois de todos os campos da policy.
    Retorna (corpo_em_bytes, content_type_header).
    """
    boundary = f"----fluxattach{uuid.uuid4().hex}"
    crlf = b"\r\n"
    parts: list[bytes] = []

    for key, value in fields.items():
        parts.append(f"--{boundary}".encode())
        parts.append(f'Content-Disposition: form-data; name="{key}"'.encode())
        parts.append(b"")
        parts.append(str(value).encode())

    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    parts.append(f"--{boundary}".encode())
    parts.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"'.encode()
    )
    parts.append(b"Content-Type: application/octet-stream")
    parts.append(b"")
    parts.append(file_bytes)
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")

    body = crlf.join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def upload_to_s3(url: str, fields: dict[str, Any], file_path: str) -> int:
    """Passo 2: POST multipart do arquivo no S3/CloudFront. Sucesso = 201."""
    body, content_type = _encode_multipart(fields, file_path)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        hint = ""
        if e.code in (401, 403):
            hint = " (token/policy do presigned expirou ou Content-Type não bate)"
        elif e.code == 413:
            hint = " (arquivo maior que o permitido)"
        raise FluxError(f"S3 HTTP {e.code}{hint}: {detail}") from e
    except urllib.error.URLError as e:
        raise FluxError(f"Falha de rede no upload S3: {e}") from e


def create_card_attachment(card_id: str, key: str, name: str, mime_type: str, size: int) -> dict:
    """Passo 3: registra o anexo no card. Query inline (não persisted)."""
    query = (
        "mutation CreateCardAttachment($input: CreateCardAttachmentInput!) {"
        " createCardAttachment(input: $input) {"
        " id name path type size extension createdAt } }"
    )
    data = _post({
        "operationName": "CreateCardAttachment",
        "query": query,
        "variables": {
            "input": {
                "cardId": card_id,
                "key": key,
                "name": name,
                "mimeType": mime_type,
                "size": size,
            }
        },
    })
    return data["createCardAttachment"]


def card_url(card_id: str) -> str:
    return (
        f"https://app.fluxcontrol.com.br/#/fluxo/{PIPE_ID}"
        f"?view_mode=board&panel=card-detail&card-tab=0&cardId={card_id}"
    )


def upload(card_id: str, file_path: str, pipe_id: str, mime_type: str | None, dry_run: bool, force: bool) -> dict:
    """Fluxo completo dos 3 passos para um arquivo."""
    if not os.path.isfile(file_path):
        raise FluxError(f"Arquivo não encontrado: {file_path}")

    name = os.path.basename(file_path)
    size = os.path.getsize(file_path)
    mime = mime_type or guess_mime(name)
    ext = file_extension(name)

    if ext and ext not in ALLOWED_EXTENSIONS:
        raise FluxError(
            f"Extensão '.{ext}' não está no allowlist do Flux. "
            f"Permitidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if size > MAX_UPLOAD_SIZE and not force:
        mb = size / (1024 * 1024)
        raise FluxError(
            f"Arquivo tem {mb:.1f} MB, acima do limite de 100 MB do Flux. "
            f"Use --force para tentar mesmo assim (o servidor pode rejeitar)."
        )

    if dry_run:
        return {
            "dry_run": True,
            "cardId": card_id,
            "pipeId": pipe_id,
            "file": file_path,
            "name": name,
            "mimeType": mime,
            "size": size,
            "steps": [
                "1) GetPreSignedPost(pipeId, name, mimeType)",
                "2) POST multipart no S3 (esperando 201)",
                "3) CreateCardAttachment(cardId, key, name, mimeType, size)",
            ],
            "cardUrl": card_url(card_id),
        }

    presigned = get_presigned_post(pipe_id, name, mime)
    fields = presigned["fields"]
    url = presigned["url"]
    key = fields.get("key")
    if not key:
        raise FluxError(
            "Resposta do GetPreSignedPost não trouxe 'key' em fields — "
            f"campos recebidos: {sorted(fields.keys())}"
        )

    status = upload_to_s3(url, fields, file_path)
    if status != 201:
        raise FluxError(f"Upload S3 retornou status {status}, esperado 201.")

    try:
        attachment = create_card_attachment(card_id, key, name, mime, size)
    except FluxError as e:
        # O arquivo já está no S3; expor a key para registro manual.
        raise FluxError(
            f"Arquivo subiu pro S3 (key={key}) mas o CreateCardAttachment "
            f"falhou: {e}. Dá pra registrar manualmente com essa key."
        ) from e

    return {**attachment, "cardUrl": card_url(card_id)}


def _cli() -> None:
    """CLI: flux_attach.py presign|upload.

    presign <pipeId> <name> <mimeType>
        imprime { url, fields } da query GetPreSignedPost.

    upload <cardId> <arquivo> [--pipe <pipeId>] [--mime <mimeType>]
           [--dry-run] [--force]
        faz os 3 passos e imprime o attachment criado.
    """
    args = sys.argv[1:]
    if not args:
        print(
            "uso: flux_attach.py [presign <pipeId> <name> <mimeType> | "
            "upload <cardId> <arquivo> [--pipe <pipeId>] [--mime <mimeType>] "
            "[--dry-run] [--force]]",
            file=sys.stderr,
        )
        sys.exit(2)

    cmd = args[0]

    if cmd == "presign":
        rest = args[1:]
        if len(rest) < 3:
            print("uso: flux_attach.py presign <pipeId> <name> <mimeType>", file=sys.stderr)
            sys.exit(2)
        pipe_id, name, mime = rest[0], rest[1], rest[2]
        print(json.dumps(get_presigned_post(pipe_id, name, mime), ensure_ascii=False, indent=2))
        return

    if cmd == "upload":
        rest = args[1:]
        dry_run = "--dry-run" in rest
        force = "--force" in rest
        rest = [a for a in rest if a not in ("--dry-run", "--force")]

        pipe_id = PIPE_ID
        mime_type: str | None = None
        positional: list[str] = []
        i = 0
        while i < len(rest):
            if rest[i] == "--pipe" and i + 1 < len(rest):
                pipe_id = rest[i + 1]
                i += 2
            elif rest[i] == "--mime" and i + 1 < len(rest):
                mime_type = rest[i + 1]
                i += 2
            else:
                positional.append(rest[i])
                i += 1

        if len(positional) < 2:
            print(
                "uso: flux_attach.py upload <cardId> <arquivo> "
                "[--pipe <pipeId>] [--mime <mimeType>] [--dry-run] [--force]",
                file=sys.stderr,
            )
            sys.exit(2)

        card_id, file_path = positional[0], positional[1]
        result = upload(card_id, file_path, pipe_id, mime_type, dry_run, force)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"comando desconhecido: {cmd}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        _cli()
    except FluxError as e:
        print(f"erro: {e}", file=sys.stderr)
        sys.exit(1)
