from contextlib import asynccontextmanager
import time
from typing import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.logging import logger
from app.routers import router
from app.settings import get_settings



_SETTINGS = get_settings()



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator:
    # Startup
    ...
    
	# Run
    yield
    
    # Shutdown
    ...



app = FastAPI(
    version='0.1.0',
    lifespan=lifespan,
    swagger_ui_parameters={
        # Core
        'queryConfigEnabled': True,

        # Display
        'deepLinking': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 0,
        'defaultModelExpandDepth': 3,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'requestSnippetsEnabled': True,

        # Authorization
        'persistAuthorization': True,
    },
)



app.add_middleware(GZipMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_SETTINGS.ALLOW_ORIGINS,
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
    expose_headers=[''],
)
@app.middleware('http')
async def uploding_time_counter(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if "multipart/form-data" in request.headers.get("content-type", ""):
        start = time.perf_counter()
        body = await request.body() # 這是 uvicorn 把全部檔案丟給 FastAPI 的時間，不是上傳時間。
        uploading_time_counter = time.perf_counter() - start
        logger.debug(f"File upload tooks {uploading_time_counter:.3f} seconds")

        request_headers: list[tuple[bytes]] = request.scope['headers']
        request_headers.append((b'uploading-time-counter', str(uploading_time_counter).encode()))
        return await call_next(Request(request.scope, {"type": "http.request", "body": body, "more_body": False}))
    else:
        return await call_next(request)



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning({
        'title': 'Request validation error',
        'instance': {
            'client': request.client,
            'method': request.method,
            'url': request.url,
            'headers': request.headers,
            'exception': exc,
            'exception_body': exc.body,
        },
    })
    return await request_validation_exception_handler(request, exc)



app.include_router(router)