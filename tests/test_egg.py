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
async def test_egg_symmetry_ab_to_ba(temp_db):
    """Test symmetry: given fact a=b and idea b=a, egg should produce fact b=a."""
    addr, engine, session = temp_db

    # Add fact a=b
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == a b)\n"))
        sess.add(Ideas(data="----\n(binary == b a)\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that fact b=a was produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        assert "----\n(binary == b a)\n" in fact_data


@pytest.mark.asyncio
async def test_egg_transitivity_abc(temp_db):
    """Test transitivity: given a=b, b=c, and idea a=c, egg should produce a=c."""
    addr, engine, session = temp_db

    # Add facts a=b and b=c
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == a b)\n"))
        sess.add(Facts(data="----\n(binary == b c)\n"))
        sess.add(Ideas(data="----\n(binary == a c)\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that fact a=c was produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        assert "----\n(binary == a c)\n" in fact_data


@pytest.mark.asyncio
async def test_egg_congruence_fx_fy(temp_db):
    """Test congruence: given x=y, expect f(x)=f(y), egg should produce it."""
    addr, engine, session = temp_db

    # Add fact x=y and idea f(x)=f(y)
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == x y)\n"))
        sess.add(Ideas(data="----\n(binary == (unary f x) (unary f y))\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that fact f(x)=f(y) was produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        assert "----\n(binary == (unary f x) (unary f y))\n" in fact_data


@pytest.mark.asyncio
async def test_egg_substitution_fx_with_xy(temp_db):
    """Test substitution: given f(x) and x=y, expect f(y) can be satisfied."""
    addr, engine, session = temp_db

    # Add fact f(x) and x=y, then idea f(y)
    async with session() as sess:
        sess.add(Facts(data="----\n(unary f x)\n"))
        sess.add(Facts(data="----\n(binary == x y)\n"))
        sess.add(Ideas(data="----\n(unary f y)\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that the idea was satisfied (removed from pool or fact produced)
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        # The idea should be satisfied because f(x) and x=y implies f(y)
        assert "----\n(unary f y)\n" in fact_data


@pytest.mark.asyncio
async def test_egg_substitution_fx_xyz(temp_db):
    """Test substitution chain: given x=y, y=z, f(x), expect f(z) can be satisfied."""
    addr, engine, session = temp_db

    # Add facts x=y, y=z, f(x), then idea f(z)
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == x y)\n"))
        sess.add(Facts(data="----\n(binary == y z)\n"))
        sess.add(Facts(data="----\n(unary f x)\n"))
        sess.add(Ideas(data="----\n(unary f z)\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that f(z) was produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        assert "----\n(unary f z)\n" in fact_data


@pytest.mark.asyncio
async def test_egg_cancellation(temp_db):
    """Test that the egg main function can be cancelled without hanging."""
    addr, engine, session = temp_db

    # Run the main function and cancel it
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.1)
    task.cancel()

    # Should complete without hanging
    try:
        await task
    except asyncio.CancelledError:
        pass
