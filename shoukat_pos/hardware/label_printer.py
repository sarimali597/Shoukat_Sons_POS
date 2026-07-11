"""
Label printer service for BlackCopper BC-LP-1300 thermal label printer.

Handles TSPL command generation, USB printing via Windows spooler,
calibration, and error handling for garment sticker printing.
"""

import logging
from typing import Dict, List, Optional, Tuple

from database.models import Variant
from utils.tspl_builder import TSPLBuilder

logger = logging.getLogger(__name__)

# Sticker size presets (width_mm, height_mm)
STICKER_SIZES = {
    "28x19": (28, 19),  # Default - BlackCopper BC-TTL-28x19-3up
    "32x25": (32, 25),  # BlackCopper BC-TTL-32x25-3up
    "32x19": (32, 19),  # BlackCopper BC-TTL-32x19-3up
    "34x24": (34, 24),  # BlackCopper BC-TTL-34x24-3up
}


def generate_sticker_tspl(
    shop_name: str,
    barcode_data: str,
    serial: str,
    size: str,
    price: int,
    secret_code: str,
    product_name: str,
    sticker_width_mm: int = 28,
    sticker_height_mm: int = 19,
) -> str:
    """
    Generate TSPL commands for a garment sticker.

    All coordinates are in dots (1mm = 8 dots at 203 DPI).
    Label elements: shop name, barcode, serial, size, price, secret code, product name.

    Args:
        shop_name: Shop/brand name for header.
        barcode_data: Barcode string to encode.
        serial: Serial number for display.
        size: Garment size (S/M/L/XL/etc.).
        price: Sale price in cents.
        secret_code: Encoded purchase price.
        product_name: Product/style name.
        sticker_width_mm: Label width in mm (default 28).
        sticker_height_mm: Label height in mm (default 19).

    Returns:
        Complete TSPL command string for printing.
    """
    assert isinstance(shop_name, str) and len(shop_name) > 0
    assert isinstance(barcode_data, str) and len(barcode_data) > 0
    assert isinstance(serial, str) and len(serial) > 0
    assert isinstance(size, str) and len(size) > 0
    assert isinstance(price, int) and price > 0
    assert isinstance(secret_code, str) and len(secret_code) > 0
    assert isinstance(product_name, str) and len(product_name) > 0
    assert isinstance(sticker_width_mm, int) and sticker_width_mm > 0
    assert isinstance(sticker_height_mm, int) and sticker_height_mm > 0

    dpmm = 8  # dots per mm at 203 DPI
    builder = TSPLBuilder(sticker_width_mm, sticker_height_mm, 2)

    # Calculate center x position
    center_x = (sticker_width_mm // 2) * dpmm

    # Shop name (centered, small font at top)
    builder.text(
        center_x, 2 * dpmm, "2", 0, 1, 1, shop_name[:16]
    )

    # Barcode (Code 128, 10mm height, centered)
    builder.barcode(
        1 * dpmm, 4 * dpmm, "128", 10 * dpmm, 1, 0, 2, 2, barcode_data
    )

    # Serial number (below barcode, centered)
    builder.text(center_x, 14 * dpmm, "3", 0, 1, 1, f"SN: {serial}")

    # Size (left), Price (center), Secret code (right)
    left_x = 2 * dpmm
    right_x = (sticker_width_mm - 2) * dpmm

    builder.text(left_x, 16 * dpmm, "2", 0, 1, 1, f"Sz:{size}")
    builder.text(center_x, 16 * dpmm, "2", 0, 1, 1, f"Rs.{price // 100}")
    builder.text(right_x, 16 * dpmm, "2", 0, 1, 1, secret_code)

    # Product name (bottom, centered, tiny font)
    builder.text(center_x, 18 * dpmm, "1", 0, 1, 1, product_name[:20])

    builder.print_label(1).end()
    return builder.build()


class LabelPrinter:
    """
    Label printer handler for BlackCopper BC-LP-1300.

    Sends TSPL commands directly to the printer via Windows spooler
    using RAW datatype to bypass driver page-size abstraction.
    """

    def __init__(self, printer_name: str) -> None:
        """
        Initialize label printer.

        Args:
            printer_name: Windows printer name for BC-LP-1300.
        """
        assert isinstance(printer_name, str) and len(printer_name) > 0
        self.printer_name = printer_name
        self._win32print = None
        self._available = False

        try:
            import win32print

            self._win32print = win32print
            self._available = True
        except ImportError:
            logger.warning("win32print not available - printer disabled")

    def send_tspl(self, tspl_data: str) -> bool:
        """
        Send raw TSPL bytes directly to the printer via Windows spooler.

        Uses RAW datatype to bypass the driver's page-size abstraction.

        Args:
            tspl_data: TSPL command string to send.

        Returns:
            True if print succeeded, False otherwise.
        """
        assert isinstance(tspl_data, str) and len(tspl_data) > 0

        if not self._available or self._win32print is None:
            logger.error("win32print not available")
            return False

        try:
            hPrinter = self._win32print.OpenPrinter(self.printer_name)
            try:
                hJob = self._win32print.StartDocPrinter(
                    hPrinter, 1, ("Shoukat POS Label", None, "RAW")
                )
                try:
                    self._win32print.StartPagePrinter(hPrinter)
                    self._win32print.WritePrinter(
                        hPrinter, tspl_data.encode("utf-8")
                    )
                    self._win32print.EndPagePrinter(hPrinter)
                finally:
                    self._win32print.EndDocPrinter(hPrinter)
            finally:
                self._win32print.ClosePrinter(hPrinter)
            return True
        except Exception as e:
            logger.error(f"Print failed: {e}")
            return False

    def print_labels(
        self,
        variants: List[Variant],
        quantities: Dict[int, int],
        shop_name: str,
        sticker_size: str = "28x19",
    ) -> Tuple[int, int]:
        """
        Print multiple labels for variants.

        Args:
            variants: List of Variant objects to print labels for.
            quantities: Dict mapping variant_id to quantity to print.
            shop_name: Shop name for label header.
            sticker_size: Size preset key from STICKER_SIZES.

        Returns:
            Tuple of (success_count, fail_count).
        """
        assert isinstance(variants, list)
        assert isinstance(quantities, dict)
        assert isinstance(shop_name, str) and len(shop_name) > 0
        assert isinstance(sticker_size, str)

        if sticker_size not in STICKER_SIZES:
            sticker_size = "28x19"

        width_mm, height_mm = STICKER_SIZES[sticker_size]

        success_count = 0
        fail_count = 0

        for variant in variants:
            qty_to_print = quantities.get(variant.id, 1)

            for _ in range(qty_to_print):
                tspl = generate_sticker_tspl(
                    shop_name=shop_name,
                    barcode_data=variant.barcode,
                    serial=str(variant.id),
                    size=variant.size,
                    price=0,  # Would need to fetch from style
                    secret_code="TODO",  # Would need to fetch from batch
                    product_name="",  # Would need to fetch from style
                    sticker_width_mm=width_mm,
                    sticker_height_mm=height_mm,
                )

                if self.send_tspl(tspl):
                    success_count += 1
                else:
                    fail_count += 1

        return success_count, fail_count

    def print_test_page(self) -> bool:
        """
        Print a test label for alignment verification.

        Returns:
            True if print succeeded, False otherwise.
        """
        tspl = generate_sticker_tspl(
            shop_name="TEST PRINT",
            barcode_data="TEST123",
            serial="0001",
            size="M",
            price=100000,
            secret_code="ABC",
            product_name="Test Product",
        )
        return self.send_tspl(tspl)

    def calibrate(self) -> bool:
        """
        Send GAPDETECT command and prompt user to confirm alignment.

        Returns:
            True if calibration command sent successfully.
        """
        if not self._available or self._win32print is None:
            return False

        # TSPL calibration command
        calibrate_tspl = "GAPDETECT\nEND\n"
        return self.send_tspl(calibrate_tspl)

    def get_printers(self) -> List[str]:
        """
        List all available Windows printers.

        Returns:
            List of printer names.
        """
        if not self._available or self._win32print is None:
            return []

        try:
            return [
                p[2]
                for p in self._win32print.EnumPrinters(
                    self._win32print.PRINTER_ENUM_LOCAL
                )
            ]
        except Exception as e:
            logger.error(f"Failed to enumerate printers: {e}")
            return []
