import sys
import asyncio
from sqlalchemy import select
from .orm import initialize_database, Facts, Ideas
from .poly import Poly


async def main(addr, engine=None, session=None):
    if engine is None or session is None:
        engine, session = await initialize_database(addr)

    max_fact = -1
    max_idea = -1

    while True:
        count = 0
        begin = asyncio.get_running_loop().time()

        async with session() as sess:
            for i in await sess.scalars(select(Facts).where(Facts.id > max_fact)):
                max_fact = max(max_fact, i.id)
                print("fact:", Poly(dsp=i.data).dsp)
            for i in await sess.scalars(select(Ideas).where(Ideas.id > max_idea)):
                max_idea = max(max_idea, i.id)
                print("idea:", Poly(dsp=i.data).dsp)

        end = asyncio.get_running_loop().time()
        duration = end - begin
        if count == 0:
            delay = max(0, 1 - duration)
            await asyncio.sleep(delay)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
