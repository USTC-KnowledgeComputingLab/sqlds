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
from .load import main as load
from .dump import main as dump

component_map = {
    "ds": ds,
    "egg": egg,
    "input": input,
    "output": output,
    "load": load,
    "dump": dump,
}


async def run(addr: str, components: list[str]) -> None:
    engine, session = await initialize_database(addr)

    try:
        try:
            coroutines = [component_map[component](addr, engine, session) for component in components]
        except KeyError as e:
            print(f"error: unsupported component: {e}")
            raise asyncio.CancelledError()

        await asyncio.wait(
            [asyncio.create_task(coro) for coro in coroutines],
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
            help="Database address URL. If not provided, uses a temporary SQLite database.",
        ),
    ] = None,
    component: Annotated[
        list[str],
        tyro.conf.arg(
            aliases=["-c"],
            help="Components to run.",
        ),
    ] = ["input", "output", "ds", "egg"],
) -> None:
    """DDSS - Distributed Deductive System Sorts: Run DDSS with an interactive deductive environment."""
    if addr is None:
        tmpdir = tempfile.TemporaryDirectory()
        path = pathlib.Path(tmpdir.name) / "ddss.db"
        addr = f"sqlite:///{path.as_posix()}"

    for key, value in sqlalchemy_driver.items():
        if addr.startswith(f"{key}://"):
            addr = addr.replace(f"{key}://", f"{key}+{value}://")
        if addr.startswith(f"{key}+{value}://"):
            break
    else:
        print(f"error: unsupported database: '{addr}'")
        return

    print(f"addr: {addr}")
    asyncio.run(run(addr, component))


def cli():
    tyro.cli(main, prog="ddss")


if __name__ == "__main__":
    cli()
