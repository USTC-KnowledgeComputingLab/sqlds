import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from sqlalchemy import Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from apyds import Search
from apyds_bnf import parse, unparse


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


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///./data.db")
    session = async_sessionmaker(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    search = Search()
    count = -1

    while True:
        begin = asyncio.get_event_loop().time()
        async with session() as sess:
            input = await sess.execute(select(Facts).where(Facts.id > count))
            for i in input.scalars():
                count = max(count, i.id)
                search.add(parse(i.data))
            output = []
            search.execute(lambda x: output.append(x))
            sess.add_all(Facts(data=unparse(f"{x}")) for x in output)
            sess.add_all(Ideas(data=unparse(f"--\n{x[0]}")) for x in output if len(x) != 0)
            await sess.commit()
        end = asyncio.get_event_loop().time()
        duration = end - begin
        delay = max(0, 1 - duration)
        await asyncio.sleep(delay)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
