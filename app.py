import asyncio
from datetime import datetime

import pandas as pd
import streamlit as st

from metacritic.database import (
    MovieRecord,
    SeasonRecord,
    SessionLocal,
    ShowRecord,
)

from stats import (
    calculate_distribution_stats,
    get_benchmark_population,
    review_quintile_label,
    score_quintile_label,
)

from sync import refresh_all


# =========================================================
# Page setup
# =========================================================

st.set_page_config(
    page_title="Metacritic Explorer",
    page_icon="🎬",
    layout="wide",
)

st.title("Metacritic Explorer")

current_year = datetime.now().year


# =========================================================
# Data loading
# =========================================================

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


# =========================================================
# Distribution display helper
# =========================================================

def render_stats_column(
    heading: str,
    stats: dict,
):
    st.markdown(f"#### {heading}")

    if not stats:
        st.write("No data available.")
        return

    st.write(
        f"**Average:** "
        f"{stats['mean']:.1f}"
    )

    st.write(
        f"**Median:** "
        f"{stats['median']:.1f}"
    )

    st.write(
        f"**20th percentile:** "
        f"{stats['q20']:.1f}"
    )

    st.write(
        f"**40th percentile:** "
        f"{stats['q40']:.1f}"
    )

    st.write(
        f"**60th percentile:** "
        f"{stats['q60']:.1f}"
    )

    st.write(
        f"**80th percentile:** "
        f"{stats['q80']:.1f}"
    )


# =========================================================
# Data controls
# =========================================================

control_col1, control_col2, control_col3 = st.columns(
    [1, 1, 3]
)

with control_col1:
    refresh_year = st.number_input(
        "Refresh year",
        min_value=1900,
        max_value=current_year + 5,
        value=current_year,
        step=1,
    )

with control_col2:
    st.write("")
    st.write("")

    reload_clicked = st.button(
        "Reload local data"
    )

with control_col3:
    st.write("")
    st.write("")

    refresh_clicked = st.button(
        "Refresh from Metacritic",
        type="primary",
    )


if reload_clicked:
    load_seasons.clear()
    load_movies.clear()

    st.session_state["last_reload"] = (
        datetime.now()
    )

    st.rerun()


if refresh_clicked:
    with st.spinner(
        f"Refreshing {refresh_year} "
        "TV and movie data..."
    ):
        try:
            asyncio.run(
                refresh_all(
                    year=int(refresh_year)
                )
            )

            load_seasons.clear()
            load_movies.clear()

            st.session_state["last_refresh"] = (
                datetime.now()
            )

            st.session_state[
                "refresh_success"
            ] = True

        except Exception as error:
            st.session_state[
                "refresh_error"
            ] = str(error)

    st.rerun()


if st.session_state.pop(
    "refresh_success",
    False,
):
    st.success(
        "Metacritic refresh completed successfully."
    )


if "refresh_error" in st.session_state:
    st.error(
        "Refresh failed: "
        + st.session_state.pop(
            "refresh_error"
        )
    )


if "last_refresh" in st.session_state:
    st.caption(
        "Last Metacritic refresh: "
        f"{st.session_state['last_refresh'].strftime('%I:%M:%S %p')}"
    )

elif "last_reload" in st.session_state:
    st.caption(
        "Local data reloaded at "
        f"{st.session_state['last_reload'].strftime('%I:%M:%S %p')}"
    )


