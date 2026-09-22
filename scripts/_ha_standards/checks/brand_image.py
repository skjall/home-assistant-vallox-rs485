# Vendored from ha-integration-standards 0.2.0. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Read a brand PNG far enough to hold it to the house style.

Pillow is not a dependency here and must not become one: these gates are
vendored into public repositories and run from a checkout with nothing but
PyYAML installed. A PNG carries its dimensions in the first chunk and its
pixels in a format the standard library can already decompress, so reading
both by hand costs less than the dependency would.

What this does not do is decode every PNG in the world. Interlaced and
16-bit images are recognised and reported as unreadable rather than guessed
at - a wrong colour would be worse than no answer.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"

# colour type -> samples per pixel
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


class NotAPng(Exception):
    """The file is not a PNG this reader will touch."""


@dataclass(frozen=True)
class Png:
    """A brand image, as much of it as the gates need."""

    width: int
    height: int
    bit_depth: int
    colour_type: int
    interlaced: bool
    _pixels: bytes | None
    _palette: bytes

    @property
    def readable(self) -> bool:
        """True when corner colours can be reported."""
        return self._pixels is not None

    def corners(self) -> set[tuple[int, int, int]]:
        """Return the RGB of the four corner pixels, alpha ignored."""
        if self._pixels is None:
            raise NotAPng("pixels were not decoded")
        return {
            self._rgb(x, y) for x in (0, self.width - 1) for y in (0, self.height - 1)
        }

    def _rgb(self, x: int, y: int) -> tuple[int, int, int]:
        assert self._pixels is not None
        samples = CHANNELS[self.colour_type]
        at = (y * self.width + x) * samples
        pixel = self._pixels[at : at + samples]
        if self.colour_type == 3:
            index = pixel[0] * 3
            return tuple(self._palette[index : index + 3])  # type: ignore[return-value]
        if self.colour_type in (0, 4):
            return (pixel[0], pixel[0], pixel[0])
        return (pixel[0], pixel[1], pixel[2])


def _chunks(raw: bytes) -> list[tuple[bytes, bytes]]:
    """Split a PNG into (type, data), ignoring the CRCs."""
    out: list[tuple[bytes, bytes]] = []
    at = len(SIGNATURE)
    while at + 8 <= len(raw):
        (length,) = struct.unpack(">I", raw[at : at + 4])
        kind = raw[at + 4 : at + 8]
        body = raw[at + 8 : at + 8 + length]
        out.append((kind, body))
        at += 12 + length
        if kind == b"IEND":
            break
    return out


def _paeth(a: int, b: int, c: int) -> int:
    """Predict a sample the way PNG does: whichever neighbour the gradient favours."""
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter(raw: bytes, width: int, height: int, samples: int) -> bytes:
    """Undo the per-scanline filters, leaving flat 8-bit samples."""
    stride = width * samples
    out = bytearray(stride * height)
    previous = bytearray(stride)
    at = 0
    for row in range(height):
        method = raw[at]
        line = bytearray(raw[at + 1 : at + 1 + stride])
        at += 1 + stride
        for i in range(stride):
            left = line[i - samples] if i >= samples else 0
            up = previous[i]
            up_left = previous[i - samples] if i >= samples else 0
            if method == 1:
                line[i] = (line[i] + left) & 0xFF
            elif method == 2:
                line[i] = (line[i] + up) & 0xFF
            elif method == 3:
                line[i] = (line[i] + (left + up) // 2) & 0xFF
            elif method == 4:
                line[i] = (line[i] + _paeth(left, up, up_left)) & 0xFF
        out[row * stride : (row + 1) * stride] = line
        previous = line
    return bytes(out)


def read(path: Path) -> Png:
    """Parse a PNG; raise NotAPng when it is not one."""
    raw = path.read_bytes()
    if not raw.startswith(SIGNATURE):
        raise NotAPng("not a PNG file")

    chunks = _chunks(raw)
    header = next((body for kind, body in chunks if kind == b"IHDR"), None)
    if header is None or len(header) < 13:
        raise NotAPng("no IHDR chunk")
    width, height, depth, colour, _, _, interlace = struct.unpack(
        ">IIBBBBB", header[:13]
    )
    if colour not in CHANNELS:
        raise NotAPng(f"unsupported colour type {colour}")

    palette = next((body for kind, body in chunks if kind == b"PLTE"), b"")
    pixels: bytes | None = None
    # 8 bits per sample and no interlacing covers everything a build produces;
    # anything else is left undecoded rather than approximated.
    if depth == 8 and not interlace:
        data = b"".join(body for kind, body in chunks if kind == b"IDAT")
        try:
            pixels = _unfilter(zlib.decompress(data), width, height, CHANNELS[colour])
        except zlib.error as err:
            raise NotAPng(f"image data will not decompress: {err}") from err

    return Png(
        width=width,
        height=height,
        bit_depth=depth,
        colour_type=colour,
        interlaced=bool(interlace),
        _pixels=pixels,
        _palette=palette,
    )


def to_hex(rgb: tuple[int, int, int]) -> str:
    """Format a colour the way the settings spell it."""
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def parse_hex(value: str) -> tuple[int, int, int] | None:
    """Read '#RRGGBB' from the settings; None when it is not one."""
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None
