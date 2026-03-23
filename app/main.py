import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from api import router as api_router
from config_logging import get_logger


logger = get_logger(__name__)

app = FastAPI(docs_url='/api/swagger')


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(api_router)
logger.info("Included API router from 'src.api'")


def custom_openapi():
    logger.debug("Generating custom OpenAPI schema")
    if app.openapi_schema:
        logger.debug("OpenAPI schema already exists, returning it")
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Title API",
        version="1.0.0",
        description="Description API service",
        routes=app.routes,
    )
    logger.debug("Base OpenAPI schema generated")

    openapi_schema["components"]["securitySchemes"] = {
        "X-API-KEY": {
            "type": "apiKey",
            "name": "X-API-KEY",
            "in": "header",
        }
    }

    logger.debug("Added BearerAuth security scheme to OpenAPI components")

    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"X-API-KEY": []}]

    logger.info("Applied X-API-KEY security requirement to all operations")
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

logger.info("Application started")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)