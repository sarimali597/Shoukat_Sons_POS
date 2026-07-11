"""
TSPL command builder for BlackCopper BC-LP-1300 label printer.

Generates TSPL commands programmatically for printing garment stickers.
Supports multiple sticker sizes and all required label elements.
"""

from typing import Optional


class TSPLBuilder:
    """
    Builder class for constructing TSPL command strings.

    BlackCopper BC-LP-1300 specs:
    - Resolution: 203 DPI (8 dots/mm)
    - Max print width: 108mm
    - Print speed: 127mm/s
    """

    def __init__(self, width_mm: int, height_mm: int, gap_mm: int = 2) -> None:
        """
        Initialize TSPL builder with label dimensions.

        Args:
            width_mm: Label width in millimeters.
            height_mm: Label height in millimeters.
            gap_mm: Gap between labels in millimeters (default 2).
        """
        assert isinstance(width_mm, int) and width_mm > 0
        assert isinstance(height_mm, int) and height_mm > 0
        assert isinstance(gap_mm, int) and gap_mm >= 0

        self.commands: list[str] = []
        self.dpi = 203
        self.dpmm = 8  # dots per mm at 203 DPI
        self.size(width_mm, height_mm)
        self.gap(gap_mm, 0)
        self.codepage("UTF-8")
        self.direction(1)
        self.cls()

    def size(self, w: int, h: int) -> "TSPLBuilder":
        """
        Set label size.

        Args:
            w: Width in mm.
            h: Height in mm.

        Returns:
            Self for method chaining.
        """
        assert isinstance(w, int) and w > 0
        assert isinstance(h, int) and h > 0
        self.commands.append(f"SIZE {w} mm,{h} mm")
        return self

    def gap(self, g: int, offset: int) -> "TSPLBuilder":
        """
        Set gap between labels.

        Args:
            g: Gap size in mm.
            offset: Offset in mm.

        Returns:
            Self for method chaining.
        """
        assert isinstance(g, int) and g >= 0
        assert isinstance(offset, int) and offset >= 0
        self.commands.append(f"GAP {g} mm,{offset} mm")
        return self

    def cls(self) -> "TSPLBuilder":
        """
        Clear image buffer.

        Returns:
            Self for method chaining.
        """
        self.commands.append("CLS")
        return self

    def direction(self, dir_val: int) -> "TSPLBuilder":
        """
        Set print direction.

        Args:
            dir_val: 1 or -1 for normal/reverse direction.

        Returns:
            Self for method chaining.
        """
        assert dir_val in (1, -1)
        self.commands.append(f"DIRECTION {dir_val}")
        return self

    def codepage(self, cp: str) -> "TSPLBuilder":
        """
        Set character code page.

        Args:
            cp: Code page name (e.g., "UTF-8").

        Returns:
            Self for method chaining.
        """
        assert isinstance(cp, str) and len(cp) > 0
        self.commands.append(f'CODEPAGE "{cp}"')
        return self

    def offset(self, offset_mm: int) -> "TSPLBuilder":
        """
        Set vertical offset for fine-tuning position.

        Args:
            offset_mm: Offset in mm.

        Returns:
            Self for method chaining.
        """
        assert isinstance(offset_mm, int)
        self.commands.append(f"OFFSET {offset_mm} mm,0 mm")
        return self

    def speed(self, s: int) -> "TSPLBuilder":
        """
        Set print speed.

        Args:
            s: Speed value (1-4 for BC-LP-1300).

        Returns:
            Self for method chaining.
        """
        assert isinstance(s, int) and 1 <= s <= 4
        self.commands.append(f"SPEED {s}")
        return self

    def density(self, d: int) -> "TSPLBuilder":
        """
        Set print density (darkness).

        Args:
            d: Density value (0-15 for BC-LP-1300).

        Returns:
            Self for method chaining.
        """
        assert isinstance(d, int) and 0 <= d <= 15
        self.commands.append(f"DENSITY {d}")
        return self

    def text(
        self,
        x: int,
        y: int,
        font: str,
        rotation: int,
        x_mul: int,
        y_mul: int,
        content: str,
    ) -> "TSPLBuilder":
        """
        Add text to label.

        Args:
            x: X coordinate in dots (1mm = 8 dots).
            y: Y coordinate in dots.
            font: Font type ("1", "2", "3", etc.).
            rotation: Rotation angle (0, 90, 180, 270).
            x_mul: X magnification (1-10).
            y_mul: Y magnification (1-10).
            content: Text content.

        Returns:
            Self for method chaining.
        """
        assert isinstance(x, int) and x >= 0
        assert isinstance(y, int) and y >= 0
        assert isinstance(font, str) and len(font) > 0
        assert isinstance(rotation, int) and rotation in (0, 90, 180, 270)
        assert isinstance(x_mul, int) and x_mul > 0
        assert isinstance(y_mul, int) and y_mul > 0
        assert isinstance(content, str)

        self.commands.append(
            f'TEXT {x},{y},"{font}",{rotation},{x_mul},{y_mul},"{content}"'
        )
        return self

    def barcode(
        self,
        x: int,
        y: int,
        code_type: str,
        height: int,
        readable: int,
        rotation: int,
        narrow: int,
        wide: int,
        content: str,
    ) -> "TSPLBuilder":
        """
        Add barcode to label.

        Args:
            x: X coordinate in dots.
            y: Y coordinate in dots.
            code_type: Barcode type ("128" for Code 128).
            height: Barcode height in dots.
            readable: 1 to show human-readable text, 0 to hide.
            rotation: Rotation angle (0, 90, 180, 270).
            narrow: Narrow bar width in dots.
            wide: Wide bar width in dots.
            content: Barcode data.

        Returns:
            Self for method chaining.
        """
        assert isinstance(x, int) and x >= 0
        assert isinstance(y, int) and y >= 0
        assert isinstance(code_type, str) and len(code_type) > 0
        assert isinstance(height, int) and height > 0
        assert isinstance(readable, int) and readable in (0, 1)
        assert isinstance(rotation, int) and rotation in (0, 90, 180, 270)
        assert isinstance(narrow, int) and narrow > 0
        assert isinstance(wide, int) and wide > 0
        assert isinstance(content, str) and len(content) > 0

        self.commands.append(
            f'BARCODE {x},{y},"{code_type}",{height},{readable},'
            f"{rotation},{narrow},{wide},\"{content}\""
        )
        return self

    def print_label(self, copies: int = 1) -> "TSPLBuilder":
        """
        Add print command.

        Args:
            copies: Number of copies to print (default 1).

        Returns:
            Self for method chaining.
        """
        assert isinstance(copies, int) and copies > 0
        self.commands.append(f"PRINT {copies}")
        return self

    def end(self) -> "TSPLBuilder":
        """
        Add END command to finalize label.

        Returns:
            Self for method chaining.
        """
        self.commands.append("END")
        return self

    def build(self) -> str:
        """
        Build complete TSPL command string.

        Returns:
            Complete TSPL commands as newline-separated string.
        """
        return "\n".join(self.commands)
