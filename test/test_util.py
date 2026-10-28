"""Tests for the shared helper utilities (no network, no database)."""

import logging
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

import util


class _RecordingList(list):
    """List that records every slice request — proves how much chunking consumed."""

    def __init__(self, items: list[Any], slices: list[slice]) -> None:
        super().__init__(items)
        self.slices = slices

    def __getitem__(self, index: Any) -> Any:
        if isinstance(index, slice):
            self.slices.append(index)
        return super().__getitem__(index)


class TestSetupLogger:
    """Tests for :func:`util.setup_logger`."""

    def test_same_name_and_file_adds_one_file_handler(self, tmp_path: Any) -> None:
        """Rebuilding a logger for the same file stacks no second file handler."""
        # Arrange
        log_file = tmp_path / "provider.log"
        name = f"test_setup_logger_{uuid4().hex}"

        # Act
        first = util.setup_logger(name, str(log_file))
        second = util.setup_logger(name, str(log_file))

        # Assert
        assert first is second
        assert len([handler for handler in first.handlers if isinstance(handler, logging.FileHandler)]) == 1

    def test_setup_logger_mirrors_to_stdout_once(self, tmp_path: Any) -> None:
        """Every logger also mirrors records to stdout — exactly one stdout handler."""
        # Arrange
        log_file = tmp_path / "provider.log"
        name = f"test_setup_logger_stdout_{uuid4().hex}"

        # Act
        util.setup_logger(name, str(log_file))
        logger = util.setup_logger(name, str(log_file))

        # Assert
        stdout_handlers = [
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        ]
        assert len(stdout_handlers) == 1

    def test_same_name_and_file_logs_one_line_per_message(self, tmp_path: Any) -> None:
        """A duplicated setup never duplicates the written log lines."""
        # Arrange
        log_file = tmp_path / "provider.log"
        name = f"test_setup_logger_lines_{uuid4().hex}"
        util.setup_logger(name, str(log_file))
        logger = util.setup_logger(name, str(log_file))

        # Act
        logger.info("once")
        logger.info("twice")

        # Assert
        lines = [line for line in log_file.read_text().splitlines() if line.strip()]
        assert len(lines) == 2
        assert sum("once" in line for line in lines) == 1

    def test_same_name_other_file_adds_second_file_handler(self, tmp_path: Any) -> None:
        """The guard is per (name, file) — a genuinely new file still gets a handler."""
        # Arrange
        name = f"test_setup_logger_files_{uuid4().hex}"

        # Act
        util.setup_logger(name, str(tmp_path / "first.log"))
        logger = util.setup_logger(name, str(tmp_path / "second.log"))

        # Assert
        assert len([handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]) == 2

    def test_logger_does_not_propagate(self, tmp_path: Any) -> None:
        """The logger owns its handlers — records never reach ancestor loggers."""
        # Arrange
        name = f"test_setup_logger_propagate_{uuid4().hex}"

        # Act
        logger = util.setup_logger(name, str(tmp_path / "provider.log"))

        # Assert
        assert logger.propagate is False

    @pytest.fixture(autouse=True)
    def close_handlers(self) -> Iterator[None]:
        """Yield, then close every file handler this test added (no leaked descriptors)."""
        yield
        for logger_name in list(logging.Logger.manager.loggerDict):
            if logger_name.startswith("test_setup_logger"):
                logger = logging.getLogger(logger_name)
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)


class TestChunkListEqualSize:
    """Tests for :func:`util.chunk_list_equal_size`."""

    @pytest.mark.parametrize(
        ("items", "batch_size", "expected"),
        [
            ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
            ([], 10, []),
            ([1, 2, 3], 10, [[1, 2, 3]]),
        ],
    )
    def test_splits_into_chunks(self, items: list[int], batch_size: int, expected: list[list[int]]) -> None:
        """Items are chunked in order with a short tail; empty input yields nothing and a
        batch size above the list length yields a single chunk."""
        # Act & Assert
        assert list(util.chunk_list_equal_size(items, batch_size)) == expected

    def test_is_lazy_and_chunks_one_at_a_time(self) -> None:
        """No slice is taken before the first yield — only the yielded chunk is built."""
        # Arrange
        slices: list[slice] = []
        items = _RecordingList(list(range(10)), slices)

        # Act
        chunks = util.chunk_list_equal_size(items, 3)
        assert slices == []  # nothing consumed yet
        first = next(chunks)

        # Assert
        assert first == [0, 1, 2]
        assert slices == [slice(0, 3, None)]  # exactly one chunk built so far
        assert list(chunks) == [[3, 4, 5], [6, 7, 8], [9]]

    def test_returns_an_iterator(self) -> None:
        """The function streams chunks instead of materializing a list of lists."""
        assert isinstance(util.chunk_list_equal_size([1, 2, 3], 2), Iterator)