# =========================================================
# Tabs
# =========================================================

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
        st.warning(
            "No TV season data found."
        )

    else:
        # -------------------------------------------------
        # Year selection
        # -------------------------------------------------

        years = sorted(
            seasons["Year"]
            .dropna()
            .astype(int)
            .unique(),
            reverse=True,
        )

        default_year = (
            current_year
            if current_year in years
            else years[0]
        )

        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(
                default_year
            ),
            key="tv_year",
        )

        # -------------------------------------------------
        # Search
        # -------------------------------------------------

        search = st.text_input(
            "Search titles",
            key="tv_search",
        )

        # -------------------------------------------------
        # Main filters
        # -------------------------------------------------

        col1, col2, col3, col4 = (
            st.columns(4)
        )

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

        # -------------------------------------------------
        # Quintile filters
        # -------------------------------------------------

        quintile_col1, quintile_col2 = (
            st.columns(2)
        )

        with quintile_col1:
            selected_score_quintiles = (
                st.multiselect(
                    "Score quintiles",
                    [
                        "Top 20%",
                        "60th–80th percentile",
                        "40th–60th percentile",
                        "20th–40th percentile",
                        "Bottom 20%",
                    ],
                    key="tv_score_quintiles",
                )
            )

        with quintile_col2:
            selected_review_quintiles = (
                st.multiselect(
                    "Review-count quintiles",
                    [
                        "Most reviewed 20%",
                        "60th–80th percentile",
                        "40th–60th percentile",
                        "20th–40th percentile",
                        "Least reviewed 20%",
                    ],
                    key="tv_review_quintiles",
                )
            )

        # -------------------------------------------------
        # Selected-year population
        # -------------------------------------------------

        year_df = seasons[
            seasons["Year"]
            == selected_year
        ].copy()

        total_seasons = len(year_df)

        scored_seasons = (
            year_df["Metascore"]
            .notna()
            .sum()
        )

        # -------------------------------------------------
        # Current-year statistics
        # -------------------------------------------------

        tv_current_score_stats = (
            calculate_distribution_stats(
                year_df,
                "Metascore",
            )
        )

        tv_current_scored_population = (
            year_df[
                year_df["Metascore"]
                .notna()
            ]
        )

        tv_current_review_stats = (
            calculate_distribution_stats(
                tv_current_scored_population,
                "Reviews",
            )
        )

        # -------------------------------------------------
        # Five-year benchmark
        # -------------------------------------------------

        (
            tv_benchmark_df,
            tv_benchmark_years,
            tv_missing_benchmark_years,
        ) = get_benchmark_population(
            seasons,
            selected_year,
        )

        tv_benchmark_scored = (
            tv_benchmark_df[
                tv_benchmark_df[
                    "Metascore"
                ].notna()
            ]
        )

        tv_benchmark_score_stats = (
            calculate_distribution_stats(
                tv_benchmark_scored,
                "Metascore",
            )
        )

        tv_benchmark_review_stats = (
            calculate_distribution_stats(
                tv_benchmark_scored,
                "Reviews",
            )
        )


        # -------------------------------------------------
        # Assign benchmark quintile categories
        # -------------------------------------------------

        if (
            not tv_missing_benchmark_years
            and tv_benchmark_score_stats
        ):
            year_df[
                "Score Quintile"
            ] = (
                year_df["Metascore"].apply(
                    lambda score:
                    score_quintile_label(
                        score,
                        tv_benchmark_score_stats,
                    )
                )
            )

        else:
            year_df[
                "Score Quintile"
            ] = None


        if (
            not tv_missing_benchmark_years
            and tv_benchmark_review_stats
        ):
            year_df[
                "Review Quintile"
            ] = year_df.apply(
                lambda row: (
                    review_quintile_label(
                        row["Reviews"],
                        tv_benchmark_review_stats,
                    )
                    if pd.notna(
                        row["Metascore"]
                    )
                    else None
                ),
                axis=1,
            )

        else:
            year_df[
                "Review Quintile"
            ] = None

        # -------------------------------------------------
        # User filters
        # -------------------------------------------------

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

        elif (
            season_type
            == "Returning shows"
        ):
            year_df = year_df[
                year_df["Season"] > 1
            ]

        if scored_only:
            year_df = year_df[
                year_df[
                    "Metascore"
                ].notna()
            ]

        year_df = year_df[
            year_df["Reviews"]
            .fillna(0)
            >= min_reviews
        ]

        year_df = year_df[
            year_df["Metascore"]
            .fillna(0)
            >= min_score
        ]

        if selected_score_quintiles:
            year_df = year_df[
                year_df[
                    "Score Quintile"
                ].isin(
                    selected_score_quintiles
                )
            ]

        if selected_review_quintiles:
            year_df = year_df[
                year_df[
                    "Review Quintile"
                ].isin(
                    selected_review_quintiles
                )
            ]

        # -------------------------------------------------
        # Default sorting
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        st.subheader(
            f"{selected_year} TV Seasons"
        )

        st.write(
            f"Showing **{len(year_df)}** seasons. "
            f"**{scored_seasons}** scored seasons "
            f"out of **{total_seasons}** total "
            f"seasons in {selected_year}."
        )

        # -------------------------------------------------
        # Benchmark status
        # -------------------------------------------------

        if (
            not tv_missing_benchmark_years
            and tv_benchmark_score_stats
            and tv_benchmark_review_stats
        ):
            st.caption(
                "Quintile categories are based on "
                "scored TV seasons from "
                f"{tv_benchmark_years[0]}"
                f"–{tv_benchmark_years[-1]}."
            )

        else:
            st.warning(
                "A complete five-year benchmark "
                "is not available for this year. "
                "Missing: "
                + ", ".join(
                    str(year)
                    for year
                    in tv_missing_benchmark_years
                )
            )

        # -------------------------------------------------
        # Distribution statistics
        # -------------------------------------------------

        with st.expander(
            f"{selected_year} TV season "
            "distribution statistics",
            expanded=False,
        ):
            st.subheader(
                f"{selected_year} distribution"
            )

            if (
                selected_year
                == current_year
                and tv_current_score_stats
                and tv_current_score_stats[
                    "count"
                ] < 50
            ):
                st.info(
                    "Current-year percentiles "
                    "are provisional. Only "
                    f"{tv_current_score_stats['count']} "
                    "scored TV seasons are "
                    "currently available."
                )

            current_score_col, (
                current_review_col
            ) = st.columns(2)

            with current_score_col:
                render_stats_column(
                    "Metascores",
                    tv_current_score_stats,
                )

            with current_review_col:
                render_stats_column(
                    "Critic reviews "
                    "(scored titles)",
                    tv_current_review_stats,
                )

            if (
                not tv_missing_benchmark_years
                and tv_benchmark_score_stats
                and tv_benchmark_review_stats
            ):
                st.divider()

                st.subheader(
                    "Five-year category benchmark "
                    f"({tv_benchmark_years[0]}"
                    f"–{tv_benchmark_years[-1]})"
                )

                benchmark_score_col, (
                    benchmark_review_col
                ) = st.columns(2)

                with benchmark_score_col:
                    render_stats_column(
                        "Metascores",
                        tv_benchmark_score_stats,
                    )

                with benchmark_review_col:
                    render_stats_column(
                        "Critic reviews "
                        "(scored titles)",
                        tv_benchmark_review_stats,
                    )

        # -------------------------------------------------
        # TV table
        # -------------------------------------------------

        st.dataframe(
            year_df[
                [
                    "Title",
                    "Season",
                    "Premiere",
                    "Metascore",
                    "Score Quintile",
                    "Reviews",
                    "Review Quintile",
                    "Positive",
                    "Mixed",
                    "Negative",
                    "Metacritic",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Metacritic":
                    st.column_config.LinkColumn(
                        "Metacritic",
                        display_text="Open",
                    ),
                "Metascore":
                    st.column_config.NumberColumn(
                        "Metascore",
                        format="%d",
                    ),
                "Reviews":
                    st.column_config.NumberColumn(
                        "Reviews",
                        format="%d",
                    ),
            },
        )


# =========================================================
# MOVIES
# =========================================================

with movies_tab:
    movies = load_movies()

    if movies.empty:
        st.warning(
            "No movie data found. "
            "Run a movie sync first."
        )

    else:
        # -------------------------------------------------
        # Year selection
        # -------------------------------------------------

        movie_years = sorted(
            movies["Year"]
            .dropna()
            .astype(int)
            .unique(),
            reverse=True,
        )

        default_movie_year = (
            current_year
            if current_year
            in movie_years
            else movie_years[0]
        )

        selected_movie_year = (
            st.selectbox(
                "Year",
                movie_years,
                index=movie_years.index(
                    default_movie_year
                ),
                key="movie_year",
            )
        )

        # -------------------------------------------------
        # Search
        # -------------------------------------------------

        movie_search = (
            st.text_input(
                "Search titles",
                key="movie_search",
            )
        )

        # -------------------------------------------------
        # Main filters
        # -------------------------------------------------

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:
            movie_scored_only = (
                st.checkbox(
                    "Only movies with a Metascore",
                    value=True,
                    key="movie_scored_only",
                )
            )

        with col2:
            movie_min_reviews = (
                st.number_input(
                    "Minimum critic reviews",
                    min_value=0,
                    value=0,
                    step=1,
                    key="movie_min_reviews",
                )
            )

        with col3:
            movie_min_score = (
                st.number_input(
                    "Minimum Metascore",
                    min_value=0,
                    max_value=100,
                    value=0,
                    step=1,
                    key="movie_min_score",
                )
            )

        # -------------------------------------------------
        # Quintile filters
        # -------------------------------------------------

        quintile_col1, quintile_col2 = (
            st.columns(2)
        )

        with quintile_col1:
            (
                selected_movie_score_quintiles
            ) = st.multiselect(
                "Score quintiles",
                [
                    "Top 20%",
                    "60th–80th percentile",
                    "40th–60th percentile",
                    "20th–40th percentile",
                    "Bottom 20%",
                ],
                key="movie_score_quintiles",
            )

        with quintile_col2:
            (
                selected_movie_review_quintiles
            ) = st.multiselect(
                "Review-count quintiles",
                [
                    "Most reviewed 20%",
                    "60th–80th percentile",
                    "40th–60th percentile",
                    "20th–40th percentile",
                    "Least reviewed 20%",
                ],
                key="movie_review_quintiles",
            )

        # -------------------------------------------------
        # Selected-year population
        # -------------------------------------------------

        movie_df = movies[
            movies["Year"]
            == selected_movie_year
        ].copy()

        total_movies = len(
            movie_df
        )

        scored_movies = (
            movie_df[
                "Metascore"
            ]
            .notna()
            .sum()
        )

        # -------------------------------------------------
        # Current-year statistics
        # -------------------------------------------------

        current_score_stats = (
            calculate_distribution_stats(
                movie_df,
                "Metascore",
            )
        )

        current_scored_population = (
            movie_df[
                movie_df[
                    "Metascore"
                ].notna()
            ]
        )

        current_review_stats = (
            calculate_distribution_stats(
                current_scored_population,
                "Reviews",
            )
        )

        # -------------------------------------------------
        # Five-year benchmark
        # -------------------------------------------------

        (
            movie_benchmark_df,
            movie_benchmark_years,
            movie_missing_benchmark_years,
        ) = get_benchmark_population(
            movies,
            selected_movie_year,
        )

        movie_benchmark_scored = (
            movie_benchmark_df[
                movie_benchmark_df[
                    "Metascore"
                ].notna()
            ]
        )

        benchmark_score_stats = (
            calculate_distribution_stats(
                movie_benchmark_scored,
                "Metascore",
            )
        )

        benchmark_review_stats = (
            calculate_distribution_stats(
                movie_benchmark_scored,
                "Reviews",
            )
        )

        # -------------------------------------------------
        # Assign benchmark quintile categories
        # -------------------------------------------------

        if (
            not movie_missing_benchmark_years
            and benchmark_score_stats
        ):
            movie_df[
                "Score Quintile"
            ] = (
                movie_df[
                    "Metascore"
                ].apply(
                    lambda score:
                    score_quintile_label(
                        score,
                        benchmark_score_stats,
                    )
                )
            )

        else:
            movie_df[
                "Score Quintile"
            ] = None


        if (
            not movie_missing_benchmark_years
            and benchmark_review_stats
        ):
            movie_df[
                "Review Quintile"
            ] = movie_df.apply(
                lambda row: (
                    review_quintile_label(
                        row["Reviews"],
                        benchmark_review_stats,
                    )
                    if pd.notna(
                        row["Metascore"]
                    )
                    else None
                ),
                axis=1,
            )

        else:
            movie_df[
                "Review Quintile"
            ] = None

        # -------------------------------------------------
        # User filters
        # -------------------------------------------------

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
                movie_df[
                    "Metascore"
                ].notna()
            ]

        movie_df = movie_df[
            movie_df["Reviews"]
            .fillna(0)
            >= movie_min_reviews
        ]

        movie_df = movie_df[
            movie_df["Metascore"]
            .fillna(0)
            >= movie_min_score
        ]

        if (
            selected_movie_score_quintiles
        ):
            movie_df = movie_df[
                movie_df[
                    "Score Quintile"
                ].isin(
                    selected_movie_score_quintiles
                )
            ]

        if (
            selected_movie_review_quintiles
        ):
            movie_df = movie_df[
                movie_df[
                    "Review Quintile"
                ].isin(
                    selected_movie_review_quintiles
                )
            ]

        # -------------------------------------------------
        # Default sorting
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        st.subheader(
            f"{selected_movie_year} Movies"
        )

        st.write(
            f"Showing **{len(movie_df)}** movies. "
            f"**{scored_movies}** scored movies "
            f"out of **{total_movies}** total "
            f"movies in {selected_movie_year}."
        )

        # -------------------------------------------------
        # Benchmark status
        # -------------------------------------------------

        if not movie_missing_benchmark_years:
            st.caption(
                "Quintile categories are based "
                "on scored movies from "
                f"{movie_benchmark_years[0]}"
                f"–{movie_benchmark_years[-1]}."
            )

        else:
            st.warning(
                "A complete five-year benchmark "
                "is not available for this year. "
                "Missing: "
                + ", ".join(
                    str(year)
                    for year
                    in movie_missing_benchmark_years
                )
            )

        # -------------------------------------------------
        # Distribution statistics
        # -------------------------------------------------

        with st.expander(
            f"{selected_movie_year} movie "
            "distribution statistics",
            expanded=False,
        ):
            st.subheader(
                f"{selected_movie_year} distribution"
            )

            if (
                selected_movie_year
                == current_year
                and current_score_stats
                and current_score_stats[
                    "count"
                ] < 50
            ):
                st.info(
                    "Current-year percentiles "
                    "are provisional. Only "
                    f"{current_score_stats['count']} "
                    "scored movies are "
                    "currently available."
                )

            current_score_col, (
                current_review_col
            ) = st.columns(2)

            with current_score_col:
                render_stats_column(
                    "Metascores",
                    current_score_stats,
                )

            with current_review_col:
                render_stats_column(
                    "Critic reviews "
                    "(scored titles)",
                    current_review_stats,
                )

            if (
                not movie_missing_benchmark_years
                and benchmark_score_stats
                and benchmark_review_stats
            ):
                st.divider()

                st.subheader(
                    "Five-year category benchmark "
                    f"({movie_benchmark_years[0]}"
                    f"–{movie_benchmark_years[-1]})"
                )

                benchmark_score_col, (
                    benchmark_review_col
                ) = st.columns(2)

                with benchmark_score_col:
                    render_stats_column(
                        "Metascores",
                        benchmark_score_stats,
                    )

                with benchmark_review_col:
                    render_stats_column(
                        "Critic reviews "
                        "(scored titles)",
                        benchmark_review_stats,
                    )

        # -------------------------------------------------
        # Movie table
        # -------------------------------------------------

        st.dataframe(
            movie_df[
                [
                    "Title",
                    "Release",
                    "Metascore",
                    "Score Quintile",
                    "Reviews",
                    "Review Quintile",
                    "Positive",
                    "Mixed",
                    "Negative",
                    "Metacritic",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Metacritic":
                    st.column_config.LinkColumn(
                        "Metacritic",
                        display_text="Open",
                    ),
                "Metascore":
                    st.column_config.NumberColumn(
                        "Metascore",
                        format="%d",
                    ),
                "Reviews":
                    st.column_config.NumberColumn(
                        "Reviews",
                        format="%d",
                    ),
            },
        )