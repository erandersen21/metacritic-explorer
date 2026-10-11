import argparse
import asyncio
from datetime import datetime, timedelta

import httpx

from metacritic.client import MetacriticClient
from metacritic.aliases import canonicalize_slug
from metacritic.discovery import discover_calendar_shows
from metacritic.database import (
    SessionLocal,
    SeasonRecord,
    ShowRecord,
    init_db,
    MovieRecord
)

TV_REFRESH_CONCURRENCY = 5
TV_REFRESH_RETRIES = 2
TV_REFRESH_FRESHNESS_HOURS = 6

RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}

def save_show_seasons(
    session,
    show: ShowRecord,
    result,
) -> int:
    for season in result.data.items:
        score = season.critic_score_summary

        record = SeasonRecord(
            id=season.id,
            show_id=show.id,
            show_slug=show.slug,
            season_number=season.season_number,
            season_slug=season.season_slug,
            premiere_date=season.premiere_date,
            metascore=(
                score.score
                if score else None
            ),
            review_count=(
                score.review_count
                if score else None
            ),
            positive_count=(
                score.positive_count
                if score else None
            ),
            neutral_count=(
                score.neutral_count
                if score else None
            ),
            negative_count=(
                score.negative_count
                if score else None
            ),
        )

        session.merge(record)

    show.seasons_fetched = True
    show.seasons_last_fetched = datetime.now()

    session.commit()

    return len(result.data.items)


async def fetch_show_seasons(
    mc: MetacriticClient,
    semaphore: asyncio.Semaphore,
    show_id: int,
    title: str,
    slug: str,
):
    async with semaphore:
        for attempt in range(
            TV_REFRESH_RETRIES + 1
        ):
            try:
                result = await mc.get_seasons(
                    slug
                )

                return {
                    "show_id": show_id,
                    "title": title,
                    "slug": slug,
                    "result": result,
                    "status": 200,
                    "error": None,
                }

            except httpx.HTTPStatusError as error:
                status = (
                    error.response.status_code
                )

                if (
                    status
                    in RETRYABLE_STATUS_CODES
                    and attempt
                    < TV_REFRESH_RETRIES
                ):
                    await asyncio.sleep(
                        1 * (2 ** attempt)
                    )

                    continue

                return {
                    "show_id": show_id,
                    "title": title,
                    "slug": slug,
                    "result": None,
                    "status": status,
                    "error": error,
                }

            except Exception as error:
                if attempt < TV_REFRESH_RETRIES:
                    await asyncio.sleep(
                        1 * (2 ** attempt)
                    )

                    continue

                return {
                    "show_id": show_id,
                    "title": title,
                    "slug": slug,
                    "result": None,
                    "status": None,
                    "error": error,
                }


