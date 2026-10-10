from sqlalchemy import func

from metacritic.database import (
    SessionLocal,
    SeasonRecord,
    ShowRecord,
    init_db,
)

import pandas as pd


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


def calculate_distribution_stats(
    df: pd.DataFrame,
    column: str,
    minimum: float | None = None,
) -> dict:
    values = (
        df[column]
        .dropna()
        .astype(float)
    )

    if minimum is not None:
        values = values[
            values >= minimum
        ]

    if values.empty:
        return {}

    quantiles = values.quantile(
        [0.2, 0.4, 0.6, 0.8]
    )

    return {
        "count": len(values),
        "mean": values.mean(),
        "median": values.median(),
        "min": values.min(),
        "max": values.max(),
        "q20": quantiles.loc[0.2],
        "q40": quantiles.loc[0.4],
        "q60": quantiles.loc[0.6],
        "q80": quantiles.loc[0.8],
    }


def quintile_number(
    value: float | int | None,
    stats: dict,
) -> int | None:
    if pd.isna(value) or not stats:
        return None

    if value <= stats["q20"]:
        return 1

    if value <= stats["q40"]:
        return 2

    if value <= stats["q60"]:
        return 3

    if value <= stats["q80"]:
        return 4

    return 5


def score_quintile_label(
    score: float | int | None,
    stats: dict,
) -> str | None:
    quintile = quintile_number(
        score,
        stats,
    )

    labels = {
        1: "Bottom 20%",
        2: "20th–40th percentile",
        3: "40th–60th percentile",
        4: "60th–80th percentile",
        5: "Top 20%",
    }

    return labels.get(quintile)


def review_quintile_label(
    reviews: float | int | None,
    stats: dict,
) -> str | None:
    if pd.isna(reviews) or reviews <= 0:
        return None

    quintile = quintile_number(
        reviews,
        stats,
    )

    labels = {
        1: "Least reviewed 20%",
        2: "20th–40th percentile",
        3: "40th–60th percentile",
        4: "60th–80th percentile",
        5: "Most reviewed 20%",
    }

    return labels.get(quintile)


if __name__ == "__main__":
    main()