"""Tests for TSPL builder module."""

import pytest

from utils.tspl_builder import TSPLBuilder


class TestTSPLBuilderInit:
    """Test TSPLBuilder initialization."""

    def test_init_creates_basic_commands(self) -> None:
        """Test that init creates SIZE, GAP, CODEPAGE, DIRECTION, CLS."""
        builder = TSPLBuilder(28, 19)
        commands = builder.build()

        assert "SIZE 28 mm,19 mm" in commands
        assert "GAP 2 mm,0 mm" in commands
        assert 'CODEPAGE "UTF-8"' in commands
        assert "DIRECTION 1" in commands
        assert "CLS" in commands

    def test_init_with_custom_gap(self) -> None:
        """Test initialization with custom gap size."""
        builder = TSPLBuilder(32, 25, gap_mm=3)
        commands = builder.build()

        assert "GAP 3 mm,0 mm" in commands


class TestTSPLBuilderMethods:
    """Test individual TSPLBuilder methods."""

    def test_size_method(self) -> None:
        """Test size method adds SIZE command."""
        builder = TSPLBuilder(28, 19)
        builder.size(32, 25)
        commands = builder.build()

        assert "SIZE 32 mm,25 mm" in commands

    def test_gap_method(self) -> None:
        """Test gap method adds GAP command."""
        builder = TSPLBuilder(28, 19)
        builder.gap(3, 1)
        commands = builder.build()

        assert "GAP 3 mm,1 mm" in commands

    def test_direction_method(self) -> None:
        """Test direction method adds DIRECTION command."""
        builder = TSPLBuilder(28, 19)
        builder.direction(-1)
        commands = builder.build()

        assert "DIRECTION -1" in commands

    def test_codepage_method(self) -> None:
        """Test codepage method adds CODEPAGE command."""
        builder = TSPLBuilder(28, 19)
        builder.codepage("ISO8859-1")
        commands = builder.build()

        assert 'CODEPAGE "ISO8859-1"' in commands

    def test_offset_method(self) -> None:
        """Test offset method adds OFFSET command."""
        builder = TSPLBuilder(28, 19)
        builder.offset(5)
        commands = builder.build()

        assert "OFFSET 5 mm,0 mm" in commands

    def test_speed_method(self) -> None:
        """Test speed method adds SPEED command."""
        builder = TSPLBuilder(28, 19)
        builder.speed(3)
        commands = builder.build()

        assert "SPEED 3" in commands

    def test_density_method(self) -> None:
        """Test density method adds DENSITY command."""
        builder = TSPLBuilder(28, 19)
        builder.density(10)
        commands = builder.build()

        assert "DENSITY 10" in commands

    def test_text_method(self) -> None:
        """Test text method adds TEXT command."""
        builder = TSPLBuilder(28, 19)
        builder.text(100, 50, "2", 0, 1, 1, "Hello")
        commands = builder.build()

        assert 'TEXT 100,50,"2",0,1,1,"Hello"' in commands

    def test_barcode_method(self) -> None:
        """Test barcode method adds BARCODE command."""
        builder = TSPLBuilder(28, 19)
        builder.barcode(10, 20, "128", 80, 1, 0, 2, 2, "TEST123")
        commands = builder.build()

        assert 'BARCODE 10,20,"128",80,1,0,2,2,"TEST123"' in commands

    def test_print_label_method(self) -> None:
        """Test print_label method adds PRINT command."""
        builder = TSPLBuilder(28, 19)
        builder.print_label(3)
        commands = builder.build()

        assert "PRINT 3" in commands

    def test_end_method(self) -> None:
        """Test end method adds END command."""
        builder = TSPLBuilder(28, 19)
        builder.end()
        commands = builder.build()

        assert "END" in commands

    def test_method_chaining(self) -> None:
        """Test that methods return self for chaining."""
        builder = TSPLBuilder(28, 19)
        result = builder.text(0, 0, "1", 0, 1, 1, "Test")

        assert result is builder


class TestTSPLBuilderComplete:
    """Test complete label generation."""

    def test_complete_label_28x19(self) -> None:
        """Test generating a complete 28x19mm label."""
        builder = TSPLBuilder(28, 19)
        builder.text(112, 16, "2", 0, 1, 1, "Shop Name")
        builder.barcode(8, 32, "128", 80, 1, 0, 2, 2, "BARCODE123")
        builder.text(112, 112, "3", 0, 1, 1, "SN: 001")
        builder.print_label(1).end()

        commands = builder.build()

        assert commands.startswith("SIZE 28 mm,19 mm")
        assert commands.endswith("END")
        assert "PRINT 1" in commands

    def test_complete_label_32x25(self) -> None:
        """Test generating a complete 32x25mm label."""
        builder = TSPLBuilder(32, 25)
        builder.text(128, 16, "2", 0, 1, 1, "Larger Label")
        builder.print_label(2).end()

        commands = builder.build()

        assert commands.startswith("SIZE 32 mm,25 mm")
        assert "PRINT 2" in commands

    def test_build_returns_string(self) -> None:
        """Test that build returns a string."""
        builder = TSPLBuilder(28, 19)
        result = builder.build()

        assert isinstance(result, str)
        assert len(result) > 0
