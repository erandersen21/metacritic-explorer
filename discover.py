import asyncio
import re

from metacritic.client import MetacriticClient
from metacritic.aliases import canonicalize_slug
from metacritic.database import (
    SessionLocal,
    ShowRecord,
    init_db,
)


SEASON_URL_PATTERN = re.compile(
    r"/tv/([^/\"?]+)/((?:season-\d+))/"
)


def find_strings(value):
    if isinstance(value, str):
        yield value

    elif isinstance(value, dict):
        for child in value.values():
            yield from find_strings(child)

    elif isinstance(value, list):
        for child in value:
            yield from find_strings(child)


def extract_season_urls(data: dict) -> set[str]:
    urls = set()

    for text in find_strings(data):
        for match in SEASON_URL_PATTERN.finditer(text):
            show_slug = match.group(1)
            season_slug = match.group(2)

            urls.add(
                f"/tv/{show_slug}/{season_slug}/"
            )

    return urls


def extract_show_slug(url: str) -> str | None:
    match = SEASON_URL_PATTERN.fullmatch(url)

    if not match:
        return None

    return match.group(1)


async def main():
    init_db()
    mc = MetacriticClient()

    try:
        current = await mc.get_article(
            "tv-premiere-dates"
        )

        archive = await mc.get_article(
            "tv-calendar-archive-of-past-dates"
        )

        current_urls = extract_season_urls(current)
        archive_urls = extract_season_urls(archive)

        combined = current_urls | archive_urls

        show_slugs = {
            canonicalize_slug(slug)
            for url in combined
            if (slug := extract_show_slug(url))
        }

        with SessionLocal() as session:
            known_slugs = {
                slug
                for (slug,) in session.query(
                    ShowRecord.slug
                ).all()
            }

        known = show_slugs & known_slugs
        missing = show_slugs - known_slugs

        print(
            f"Current calendar season URLs: "
            f"{len(current_urls)}"
        )

        print(
            f"Archive season URLs:          "
            f"{len(archive_urls)}"
        )

        print(
            f"Combined unique season URLs:  "
            f"{len(combined)}"
        )

        print()
        print(
            f"Unique shows discovered:      "
            f"{len(show_slugs)}"
        )

        print(
            f"Already in database:          "
            f"{len(known)}"
        )

        print(
            f"Missing from database:        "
            f"{len(missing)}"
        )

        if missing:
            print("\nMissing show slugs:\n")

            for slug in sorted(missing):
                print(slug)

    finally:
        await mc.close()


if __name__ == "__main__":
    asyncio.run(main())