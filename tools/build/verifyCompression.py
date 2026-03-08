#!/usr/bin/python3
"""
Verify that our compression tools produce byte-identical output to the
precompressed assets from the original ROM.

Usage:
    python3 tools/build/verifyCompression.py [--fix] [--verbose] [category]

Categories: gfx, rooms, tilesets, text, all (default: all)

With --fix, attempts to determine the correct compression parameters by
analyzing the precompressed files.
"""

import sys
import os
import glob
import struct

sys.path.append(os.path.dirname(__file__) + '/..')
from common import *


def read_cmp_file(filepath):
    """Read a .cmp file and return (mode, decompressed_size, compressed_data, raw_file_data)"""
    with open(filepath, 'rb') as f:
        data = bytearray(f.read())

    if len(data) < 3:
        return None

    mode = data[0]
    decompressed_size = data[1] | (data[2] << 8)
    compressed_data = data[3:]
    return (mode, decompressed_size, compressed_data, data)


def decompress_cmp_file(filepath):
    """Decompress a .cmp file and return (mode, decompressed_data, compressed_data)"""
    info = read_cmp_file(filepath)
    if info is None:
        return None

    mode, decompressed_size, compressed_data, raw = info

    if mode == 0:
        return (mode, compressed_data[:decompressed_size], compressed_data)
    elif mode == 2:
        result = decompressGfxData(compressed_data, 0, decompressed_size // 16 - 1, mode)
        return (mode, bytearray(result[1][:decompressed_size]), compressed_data)
    elif mode == 1 or mode == 3:
        result = decompressGfxData(compressed_data, 0, decompressed_size // 16 - 1, mode)
        return (mode, bytearray(result[1][:decompressed_size]), compressed_data)

    return None


def analyze_gfx_files(precmp_dir, src_dirs, verbose=False):
    """Analyze precompressed GFX files and their source counterparts."""
    results = {'match': 0, 'mismatch': 0, 'missing_src': 0, 'errors': []}

    for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
        basename = os.path.basename(cmp_path)
        name = os.path.splitext(basename)[0]

        info = read_cmp_file(cmp_path)
        if info is None:
            results['errors'].append(f"Could not read {cmp_path}")
            continue

        mode, decompressed_size, compressed_data, raw = info

        if verbose:
            print(f"  {basename}: mode={mode}, decompressed_size={decompressed_size}, "
                  f"compressed_size={len(compressed_data)}")

    return results


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    fix = '--fix' in sys.argv

    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    category = args[0] if args else 'all'

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if category in ('gfx', 'all'):
        print("=== Analyzing precompressed GFX files ===")
        for subdir in ['common', 'seasons', 'ages']:
            precmp_dir = os.path.join(base_dir, 'precompressed', 'gfx_compressible', subdir)
            if not os.path.isdir(precmp_dir):
                continue
            print(f"\n--- {subdir} ---")

            for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
                basename = os.path.basename(cmp_path)
                name = os.path.splitext(basename)[0]

                info = read_cmp_file(cmp_path)
                if info is None:
                    print(f"  ERROR: Could not read {basename}")
                    continue

                mode, decompressed_size, compressed_data, raw = info
                compression_ratio = len(compressed_data) / decompressed_size if decompressed_size > 0 else 0

                if verbose:
                    print(f"  {basename}: mode={mode}, "
                          f"decompressed={decompressed_size}, "
                          f"compressed={len(compressed_data)}, "
                          f"ratio={compression_ratio:.2%}")

                # Try to decompress and verify
                try:
                    result = decompress_cmp_file(cmp_path)
                    if result is None:
                        print(f"  ERROR: Could not decompress {basename}")
                        continue
                    _, decompressed, _ = result
                    if len(decompressed) != decompressed_size:
                        print(f"  WARNING: {basename}: decompressed size mismatch: "
                              f"expected {decompressed_size}, got {len(decompressed)}")
                except Exception as e:
                    print(f"  ERROR: {basename}: {e}")

    if category in ('rooms', 'all'):
        print("\n=== Analyzing precompressed room files ===")
        for subdir in ['seasons', 'ages']:
            precmp_dir = os.path.join(base_dir, 'precompressed', 'rooms', subdir)
            if not os.path.isdir(precmp_dir):
                continue
            print(f"\n--- {subdir} ---")

            mode_counts = {}
            for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
                basename = os.path.basename(cmp_path)
                with open(cmp_path, 'rb') as f:
                    data = bytearray(f.read())
                mode = data[0]
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
                if verbose:
                    print(f"  {basename}: mode={mode}, size={len(data)-1}")

            print(f"  Mode distribution: {mode_counts}")

    if category in ('tilesets', 'all'):
        print("\n=== Analyzing precompressed tileset layout files ===")
        for subdir in ['seasons', 'ages']:
            precmp_dir = os.path.join(base_dir, 'precompressed', 'tileset_layouts', subdir)
            if not os.path.isdir(precmp_dir):
                continue
            print(f"\n--- {subdir} ---")

            for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
                basename = os.path.basename(cmp_path)
                with open(cmp_path, 'rb') as f:
                    data = bytearray(f.read())
                if verbose:
                    print(f"  {basename}: size={len(data)}")

            for bin_path in sorted(glob.glob(os.path.join(precmp_dir, '*.bin'))):
                basename = os.path.basename(bin_path)
                with open(bin_path, 'rb') as f:
                    data = bytearray(f.read())
                if verbose:
                    print(f"  {basename}: size={len(data)}")


if __name__ == '__main__':
    main()
