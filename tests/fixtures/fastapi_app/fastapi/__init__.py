"""Lightweight offline FastAPI compatibility shim over Starlette."""
from __future__ import annotations

import inspect
from typing import Any, Callable

from starlette import status
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

__all__ = ["FastAPI", "HTTPException", "Request", "JSONResponse", "status"]


class FastAPI(Starlette):
    def get(self, path: str, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            async def endpoint_wrapper(request: Request) -> Any:
                sig = inspect.signature(func)
                args = [request] if len(sig.parameters) > 0 else []
                if inspect.iscoroutinefunction(func):
                    res = await func(*args)
                else:
                    res = func(*args)
                if isinstance(res, JSONResponse):
                    return res
                return JSONResponse(res)

            self.add_route(path, endpoint_wrapper, methods=["GET"])
            return func
        return decorator

    def post(self, path: str, **kwargs: Any) -> Callable:
        def decorator(func: Callable) -> Callable:
            async def endpoint_wrapper(request: Request) -> Any:
                sig = inspect.signature(func)
                args = [request] if len(sig.parameters) > 0 else []
                if inspect.iscoroutinefunction(func):
                    res = await func(*args)
                else:
                    res = func(*args)
                if isinstance(res, JSONResponse):
                    return res
                return JSONResponse(res)

            self.add_route(path, endpoint_wrapper, methods=["POST"])
            return func
        return decorator
