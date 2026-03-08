#!/usr/bin/python3
"""
Test all precompressed assets by running the non-vanilla compressors and
comparing the output to the precompressed files.

This tests:
1. Large room layouts (dictionary compression)
2. Tileset layout data (collision and mapping compression + generated binary data)
3. Text data
"""
import sys
import os
import glob
import subprocess
import tempfile
import shutil

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(base_dir, 'tools'))
from common import *


def compare_files(file1, file2):
    """Compare two files byte-by-byte. Returns (match, first_diff_pos, size1, size2)."""
    with open(file1, 'rb') as f:
        data1 = f.read()
    with open(file2, 'rb') as f:
        data2 = f.read()

    if data1 == data2:
        return True, -1, len(data1), len(data2)

    min_len = min(len(data1), len(data2))
    for i in range(min_len):
        if data1[i] != data2[i]:
            return False, i, len(data1), len(data2)
    return False, min_len, len(data1), len(data2)


def test_large_rooms(game, verbose=False):
    """Test large room dictionary compression."""
    print("\n--- %s large rooms ---" % game)

    precmp_dir = os.path.join(base_dir, 'precompressed', 'rooms', game)
    if not os.path.isdir(precmp_dir):
        print("  No precompressed rooms found")
        return 0, 0

    passed = 0
    failed = 0

    # Group rooms by their dictionary
    room_groups = {}
    for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, '*.cmp'))):
        basename = os.path.basename(cmp_path)
        room_name = os.path.splitext(basename)[0]

        # Determine which group (04, 05, 06) and dictionary
        room_num = room_name[4:6]  # e.g., "04", "05", "06"
        if room_num not in room_groups:
            room_groups[room_num] = []
        room_groups[room_num].append(cmp_path)

    for group_num, cmp_files in sorted(room_groups.items()):
        dict_path = os.path.join(base_dir, 'rooms', game, 'dictionary%s.bin' % group_num[-1])
        src_dir = os.path.join(base_dir, 'rooms', game, 'large')

        if not os.path.exists(dict_path):
            print("  SKIP: No dictionary for group %s" % group_num)
            continue

        for cmp_path in cmp_files:
            basename = os.path.basename(cmp_path)
            room_name = os.path.splitext(basename)[0]
            src_path = os.path.join(src_dir, room_name + '.bin')

            if not os.path.exists(src_path):
                if verbose:
                    print("  SKIP: No source for %s" % basename)
                continue

            # Compress using the existing tool
            with tempfile.NamedTemporaryFile(suffix='.cmp', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(base_dir, 'tools', 'build', 'compressRoomLayoutVanilla.py'),
                     src_path, tmp_path, '-d', dict_path],
                    capture_output=True, text=True, cwd=base_dir
                )

                if result.returncode != 0:
                    print("  ERROR: %s: %s" % (basename, result.stderr.strip()))
                    failed += 1
                    continue

                match, diff_pos, size1, size2 = compare_files(cmp_path, tmp_path)
                if match:
                    passed += 1
                    if verbose:
                        print("  PASS: %s" % basename)
                else:
                    print("  FAIL: %s (orig=%d, new=%d, first_diff=%d)" % (
                        basename, size1, size2, diff_pos))
                    failed += 1
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    print("  Results: %d passed, %d failed" % (passed, failed))
    return passed, failed


