#!/usr/bin/python3
"""
Test that room layout compression produces byte-identical output to precompressed files.

Room layouts use 3 compression modes:
  Mode 0: Raw (uncompressed)
  Mode 1: Common-byte with 1-byte key (8 bytes per group)
  Mode 2: Common-byte with 2-byte key (16 bytes per group)
  Mode 3: Dictionary-based compression (for large rooms)
"""
import sys
import os
import glob

sys.path.append(os.path.dirname(__file__) + '/..')
from common import *

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def decompress_room(data):
    """Decompress a room layout .cmp file."""
    mode = data[0]
    compressed = data[1:]

    if mode == 0:
        return mode, bytearray(compressed)
    elif mode == 1:
        _, result = decompressData_commonByte(compressed, 1)
        return mode, result
    elif mode == 2:
        _, result = decompressData_commonByte(compressed, 2)
        return mode, result
    elif mode == 3:
        # Dictionary compression - can't easily decompress without the dictionary
        return mode, None
    else:
        return mode, None


def test_small_rooms(game):
    """Test small room compression."""
    precmp_dir = os.path.join(base_dir, 'precompressed', 'rooms', game)
    src_dir = os.path.join(base_dir, 'rooms', game, 'small')

    if not os.path.isdir(precmp_dir) or not os.path.isdir(src_dir):
        return 0, 0, 0

    passed = 0
    failed = 0
    skipped = 0

    for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
        basename = os.path.basename(cmp_path)
        room_name = os.path.splitext(basename)[0]

        # Check if this is a small room (has source in small/ directory)
        src_path = os.path.join(src_dir, room_name + '.bin')
        if not os.path.exists(src_path):
            # Might be a large room
            skipped += 1
            continue

        with open(cmp_path, 'rb') as f:
            original = bytearray(f.read())

        with open(src_path, 'rb') as f:
            source = bytearray(f.read())

        mode = original[0]
        original_compressed = original[1:]

        # Recompress using the same algorithm as compressRoomLayout.py
        possibilities = []
        possibilities.append(source)
        possibilities.append(compressData_commonByte(source, 1))
        possibilities.append(compressData_commonByte(source, 2))

        # Use the same strange condition as the original
        smallest_index = 0
        if len(possibilities[1]) >= len(possibilities[0]) or len(possibilities[2]) >= len(possibilities[0]):
            smallest_index = 0
        else:
            smallest_len = len(source)
            for i in range(3):
                if len(possibilities[i]) <= smallest_len:
                    smallest_len = len(possibilities[i])
                    smallest_index = i

        recompressed = bytearray([smallest_index]) + bytearray(possibilities[smallest_index])

        if recompressed == original:
            passed += 1
        else:
            print("  FAIL: %s mode=%d orig_size=%d new_size=%d" % (
                basename, mode, len(original), len(recompressed)))
            failed += 1

    return passed, failed, skipped


def test_large_rooms(game):
    """Test large room (dictionary) compression."""
    precmp_dir = os.path.join(base_dir, 'precompressed', 'rooms', game)

    if not os.path.isdir(precmp_dir):
        return 0, 0, 0

    passed = 0
    failed = 0
    skipped = 0

    for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
        basename = os.path.basename(cmp_path)
        room_name = os.path.splitext(basename)[0]

        # Check if this is a large room
        for group in ['large']:
            src_path = os.path.join(base_dir, 'rooms', game, group, room_name + '.bin')
            if os.path.exists(src_path):
                break
        else:
            continue

        with open(cmp_path, 'rb') as f:
            original = bytearray(f.read())

        mode = original[0]
        if mode == 3:
            # Dictionary compression - need to test with the actual compressor
            skipped += 1
        else:
            skipped += 1

    return passed, failed, skipped


def main():
    print("=== Testing room layout compression ===")
    for game in ['seasons', 'ages']:
        print("\n--- %s (small rooms) ---" % game)
        p, f, s = test_small_rooms(game)
        print("  Results: %d passed, %d failed, %d skipped" % (p, f, s))

        print("--- %s (large rooms) ---" % game)
        p2, f2, s2 = test_large_rooms(game)
        print("  Results: %d passed, %d failed, %d skipped" % (p2, f2, s2))


if __name__ == '__main__':
    main()
