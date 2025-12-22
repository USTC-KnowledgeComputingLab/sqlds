import asyncio
import tempfile
import pathlib
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select

from ddss.orm import initialize_database, Facts, Ideas
from ddss.input import main


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
async def test_input_valid_fact(temp_db):
    """Test that valid input is parsed and stored as a Fact in the database."""
    addr, engine, session = temp_db

    # Mock PromptSession to simulate user input
    mock_prompt_session = MagicMock()
    # First call returns valid input (parse will transform it), second call raises EOFError to exit
    mock_prompt_session.prompt_async = AsyncMock(side_effect=["a => b", EOFError()])

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function
        task = asyncio.create_task(main(addr, engine, session))
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Verify data was stored (parse transforms "a => b" to "a\n----\nb\n")
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        facts_list = list(facts)
        assert len(facts_list) == 1
        assert facts_list[0].data == "a\n----\nb\n"


@pytest.mark.asyncio
async def test_input_generates_idea(temp_db):
    """Test that input that parses to non-dashed form generates an Idea."""
    addr, engine, session = temp_db

    # Mock PromptSession to simulate user input
    mock_prompt_session = MagicMock()
    # Input "a => b" parses to "a\n----\nb\n" which doesn't start with "--"
    # so it generates an idea
    mock_prompt_session.prompt_async = AsyncMock(side_effect=["a => b", EOFError()])

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function
        task = asyncio.create_task(main(addr, engine, session))
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Verify both Fact and Idea were stored
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        facts_list = list(facts)
        assert len(facts_list) == 1
        # parse("a => b") returns "a\n----\nb\n"
        assert facts_list[0].data == "a\n----\nb\n"

        ideas = await sess.scalars(select(Ideas))
        ideas_list = list(ideas)
        assert len(ideas_list) == 1
        # rule_get_idea extracts first line: "----\na\n"
        assert ideas_list[0].data == "----\na\n"


@pytest.mark.asyncio
async def test_input_invalid_input_handling(temp_db, capsys):
    """Test that invalid/malformed input is handled gracefully with error message."""
    addr, engine, session = temp_db

    # Mock PromptSession to simulate user input
    mock_prompt_session = MagicMock()
    # First input will cause parse error, second exits
    mock_prompt_session.prompt_async = AsyncMock(side_effect=["=>", EOFError()])

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function
        task = asyncio.create_task(main(addr, engine, session))
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Check that error was printed
    captured = capsys.readouterr()
    assert "error:" in captured.out

    # Verify no data was stored
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        facts_list = list(facts)
        assert len(facts_list) == 0


@pytest.mark.asyncio
async def test_input_empty_input_continues(temp_db):
    """Test that empty input is skipped and loop continues."""
    addr, engine, session = temp_db

    # Mock PromptSession to simulate user input
    mock_prompt_session = MagicMock()
    # Empty strings should be skipped, then valid input, then exit
    mock_prompt_session.prompt_async = AsyncMock(side_effect=["", "  ", "a => b", EOFError()])

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function
        task = asyncio.create_task(main(addr, engine, session))
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Verify only the valid input was stored (empty ones were skipped)
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        facts_list = list(facts)
        assert len(facts_list) == 1
        # parse("a => b") returns "a\n----\nb\n"
        assert facts_list[0].data == "a\n----\nb\n"


@pytest.mark.asyncio
async def test_input_keyboard_interrupt_handling(temp_db):
    """Test that KeyboardInterrupt is handled and causes cancellation."""
    addr, engine, session = temp_db

    # Mock PromptSession to simulate user input
    mock_prompt_session = MagicMock()
    # Simulate KeyboardInterrupt
    mock_prompt_session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt())

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function
        task = asyncio.create_task(main(addr, engine, session))
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected - cancellation worked

    # Verify no data was stored
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        facts_list = list(facts)
        assert len(facts_list) == 0


@pytest.mark.asyncio
async def test_input_cancellation(temp_db):
    """Test that the input main function can be cancelled without hanging."""
    addr, engine, session = temp_db

    # Mock PromptSession with infinite input loop
    mock_prompt_session = MagicMock()

    # This will keep returning valid input indefinitely
    async def infinite_input(*args, **kwargs):
        await asyncio.sleep(0.1)
        return "a => b"

    mock_prompt_session.prompt_async = AsyncMock(side_effect=infinite_input)

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function and cancel it
        task = asyncio.create_task(main(addr, engine, session))
        await asyncio.sleep(0.2)  # Let it process a bit
        task.cancel()

        # Should complete without hanging
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected - cancellation worked


@pytest.mark.asyncio
async def test_input_multiple_entries(temp_db):
    """Test that multiple valid inputs are stored correctly."""
    addr, engine, session = temp_db

    # Mock PromptSession to simulate user input
    mock_prompt_session = MagicMock()
    # Multiple valid inputs
    mock_prompt_session.prompt_async = AsyncMock(
        side_effect=[
            "a => b",  # Generates idea (parses to "a\n----\nb\n")
            "c => d",  # Generates idea (parses to "c\n----\nd\n")
            "simple",  # No idea (parses to "----\nsimple\n" which starts with --)
            EOFError(),
        ]
    )

    with patch("ddss.input.PromptSession", return_value=mock_prompt_session):
        # Run the main function
        task = asyncio.create_task(main(addr, engine, session))
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Verify all data was stored
    async with session() as sess:
        facts = await sess.scalars(select(Facts))
        facts_list = list(facts)
        # Should have 3 facts
        assert len(facts_list) == 3
        fact_data = [f.data for f in facts_list]
        assert "a\n----\nb\n" in fact_data
        assert "c\n----\nd\n" in fact_data
        assert "----\nsimple\n" in fact_data

        # Should have 2 ideas (from "a => b" and "c => d")
        ideas = await sess.scalars(select(Ideas))
        ideas_list = list(ideas)
        assert len(ideas_list) == 2
        idea_data = [i.data for i in ideas_list]
        assert "----\na\n" in idea_data
        assert "----\nc\n" in idea_data
