"""Tests for scripts/strip_png_metadata.py."""

import importlib.util
import struct
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("strip_png_metadata", ROOT / "scripts" / "strip_png_metadata.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def chunk(kind: bytes, body: bytes, crc: int | None = None) -> bytes:
    if crc is None:
        crc = zlib.crc32(kind + body)
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


IHDR = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
IDAT = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
IEND = chunk(b"IEND", b"")


def png(*extra: bytes, tail: bytes = IEND) -> bytes:
    return mod.SIGNATURE + IHDR + b"".join(extra) + IDAT + tail


def test_only_the_allowlist_survives_and_pixels_are_kept():
    dirty = png(
        chunk(b"tEXt", b"Comment\x00hello"),
        chunk(b"eXIf", b"II*\x00"),
        chunk(b"iTXt", b"k\x00\x00\x00\x00\x00v"),
        chunk(b"tIME", b"\x07\xea\x0a\x10\x00\x00\x00"),
        chunk(b"iCCP", b"profile\x00\x00data"),
        chunk(b"pHYs", b"\x00" * 9),
        chunk(b"bKGD", b"\x00\x00"),
        chunk(b"zzzz", b"unknown"),
        chunk(b"gAMA", b"\x00\x00\xb1\x8f"),
        chunk(b"sRGB", b"\x00"),
        chunk(b"tRNS", b"\x00"),
    )
    clean = mod.strip(dirty)
    assert mod.chunk_types(clean) == [b"IHDR", b"gAMA", b"sRGB", b"tRNS", b"IDAT", b"IEND"]
    assert set(mod.chunk_types(clean)) <= mod.KEEP
    assert mod.strip(clean) == clean


def test_a_clean_file_is_left_byte_identical(tmp_path):
    f = tmp_path / "a.png"
    f.write_bytes(png())
    before = f.read_bytes()
    assert mod.main([str(f)]) == 0
    assert f.read_bytes() == before


def test_main_rewrites_in_place_and_check_flags_without_writing(tmp_path):
    f = tmp_path / "a.png"
    dirty = png(chunk(b"tEXt", b"Software\x00x"))
    f.write_bytes(dirty)
    assert mod.main(["--check", str(f)]) == 1
    assert f.read_bytes() == dirty
    assert mod.main([str(f)]) == 0
    assert mod.main(["--check", str(f)]) == 0


@pytest.mark.parametrize(
    ("label", "data", "message"),
    [
        ("not a png", b"GIF89a....", "signature"),
        ("empty", b"", "signature"),
        ("signature only", mod.SIGNATURE, "IEND"),
        ("missing IEND", mod.SIGNATURE + IHDR + IDAT, "IEND"),
        ("bad CRC", mod.SIGNATURE + IHDR + chunk(b"IDAT", b"abc", crc=0) + IEND, "CRC"),
        ("bad CRC on a metadata chunk", png(chunk(b"tEXt", b"x\x00y", crc=1)), "CRC"),
        ("trailing bytes", png() + b"\x00\x00\x00", "after IEND"),
        ("whole chunk after IEND", png() + chunk(b"tEXt", b"x\x00y"), "after IEND"),
        ("truncated header", mod.SIGNATURE + IHDR[:6], "truncated"),
        ("truncated body", mod.SIGNATURE + IHDR + IDAT[:-3], "truncated"),
        ("length past the end", mod.SIGNATURE + struct.pack(">I", 2**31) + b"IDAT", "length"),
        ("two IEND", png() + IEND, "after IEND"),
        ("IHDR not first", mod.SIGNATURE + IDAT + IHDR + IEND, "IHDR"),
        ("APNG acTL", png(chunk(b"acTL", b"\x00" * 8)), "APNG"),
        ("APNG fcTL", png(chunk(b"fcTL", b"\x00" * 26)), "APNG"),
        ("APNG fdAT", png(chunk(b"fdAT", b"\x00" * 6)), "APNG"),
    ],
)
def test_malformed_or_unsupported_files_are_refused_and_left_untouched(tmp_path, label, data, message):
    with pytest.raises(mod.PngError, match=message):
        mod.strip(data)
    f = tmp_path / "bad.png"
    f.write_bytes(data)
    assert mod.main([str(f)]) == 1, label
    assert mod.main(["--check", str(f)]) == 1, label
    assert f.read_bytes() == data


def test_a_missing_file_is_an_error_not_a_crash(tmp_path):
    assert mod.main([str(tmp_path / "nope.png")]) == 1


def test_no_arguments_is_a_usage_error():
    assert mod.main([]) == 2
