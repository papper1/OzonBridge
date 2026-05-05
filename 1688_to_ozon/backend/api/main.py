from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.auth_routes import router as auth_router
from .routes.crawl_routes import router as crawl_router
from .routes.export_routes import router as export_router
from .routes.health_routes import router as health_router
from .routes.mapping_routes import router as mapping_router
from .routes.translate_routes import router as translate_router


app = FastAPI(
    title="CrawlDesk Pro Backend API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(crawl_router)
app.include_router(translate_router)
app.include_router(mapping_router)
app.include_router(export_router)
