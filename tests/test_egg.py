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
async def test_egg_complex_situation(temp_db):
    """Test comprehensive combination: symmetry, transitivity, congruence, and substitution.

    Given:
    - a=b (fact)
    - b=c (fact)
    - f(a) (fact)

    Should derive:
    - b=a (via symmetry from a=b)
    - a=c (via transitivity from a=b, b=c)
    - f(b)=f(c) (via congruence from b=c)
    - f(c) (via substitution: f(a) and a=c)
    """
    addr, engine, session = temp_db

    # Add facts a=b, b=c, f(a)
    # Add ideas for b=a (symmetry), a=c (transitivity), f(b)=f(c) (congruence), f(c) (substitution)
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == a b)\n"))
        sess.add(Facts(data="----\n(binary == b c)\n"))
        sess.add(Facts(data="----\n(unary f a)\n"))
        # Ideas to test
        sess.add(Ideas(data="----\n(binary == b a)\n"))  # symmetry
        sess.add(Ideas(data="----\n(binary == a c)\n"))  # transitivity
        sess.add(Ideas(data="----\n(binary == (unary f b) (unary f c))\n"))  # congruence
        sess.add(Ideas(data="----\n(unary f c)\n"))  # substitution
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that all expected facts were produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        # Test symmetry: a=b should derive b=a
        assert "----\n(binary == b a)\n" in fact_data
        # Test transitivity: a=b, b=c should derive a=c
        assert "----\n(binary == a c)\n" in fact_data
        # Test congruence: b=c should derive f(b)=f(c)
        assert "----\n(binary == (unary f b) (unary f c))\n" in fact_data
        # Test substitution: f(a) and a=c should derive f(c)
        assert "----\n(unary f c)\n" in fact_data


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


# Variable-based tests
@pytest.mark.asyncio
async def test_egg_symmetry_with_variables(temp_db):
    """Test symmetry with variables: given variable equality a(`x)=b(`x),
    the system can derive the symmetric concrete instance b(t)=a(t) by
    unifying the variable pattern with concrete value t."""
    addr, engine, session = temp_db

    # Add fact a(`x)=b(`x) with variable
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == (unary a `x) (unary b `x))\n"))
        sess.add(Ideas(data="----\n(binary == (unary b t) (unary a t))\n"))
        await sess.commit()

    # Run the main function with a timeout
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that fact b(t)=a(t) was produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        assert "----\n(binary == (unary b t) (unary a t))\n" in fact_data


@pytest.mark.asyncio
async def test_egg_transitivity_with_variables(temp_db):
    """Test transitivity with variables: given a(`x)=b(`x), b(`x)=c(`x), should produce a(t)=c(t)."""
    addr, engine, session = temp_db

    # Add facts a(`x)=b(`x) and b(`x)=c(`x)
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == (unary a `x) (unary b `x))\n"))
        sess.add(Facts(data="----\n(binary == (unary b `x) (unary c `x))\n"))
        sess.add(Ideas(data="----\n(binary == (unary a t) (unary c t))\n"))
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that fact a(t)=c(t) was produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        assert "----\n(binary == (unary a t) (unary c t))\n" in fact_data


@pytest.mark.asyncio
async def test_egg_congruence_with_variables(temp_db):
    """Test congruence with variables: given a(`x)=b(`x), derive f(a(t))=f(b(t)).

    This tests that variable patterns enable congruence on nested structures:
    - Variable fact a(`x)=b(`x) allows deriving concrete equality a(t)=b(t)
    - Concrete equality a(t)=b(t) enables congruence to derive f(a(t))=f(b(t))
    """
    addr, engine, session = temp_db

    # Add variable equality fact
    async with session() as sess:
        sess.add(Facts(data="----\n(binary == (unary a `x) (unary b `x))\n"))
        # Add ideas to test the derivation chain
        sess.add(Ideas(data="----\n(binary == (unary a t) (unary b t))\n"))  # concrete instance
        sess.add(Ideas(data="----\n(binary == (unary f (unary a t)) (unary f (unary b t)))\n"))  # congruence
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that both facts were produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        # First, a(t)=b(t) should be derived from a(`x)=b(`x)
        assert "----\n(binary == (unary a t) (unary b t))\n" in fact_data
        # Then, f(a(t))=f(b(t)) should be derived via congruence
        assert "----\n(binary == (unary f (unary a t)) (unary f (unary b t)))\n" in fact_data


