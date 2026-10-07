import httpx
import asyncio

from metacritic.models import FinderResponse, SeasonListResponse, Show


BASE_URL = "https://backend.metacritic.com"


class MetacriticClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/154.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Referer": "https://www.metacritic.com/",
            },
            timeout=30.0,
        )

    async def close(self):
        await self.client.aclose()

    async def get_shows(
        self,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "-releaseDate",
    ) -> FinderResponse:
        response = await self.client.get(
            "/finder/metacritic/web",
            params={
                "sortBy": sort_by,
                "mcoTypeId": 1,
                "offset": offset,
                "limit": limit,
                "componentName": "finder",
                "componentType": "Finder",
            },
        )

        response.raise_for_status()
        return FinderResponse.model_validate(response.json())

    async def get_seasons(self, slug: str) -> SeasonListResponse:
        response = await self.client.get(
            f"/shows/metacritic/{slug}/seasons/web",
            params={
                "componentName": "seasons",
                "componentDisplayName": "All Seasons",
                "componentType": "SeasonList",
            },
        )

        response.raise_for_status()
        return SeasonListResponse.model_validate(response.json())
    
    async def get_all_shows(
        self,
        sort_by: str = "-releaseDate",
        limit: int = 50,
    ) -> list[Show]:
        first_page = await self.get_shows(
            offset=0,
            limit=limit,
            sort_by=sort_by,
        )

        total = first_page.data.total_results
        shows = list(first_page.data.items)

        print(f"Metacritic reports {total} results.")

        offset = limit

        while offset < total:
            page = await self.get_shows(
                offset=offset,
                limit=limit,
                sort_by=sort_by,
            )

            shows.extend(page.data.items)

            print(
                f"Fetched {min(len(shows), total)}/{total}",
                end="\r",
            )

            offset += limit
            await asyncio.sleep(0.1)

        print()

        return shows