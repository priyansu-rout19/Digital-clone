"""
Pytest configuration for Digital Clone Engine tests.

Configures pytest-asyncio for async test support and loads .env for tests.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env at test session startup
load_dotenv()

# Configure pytest-asyncio for async test support
pytest_plugins = ('pytest_asyncio',)
