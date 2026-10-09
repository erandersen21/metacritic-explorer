from datetime import datetime

import pandas as pd
import streamlit as st

from metacritic.database import (
    MovieRecord,
    SeasonRecord,
    SessionLocal,
    ShowRecord,
)


st.set_page_config(
    page_title="Metacritic Explorer",
    page_icon="🎬",
    layout="wide",
)

st.title("Metacritic Explorer")


# ---------------------------------------------------------
# Data loading
# ---------------------------------------------------------

@st.cache_data
def load_seasons() -> pd.DataFrame:
    with SessionLocal() as session:
        rows = (
            session.query(
                ShowRecord.title,
                SeasonRecord.show_slug,
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
                SeasonRecord,
                SeasonRecord.show_id == ShowRecord.id,
            )
            .filter(
                SeasonRecord.season_number != 0
            )
            .all()
        )

    data = []

    for row in rows:
        premiere = row.premiere_date

        year = None

        if premiere and len(premiere) >= 4:
            try:
                year = int(premiere[:4])
            except ValueError:
                pass

        if row.season_slug:
            url = (
                f"https://www.metacritic.com/tv/"
                f"{row.show_slug}/"
                f"{row.season_slug}/"
            )
        else:
            url = (
                f"https://www.metacritic.com/tv/"
                f"{row.show_slug}/"
            )

        data.append(
            {
                "Title": row.title,
                "Season": row.season_number,
                "Premiere": premiere,
                "Year": year,
                "Metascore": row.metascore,
                "Reviews": row.review_count,
                "Positive": row.positive_count,
                "Mixed": row.neutral_count,
                "Negative": row.negative_count,
                "Metacritic": url,
            }
        )

    return pd.DataFrame(data)


@st.cache_data
def load_movies() -> pd.DataFrame:
    with SessionLocal() as session:
        rows = (
            session.query(MovieRecord)
            .all()
        )

    data = []

    for movie in rows:
        data.append(
            {
                "Title": movie.title,
                "Release": movie.release_date,
                "Year": movie.release_year,
                "Metascore": movie.metascore,
                "Reviews": movie.review_count,
                "Positive": movie.positive_count,
                "Mixed": movie.neutral_count,
                "Negative": movie.negative_count,
                "Metacritic": (
                    f"https://www.metacritic.com/"
                    f"movie/{movie.slug}/"
                ),
            }
        )

    return pd.DataFrame(data)


# ---------------------------------------------------------
# Reload button
# ---------------------------------------------------------

if st.button("Reload data"):
    load_seasons.clear()
    load_movies.clear()

    st.session_state["last_reload"] = datetime.now()

    st.rerun()


if "last_reload" in st.session_state:
    st.caption(
        "Data reloaded from SQLite at "
        f"{st.session_state['last_reload'].strftime('%I:%M:%S %p')}"
    )


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------

tv_tab, movies_tab = st.tabs(
    [
        "TV Seasons",
        "Movies",
    ]
)


# =========================================================
# TV
# =========================================================

