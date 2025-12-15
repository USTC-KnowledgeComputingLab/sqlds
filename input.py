import sys
import asyncio
from orm import initialize_database, insert_or_ignore, Facts, Ideas
from poly import Poly


async def main(addr):
    engine, session = await initialize_database(addr)

    while True:
        try:
            data = input()
        except EOFError:
            break
        async with session() as sess:
            poly = Poly(dsp=data)
            await insert_or_ignore(sess, Facts, poly.dsp)
            if idea := poly.idea:
                await insert_or_ignore(sess, Ideas, idea.dsp)
            await sess.commit()

    await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
