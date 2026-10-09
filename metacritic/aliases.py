SLUG_ALIASES = {
    "miss-scarlet-the-duke": "miss-scarlet",
}


def canonicalize_slug(slug: str) -> str:
    return SLUG_ALIASES.get(slug, slug)