with tv_tab:
    seasons = load_seasons()

    if seasons.empty:
        st.warning("No TV season data found.")

    else:
        years = sorted(
            seasons["Year"]
            .dropna()
            .astype(int)
            .unique(),
            reverse=True,
        )

        default_year = (
            2026
            if 2026 in years
            else years[0]
        )

        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(default_year),
            key="tv_year",
        )

        search = st.text_input(
            "Search titles",
            key="tv_search",
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            season_type = st.selectbox(
                "Season type",
                [
                    "All",
                    "New shows",
                    "Returning shows",
                ],
                key="tv_season_type",
            )

        with col2:
            scored_only = st.checkbox(
                "Only seasons with a Metascore",
                value=True,
                key="tv_scored_only",
            )

        with col3:
            min_reviews = st.number_input(
                "Minimum critic reviews",
                min_value=0,
                value=0,
                step=1,
                key="tv_min_reviews",
            )

        with col4:
            min_score = st.number_input(
                "Minimum Metascore",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key="tv_min_score",
            )

        year_df = seasons[
            seasons["Year"] == selected_year
        ].copy()

        total_seasons = len(year_df)

        scored_seasons = (
            year_df["Metascore"]
            .notna()
            .sum()
        )

        if search:
            year_df = year_df[
                year_df["Title"]
                .str.contains(
                    search,
                    case=False,
                    na=False,
                )
            ]

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

        year_df = year_df[
            year_df["Reviews"].fillna(0)
            >= min_reviews
        ]

        year_df = year_df[
            year_df["Metascore"].fillna(0)
            >= min_score
        ]

        year_df = year_df.sort_values(
            [
                "Reviews",
                "Metascore",
            ],
            ascending=[
                False,
                False,
            ],
            na_position="last",
        )

        st.subheader(
            f"{selected_year} TV Seasons"
        )

        st.write(
            f"Showing **{len(year_df)}** seasons. "
            f"**{scored_seasons}** scored seasons "
            f"out of **{total_seasons}** total seasons "
            f"in {selected_year}."
        )

        st.dataframe(
            year_df[
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
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Metacritic": st.column_config.LinkColumn(
                    "Metacritic",
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


# =========================================================
# Movies
# =========================================================

with movies_tab:
    movies = load_movies()

    if movies.empty:
        st.warning(
            "No movie data found. "
            "Run a movie sync first."
        )

    else:
        movie_years = sorted(
            movies["Year"]
            .dropna()
            .astype(int)
            .unique(),
            reverse=True,
        )

        default_movie_year = (
            2026
            if 2026 in movie_years
            else movie_years[0]
        )

        selected_movie_year = st.selectbox(
            "Year",
            movie_years,
            index=movie_years.index(
                default_movie_year
            ),
            key="movie_year",
        )

        movie_search = st.text_input(
            "Search titles",
            key="movie_search",
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            movie_scored_only = st.checkbox(
                "Only movies with a Metascore",
                value=True,
                key="movie_scored_only",
            )

        with col2:
            movie_min_reviews = st.number_input(
                "Minimum critic reviews",
                min_value=0,
                value=0,
                step=1,
                key="movie_min_reviews",
            )

        with col3:
            movie_min_score = st.number_input(
                "Minimum Metascore",
                min_value=0,
                max_value=100,
                value=0,
                step=1,
                key="movie_min_score",
            )

        movie_df = movies[
            movies["Year"]
            == selected_movie_year
        ].copy()

        total_movies = len(movie_df)

        scored_movies = (
            movie_df["Metascore"]
            .notna()
            .sum()
        )

        if movie_search:
            movie_df = movie_df[
                movie_df["Title"]
                .str.contains(
                    movie_search,
                    case=False,
                    na=False,
                )
            ]

        if movie_scored_only:
            movie_df = movie_df[
                movie_df["Metascore"].notna()
            ]

        movie_df = movie_df[
            movie_df["Reviews"].fillna(0)
            >= movie_min_reviews
        ]

        movie_df = movie_df[
            movie_df["Metascore"].fillna(0)
            >= movie_min_score
        ]

        movie_df = movie_df.sort_values(
            [
                "Reviews",
                "Metascore",
            ],
            ascending=[
                False,
                False,
            ],
            na_position="last",
        )

        st.subheader(
            f"{selected_movie_year} Movies"
        )

        st.write(
            f"Showing **{len(movie_df)}** movies. "
            f"**{scored_movies}** scored movies "
            f"out of **{total_movies}** total movies "
            f"in {selected_movie_year}."
        )

        st.dataframe(
            movie_df[
                [
                    "Title",
                    "Release",
                    "Metascore",
                    "Reviews",
                    "Positive",
                    "Mixed",
                    "Negative",
                    "Metacritic",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Metacritic": st.column_config.LinkColumn(
                    "Metacritic",
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