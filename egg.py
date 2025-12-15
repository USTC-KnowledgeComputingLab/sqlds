import sys
import asyncio
from sqlalchemy import select
from orm import initialize_database, insert_or_ignore, Facts, Ideas
from egraph import Search
from poly import Poly


async def main(addr):
    engine, session = await initialize_database(addr)

    search = Search()
    pool = []
    max_fact = -1
    max_idea = -1

    while True:
        count = 0
        begin = asyncio.get_event_loop().time()

        async with session() as sess:
            for i in await sess.scalars(select(Facts).where(Facts.id > max_fact)):
                max_fact = max(max_fact, i.id)
                search.add(Poly(dsp=i.data))
            for i in await sess.scalars(select(Ideas).where(Ideas.id > max_idea)):
                max_idea = max(max_idea, i.id)
                pool.append(Poly(dsp=i.data))
            tasks = []
            for i in pool:
                for o in search.execute(i):
                    tasks.append(asyncio.create_task(insert_or_ignore(sess, Facts, o.dsp)))
            await asyncio.gather(*tasks)
            await sess.commit()

        end = asyncio.get_event_loop().time()
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
