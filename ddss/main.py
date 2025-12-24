import asyncio
import tempfile
import pathlib
import sys
from typing import Annotated, Optional
import tyro
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


# Global to keep temporary directory alive during execution
_tmpdir = None


def cli():
    """DDSS - Distributed Deductive System Sorts
    
    Run DDSS with an interactive deductive reasoning environment.
    """
    
    def run(
        addr: Annotated[
            Optional[str],
            tyro.conf.arg(
                aliases=["-a"],
                help="Database address URL. Supported: sqlite://, mysql://, mariadb://, postgresql://. "
                "If not provided, uses a temporary SQLite database."
            )
        ] = None,
    ) -> None:
        """Start DDSS with the specified database address."""
        # Use a global to keep the temporary directory alive
        global _tmpdir
        if addr is None:
            _tmpdir = tempfile.TemporaryDirectory()
            path = pathlib.Path(_tmpdir.name) / "ddss.db"
            addr = f"sqlite:///{path.as_posix()}"
        
        # Add driver suffix to database URL if needed
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
    
    tyro.cli(run)


if __name__ == "__main__":
    cli()
