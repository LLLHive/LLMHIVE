"""SQLAlchemy models for LLMHIVE."""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class."""


class Example(Base):
    """Example model used by migrations to validate configuration."""

    __tablename__ = "example"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
