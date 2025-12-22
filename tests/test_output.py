import asyncio
import tempfile
import pathlib
import pytest
import pytest_asyncio
from ddss.orm import initialize_database, Facts, Ideas
from ddss.output import main


@pytest_asyncio.fixture
async def temp_db():
    """Fixture to create a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "test.db"
        addr = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        engine, session = await initialize_database(addr)
        yield addr, engine, session
        await engine.dispose()


@pytest.mark.asyncio
async def test_output_formats_facts_correctly(temp_db, capsys):
    """Test that Facts data is formatted correctly using unparse() ('a\\n----\\nb' becomes 'a => b')."""
    addr, engine, session = temp_db

    # Add test data
    async with session() as sess:
        sess.add(Facts(data="a\n----\nb\n"))
        await sess.commit()

    # Run the main function with a timeout to avoid infinite loop
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.2)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check output
    captured = capsys.readouterr()
    assert "fact: a => b" in captured.out


@pytest.mark.asyncio
async def test_output_formats_ideas_correctly(temp_db, capsys):
    """Test that Ideas data is formatted correctly using unparse() ('x\\n----\\ny' becomes 'x => y')."""
    addr, engine, session = temp_db

    # Add test data
    async with session() as sess:
        sess.add(Ideas(data="x\n----\ny\n"))
        await sess.commit()

    # Run the main function with a timeout to avoid infinite loop
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.2)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check output
    captured = capsys.readouterr()
    assert "idea: x => y" in captured.out


@pytest.mark.asyncio
async def test_output_multiple_entries(temp_db, capsys):
    """Test that output handles multiple Facts and Ideas correctly."""
    addr, engine, session = temp_db

    # Add test data
    async with session() as sess:
        sess.add(Facts(data="a\n----\nb\n"))
        sess.add(Facts(data="c\n----\nd\n"))
        sess.add(Ideas(data="x\n----\ny\n"))
        sess.add(Ideas(data="p\n----\nq\n"))
        await sess.commit()

    # Run the main function with a timeout to avoid infinite loop
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.2)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check output
    captured = capsys.readouterr()
    assert "idea: x => y" in captured.out
    assert "idea: p => q" in captured.out
    assert "fact: a => b" in captured.out
    assert "fact: c => d" in captured.out


@pytest.mark.asyncio
async def test_output_cancellation(temp_db):
    """Test that the output main function can be cancelled without hanging."""
    addr, engine, session = temp_db

    # Run the main function and cancel it
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.1)  # Let it start
    task.cancel()

    # Should complete without hanging
    try:
        await task
    except asyncio.CancelledError:
        pass  # Expected - cancellation worked
