import sys
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from apyds_bnf import parse
from .orm import initialize_database, insert_or_ignore, Facts, Ideas
from .poly import Poly


async def main(addr, engine=None, session=None):
    if engine is None or session is None:
        engine, session = await initialize_database(addr)

    try:
        prompt = PromptSession()
        while True:
            try:
                with patch_stdout():
                    data = await prompt.prompt_async("input: ")
                if data.strip() == "":
                    continue
            except (EOFError, KeyboardInterrupt):
                raise asyncio.CancelledError()
            try:
                parse(data)
            except Exception as e:
                print(f"error: {e}")
                continue
            async with session() as sess:
                poly = Poly(dsp=data)
                await insert_or_ignore(sess, Facts, poly.dsp)
                if idea := poly.idea:
                    await insert_or_ignore(sess, Ideas, idea.dsp)
                await sess.commit()
    except asyncio.CancelledError:
        pass
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <database-addr>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
