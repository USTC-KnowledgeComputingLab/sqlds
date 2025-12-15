import sys
import time
from apyds import Search
from apyds_bnf import parse, unparse
from orm import initialize_database, insert_or_ignore, Facts, Ideas


def main(addr):
    engine, session = initialize_database(addr)

    search = Search()
    max_fact = -1

    while True:
        begin = time.time()
        with session() as sess:
            query = sess.query(Facts).filter(Facts.id > max_fact)
            for i in query:
                max_fact = max(max_fact, i.id)
                search.add(parse(i.data))

            def handler(o):
                fact = unparse(f"{o}")
                insert_or_ignore(sess, Facts, fact)
                if len(o) != 0:
                    idea = unparse(f"--\n{o[0]}")
                    insert_or_ignore(sess, Ideas, idea)
                return False

            count = search.execute(handler)
            sess.commit()

        end = time.time()
        duration = end - begin
        if count == 0:
            delay = max(0, 1 - duration)
            time.sleep(delay)

    engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    main(sys.argv[1])
