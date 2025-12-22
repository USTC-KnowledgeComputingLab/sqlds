import asyncio
import tempfile
import pathlib
from io import StringIO
import sys
import unittest
from ddss.orm import initialize_database, Facts, Ideas
from ddss.output import main


class TestOutput(unittest.TestCase):
    """Test the output module."""

    def test_output_formats_facts_correctly(self):
        """Test that Facts data is formatted correctly using unparse() ('a\\n----\\nb' becomes 'a => b')."""

        async def run_test():
            # Create a temporary database
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = pathlib.Path(tmpdir) / "test.db"
                addr = f"sqlite+aiosqlite:///{db_path.as_posix()}"

                # Initialize database and add test data
                engine, session = await initialize_database(addr)
                async with session() as sess:
                    sess.add(Facts(data="a\n----\nb"))
                    await sess.commit()

                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                try:
                    # Run the main function with a timeout to avoid infinite loop
                    task = asyncio.create_task(main(addr, engine, session))
                    await asyncio.sleep(0.2)  # Give it time to process
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                finally:
                    sys.stdout = old_stdout
                    await engine.dispose()

                # Check output
                output = captured_output.getvalue()
                self.assertIn("fact: a => b", output)

        asyncio.run(run_test())

    def test_output_formats_ideas_correctly(self):
        """Test that Ideas data is formatted correctly using unparse() ('x\\n----\\ny' becomes 'x => y')."""

        async def run_test():
            # Create a temporary database
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = pathlib.Path(tmpdir) / "test.db"
                addr = f"sqlite+aiosqlite:///{db_path.as_posix()}"

                # Initialize database and add test data
                engine, session = await initialize_database(addr)
                async with session() as sess:
                    sess.add(Ideas(data="x\n----\ny"))
                    await sess.commit()

                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                try:
                    # Run the main function with a timeout to avoid infinite loop
                    task = asyncio.create_task(main(addr, engine, session))
                    await asyncio.sleep(0.2)  # Give it time to process
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                finally:
                    sys.stdout = old_stdout
                    await engine.dispose()

                # Check output
                output = captured_output.getvalue()
                self.assertIn("idea: x => y", output)

        asyncio.run(run_test())

    def test_output_multiple_entries(self):
        """Test that output handles multiple Facts and Ideas correctly."""

        async def run_test():
            # Create a temporary database
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = pathlib.Path(tmpdir) / "test.db"
                addr = f"sqlite+aiosqlite:///{db_path.as_posix()}"

                # Initialize database and add test data
                engine, session = await initialize_database(addr)
                async with session() as sess:
                    sess.add(Facts(data="a\n----\nb"))
                    sess.add(Facts(data="c\n----\nd"))
                    sess.add(Ideas(data="x\n----\ny"))
                    sess.add(Ideas(data="p\n----\nq"))
                    await sess.commit()

                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                try:
                    # Run the main function with a timeout to avoid infinite loop
                    task = asyncio.create_task(main(addr, engine, session))
                    await asyncio.sleep(0.2)  # Give it time to process
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                finally:
                    sys.stdout = old_stdout
                    await engine.dispose()

                # Check output
                output = captured_output.getvalue()
                self.assertIn("idea: x => y", output)
                self.assertIn("idea: p => q", output)
                self.assertIn("fact: a => b", output)
                self.assertIn("fact: c => d", output)

        asyncio.run(run_test())

    def test_output_cancellation(self):
        """Test that the output main function can be cancelled without hanging."""

        async def run_test():
            # Create a temporary database
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = pathlib.Path(tmpdir) / "test.db"
                addr = f"sqlite+aiosqlite:///{db_path.as_posix()}"

                # Initialize database
                engine, session = await initialize_database(addr)

                # Run the main function and cancel it
                task = asyncio.create_task(main(addr, engine, session))
                await asyncio.sleep(0.1)  # Let it start
                task.cancel()

                # Should complete without hanging
                try:
                    await task
                except asyncio.CancelledError:
                    pass  # Expected - cancellation worked

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
