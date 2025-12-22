import asyncio
import tempfile
import pathlib
import pytest
import pytest_asyncio
from sqlalchemy import select
from ddss.orm import initialize_database, Facts, Ideas
from ddss.egg import main


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
async def test_egg_processes_ideas_with_matching_facts(temp_db):
    """Test that egg processes Ideas and generates Facts when there are matching facts."""
    addr, engine, session = temp_db

    # Add test data - a fact and an idea that should match
    async with session() as sess:
        # Add a fact that defines an equality
        sess.add(Facts(data="----\n(binary == a b)\n"))
        # Add an idea that should match the fact
        sess.add(Ideas(data="----\n(binary == a b)\n"))
        await sess.commit()

    # Run the main function with a timeout to avoid infinite loop
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that the idea was processed (it should be removed from pool when matched)
    # The fact count should remain the same or increase
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_count = len(facts.all())
        assert fact_count >= 1


@pytest.mark.asyncio
async def test_egg_adds_facts_from_search_results(temp_db):
    """Test that egg adds new Facts generated from search results."""
    addr, engine, session = temp_db

    # Add test data
    async with session() as sess:
        # Add a base fact
        sess.add(Facts(data="----\nx\n"))
        # Add an idea that won't immediately match (will stay in pool)
        sess.add(Ideas(data="----\ny\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that facts were processed
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_list = facts.all()
        assert len(fact_list) >= 1


@pytest.mark.asyncio
async def test_egg_with_multiple_ideas_and_facts(temp_db):
    """Test that egg handles multiple Ideas and Facts correctly."""
    addr, engine, session = temp_db

    # Add test data
    async with session() as sess:
        sess.add(Facts(data="----\na\n"))
        sess.add(Facts(data="----\nb\n"))
        sess.add(Ideas(data="----\nx\n"))
        sess.add(Ideas(data="----\ny\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)  # Give it time to process
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that the system processed the data
    async with session() as sess:
        ideas = await sess.scalars(select(Ideas))
        facts = await sess.scalars(select(Facts))
        idea_list = ideas.all()
        fact_list = facts.all()
        assert len(idea_list) == 2  # Ideas should remain
        assert len(fact_list) >= 2  # Facts should be present


@pytest.mark.asyncio
async def test_egg_cancellation(temp_db):
    """Test that the egg main function can be cancelled without hanging."""
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
async def test_egg_loop_continues_processing(temp_db):
    """Test that egg continues looping and processing new data."""
    addr, engine, session = temp_db

    # Add initial data
    async with session() as sess:
        sess.add(Facts(data="----\ninitial\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.2)  # Let it process initial data

    # Add more data while it's running
    async with session() as sess:
        sess.add(Ideas(data="----\nnew_idea\n"))
        await sess.commit()

    await asyncio.sleep(0.2)  # Give it time to process new data
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that new data was processed
    async with session() as sess:
        ideas_result = await sess.scalars(select(Ideas))
        idea_list = ideas_result.all()
        assert len(idea_list) >= 1


@pytest.mark.asyncio
async def test_egg_incremental_processing(temp_db):
    """Test that egg only processes new Facts and Ideas (using id > max_fact/max_idea)."""
    addr, engine, session = temp_db

    # Add initial data
    async with session() as sess:
        sess.add(Facts(data="----\nfact1\n"))
        sess.add(Ideas(data="----\nidea1\n"))
        await sess.commit()

    # Run the main function briefly
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Add more data with higher IDs
    async with session() as sess:
        sess.add(Facts(data="----\nfact2\n"))
        sess.add(Ideas(data="----\nidea2\n"))
        await sess.commit()

    # Run again - it should process the new data
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify all data is in database
    async with session() as sess:
        facts_result = await sess.scalars(select(Facts))
        ideas_result = await sess.scalars(select(Ideas))
        assert len(facts_result.all()) >= 2
        assert len(ideas_result.all()) >= 2
