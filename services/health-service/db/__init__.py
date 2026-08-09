"""
health-service/db/__init__.py

Exports the shared SQLAlchemy Base and ScopedRepository for use in
health-service models and repositories.
"""

from .base_repository import Base, ScopedRepository

__all__ = ["Base", "ScopedRepository"]
