import sys
import asyncio
from loguru import logger
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
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <5}</level> | <cyan>{message}</cyan>",
    )

    engine = create_async_engine("sqlite+aiosqlite:///./data.db")
    session = async_sessionmaker(engine)
    logger.info("Engine initialized and session factory created")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema ensured")

    search = Search()
    count = -1
    logger.info("Search initialized")

    while True:
        begin = asyncio.get_event_loop().time()
        async with session() as sess:
            input = await sess.execute(select(Facts).where(Facts.id > count))
            for i in input.scalars():
                count = max(count, i.id)
                search.add(parse(i.data))
                logger.debug("input: {data}", data=i.data)

            def handler(o):
                fact = unparse(f"{o}")
                sess.add(Facts(data=fact))
                logger.debug("output: {fact}", fact=fact)
                if len(o) != 0:
                    idea = unparse(f"--\n{o[0]}")
                    sess.add(Ideas(data=idea))
                    logger.debug("idea output: {idea}", idea=idea)
                return False

            number = search.execute(handler)
            await sess.commit()
        end = asyncio.get_event_loop().time()
        duration = end - begin
        logger.info("duration: {duration:0.3f}s", duration=duration)
        if number == 0:
            delay = max(0, 1 - duration)
            logger.info("sleeping: {delay:0.3f}s", delay=delay)
            await asyncio.sleep(delay)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
