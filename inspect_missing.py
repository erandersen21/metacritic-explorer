import asyncio
import json

from metacritic.client import MetacriticClient


MISSING = [
    "miss-scarlet-the-duke",
]


async def main():
    mc = MetacriticClient()

    try:
        for slug in MISSING:
            print(f"\n{'=' * 70}")
            print(slug)
            print("=" * 70)

            try:
                data = await mc.get_show(slug)

                print(json.dumps(
                    data,
                    indent=2,
                )[:5000])

            except Exception as error:
                print(
                    f"{type(error).__name__}: "
                    f"{error}"
                )

    finally:
        await mc.close()


if __name__ == "__main__":
    asyncio.run(main())