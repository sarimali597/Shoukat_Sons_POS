"""
Barcode generator for Shoukat Sons Garments POS.

Generates Code 128 barcodes for product labels and invoice receipts.
Supports both image generation for preview and TSPL commands for printing.
"""

from typing import Optional

try:
    from barcode import get_barcode_class
    from barcode.writer import ImageWriter
    from PIL import Image

    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False


def generate_barcode_image(
    data: str, output_path: Optional[str] = None
) -> Optional["Image.Image"]:
    """
    Generate a Code 128 barcode image for on-screen preview.

    Args:
        data: Barcode data to encode.
        output_path: Optional path to save the image file.

    Returns:
        PIL Image object if successful, None if barcode library unavailable.
    """
    assert isinstance(data, str) and len(data) > 0

    if not BARCODE_AVAILABLE:
        return None

    code128 = get_barcode_class("code128")
    barcode_instance = code128(data, writer=ImageWriter())

    if output_path:
        assert isinstance(output_path, str) and len(output_path) > 0
        barcode_instance.save(output_path)

    return barcode_instance.render()


def generate_barcode_svg(data: str, output_path: str) -> None:
    """
    Generate SVG barcode for high-quality rendering.

    Args:
        data: Barcode data to encode.
        output_path: Path to save the SVG file.
    """
    assert isinstance(data, str) and len(data) > 0
    assert isinstance(output_path, str) and len(output_path) > 0

    if not BARCODE_AVAILABLE:
        raise RuntimeError("Barcode library not available")

    code128 = get_barcode_class("code128")
    barcode_instance = code128(data)

    with open(output_path, "wb") as f:
        barcode_instance.write(f)
