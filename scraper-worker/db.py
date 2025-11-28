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


def get_destination(destination_id: int) -> dict:
    """Get destination info from database."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT d.id, d.location_name, g.adults, g.teens, g.child, g.pets, 
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
                ON CONFLICT (user_id) DO UPDATE SET
                    destination_id = EXCLUDED.destination_id,
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


def insert_property(property_data: dict) -> str:
    """Insert or update a property in the database. Returns the airbnb_id."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO properties (airbnb_id, title, price_per_night, bnb_rating, bnb_review_count, 
                                    main_image_url, min_bedrooms, min_beds, min_bathrooms, property_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (airbnb_id) DO UPDATE SET
                title = EXCLUDED.title,
                price_per_night = EXCLUDED.price_per_night,
                bnb_rating = EXCLUDED.bnb_rating,
                bnb_review_count = EXCLUDED.bnb_review_count,
                main_image_url = EXCLUDED.main_image_url,
                min_bedrooms = COALESCE(properties.min_bedrooms, EXCLUDED.min_bedrooms),
                min_beds = COALESCE(properties.min_beds, EXCLUDED.min_beds),
                min_bathrooms = COALESCE(properties.min_bathrooms, EXCLUDED.min_bathrooms),
                property_type = COALESCE(properties.property_type, EXCLUDED.property_type)
            RETURNING airbnb_id
            """,
            (
                property_data.get("airbnb_id"),
                property_data.get("title"),
                property_data.get("price_per_night"),
                property_data.get("rating"),
                property_data.get("review_count"),
                property_data.get("main_image_url"),
                property_data.get("min_bedrooms"),
                property_data.get("min_beds"),
                property_data.get("min_bathrooms"),
                property_data.get("property_type"),
            ),
        )
        return cursor.fetchone()["airbnb_id"]


def add_property_to_group_candidates(group_id: int, property_id: str):
    """Add a property to group candidates."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO group_candidates (group_id, property_id, added_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (group_id, property_id) DO NOTHING
            """,
            (group_id, property_id),
        )


def get_group_id_for_destination(destination_id: int) -> int:
    """Get the group ID for a destination."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT group_id FROM destinations WHERE id = %s",
            (destination_id,),
        )
        result = cursor.fetchone()
        if result:
            return result["group_id"]
        return None
