from sqlalchemy import create_engine, Integer, Text
from sqlalchemy.exc import IntegrityError
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


def initialize_database(addr):
    engine = create_engine(addr)
    session = sessionmaker(engine)

    Base.metadata.create_all(engine)
    return engine, session


def insert_or_ignore(sess, model, data):
    try:
        with sess.begin_nested():
            sess.add(model(data=data))
    except IntegrityError:
        pass
