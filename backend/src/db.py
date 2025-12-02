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
