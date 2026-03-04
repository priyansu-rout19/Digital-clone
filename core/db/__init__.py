# Database Schema and Session Management
import os


def psycopg_url() -> str:
    """Convert SQLAlchemy DATABASE_URL to raw psycopg format.

    SQLAlchemy uses 'postgresql+psycopg://' but psycopg.connect()
    needs plain 'postgresql://'. This strips the driver suffix.
    """
    return os.environ.get("DATABASE_URL", "").replace("+psycopg", "")
