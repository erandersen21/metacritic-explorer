import re

from metacritic.aliases import canonicalize_slug


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


async def discover_calendar_shows(mc):
    current = await mc.get_article(
        "tv-premiere-dates"
    )

    archive = await mc.get_article(
        "tv-calendar-archive-of-past-dates"
    )

    current_urls = extract_season_urls(current)
    archive_urls = extract_season_urls(archive)

    combined_urls = current_urls | archive_urls

    show_slugs = {
        canonicalize_slug(slug)
        for url in combined_urls
        if (slug := extract_show_slug(url))
    }

    return {
        "current_urls": current_urls,
        "archive_urls": archive_urls,
        "combined_urls": combined_urls,
        "show_slugs": show_slugs,
    }