from sqlalchemy import func

from metacritic.database import (
    SessionLocal,
    SeasonRecord,
    ShowRecord,
    init_db,
)


def main():
    init_db()

    with SessionLocal() as session:
        total_shows = session.query(
            func.count(ShowRecord.id)
        ).scalar()

        fetched_shows = (
            session.query(func.count(ShowRecord.id))
            .filter(ShowRecord.seasons_fetched == True)
            .scalar()
        )

        total_seasons = session.query(
            func.count(SeasonRecord.id)
        ).scalar()

        seasons_2026 = (
            session.query(func.count(SeasonRecord.id))
            .filter(
                SeasonRecord.season_number > 0,
                SeasonRecord.premiere_date >= "2026-01-01",
                SeasonRecord.premiere_date < "2027-01-01",
            )
            .scalar()
        )

        scored_2026 = (
            session.query(func.count(SeasonRecord.id))
            .filter(
                SeasonRecord.season_number > 0,
                SeasonRecord.premiere_date >= "2026-01-01",
                SeasonRecord.premiere_date < "2027-01-01",
                SeasonRecord.metascore != None,
            )
            .scalar()
        )

        print(f"Shows in database:        {total_shows}")
        print(f"Shows processed:          {fetched_shows}")
        print(f"Shows remaining:          {total_shows - fetched_shows}")
        print(f"Total seasons saved:      {total_seasons}")
        print(f"2026 seasons:             {seasons_2026}")
        print(f"2026 seasons with scores: {scored_2026}")


if __name__ == "__main__":
    main()