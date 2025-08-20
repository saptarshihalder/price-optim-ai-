import os
import json
from typing import Iterable, TYPE_CHECKING

import asyncpg

from app.env import mode, Mode

try:
    import databutton as db  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    db = None  # Fallback to environment variables

if TYPE_CHECKING:  # pragma: no cover
    from app.apis.competitor_scraping import ScrapedProduct


async def get_db_connection() -> asyncpg.Connection:
    """Return a new database connection.

    Uses databutton secrets in production if available, otherwise falls
    back to the ``DATABASE_URL`` environment variable. Raises RuntimeError
    if no database URL can be determined.
    """
    if db is not None:
        if mode == Mode.PROD:
            db_url = db.secrets.get("DATABASE_URL_ADMIN_PROD")
        else:
            db_url = db.secrets.get("DATABASE_URL_ADMIN_DEV")
    else:
        db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("Database URL not configured")

    return await asyncpg.connect(db_url)


async def save_scraped_products(products: Iterable["ScrapedProduct"]) -> None:
    """Persist scraped products to the database.

    Creates the ``scraped_products`` table if it does not already exist and
    inserts or updates each product. Products are matched on ``product_url``
    to avoid duplicates.
    """
    products = list(products)
    if not products:
        return

    conn = await get_db_connection()
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scraped_products (
                id SERIAL PRIMARY KEY,
                store_name TEXT,
                product_id TEXT,
                title TEXT,
                price DOUBLE PRECISION,
                currency TEXT,
                brand TEXT,
                description TEXT,
                image_url TEXT,
                product_url TEXT UNIQUE,
                in_stock BOOLEAN,
                scraped_at TIMESTAMPTZ,
                match_score DOUBLE PRECISION,
                match_confidence TEXT,
                match_reasoning TEXT,
                raw_data JSONB
            )
            """
        )

        insert_sql = """
            INSERT INTO scraped_products (
                store_name, product_id, title, price, currency, brand,
                description, image_url, product_url, in_stock, scraped_at,
                match_score, match_confidence, match_reasoning, raw_data
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11,
                $12, $13, $14, $15
            )
            ON CONFLICT (product_url) DO UPDATE SET
                price = EXCLUDED.price,
                in_stock = EXCLUDED.in_stock,
                scraped_at = EXCLUDED.scraped_at,
                match_score = EXCLUDED.match_score,
                match_confidence = EXCLUDED.match_confidence,
                match_reasoning = EXCLUDED.match_reasoning,
                raw_data = EXCLUDED.raw_data
        """

        await conn.executemany(
            insert_sql,
            [
                (
                    p.store_name,
                    p.product_id,
                    p.title,
                    p.price,
                    p.currency,
                    p.brand,
                    p.description,
                    p.image_url,
                    p.product_url,
                    p.in_stock,
                    p.scraped_at,
                    p.match_score,
                    p.match_confidence,
                    p.match_reasoning,
                    json.dumps(p.raw_data),
                )
                for p in products
            ],
        )
    finally:
        await conn.close()
