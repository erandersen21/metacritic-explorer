import pandas as pd
import streamlit as st
from sqlalchemy import select

from metacritic.database import (
    SessionLocal,
    SeasonRecord,
    ShowRecord,
    init_db,
)


st.set_page_config(
    page_title="Metacritic Explorer",
    layout="wide",
)

init_db()


def load_seasons() -> pd.DataFrame:
    with SessionLocal() as session:
        rows = session.execute(
            select(
                ShowRecord.title,
                ShowRecord.slug,
                SeasonRecord.season_number,
                SeasonRecord.season_slug,
                SeasonRecord.premiere_date,
                SeasonRecord.metascore,
                SeasonRecord.review_count,
                SeasonRecord.positive_count,
                SeasonRecord.neutral_count,
                SeasonRecord.negative_count,
            )
            .join(
                ShowRecord,
                SeasonRecord.show_id == ShowRecord.id,
            )
            .where(SeasonRecord.season_number > 0)
        ).all()

    records = []

    for row in rows:
        premiere_date = row.premiere_date

        year = None

        if premiere_date and len(premiere_date) >= 4:
            try:
                year = int(premiere_date[:4])
            except ValueError:
                pass

        url = (
            f"https://www.metacritic.com/tv/"
            f"{row.slug}/{row.season_slug}/"
            if row.season_slug
            else None
        )

        records.append(
            {
                "Title": row.title,
                "Season": row.season_number,
                "Premiere": premiere_date,
                "Year": year,
                "Metascore": row.metascore,
                "Reviews": row.review_count,
                "Positive": row.positive_count,
                "Mixed": row.neutral_count,
                "Negative": row.negative_count,
                "Metacritic": url,
            }
        )

    return pd.DataFrame(records)


df = load_seasons()

st.title("Metacritic Explorer")

years = sorted(
    df["Year"].dropna().astype(int).unique(),
    reverse=True,
)

year = st.selectbox(
    "Year",
    years,
    index=years.index(2026) if 2026 in years else 0,
)

year_df = df[df["Year"] == year].copy()

col1, col2, col3 = st.columns(3)

with col1:
    scored_only = st.checkbox(
        "Only seasons with a Metascore",
        value=True,
    )

with col2:
    minimum_reviews = st.number_input(
        "Minimum critic reviews",
        min_value=0,
        value=0,
        step=1,
    )

with col3:
    sort_option = st.selectbox(
        "Sort by",
        [
            "Critic reviews",
            "Metascore",
            "Premiere date",
            "Title",
        ],
    )

if scored_only:
    year_df = year_df[
        year_df["Metascore"].notna()
    ]

year_df = year_df[
    year_df["Reviews"].fillna(0) >= minimum_reviews
]

if sort_option == "Critic reviews":
    year_df = year_df.sort_values(
        ["Reviews", "Metascore"],
        ascending=[False, False],
        na_position="last",
    )

elif sort_option == "Metascore":
    year_df = year_df.sort_values(
        ["Metascore", "Reviews"],
        ascending=[False, False],
        na_position="last",
    )

elif sort_option == "Premiere date":
    year_df = year_df.sort_values(
        "Premiere",
        ascending=False,
        na_position="last",
    )

elif sort_option == "Title":
    year_df = year_df.sort_values(
        ["Title", "Season"],
        ascending=[True, True],
    )

st.write(
    f"**{len(year_df):,} seasons**"
)

display_df = year_df[
    [
        "Title",
        "Season",
        "Premiere",
        "Metascore",
        "Reviews",
        "Positive",
        "Mixed",
        "Negative",
        "Metacritic",
    ]
]

st.dataframe(
    display_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Metacritic": st.column_config.LinkColumn(
            "Link",
            display_text="Open",
        ),
        "Metascore": st.column_config.NumberColumn(
            "Metascore",
            format="%d",
        ),
        "Reviews": st.column_config.NumberColumn(
            "Reviews",
            format="%d",
        ),
    },
)