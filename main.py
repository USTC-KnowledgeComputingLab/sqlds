import sys
import asyncio
from orm import initialize_database
from ds import main as ds
from egg import main as egg
from input import main as input


async def main(addr):
    engine, session = await initialize_database(addr)
    await asyncio.gather(ds(addr, engine, session), egg(addr, engine, session), input(addr, engine, session))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
