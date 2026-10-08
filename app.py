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


@st.cache_data
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

# -------------------------
# Year
# -------------------------

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

total_for_year = len(year_df)
scored_for_year = year_df["Metascore"].notna().sum()


# -------------------------
# Filters
# -------------------------

search = st.text_input(
    "Search titles",
    placeholder="Search for a show...",
)

if search:
    year_df = year_df[
        year_df["Title"].str.contains(
            search,
            case=False,
            na=False,
        )
    ]


col1, col2, col3, col4 = st.columns(4)

with col1:
    season_type = st.selectbox(
        "Season type",
        [
            "All",
            "New shows",
            "Returning shows",
        ],
    )

with col2:
    scored_only = st.checkbox(
        "Only seasons with a Metascore",
        value=True,
    )

with col3:
    minimum_reviews = st.number_input(
        "Minimum critic reviews",
        min_value=0,
        value=0,
        step=1,
    )

with col4:
    minimum_metascore = st.number_input(
        "Minimum Metascore",
        min_value=0,
        max_value=100,
        value=0,
        step=1,
    )


# -------------------------
# Apply filters
# -------------------------

if season_type == "New shows":
    year_df = year_df[
        year_df["Season"] == 1
    ]

elif season_type == "Returning shows":
    year_df = year_df[
        year_df["Season"] > 1
    ]


if scored_only:
    year_df = year_df[
        year_df["Metascore"].notna()
    ]


if minimum_reviews > 0:
    year_df = year_df[
        year_df["Reviews"].fillna(0)
        >= minimum_reviews
    ]


if minimum_metascore > 0:
    year_df = year_df[
        year_df["Metascore"].notna()
        & (
            year_df["Metascore"]
            >= minimum_metascore
        )
    ]

year_df = year_df.sort_values(
    ["Reviews", "Metascore"],
    ascending=[False, False],
    na_position="last",
)


# -------------------------
# Summary
# -------------------------

st.markdown(
    f"""
**Showing {len(year_df):,} seasons**  
{scored_for_year:,} scored seasons out of
{total_for_year:,} total seasons in {year}
"""
)


# -------------------------
# Table
# -------------------------

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
    width="stretch",
    column_config={
        "Season": st.column_config.NumberColumn(
            "Season",
            format="%d",
        ),
        "Metascore": st.column_config.NumberColumn(
            "Metascore",
            format="%d",
        ),
        "Reviews": st.column_config.NumberColumn(
            "Reviews",
            format="%d",
        ),
        "Positive": st.column_config.NumberColumn(
            "Positive",
            format="%d",
        ),
        "Mixed": st.column_config.NumberColumn(
            "Mixed",
            format="%d",
        ),
        "Negative": st.column_config.NumberColumn(
            "Negative",
            format="%d",
        ),
        "Metacritic": st.column_config.LinkColumn(
            "Link",
            display_text="Open",
        ),
    },
)