def test_tileset_layouts(game, verbose=False):
    """Test tileset layout compression."""
    print("\n--- %s tileset layouts ---" % game)

    precmp_dir = os.path.join(base_dir, 'precompressed', 'tileset_layouts', game)
    if not os.path.isdir(precmp_dir):
        print("  No precompressed tileset layouts found")
        return 0, 0

    passed = 0
    failed = 0

    # First, test the generated binary files by running parseTilesetLayouts
    with tempfile.TemporaryDirectory() as tmp_dir:
        tl_dir = os.path.join(tmp_dir, 'tileset_layouts')
        os.makedirs(tl_dir)

        result = subprocess.run(
            [sys.executable, os.path.join(base_dir, 'tools', 'build', 'parseTilesetLayouts.py'),
             game, tmp_dir],
            capture_output=True, text=True, cwd=base_dir
        )

        if result.returncode != 0:
            print("  ERROR running parseTilesetLayouts: %s" % result.stderr.strip())
            return 0, 1

        # Compare generated binary files
        for bin_name in ['tileMappingTable.bin', 'tileMappingIndexData.bin',
                         'tileMappingAttributeData.bin', 'mappingsDictionary.bin']:
            precmp_path = os.path.join(precmp_dir, bin_name)
            gen_path = os.path.join(tl_dir, bin_name)

            if not os.path.exists(precmp_path):
                continue

            if not os.path.exists(gen_path):
                print("  FAIL: %s not generated" % bin_name)
                failed += 1
                continue

            match, diff_pos, size1, size2 = compare_files(precmp_path, gen_path)
            if match:
                passed += 1
                if verbose:
                    print("  PASS: %s" % bin_name)
            else:
                print("  FAIL: %s (orig=%d, new=%d, first_diff=%d)" % (
                    bin_name, size1, size2, diff_pos))
                failed += 1

        # Now test collision compression
        coll_dict_path = os.path.join(precmp_dir, 'collisionsDictionary.bin')
        if os.path.exists(coll_dict_path):
            for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, 'tilesetCollisions*.cmp'))):
                basename = os.path.basename(cmp_path)
                src_name = basename.replace('.cmp', '.bin')
                src_path = os.path.join(base_dir, 'tileset_layouts', game, src_name)

                if not os.path.exists(src_path):
                    continue

                with tempfile.NamedTemporaryFile(suffix='.cmp', delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    result = subprocess.run(
                        [sys.executable, os.path.join(base_dir, 'tools', 'build', 'compressTilesetLayoutData.py'),
                         src_path, tmp_path, '0', coll_dict_path],
                        capture_output=True, text=True, cwd=base_dir
                    )

                    if result.returncode != 0:
                        print("  ERROR: %s: %s" % (basename, result.stderr.strip()))
                        failed += 1
                        continue

                    match, diff_pos, size1, size2 = compare_files(cmp_path, tmp_path)
                    if match:
                        passed += 1
                        if verbose:
                            print("  PASS: %s" % basename)
                    else:
                        print("  FAIL: %s (orig=%d, new=%d, first_diff=%d)" % (
                            basename, size1, size2, diff_pos))
                        failed += 1
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        # Test mapping indices compression
        map_dict_path = os.path.join(tl_dir, 'mappingsDictionary.bin')
        if os.path.exists(map_dict_path):
            for cmp_path in sorted(glob.glob(os.path.join(precmp_dir, 'tilesetMappings*Indices.cmp'))):
                basename = os.path.basename(cmp_path)
                src_name = basename.replace('.cmp', '.bin')
                src_path = os.path.join(tl_dir, src_name)

                if not os.path.exists(src_path):
                    continue

                with tempfile.NamedTemporaryFile(suffix='.cmp', delete=False) as tmp:
                    tmp_path = tmp.name

                try:
                    result = subprocess.run(
                        [sys.executable, os.path.join(base_dir, 'tools', 'build', 'compressTilesetLayoutData.py'),
                         src_path, tmp_path, '1', map_dict_path],
                        capture_output=True, text=True, cwd=base_dir
                    )

                    if result.returncode != 0:
                        print("  ERROR: %s: %s" % (basename, result.stderr.strip()))
                        failed += 1
                        continue

                    match, diff_pos, size1, size2 = compare_files(cmp_path, tmp_path)
                    if match:
                        passed += 1
                        if verbose:
                            print("  PASS: %s" % basename)
                    else:
                        print("  FAIL: %s (orig=%d, new=%d, first_diff=%d)" % (
                            basename, size1, size2, diff_pos))
                        failed += 1
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

    print("  Results: %d passed, %d failed" % (passed, failed))
    return passed, failed


def test_text(game, verbose=False):
    """Test text compression."""
    print("\n--- %s text ---" % game)

    precmp_dir = os.path.join(base_dir, 'precompressed', 'text', game)
    text_dir = os.path.join(base_dir, 'text', game)

    if not os.path.isdir(precmp_dir) or not os.path.isdir(text_dir):
        print("  No text source/precompressed data found")
        return 0, 0

    text_yaml = os.path.join(text_dir, 'text.yaml')
    dict_yaml = os.path.join(text_dir, 'dict.yaml')

    if not os.path.exists(text_yaml) or not os.path.exists(dict_yaml):
        print("  Missing text.yaml or dict.yaml")
        return 0, 0

    passed = 0
    failed = 0

    # Determine text insert address
    if game == 'seasons':
        text_insert_address = 0x71c00
    else:
        text_insert_address = 0x74000

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_text_data = os.path.join(tmp_dir, 'textData.s')

        result = subprocess.run(
            [sys.executable, os.path.join(base_dir, 'tools', 'build', 'parseText.py'),
             dict_yaml, text_yaml, tmp_text_data, str(text_insert_address)],
            capture_output=True, text=True, cwd=base_dir
        )

        if result.returncode != 0:
            print("  ERROR running parseText: %s" % result.stderr.strip())
            return 0, 1

        # Compare textData.s
        precmp_text = os.path.join(precmp_dir, 'textData.s')
        if os.path.exists(precmp_text):
            match, diff_pos, size1, size2 = compare_files(precmp_text, tmp_text_data)
            if match:
                passed += 1
                print("  PASS: textData.s")
            else:
                print("  FAIL: textData.s (orig=%d, new=%d, first_diff=%d)" % (
                    size1, size2, diff_pos))
                failed += 1

        # Compare textDefines.s
        tmp_text_defines = os.path.join(tmp_dir, 'textDefines.s')
        precmp_defines = os.path.join(precmp_dir, 'textDefines.s')
        if os.path.exists(precmp_defines) and os.path.exists(tmp_text_defines):
            match, diff_pos, size1, size2 = compare_files(precmp_defines, tmp_text_defines)
            if match:
                passed += 1
                print("  PASS: textDefines.s")
            else:
                print("  FAIL: textDefines.s (orig=%d, new=%d, first_diff=%d)" % (
                    size1, size2, diff_pos))
                failed += 1

    print("  Results: %d passed, %d failed" % (passed, failed))
    return passed, failed


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    total_passed = 0
    total_failed = 0

    for game in ['seasons', 'ages']:
        print("\n=== %s ===" % game.upper())

        p, f = test_large_rooms(game, verbose)
        total_passed += p
        total_failed += f

        p, f = test_tileset_layouts(game, verbose)
        total_passed += p
        total_failed += f

        p, f = test_text(game, verbose)
        total_passed += p
        total_failed += f

    print("\n=== TOTAL: %d passed, %d failed ===" % (total_passed, total_failed))
    if total_failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
