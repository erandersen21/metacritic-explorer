from metacritic.database import (
    SessionLocal,
    SeasonRecord,
    ShowRecord,
    init_db,
)


def main():
    init_db()

    with SessionLocal() as session:
        seasons = (
            session.query(SeasonRecord, ShowRecord)
            .join(
                ShowRecord,
                SeasonRecord.show_id == ShowRecord.id,
            )
            .filter(
                SeasonRecord.season_number > 0,
                SeasonRecord.premiere_date >= "2026-01-01",
                SeasonRecord.premiere_date < "2027-01-01",
            )
            .order_by(
                SeasonRecord.review_count.desc()
            )
            .all()
        )

        print(
            f"{'Reviews':<9}"
            f"{'Score':<7}"
            f"{'Premiere':<13}"
            f"Show"
        )

        print("-" * 80)

        for season, show in seasons:
            print(
                f"{str(season.review_count or 0):<9}"
                f"{str(season.metascore or '-'): <7}"
                f"{season.premiere_date:<13}"
                f"{show.title} — Season "
                f"{season.season_number}"
            )


if __name__ == "__main__":
    main()