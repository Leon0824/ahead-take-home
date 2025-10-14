from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.logging import logger
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
