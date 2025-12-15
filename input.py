import sys
from sqlalchemy import create_engine, Integer, Text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from apyds import Rule
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


def main(addr):
    engine = create_engine(addr)
    session = sessionmaker(engine)

    Base.metadata.create_all(engine)

    while True:
        data = input()
        with session() as sess:
            o = Rule(parse(data))

            fact = unparse(f"{o}")
            try:
                with sess.begin_nested():
                    sess.add(Facts(data=fact))
            except IntegrityError:
                pass
            if len(o) != 0:
                idea = unparse(f"--\n{o[0]}")
                try:
                    with sess.begin_nested():
                        sess.add(Ideas(data=idea))
                except IntegrityError:
                    pass

            sess.commit()

    engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    main(sys.argv[1])
