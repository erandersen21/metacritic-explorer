import argparse
import asyncio
from datetime import datetime

import httpx

from metacritic.client import MetacriticClient
from metacritic.database import (
    SessionLocal,
    SeasonRecord,
    ShowRecord,
    init_db,
)


async def sync_seasons(limit: int | None = None):
    init_db()
    mc = MetacriticClient()

    try:
        with SessionLocal() as session:
            query = (
                session.query(ShowRecord)
                .filter(ShowRecord.seasons_fetched == False)
                .order_by(ShowRecord.id)
            )

            if limit is not None:
                query = query.limit(limit)

            shows = query.all()

            print(f"{len(shows)} shows to process.\n")

            for index, show in enumerate(shows, start=1):
                print(
                    f"[{index}/{len(shows)}] "
                    f"{show.title} ({show.slug})"
                )

                try:
                    result = await mc.get_seasons(show.slug)

                    for season in result.data.items:
                        score = season.critic_score_summary

                        record = SeasonRecord(
                            id=season.id,
                            show_id=show.id,
                            show_slug=show.slug,
                            season_number=season.season_number,
                            season_slug=season.season_slug,
                            premiere_date=season.premiere_date,
                            metascore=score.score if score else None,
                            review_count=score.review_count if score else None,
                            positive_count=(
                                score.positive_count if score else None
                            ),
                            neutral_count=(
                                score.neutral_count if score else None
                            ),
                            negative_count=(
                                score.negative_count if score else None
                            ),
                        )

                        session.merge(record)

                    show.seasons_fetched = True
                    show.seasons_last_fetched = datetime.now()

                    session.commit()

                    print(
                        f"  ✓ Saved {len(result.data.items)} seasons"
                    )

                except httpx.HTTPStatusError as error:
                    status = error.response.status_code

                    if status == 404:
                        # This appears to be a TV catalog entry that
                        # doesn't expose a season list.
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
                        f"  ✗ {type(error).__name__}: {error}"
                    )

                # Don't hammer Metacritic's backend.
                await asyncio.sleep(0.2)

    finally:
        await mc.close()


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of shows to process",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    asyncio.run(
        sync_seasons(limit=args.limit)
    )