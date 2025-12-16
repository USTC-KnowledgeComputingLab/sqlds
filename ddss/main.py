import sys
import asyncio
import tempfile
from .orm import initialize_database
from .ds import main as ds
from .egg import main as egg
from .input import main as input
from .output import main as output


async def main(addr):
    engine, session = await initialize_database(addr)
    try:
        await asyncio.wait(
            [
                asyncio.create_task(ds(addr, engine, session)),
                asyncio.create_task(egg(addr, engine, session)),
                asyncio.create_task(input(addr, engine, session)),
                asyncio.create_task(output(addr, engine, session)),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
    except asyncio.CancelledError:
        pass
    finally:
        await engine.dispose()


sqlalchemy_driver = {
    "sqlite": "aiosqlite",
    "mysql": "aiomysql",
    "mariadb": "aiomysql",
    "postgresql": "asyncpg",
}


def cli():
    if len(sys.argv) == 1:
        file = tempfile.NamedTemporaryFile()
        addr = f"sqlite:///{file.name}"
    elif len(sys.argv) == 2 and sys.argv[1] not in ["--help", "-help", "-h", "/help", "/h", "/?"]:
        addr = sys.argv[1]
    else:
        print(f"Usage: {sys.argv[0]} [<database-addr>]")
        sys.exit(1)
    for key, value in sqlalchemy_driver.items():
        if addr.startswith(f"{key}://"):
            addr = addr.replace(f"{key}://", f"{key}+{value}://")
        if addr.startswith(f"{key}+{value}://"):
            break
    else:
        print(f"Unsupported database address: {addr}")
        sys.exit(1)
    print(f"addr: {addr}")
    asyncio.run(main(addr))


if __name__ == "__main__":
    cli()
