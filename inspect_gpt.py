#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import argparse
from pathlib import Path
import struct
import zlib


SECTOR = 512


def read_gpt(image, header_lba, total_sectors):
    image.seek(header_lba * SECTOR)
    header = image.read(SECTOR)
    if header[:8] != b"EFI PART":
        raise ValueError(f"No GPT signature at LBA {header_lba}")

    header_size, expected_crc = struct.unpack_from("<II", header, 12)
    if not 92 <= header_size <= SECTOR:
        raise ValueError(f"Invalid GPT header size at LBA {header_lba}")
    header_for_crc = bytearray(header[:header_size])
    header_for_crc[16:20] = bytes(4)
    if zlib.crc32(header_for_crc) != expected_crc:
        raise ValueError(f"GPT header CRC mismatch at LBA {header_lba}")

    current, other, first_usable, last_usable = struct.unpack_from("<QQQQ", header, 24)
    if current != header_lba or other != (total_sectors - 1 if header_lba == 1 else 1):
        raise ValueError(f"Unexpected primary/backup pointers at LBA {header_lba}")
    if not 1 < first_usable <= last_usable < total_sectors - 1:
        raise ValueError(f"Invalid usable range at LBA {header_lba}")

    entries_lba, count, entry_size, expected_crc = struct.unpack_from("<QIII", header, 72)
    entries_size = count * entry_size
    end_lba = entries_lba + (entries_size + SECTOR - 1) // SECTOR
    if (
        not 0 < count <= 4096
        or not 128 <= entry_size <= 4096
        or entry_size % 128
        or not 1 < entries_lba < end_lba < total_sectors
        or entries_lba <= header_lba < end_lba
        or not (end_lba <= first_usable or entries_lba > last_usable)
    ):
        raise ValueError(f"Invalid partition table geometry at LBA {header_lba}")
    image.seek(entries_lba * SECTOR)
    entries = image.read(entries_size)
    if len(entries) != entries_size or zlib.crc32(entries) != expected_crc:
        raise ValueError(f"GPT partition table CRC mismatch at LBA {header_lba}")
    return first_usable, last_usable, header[56:72], entry_size, entries


def inspect(path):
    size = path.stat().st_size
    if size % SECTOR or size < 68 * SECTOR:
        raise ValueError("Expected a complete 512-byte-sector eMMC user-area image")
    total_sectors = size // SECTOR
    with path.open("rb") as image:
        primary = read_gpt(image, 1, total_sectors)
        backup = read_gpt(image, total_sectors - 1, total_sectors)
    if primary != backup:
        raise ValueError("Primary and backup GPT disagree")

    first_usable, last_usable, _, entry_size, entries = primary
    partitions = []
    for offset in range(0, len(entries), entry_size):
        entry = entries[offset:offset + entry_size]
        if not any(entry[:16]):
            continue
        first, last = struct.unpack_from("<QQ", entry, 32)
        if not first_usable <= first <= last <= last_usable:
            raise ValueError("Partition exceeds the GPT usable range")
        name = entry[56:128].decode("utf-16le").split(chr(0), 1)[0]
        partitions.append((offset // entry_size + 1, name, first, last))
    return size, partitions


def main():
    parser = argparse.ArgumentParser(description="Read and verify a complete eMMC GPT backup")
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        size, partitions = inspect(args.image)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"{size:,} bytes; primary and backup GPT verified; {len(partitions)} partitions")
    print(f"{'No.':>3}  {'Name':16} {'First LBA':>10} {'Last LBA':>10} {'Sectors':>10}")
    for index, name, first, last in partitions:
        print(f"{index:3}  {name:16} {first:10} {last:10} {last - first + 1:10}")


if __name__ == "__main__":
    main()
