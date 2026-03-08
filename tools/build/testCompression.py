#!/usr/bin/python3
"""
Test that our vanilla-matching compressor produces byte-identical output
to the precompressed assets from the original ROM.

Usage:
    python3 tools/build/testCompression.py [--verbose] [--stop-on-fail] [category]

Categories: gfx, rooms, tilesets, all (default: all)
"""

import sys
import os
import glob
import tempfile
import subprocess

sys.path.append(os.path.dirname(__file__) + '/..')
from common import *
from compressGfxVanilla import compress_mode, compress_auto


def read_cmp_file(filepath):
    """Read a .cmp file and return (mode, decompressed_size, compressed_data, raw_bytes)"""
    with open(filepath, 'rb') as f:
        data = bytearray(f.read())
    if len(data) < 3:
        return None
    mode = data[0]
    decompressed_size = data[1] | (data[2] << 8)
    compressed_data = data[3:]
    return (mode, decompressed_size, compressed_data, data)


def decompress_gfx(compressed_data, mode, decompressed_size):
    """Decompress GFX data using the specified mode."""
    if mode == 0:
        return bytearray(compressed_data[:decompressed_size])
    else:
        num_blocks = decompressed_size // 16 - 1
        if decompressed_size % 16 != 0:
            num_blocks = decompressed_size // 16
        result = decompressGfxData(compressed_data, 0, num_blocks, mode)
        return bytearray(result[1][:decompressed_size])


def test_gfx_file(cmp_path, verbose=False):
    """Test compression of a single GFX file.

    Returns: (success, message)
    """
    basename = os.path.basename(cmp_path)
    info = read_cmp_file(cmp_path)
    if info is None:
        return (False, f"{basename}: Could not read file")

    mode, decompressed_size, original_compressed, raw = info

    # Step 1: Decompress the original
    try:
        decompressed = decompress_gfx(original_compressed, mode, decompressed_size)
    except Exception as e:
        return (False, f"{basename}: Decompression failed: {e}")

    if len(decompressed) != decompressed_size:
        return (False, f"{basename}: Decompressed size mismatch: "
                f"expected {decompressed_size}, got {len(decompressed)}")

    # Step 2: Re-compress with the same mode
    try:
        recompressed = compress_mode(decompressed, mode)
    except Exception as e:
        return (False, f"{basename}: Recompression failed: {e}")

    # Step 3: Compare
    if recompressed == original_compressed:
        if verbose:
            return (True, f"{basename}: MATCH (mode={mode}, "
                    f"decompressed={decompressed_size}, "
                    f"compressed={len(original_compressed)})")
        return (True, None)
    else:
        # Find first difference
        min_len = min(len(recompressed), len(original_compressed))
        diff_pos = -1
        for i in range(min_len):
            if recompressed[i] != original_compressed[i]:
                diff_pos = i
                break
        if diff_pos == -1:
            diff_pos = min_len

        # Also verify that our recompressed data decompresses correctly
        try:
            re_decompressed = decompress_gfx(recompressed, mode, decompressed_size)
            decompresses_ok = (re_decompressed == decompressed)
        except:
            decompresses_ok = False

        return (False, f"{basename}: MISMATCH (mode={mode}, "
                f"orig_compressed={len(original_compressed)}, "
                f"new_compressed={len(recompressed)}, "
                f"first_diff_at={diff_pos}, "
                f"decompresses_correctly={decompresses_ok})")


def test_room_file(cmp_path, verbose=False):
    """Test compression of a single room layout file.

    Returns: (success, message)
    """
    basename = os.path.basename(cmp_path)
    with open(cmp_path, 'rb') as f:
        data = bytearray(f.read())

    mode = data[0]
    compressed = data[1:]

    # Decompress based on mode
    if mode == 0:
        decompressed = compressed
    elif mode == 1:
        _, decompressed = decompressData_commonByte(compressed, 1)
    elif mode == 2:
        _, decompressed = decompressData_commonByte(compressed, 2)
    elif mode == 3:
        # Dictionary compression - skip for now
        if verbose:
            return (True, f"{basename}: SKIP (dictionary mode)")
        return (True, None)
    else:
        return (False, f"{basename}: Unknown mode {mode}")

    # Re-compress
    from compressRoomLayout import compressData_commonByte
    # This is handled differently - skip for now
    if verbose:
        return (True, f"{basename}: mode={mode}, size={len(data)}")
    return (True, None)


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    stop_on_fail = '--stop-on-fail' in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    category = args[0] if args else 'all'

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    total_pass = 0
    total_fail = 0
    total_skip = 0

    if category in ('gfx', 'all'):
        print("=== Testing GFX compression ===")
        for subdir in ['common', 'seasons', 'ages']:
            precmp_dir = os.path.join(base_dir, 'precompressed', 'gfx_compressible', subdir)
            if not os.path.isdir(precmp_dir):
                continue
            print(f"\n--- {subdir} ---")

            subdir_pass = 0
            subdir_fail = 0

            for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
                success, message = test_gfx_file(cmp_path, verbose)
                if success:
                    subdir_pass += 1
                    if message:
                        print(f"  PASS: {message}")
                else:
                    subdir_fail += 1
                    print(f"  FAIL: {message}")
                    if stop_on_fail:
                        print("\nStopping on first failure.")
                        sys.exit(1)

            print(f"  Results: {subdir_pass} passed, {subdir_fail} failed")
            total_pass += subdir_pass
            total_fail += subdir_fail

    if category in ('rooms', 'all'):
        print("\n=== Testing room layout compression ===")
        print("  (Not yet implemented)")

    if category in ('tilesets', 'all'):
        print("\n=== Testing tileset layout compression ===")
        print("  (Not yet implemented)")

    print(f"\n=== TOTAL: {total_pass} passed, {total_fail} failed ===")
    if total_fail > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
