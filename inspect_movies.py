import asyncio
import json

from metacritic.client import MetacriticClient


async def main():
    mc = MetacriticClient()

    try:
        data = await mc.get_movies(2026)

        finder = data["data"]

        print(
            f"Metacritic reports "
            f"{finder['totalResults']} movies for 2026."
        )

        print("\nFirst 5 movies:\n")

        for movie in finder["items"][:5]:
            score = movie.get("criticScoreSummary") or {}

            print(
                movie.get("title"),
                "|",
                movie.get("premiereYear"),
                "| score:",
                score.get("score"),
                "| reviews:",
                score.get("reviewCount"),
                "| slug:",
                movie.get("slug"),
            )

        print("\nKeys on first movie:\n")
        print(finder["items"][0].keys())

        print("\nFirst movie raw JSON:\n")
        print(
            json.dumps(
                finder["items"][0],
                indent=2,
            )[:5000]
        )

    finally:
        await mc.close()


if __name__ == "__main__":
    asyncio.run(main())