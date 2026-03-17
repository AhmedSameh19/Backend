import re

import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="AIESEC Egypt CRM API")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return JSON with error detail for unhandled exceptions (500) so you see the real error."""
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


class StripXFrameOptionsMiddleware(BaseHTTPMiddleware):
    """Remove X-Frame-Options so our proxy and other endpoints can be embedded in iframes when needed."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if "x-frame-options" in response.headers:
            del response.headers["x-frame-options"]
        return response


app.add_middleware(StripXFrameOptionsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint - returns API information"""
    return {
        "message": "AIESEC Egypt CRM API",
        "version": "v1",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/market-research/podio-form-proxy", response_class=HTMLResponse)
def podio_form_proxy():
    """Proxy Podio webform for iframe embedding (bypasses X-Frame-Options)."""
    form_url = settings.PODIO_WEBFORM_URL
    try:
        resp = requests.get(
            form_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=30,
        )
        resp.raise_for_status()
        html = resp.text
        base = "https://podio.com"
        # Rewrite relative URLs to absolute
        def _replace(m):
            attr, val = m.group(1), m.group(2)
            if val.startswith(("//", "http", "mailto:", "#")):
                return m.group(0)
            if val.startswith("/"):
                return f'{attr}="{base}{val}"'
            return m.group(0)
        html = re.sub(r'(href|src|action)=["\']([^"\']+)["\']', _replace, html)
        return HTMLResponse(
            content=html,
            headers={"Content-Security-Policy": "frame-ancestors 'self' http://localhost:3000 http://localhost:5173 https://localhost:3000 https://localhost:5173"},
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Podio form: {str(e)}")


@app.api_route("/webforms/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def podio_webforms_proxy(path: str, request: Request):
    """Proxy Podio webform API calls (e.g. items_search) so the embedded form works."""
    url = f"https://podio.com/webforms/{path}"
    try:
        if request.method == "OPTIONS":
            return Response(status_code=200)
        params = dict(request.query_params)
        headers = {
            "User-Agent": request.headers.get("user-agent", "Mozilla/5.0"),
            "Accept": request.headers.get("accept", "*/*"),
            "Accept-Language": request.headers.get("accept-language", "en-US,en;q=0.9"),
        }
        if request.method == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        else:
            body = await request.body()
            resp = requests.post(url, params=params, data=body, headers=headers, timeout=30)
        # Forward only safe response headers (avoid Set-Cookie, etc.)
        out_headers = {}
        for k, v in resp.headers.items():
            if k.lower() not in ("set-cookie", "x-frame-options", "content-encoding"):
                out_headers[k] = v
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=out_headers,
            media_type=resp.headers.get("Content-Type"),
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Podio proxy error: {str(e)}")


app.include_router(api_router, prefix="/api/v1")
