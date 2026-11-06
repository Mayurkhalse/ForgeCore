"""Lightweight in-process ASGI test client shim avoiding external sockets and event loops."""
from __future__ import annotations

import inspect
import json
import urllib.parse
from typing import Any


class _TestResponse:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self.content = body
        self.text = body.decode("utf-8", errors="replace")
        try:
            self._json_data = json.loads(self.text) if self.text else None
        except Exception:
            self._json_data = None

    def json(self) -> Any:
        return self._json_data


def _run_coro_sync(coro: Any) -> Any:
    stack = [coro]
    val = None
    while stack:
        top = stack[-1]
        try:
            nxt = top.send(val)
            if inspect.iscoroutine(nxt):
                stack.append(nxt)
                val = None
            else:
                val = nxt
        except StopIteration as e:
            stack.pop()
            val = e.value
    return val


class TestClient:
    __test__ = False

    def __init__(self, app: Any) -> None:
        self.app = app

    def get(self, url: str, **kwargs: Any) -> _TestResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> _TestResponse:
        return self.request("POST", url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> _TestResponse:
        split = urllib.parse.urlsplit(url)
        path = split.path or "/"
        query = split.query or ""

        headers = kwargs.get("headers")
        req_headers: list[tuple[bytes, bytes]] = []
        if headers:
            for k, v in headers.items():
                req_headers.append((k.lower().encode("latin-1"), str(v).encode("latin-1")))

        body_bytes = b""
        if "json" in kwargs and kwargs["json"] is not None:
            body_bytes = json.dumps(kwargs["json"]).encode("utf-8")
            req_headers.append((b"content-type", b"application/json"))
            req_headers.append((b"content-length", str(len(body_bytes)).encode("ascii")))
        elif "data" in kwargs and kwargs["data"] is not None:
            d = kwargs["data"]
            body_bytes = d if isinstance(d, bytes) else str(d).encode("utf-8")

        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query.encode("ascii"),
            "headers": req_headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }

        req_complete = False

        async def receive() -> dict[str, Any]:
            nonlocal req_complete
            if not req_complete:
                req_complete = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.disconnect"}

        status_code = 500
        resp_headers: dict[str, str] = {}
        resp_body = bytearray()

        async def send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                for k, v in message.get("headers", []):
                    resp_headers[k.decode("latin-1").lower()] = v.decode("latin-1")
            elif message["type"] == "http.response.body":
                resp_body.extend(message.get("body", b""))

        _run_coro_sync(self.app(scope, receive, send))
        return _TestResponse(status_code, resp_headers, bytes(resp_body))


__all__ = ["TestClient"]
