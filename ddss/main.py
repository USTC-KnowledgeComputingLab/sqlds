import asyncio
import tempfile
import pathlib
from typing import Annotated, Optional
import tyro
from .orm import initialize_database
from .ds import main as ds
from .egg import main as egg
from .input import main as input
from .output import main as output


async def run(addr, components):
    engine, session = await initialize_database(addr)

    # Map component names to their main functions
    component_map = {
        "ds": ds,
        "egg": egg,
        "input": input,
        "output": output,
    }

    # Create tasks only for requested components
    tasks = [
        asyncio.create_task(component_map[component](addr, engine, session))
        for component in components
        if component in component_map
    ]

    try:
        await asyncio.wait(
            tasks,
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


def main(
    addr: Annotated[
        Optional[str],
        tyro.conf.arg(
            aliases=["-a"],
            help="Database address URL. Supported: sqlite://, mysql://, mariadb://, postgresql://. "
            "If not provided, uses a temporary SQLite database.",
        ),
    ] = None,
    component: Annotated[
        Optional[list[str]], tyro.conf.arg(help="Components to run. Available: input, output, ds, egg.")
    ] = None,
) -> None:
    """DDSS - Distributed Deductive System Sorts

    Run DDSS with an interactive deductive reasoning environment.
    """
    if addr is None:
        tmpdir = tempfile.TemporaryDirectory()
        path = pathlib.Path(tmpdir.name) / "ddss.db"
        addr = f"sqlite:///{path.as_posix()}"

    if component is None:
        component = ["input", "output", "ds", "egg"]

    # Add driver suffix to database URL if needed
    for key, value in sqlalchemy_driver.items():
        if addr.startswith(f"{key}://"):
            addr = addr.replace(f"{key}://", f"{key}+{value}://")
        if addr.startswith(f"{key}+{value}://"):
            break
    else:
        print(f"Unsupported database address: {addr}")
        raise SystemExit(1)

    print(f"addr: {addr}")
    asyncio.run(run(addr, component))


def cli():
    tyro.cli(main)


if __name__ == "__main__":
    cli()
