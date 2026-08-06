"""ASGI middleware: honor X-Client-Request-Id on clinical mutating requests."""

from __future__ import annotations

import json
import logging

from fastapi import Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from database import SessionLocal
from services.client_request_idempotency import (
    find_idempotent_response,
    hash_request_body,
    store_idempotent_response,
)

logger = logging.getLogger(__name__)

_MUTATING = {"POST", "PUT", "PATCH"}


class ClientRequestIdempotencyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        if method not in _MUTATING or not path.startswith("/clinical"):
            await self.app(scope, receive, send)
            return

        headers = {
            (k.decode("latin-1").lower()): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        req_id = (headers.get("x-client-request-id") or "").strip()
        if not req_id:
            await self.app(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if not message.get("more_body"):
                break

        body_bytes = bytes(body)
        request_hash = hash_request_body(body_bytes)

        db = SessionLocal()
        try:
            existing = find_idempotent_response(
                db, client_request_id=req_id, request_hash=request_hash
            )
            if existing is not None and existing.request_hash != request_hash:
                conflict = JSONResponse(
                    status_code=409,
                    content={
                        "detail": "X-Client-Request-Id reuse with a different payload",
                        "client_request_id": req_id,
                    },
                )
                await conflict(scope, receive, send)
                return
            if existing is not None and existing.request_hash == request_hash:
                replay = Response(
                    content=existing.response_body or "",
                    status_code=existing.status_code,
                    media_type="application/json",
                    headers={"X-Idempotent-Replay": "true"},
                )
                await replay(scope, receive, send)
                return
        finally:
            db.close()

        async def receive_replay() -> Message:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        status_code_box: dict[str, int] = {}
        response_headers: list[tuple[bytes, bytes]] = []
        response_chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code_box["status"] = int(message["status"])
                response_headers[:] = list(message.get("headers") or [])
                await send(message)
                return
            if message["type"] == "http.response.body":
                chunk = message.get("body", b"") or b""
                response_chunks.append(chunk)
                more = bool(message.get("more_body"))
                if not more:
                    status = status_code_box.get("status", 500)
                    raw = b"".join(response_chunks)
                    if 200 <= status < 300:
                        store_db = SessionLocal()
                        try:
                            store_idempotent_response(
                                store_db,
                                client_request_id=req_id,
                                method=method,
                                path=path,
                                request_hash=request_hash,
                                status_code=status,
                                response_body=raw.decode("utf-8", errors="replace"),
                            )
                        except Exception:
                            logger.exception("Failed to persist idempotency key %s", req_id)
                        finally:
                            store_db.close()
                await send(message)
                return
            await send(message)

        await self.app(scope, receive_replay, send_wrapper)
