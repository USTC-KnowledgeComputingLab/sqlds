from __future__ import annotations
import sys
from loguru import logger
from sqlalchemy import create_engine, Integer, Text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column


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


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    addr = sys.argv[1]

    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <5}</level> | <cyan>{message}</cyan>",
    )

    engine = create_engine(addr)
    session = sessionmaker(engine)
    logger.info("Engine initialized")

    Base.metadata.create_all(engine)
    logger.info("Database schema ensured")

    with session() as sess:
        query = sess.query(Facts)
        for i in query:
            logger.info("fact: {data}", data=i.data)

        query = sess.query(Ideas)
        for i in query:
            logger.info("idea: {data}", data=i.data)

        sess.commit()

    engine.dispose()


if __name__ == "__main__":
    main()