async def refresh_show_batch(
    session,
    mc: MetacriticClient,
    shows: list[ShowRecord],
) -> tuple[int, int]:
    semaphore = asyncio.Semaphore(
        TV_REFRESH_CONCURRENCY
    )

    tasks = [
        asyncio.create_task(
            fetch_show_seasons(
                mc=mc,
                semaphore=semaphore,
                show_id=show.id,
                title=show.title,
                slug=show.slug,
            )
        )
        for show in shows
    ]

    success_count = 0
    failure_count = 0

    total = len(tasks)

    for index, task in enumerate(
        asyncio.as_completed(tasks),
        start=1,
    ):
        fetched = await task

        print(
            f"[{index}/{total}] "
            f"{fetched['title']}"
        )

        show = session.get(
            ShowRecord,
            fetched["show_id"],
        )

        if show is None:
            failure_count += 1

            print(
                "  ✗ Show disappeared "
                "from local database"
            )

            continue

        if fetched["status"] == 200:
            try:
                count = save_show_seasons(
                    session,
                    show,
                    fetched["result"],
                )

                success_count += 1

                print(
                    f"  ✓ Saved/updated "
                    f"{count} seasons"
                )

            except Exception as error:
                session.rollback()
                failure_count += 1

                print(
                    f"  ✗ Database error: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )

        elif fetched["status"] == 404:
            show.seasons_fetched = True
            show.seasons_last_fetched = (
                datetime.now()
            )

            session.commit()

            success_count += 1

            print(
                "  - No season list (404)"
            )

        else:
            failure_count += 1

            if fetched["status"] is not None:
                print(
                    f"  ✗ HTTP "
                    f"{fetched['status']}"
                )

            else:
                error = fetched["error"]

                print(
                    f"  ✗ "
                    f"{type(error).__name__}: "
                    f"{error}"
                )

    return (
        success_count,
        failure_count,
    )


async def sync_seasons(
    limit: int | None = None,
    refresh_year: int | None = None,
):
    init_db()
    mc = MetacriticClient()

    try:
        with SessionLocal() as session:

            if refresh_year is not None:
                # Refresh any show for which we already know about
                # at least one season in the requested year.
                #
                # LIKE is intentional because Metacritic sometimes
                # gives us partial dates such as "2026" or "2026-10".
                query = (
                    session.query(ShowRecord)
                    .join(
                        SeasonRecord,
                        SeasonRecord.show_id == ShowRecord.id,
                    )
                    .filter(
                        SeasonRecord.premiere_date.like(
                            f"{refresh_year}%"
                        )
                    )
                    .distinct()
                    .order_by(ShowRecord.id)
                )

                mode_description = (
                    f"shows with known {refresh_year} seasons"
                )

            else:
                query = (
                    session.query(ShowRecord)
                    .filter(
                        ShowRecord.seasons_fetched == False
                    )
                    .order_by(ShowRecord.id)
                )

                mode_description = "unfetched shows"

            if limit is not None:
                query = query.limit(limit)

            shows = query.all()

            print(
                f"{len(shows)} {mode_description} "
                f"to process.\n"
            )

            for index, show in enumerate(shows, start=1):
                print(
                    f"[{index}/{len(shows)}] "
                    f"{show.title} ({show.slug})"
                )

                try:
                    result = await mc.get_seasons(
                        show.slug
                    )

                    count = save_show_seasons(
                        session,
                        show,
                        result,
                    )

                    print(
                        f"  ✓ Saved/updated {count} seasons"
                    )

                except httpx.HTTPStatusError as error:
                    status = error.response.status_code

                    if status == 404:
                        show.seasons_fetched = True
                        show.seasons_last_fetched = datetime.now()

                        session.commit()

                        print("  - No season list (404)")

                    else:
                        session.rollback()
                        print(f"  ✗ HTTP {status}")

                except Exception as error:
                    session.rollback()

                    print(
                        f"  ✗ "
                        f"{type(error).__name__}: {error}"
                    )

                await asyncio.sleep(0.2)

    finally:
        await mc.close()


async def ensure_show_exists(
    session,
    mc: MetacriticClient,
    slug: str,
) -> ShowRecord | None:
    slug = canonicalize_slug(slug)

    existing = (
        session.query(ShowRecord)
        .filter(ShowRecord.slug == slug)
        .one_or_none()
    )

    if existing:
        return existing

    try:
        data = await mc.get_show(slug)
        item = data["data"]["item"]

        show = ShowRecord(
            id=item["id"],
            title=item["title"],
            slug=item["slug"],
            premiere_year=item.get("premiereYear"),
        )

        session.merge(show)
        session.commit()

        return session.get(ShowRecord, item["id"])

    except Exception as error:
        session.rollback()

        print(
            f"  ✗ Could not add {slug}: "
            f"{type(error).__name__}: {error}"
        )

        return None


async def refresh(
    year: int,
    limit: int | None = None,
    force: bool = False,
):
    init_db()
    mc = MetacriticClient()

    try:
        with SessionLocal() as session:
            print("Discovering current TV calendar...")

            discovery = await discover_calendar_shows(mc)

            calendar_slugs = discovery["show_slugs"]

            print(
                f"Found {len(discovery['current_urls'])} "
                f"current calendar season URLs."
            )

            print(
                f"Found {len(discovery['archive_urls'])} "
                f"archive season URLs."
            )

            print(
                f"Found {len(calendar_slugs)} "
                f"unique calendar shows.\n"
            )

            # -------------------------
            # Make sure every calendar
            # show exists locally.
            # -------------------------

            before_count = session.query(
                ShowRecord
            ).count()

            calendar_shows = {}

            for slug in sorted(calendar_slugs):
                show = await ensure_show_exists(
                    session,
                    mc,
                    slug,
                )

                if show is not None:
                    calendar_shows[show.id] = show


            after_count = session.query(
                ShowRecord
            ).count()

            print(
                f"New shows added from calendar: "
                f"{after_count - before_count}"
            )

            # -------------------------
            # Find every show for which
            # we already know about a
            # season in the requested year.
            # -------------------------

            year_shows = (
                session.query(ShowRecord)
                .join(
                    SeasonRecord,
                    SeasonRecord.show_id
                    == ShowRecord.id,
                )
                .filter(
                    SeasonRecord.premiere_date.like(
                        f"{year}%"
                    )
                )
                .distinct()
                .all()
            )

            # Union calendar discoveries
            # with known shows from this year.
            shows_to_refresh = {
                show.id: show
                for show in year_shows
            }

            shows_to_refresh.update(
                calendar_shows
            )

            all_shows = list(
                shows_to_refresh.values()
            )

            if force:
                shows = all_shows
                skipped_count = 0
            else:
                fresh_cutoff = (
                    datetime.now()
                    - timedelta(
                        hours=TV_REFRESH_FRESHNESS_HOURS
                    )
                )

                shows = [
                    show
                    for show in all_shows
                    if (
                        show.seasons_last_fetched is None
                        or show.seasons_last_fetched
                        < fresh_cutoff
                    )
                ]

                skipped_count = (
                    len(all_shows) - len(shows)
                )

            shows = sorted(
                shows,
                key=lambda show: show.id,
            )

            if limit is not None:
                shows = shows[:limit]

            print(
                f"Known {year} shows: "
                f"{len(year_shows)}"
            )

            print(
                f"Total unique candidate shows: "
                f"{len(all_shows)}"
            )

            if force:
                print(
                    "Force refresh enabled; "
                    "freshness window ignored."
                )
            else:
                print(
                    f"Skipping {skipped_count} shows "
                    f"refreshed in the last "
                    f"{TV_REFRESH_FRESHNESS_HOURS} hours."
                )

            print(
                f"Shows to refresh: "
                f"{len(shows)}\n"
            )

            # -------------------------
            # Refresh seasons
            # -------------------------

            print(
                f"Fetching up to "
                f"{TV_REFRESH_CONCURRENCY} "
                f"shows concurrently...\n"
            )

            (
                success_count,
                failure_count,
            ) = await refresh_show_batch(
                session=session,
                mc=mc,
                shows=shows,
            )

            print()
            print("Refresh complete.")
            print(
                f"Successful: {success_count}"
            )
            print(
                f"Failed:     {failure_count}"
            )

    finally:
        await mc.close()


async def sync_movies(year: int):
    init_db()
    mc = MetacriticClient()

    try:
        print(
            f"Crawling {year} movies "
            f"newest → oldest..."
        )

        newest_first = await mc.get_all_movies(
            year=year,
            sort_by="-releaseDate",
        )

        print(
            f"\nCrawling {year} movies "
            f"oldest → newest..."
        )

        oldest_first = await mc.get_all_movies(
            year=year,
            sort_by="releaseDate",
        )

        newest_by_id = {
            movie.id: movie
            for movie in newest_first
        }

        oldest_by_id = {
            movie.id: movie
            for movie in oldest_first
        }

        combined = {
            **newest_by_id,
            **oldest_by_id,
        }

        print()
        print(
            f"Newest-first unique: "
            f"{len(newest_by_id)}"
        )

        print(
            f"Oldest-first unique: "
            f"{len(oldest_by_id)}"
        )

        print(
            f"Combined unique:     "
            f"{len(combined)}"
        )

        with SessionLocal() as session:
            for movie in combined.values():
                score = movie.critic_score_summary

                record = MovieRecord(
                    id=movie.id,
                    title=movie.title,
                    slug=movie.slug,
                    release_year=movie.premiere_year,
                    release_date=movie.release_date,
                    metascore=(
                        score.score
                        if score else None
                    ),
                    review_count=(
                        score.review_count
                        if score else None
                    ),
                    positive_count=(
                        score.positive_count
                        if score else None
                    ),
                    neutral_count=(
                        score.neutral_count
                        if score else None
                    ),
                    negative_count=(
                        score.negative_count
                        if score else None
                    ),
                    last_fetched=datetime.now(),
                )

                session.merge(record)

            session.commit()

        print(
            f"\nSaved {len(combined)} "
            f"{year} movies."
        )

    finally:
        await mc.close()

async def refresh_all(
    year: int,
    limit: int | None = None,
    force: bool = False,
):
    print("=" * 60)
    print(f"REFRESHING TV DATA FOR {year}")
    print("=" * 60)
    print()

    await refresh(
        year=year,
        limit=limit,
        force=force,
    )

    print()
    print("=" * 60)
    print(f"REFRESHING MOVIE DATA FOR {year}")
    print("=" * 60)
    print()

    await sync_movies(year)

    print()
    print("=" * 60)
    print("FULL REFRESH COMPLETE")
    print("=" * 60)

async def sync_movie_range(
    start_year: int,
    end_year: int,
):
    if start_year > end_year:
        raise ValueError(
            "Start year must be before end year."
        )

    for year in range(
        start_year,
        end_year + 1,
    ):
        print()
        print("=" * 60)
        print(f"SYNCING MOVIES FOR {year}")
        print("=" * 60)
        print()

        await sync_movies(year)

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of shows to process",
    )

    parser.add_argument(
        "--refresh-year",
        type=int,
        default=None,
        help=(
            "Refresh shows that already have a season "
            "in this year"
        ),
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "Refresh TV seasons and movies "
            "for the selected year"
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Ignore the TV freshness window and "
            "refresh all candidate shows"
        ),
    )

    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Year to refresh (default: current year)",
    )

    parser.add_argument(
        "--movies-year",
        type=int,
        default=None,
        help="Sync movies released in this year",
    )

    parser.add_argument(
        "--movies-range",
        nargs=2,
        type=int,
        metavar=("START_YEAR", "END_YEAR"),
        help="Sync movies for an inclusive range of years",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.movies_range is not None:
        start_year, end_year = args.movies_range

        asyncio.run(
            sync_movie_range(
                start_year,
                end_year,
            )
        )

    elif args.movies_year is not None:
        asyncio.run(
            sync_movies(args.movies_year)
        )

    elif args.refresh:
        asyncio.run(
            refresh_all(
                year=args.year,
                limit=args.limit,
                force=args.force,
            )
        )

    else:
        asyncio.run(
            sync_seasons(
                limit=args.limit,
                refresh_year=args.refresh_year,
            )
        )