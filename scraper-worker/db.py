import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Database configuration from environment variables
DB_CONFIG = {
    "host": os.getenv("PG_HOST", "db"),
    "port": os.getenv("PG_PORT", "5432"),
    "user": os.getenv("PG_USERNAME", "postgres"),
    "password": os.getenv("PG_PASSWORD", "postgres"),
    "dbname": os.getenv("PG_NAME", "postgres"),
}


def get_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def get_cursor():
    """Context manager for database cursor with automatic commit/rollback."""
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def get_user_filter(user_id: int) -> dict:
    """Get user filter from database."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT min_price, max_price, min_bedrooms, min_beds, min_bathrooms, property_type
            FROM user_filters
            WHERE user_id = %s
            """,
            (user_id,),
        )
        result = cursor.fetchone()
        if result:
            return dict(result)
        return {}


def get_filter_amenities(user_id: int) -> list:
    """Get amenity IDs from user's filter."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT amenity_id
            FROM filter_amenities
            WHERE user_id = %s
            """,
            (user_id,),
        )
        results = cursor.fetchall()
        return [row["amenity_id"] for row in results]


def get_destination(destination_id: int) -> dict:
    """Get destination info from database including group info."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT d.id, d.group_id, d.location_name, g.adults, g.children, g.infants, g.pets, 
                   g.date_range_start, g.date_range_end
            FROM destinations d
            JOIN groups g ON d.group_id = g.id
            WHERE d.id = %s
            """,
            (destination_id,),
        )
        result = cursor.fetchone()
        if result:
            return dict(result)
        return {}


def update_filter_request_progress(user_id: int, destination_id: int, pages_fetched: int, pages_total: int = None):
    """Update or create filter request progress."""
    with get_cursor() as cursor:
        if pages_total is not None:
            cursor.execute(
                """
                INSERT INTO filter_request (user_id, destination_id, pages_fetched, pages_total)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, destination_id) DO UPDATE SET
                    pages_fetched = EXCLUDED.pages_fetched,
                    pages_total = EXCLUDED.pages_total
                """,
                (user_id, destination_id, pages_fetched, pages_total),
            )
        else:
            cursor.execute(
                """
                UPDATE filter_request
                SET pages_fetched = %s
                WHERE user_id = %s AND destination_id = %s
                """,
                (pages_fetched, user_id, destination_id),
            )


def insert_bnb(bnb_data: dict) -> str:
    """Insert or update a bnb in the database. Returns the airbnb_id."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO bnbs (airbnb_id, group_id, destination_id, title, price_per_night, bnb_rating, 
                              bnb_review_count, main_image_url, min_bedrooms, min_beds, min_bathrooms, property_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (airbnb_id) DO UPDATE SET
                title = EXCLUDED.title,
                price_per_night = EXCLUDED.price_per_night,
                bnb_rating = EXCLUDED.bnb_rating,
                bnb_review_count = EXCLUDED.bnb_review_count,
                main_image_url = EXCLUDED.main_image_url,
                min_bedrooms = GREATEST(bnbs.min_bedrooms, EXCLUDED.min_bedrooms),
                min_beds = GREATEST(bnbs.min_beds, EXCLUDED.min_beds),
                min_bathrooms = GREATEST(bnbs.min_bathrooms, EXCLUDED.min_bathrooms),
                property_type = COALESCE(bnbs.property_type, EXCLUDED.property_type)
            RETURNING airbnb_id
            """,
            (
                bnb_data.get("airbnb_id"),
                bnb_data.get("group_id"),
                bnb_data.get("destination_id"),
                bnb_data.get("title"),
                bnb_data.get("price_per_night"),
                bnb_data.get("rating"),
                bnb_data.get("review_count"),
                bnb_data.get("main_image_url"),
                bnb_data.get("min_bedrooms"),
                bnb_data.get("min_beds"),
                bnb_data.get("min_bathrooms"),
                bnb_data.get("property_type"),
            ),
        )
        return cursor.fetchone()["airbnb_id"]


def insert_bnb_images(airbnb_id: str, image_urls: list):
    """Insert additional images for a bnb."""
    if not image_urls:
        return
    
    with get_cursor() as cursor:
        for image_url in image_urls:
            cursor.execute(
                """
                INSERT INTO bnb_images (airbnb_id, image_url)
                VALUES (%s, %s)
                ON CONFLICT (airbnb_id, image_url) DO NOTHING
                """,
                (airbnb_id, image_url),
            )


def insert_bnb_amenities(airbnb_id: str, amenity_ids: list):
    """Insert amenities for a bnb."""
    if not amenity_ids:
        return
    
    with get_cursor() as cursor:
        for amenity_id in amenity_ids:
            cursor.execute(
                """
                INSERT INTO bnb_amenities (airbnb_id, amenity_id)
                VALUES (%s, %s)
                ON CONFLICT (airbnb_id, amenity_id) DO NOTHING
                """,
                (airbnb_id, amenity_id),
            )
