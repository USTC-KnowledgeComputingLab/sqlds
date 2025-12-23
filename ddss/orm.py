import asyncio
from collections import defaultdict
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert


class Base(DeclarativeBase):
    pass


class Facts(Base):
    __tablename__ = "facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class Ideas(Base):
    __tablename__ = "ideas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


async def initialize_database(addr: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(addr)
    session = async_sessionmaker(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, session


async def insert_or_ignore(sess: AsyncSession, model: type[Base], data: str, locks=defaultdict(asyncio.Lock)) -> None:
    match sess.bind.dialect.name:
        case "sqlite":
            statement = sqlite_insert(model).values(data=data).on_conflict_do_nothing()
            await sess.execute(statement)
        case "mysql" | "mariadb":
            statement = mysql_insert(model).values(data=data).prefix_with("IGNORE")
            await sess.execute(statement)
        case "postgresql":
            statement = postgresql_insert(model).values(data=data).on_conflict_do_nothing()
            await sess.execute(statement)
        case _:
            async with locks[id(sess.bind)]:
                try:
                    async with sess.begin_nested():
                        sess.add(model(data=data))
                        await sess.flush()
                except IntegrityError:
                    pass
