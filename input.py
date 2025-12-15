import sys
from apyds import Rule
from apyds_bnf import parse, unparse
from orm import initialize_database, insert_or_ignore, Facts, Ideas


def main(addr):
    engine, session = initialize_database(addr)

    while True:
        data = input()
        with session() as sess:
            o = Rule(parse(data))
            fact = unparse(f"{o}")
            insert_or_ignore(sess, Facts, fact)
            if len(o) != 0:
                idea = unparse(f"--\n{o[0]}")
                insert_or_ignore(sess, Ideas, idea)
            sess.commit()

    engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    main(sys.argv[1])