@pytest.mark.asyncio
async def test_egg_substitution_with_variables(temp_db):
    """Test substitution with variables: given f(a(`x)) and a(`x)=b(`x), derive f(b(t)).

    This tests that variable patterns enable substitution in nested structures:
    - Facts f(a(`x)) and a(`x)=b(`x) allow deriving f(b(`x)) via e-graph equality
    - Variable fact f(b(`x)) allows deriving concrete instance f(b(t))
    """
    addr, engine, session = temp_db

    # Add facts with variables
    async with session() as sess:
        sess.add(Facts(data="----\n(unary f (unary a `x))\n"))
        sess.add(Facts(data="----\n(binary == (unary a `x) (unary b `x))\n"))
        # Add ideas to test the derivation chain
        sess.add(Ideas(data="----\n(unary f (unary b `x))\n"))  # substitution via equality
        sess.add(Ideas(data="----\n(unary f (unary b t))\n"))  # concrete instance
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that both facts were produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        # First, f(b(`x)) should be derived via substitution
        assert "----\n(unary f (unary b `x))\n" in fact_data
        # Then, f(b(t)) should be derived as a concrete instance
        assert "----\n(unary f (unary b t))\n" in fact_data


@pytest.mark.asyncio
async def test_egg_complex_situation_with_variables(temp_db):
    """Test comprehensive combination with variables alongside concrete facts.

    This test demonstrates that variable facts and concrete facts can work together.

    Given:
    - a(`x)=b(`x) (variable fact: establishes parametric equality)
    - b(`x)=c(`x) (variable fact: establishes parametric equality)
    - a=b (concrete fact: needed for congruence to work on concrete terms)
    - b=c (concrete fact: needed for congruence to work on concrete terms)
    - f(a) (concrete fact)

    Should derive:
    - b(t)=a(t) (via symmetry from variable fact a(`x)=b(`x))
    - a(t)=c(t) (via transitivity from variable facts a(`x)=b(`x), b(`x)=c(`x))
    - f(b)=f(c) (via congruence from concrete facts a=b, b=c)
    - f(c) (via substitution: f(a) and concrete transitivity a=b=c)
    """
    addr, engine, session = temp_db

    # Add both variable facts and concrete facts
    async with session() as sess:
        # Variable facts for testing parametric reasoning
        sess.add(Facts(data="----\n(binary == (unary a `x) (unary b `x))\n"))
        sess.add(Facts(data="----\n(binary == (unary b `x) (unary c `x))\n"))
        # Concrete facts needed for congruence on non-parametric terms
        sess.add(Facts(data="----\n(binary == a b)\n"))
        sess.add(Facts(data="----\n(binary == b c)\n"))
        sess.add(Facts(data="----\n(unary f a)\n"))
        # Ideas to test
        sess.add(Ideas(data="----\n(binary == (unary b t) (unary a t))\n"))  # symmetry
        sess.add(Ideas(data="----\n(binary == (unary a t) (unary c t))\n"))  # transitivity
        sess.add(Ideas(data="----\n(binary == (unary f b) (unary f c))\n"))  # congruence
        sess.add(Ideas(data="----\n(unary f c)\n"))  # substitution
        await sess.commit()

    # Run the main function
    task = asyncio.create_task(main(addr, engine, session))
    await asyncio.sleep(0.3)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify that all expected facts were produced
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        fact_data = [f.data for f in facts.all()]
        # Test symmetry: a(`x)=b(`x) should derive b(t)=a(t)
        assert "----\n(binary == (unary b t) (unary a t))\n" in fact_data
        # Test transitivity: a(`x)=b(`x), b(`x)=c(`x) should derive a(t)=c(t)
        assert "----\n(binary == (unary a t) (unary c t))\n" in fact_data
        # Test congruence: a=b, b=c should derive f(b)=f(c)
        assert "----\n(binary == (unary f b) (unary f c))\n" in fact_data
        # Test substitution: f(a) and a=b=c should derive f(c)
        assert "----\n(unary f c)\n" in fact_data
