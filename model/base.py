"""Base declarativa do SQLAlchemy."""

from sqlalchemy.orm import declarative_base

# Base declarativa compartilhada por todos os modelos do ORM
Base = declarative_base()
