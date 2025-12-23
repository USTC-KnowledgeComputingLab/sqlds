import asyncio
import tempfile
import pathlib
import pytest
import pytest_asyncio
from sqlalchemy import select
from ddss.orm import initialize_database, Facts, Ideas
from ddss.ds import main


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
async def test_ds_simple_modus_ponens(temp_db):
    """Test simple modus ponens: 'a => b' with '=> a' produces '=> b'."""
    addr, engine, session = temp_db

    # Add initial facts: a => b and => a
    async with session() as sess:
        sess.add(Facts(data="a\n----\nb\n"))
        sess.add(Facts(data="----\na\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check that the new fact '=> b' was created
    async with session() as sess:
        all_facts = await sess.scalars(select(Facts))
        facts_data = [f.data for f in all_facts]

    assert "----\nb\n" in facts_data


@pytest.mark.asyncio
async def test_ds_multi_premise_with_idea(temp_db):
    """Test multi-premise rule: 'a, b => c' with '=> a' produces 'b => c' and idea '=> b'."""
    addr, engine, session = temp_db

    # Add initial facts: a, b => c and => a
    async with session() as sess:
        sess.add(Facts(data="a\nb\n----\nc\n"))
        sess.add(Facts(data="----\na\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check that the new fact 'b => c' was created
    async with session() as sess:
        all_facts = await sess.scalars(select(Facts))
        facts_data = [f.data for f in all_facts]

    assert "b\n----\nc\n" in facts_data

    # Check that the idea '=> b' was created
    async with session() as sess:
        all_ideas = await sess.scalars(select(Ideas))
        ideas_data = [i.data for i in all_ideas]

    assert "----\nb\n" in ideas_data


@pytest.mark.asyncio
async def test_ds_no_inference_without_matching_facts(temp_db):
    """Test that no inference occurs when facts don't match."""
    addr, engine, session = temp_db

    # Add facts that don't match: a => b and => c
    async with session() as sess:
        sess.add(Facts(data="a\n----\nb\n"))
        sess.add(Facts(data="----\nc\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check that only the original facts exist (no new inference)
    async with session() as sess:
        all_facts = await sess.scalars(select(Facts))
        facts_data = [f.data for f in all_facts]

    # Should only have the original 2 facts
    assert len(facts_data) == 2
    assert "a\n----\nb\n" in facts_data
    assert "----\nc\n" in facts_data


@pytest.mark.asyncio
async def test_ds_multiple_inferences(temp_db):
    """Test multiple inference steps in sequence."""
    addr, engine, session = temp_db

    # Add facts for chained inference: a => b, b => c, => a
    async with session() as sess:
        sess.add(Facts(data="a\n----\nb\n"))
        sess.add(Facts(data="b\n----\nc\n"))
        sess.add(Facts(data="----\na\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.5)  # Give it time for multiple rounds
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Check that both => b and => c were inferred
    async with session() as sess:
        all_facts = await sess.scalars(select(Facts))
        facts_data = [f.data for f in all_facts]

    assert "----\nb\n" in facts_data
    assert "----\nc\n" in facts_data


@pytest.mark.asyncio
async def test_ds_cancellation(temp_db):
    """Test that the ds main function can be cancelled without hanging."""
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


@pytest.mark.asyncio
async def test_ds_duplicate_facts_not_added(temp_db):
    """Test that duplicate facts are not added to the database."""
    addr, engine, session = temp_db

    # Add facts that will produce a duplicate: a => b twice with => a
    async with session() as sess:
        sess.add(Facts(data="a\n----\nc\n"))
        sess.add(Facts(data="b\n----\nc\n"))
        sess.add(Facts(data="----\na\n"))
        sess.add(Facts(data="----\nb\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Count the facts - should have 5: original 4 + 1 inferred => c
    async with session() as sess:
        all_facts = await sess.scalars(select(Facts))
        facts_list = list(all_facts)

    assert len(facts_list) == 5
    facts_data = [f.data for f in facts_list]
    assert facts_data.count("----\nc\n") == 1  # Should only appear once
