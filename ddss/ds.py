import sys
import asyncio
from sqlalchemy import select
from apyds import Search
from .orm import initialize_database, insert_or_ignore, Facts, Ideas
from .poly import Poly


async def main(addr, engine=None, session=None):
    if engine is None or session is None:
        engine, session = await initialize_database(addr)

    search = Search()
    max_fact = -1

    while True:
        begin = asyncio.get_running_loop().time()

        async with session() as sess:
            for i in await sess.scalars(select(Facts).where(Facts.id > max_fact)):
                max_fact = max(max_fact, i.id)
                search.add(Poly(dsp=i.data).ds)
            tasks = []

            def handler(rule):
                poly = Poly(rule=rule)
                tasks.append(asyncio.create_task(insert_or_ignore(sess, Facts, poly.dsp)))
                if idea := poly.idea:
                    tasks.append(asyncio.create_task(insert_or_ignore(sess, Ideas, idea.dsp)))
                return False

            count = search.execute(handler)
            await asyncio.gather(*tasks)
            await sess.commit()

        end = asyncio.get_running_loop().time()
        duration = end - begin
        if count == 0:
            delay = max(0, 1 - duration)
            await asyncio.sleep(delay)

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
