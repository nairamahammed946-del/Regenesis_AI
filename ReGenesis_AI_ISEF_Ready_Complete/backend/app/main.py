import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.api.router import api_router
from backend.app.services.demo_seed_service import seed_showcase_data


def ensure_schema_compatibility() -> None:
    """Small additive SQLite migration for databases created by earlier MVP builds."""
    if engine.dialect.name != "sqlite":
        return
    additions = {
        "factories": {
            "data_origin": "VARCHAR(50) NOT NULL DEFAULT 'user_submitted'",
            "source_name": "VARCHAR(255)",
            "source_url": "VARCHAR(1000)",
            "source_date": "VARCHAR(100)",
        },
        "waste_listings": {
            "data_origin": "VARCHAR(50) NOT NULL DEFAULT 'user_submitted'",
            "price_basis": "VARCHAR(120) NOT NULL DEFAULT 'seller_entered'",
            "images_are_illustrative": "BOOLEAN NOT NULL DEFAULT 0",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            present = {row["name"] for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()}
            for column, definition in columns.items():
                if column not in present:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def seed_initial_data():
    """Load source-attributed public facilities and ISEF demo marketplace data idempotently."""
    with SessionLocal() as db:
        counts = seed_showcase_data(db, enable_marketplace_demo=(settings.SEED_DEMO_DATA and settings.ENVIRONMENT.lower() != "production"))
        db.commit()
        print(
            "[REGENESIS DATA] categories={categories}, public_facilities={public_facilities}, "
            "demo_factories={demo_factories}, demo_listings={demo_listings}, demo_matches={demo_matches}".format(**counts)
        )
        print("[REGENESIS DATA] Public directory entries are unverified; demo listings, values and pictures are illustrative only.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    seed_initial_data()
    yield


def create_application() -> FastAPI:
    app = FastAPI(
        title="ReGenesis AI - Industrial Circular Economy Platform",
        description=(
            "AI-powered industrial waste marketplace, material intelligence, explainable matching, "
            "upcycling pathways and preliminary environmental guidance."
        ),
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o for o in settings.CORS_ORIGINS if o != "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
    frontend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.exists(os.path.join(frontend_dir, "index.html")):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    return app


app = create_application()
