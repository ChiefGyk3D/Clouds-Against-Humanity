#!/usr/bin/env python3
"""Strip metadata chunks from PNG files, in place, using only the standard library.

Allowlist, not blocklist: only these chunks survive.

  IHDR PLTE IDAT IEND   the image itself
  tRNS                  transparency (palette or color-key alpha)
  gAMA cHRM sRGB        the color description a browser screenshot carries

Everything else is dropped: text (tEXt, zTXt, iTXt), EXIF (eXIf), timestamps
(tIME), physical size (pHYs), background (bKGD), histogram, suggested palette,
private chunks, and the embedded ICC profile (iCCP). iCCP is removed on
purpose: a profile carries free text (description, copyright, device and
software names) that can identify a machine, and sRGB plus gAMA/cHRM describe
what a browser screenshot needs; a viewer with no profile assumes sRGB. If a
picture's colors matter beyond that, check it by eye after stripping.

The file is validated as it is read: a good signature, an IHDR first, every
CRC correct, exactly one IEND which is the last chunk with nothing after it,
and every chunk inside the file. APNG (acTL, fcTL, fdAT) is refused, because
dropping those chunks would silently turn an animation into one still frame.
A file that fails any check is reported and left untouched.

Usage: python scripts/strip_png_metadata.py FILE.png [FILE.png ...]
       python scripts/strip_png_metadata.py --check FILE.png ...   (exit 1 if any would change or is invalid)
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"
KEEP = frozenset({b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND", b"gAMA", b"cHRM", b"sRGB"})
APNG = frozenset({b"acTL", b"fcTL", b"fdAT"})
MAX_CHUNK = 2**31 - 1


class PngError(ValueError):
    """The file is not a well-formed, supported PNG."""


def chunks(data: bytes):
    """Yield (type, raw bytes with length and CRC) for each chunk, validating the structure."""
    if not data.startswith(SIGNATURE):
        raise PngError("not a PNG (bad signature)")
    pos = len(SIGNATURE)
    seen_iend = False
    first = True
    while pos < len(data):
        if seen_iend:
            raise PngError("data after IEND")
        if pos + 8 > len(data):
            raise PngError("truncated chunk header")
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        if length > MAX_CHUNK:
            raise PngError(f"chunk {kind!r} has an impossible length")
        end = pos + 12 + length
        if end > len(data):
            raise PngError(f"truncated chunk {kind!r}")
        body = data[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", data[end - 4 : end])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise PngError(f"bad CRC in chunk {kind!r}")
        if kind in APNG:
            raise PngError("APNG (animated PNG) is not supported")
        if first and (kind != b"IHDR" or length != 13):
            raise PngError("first chunk is not a 13-byte IHDR")
        first = False
        if kind == b"IEND":
            if length != 0:
                raise PngError("IEND is not empty")
            seen_iend = True
        yield kind, data[pos:end]
        pos = end
    if not seen_iend:
        raise PngError("missing IEND")


def chunk_types(data: bytes) -> list[bytes]:
    return [kind for kind, _ in chunks(data)]


def strip(data: bytes) -> bytes:
    kept = [raw for kind, raw in chunks(data) if kind in KEEP]
    return SIGNATURE + b"".join(kept)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    files = [a for a in argv if a != "--check"]
    if not files:
        print(__doc__, file=sys.stderr)
        return 2
    status = 0
    for name in files:
        path = Path(name)
        try:
            data = path.read_bytes()
            clean = strip(data)
        except (PngError, OSError) as err:
            print(f"{name}: {err}", file=sys.stderr)
            status = 1
            continue
        if clean != data:
            if check:
                print(f"{name}: has metadata chunks")
                status = 1
            else:
                path.write_bytes(clean)
                print(f"{name}: stripped {len(data) - len(clean)} bytes")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
