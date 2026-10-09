from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


DATABASE_URL = "sqlite:///metacritic.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class ShowRecord(Base):
    __tablename__ = "shows"

    # Metacritic's catalog ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
    )

    premiere_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    seasons_fetched: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    seasons_last_fetched: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

class SeasonRecord(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    show_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    show_slug: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    season_number: Mapped[int] = mapped_column(Integer)

    season_slug: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    premiere_date: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    metascore: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    review_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    positive_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    neutral_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    negative_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

class MovieRecord(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(String)

    slug: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    release_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    release_date: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    metascore: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    review_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    positive_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    neutral_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    negative_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    last_fetched: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

def init_db():
    Base.metadata.create_all(engine)