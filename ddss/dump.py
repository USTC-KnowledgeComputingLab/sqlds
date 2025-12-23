import sys
import asyncio
from sqlalchemy import select
from apyds_bnf import unparse
from .orm import initialize_database, Facts, Ideas


async def main(addr, engine=None, session=None):
    if engine is None or session is None:
        engine, session = await initialize_database(addr)

    try:
        async with session() as sess:
            # Output all ideas first
            for i in await sess.scalars(select(Ideas)):
                print("idea:", unparse(i.data))
            # Then output all facts
            for f in await sess.scalars(select(Facts)):
                print("fact:", unparse(f.data))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
