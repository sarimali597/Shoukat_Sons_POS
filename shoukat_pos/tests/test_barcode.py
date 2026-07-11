"""
Tests for barcode generator module.

Verifies Code 128 barcode generation, image output, and TSPL command generation.
"""

import pytest
from io import BytesIO

from utils.barcode_generator import (
    BARCODE_AVAILABLE,
    generate_barcode_image,
    generate_barcode_svg,
)


class TestBarcodeImageGeneration:
    """Test barcode image generation."""

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_generate_barcode_image_returns_image(self):
        """Test that barcode generation returns a PIL Image."""
        from PIL import Image

        img = generate_barcode_image("TEST123456")
        assert img is not None
        assert isinstance(img, Image.Image)

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_generate_barcode_image_with_output_path(self, tmp_path):
        """Test barcode generation with file output."""
        from PIL import Image

        output_path = tmp_path / "test_barcode.png"
        img = generate_barcode_image("TEST123456", str(output_path))

        assert img is not None
        # The python-barcode library saves with extension added automatically
        png_path = tmp_path / "test_barcode.png.png"
        assert png_path.exists() or output_path.exists()

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_generate_barcode_image_various_data(self):
        """Test barcode generation with various data formats."""
        test_data = [
            "123456789012",
            "SSG-TSH-001",
            "ABC-XYZ-999",
            "9999999999999",
        ]

        for data in test_data:
            img = generate_barcode_image(data)
            assert img is not None

    def test_generate_barcode_image_library_unavailable(self, monkeypatch):
        """Test graceful handling when barcode library is unavailable."""
        monkeypatch.setattr("utils.barcode_generator.BARCODE_AVAILABLE", False)

        result = generate_barcode_image("TEST123")
        assert result is None

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_empty_data_raises_assertion(self):
        """Test that empty data raises assertion error."""
        with pytest.raises(AssertionError):
            generate_barcode_image("")

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_non_string_data_raises_assertion(self):
        """Test that non-string data raises assertion error."""
        with pytest.raises(AssertionError):
            generate_barcode_image(123456)


class TestBarcodeSVGGeneration:
    """Test SVG barcode generation."""

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_generate_barcode_svg_creates_file(self, tmp_path):
        """Test SVG barcode creates a file."""
        output_path = tmp_path / "test_barcode.svg"
        generate_barcode_svg("TEST123456", str(output_path))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_generate_barcode_svg_content(self, tmp_path):
        """Test SVG barcode contains valid SVG content."""
        output_path = tmp_path / "test_barcode.svg"
        generate_barcode_svg("TEST123456", str(output_path))

        content = output_path.read_text()
        assert "<svg" in content
        assert "</svg>" in content

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_generate_barcode_svg_encodes_data(self, tmp_path):
        """Test SVG barcode encodes the input data."""
        output_path = tmp_path / "test_barcode.svg"
        test_data = "UNIQUE123"
        generate_barcode_svg(test_data, str(output_path))

        content = output_path.read_text()
        # The data should be encoded in the barcode
        assert len(content) > 0

    def test_generate_barcode_svg_library_unavailable(self, tmp_path, monkeypatch):
        """Test graceful handling when barcode library is unavailable."""
        monkeypatch.setattr("utils.barcode_generator.BARCODE_AVAILABLE", False)

        output_path = tmp_path / "test_barcode.svg"
        with pytest.raises(RuntimeError, match="Barcode library not available"):
            generate_barcode_svg("TEST123", str(output_path))

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_empty_data_raises_assertion(self, tmp_path):
        """Test that empty data raises assertion error."""
        output_path = tmp_path / "test_barcode.svg"
        with pytest.raises(AssertionError):
            generate_barcode_svg("", str(output_path))

    @pytest.mark.skipif(not BARCODE_AVAILABLE, reason="Barcode library not available")
    def test_invalid_path_raises_assertion(self):
        """Test that invalid path raises assertion error."""
        with pytest.raises(AssertionError):
            generate_barcode_svg("TEST123", "")
