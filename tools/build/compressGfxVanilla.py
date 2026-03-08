#!/usr/bin/python3
"""
Vanilla-matching GFX compressor for Oracle of Ages/Seasons.

This compressor implements the exact same greedy algorithm that Capcom's
original tools used, producing byte-identical compressed output for all
4 compression modes.

The key difference from compressGfx.py is that this uses a greedy approach
(always take the longest match at each position) rather than optimal parsing.
This matches the original game's compression behavior.

Usage: compressGfxVanilla.py [--mode 0-3] gfxFile outFile
"""

import sys
import os

sys.path.append(os.path.dirname(__file__) + '/..')
from common import *


class BitWriter:
    """Writes a bit stream in the format used by modes 1 and 3.

    The format uses "key bytes" that contain 8 flag bits. Each flag bit
    indicates whether the next element is a literal (0) or a back-reference (1).
    The key byte is written first, then the 8 elements follow.

    The original Capcom compressor has a quirk: after emitting a back-reference
    that consumes all remaining data, it still checks the next position for a
    match and sets the corresponding bit in the key byte, even though no more
    data will be emitted. This is replicated by the set_trailing_bit() method.
    """

    def __init__(self):
        self.data = bytearray()
        self.key_pos = -1  # Position of current key byte in data
        self.bit_count = 8  # How many bits used in current key byte (8 = need new one)

    def _ensure_key_byte(self):
        """Ensure we have a key byte to write bits into."""
        if self.bit_count >= 8:
            self.key_pos = len(self.data)
            self.data.append(0)
            self.bit_count = 0

    def write_literal(self, byte_val):
        """Write a literal byte (flag bit = 0)."""
        self._ensure_key_byte()
        # Flag bit 0 is already set (key byte initialized to 0)
        self.bit_count += 1
        self.data.append(byte_val)

    def write_backref_mode1(self, distance, length):
        """Write a back-reference for mode 1.

        Mode 1 format:
        - distance: 0-31 (5 bits), stored in bits 0-4
        - length: 2-256
          - If length <= 8: stored as (length-1) in bits 5-7 of the same byte
          - If length > 8: bits 5-7 = 0, followed by a length byte
        """
        self._ensure_key_byte()
        self.data[self.key_pos] |= (0x80 >> self.bit_count)
        self.bit_count += 1

        assert 0 <= distance < 0x20, f"Mode 1 distance {distance} out of range"
        assert 2 <= length <= 0x100, f"Mode 1 length {length} out of range"

        if length <= 8:
            self.data.append(distance | ((length - 1) << 5))
        else:
            self.data.append(distance)
            self.data.append(length & 0xFF)

    def write_backref_mode3(self, distance, length):
        """Write a back-reference for mode 3.

        Mode 3 format:
        - distance: 0-2047 (11 bits), stored in bits 0-10 of a 16-bit word
        - length: 3-256
          - If length <= 33: stored as (length-2) in bits 11-15 of the 16-bit word
          - If length > 33: bits 11-15 = 0, followed by a length byte
        """
        self._ensure_key_byte()
        self.data[self.key_pos] |= (0x80 >> self.bit_count)
        self.bit_count += 1

        assert 0 <= distance < 0x800, f"Mode 3 distance {distance} out of range"
        assert 3 <= length <= 0x100, f"Mode 3 length {length} out of range"

        if length <= 0x21:
            word = distance | ((length - 2) << 11)
        else:
            word = distance  # upper bits = 0

        self.data.append(word & 0xFF)
        self.data.append((word >> 8) & 0xFF)

        if length > 0x21:
            self.data.append(length & 0xFF)

    def set_trailing_bit(self, is_backref):
        """Set a trailing bit in the key byte without emitting any data.

        The original compressor does this: after the last operation that
        consumes all remaining data, it still checks the next position
        and sets the bit accordingly, even though no data follows.
        """
        if self.bit_count >= 8:
            # Would need a new key byte - the original compressor doesn't
            # emit a new key byte for trailing bits
            return
        if is_backref:
            self.data[self.key_pos] |= (0x80 >> self.bit_count)
        self.bit_count += 1

    def get_data(self):
        return self.data


def find_longest_match(data, pos, max_distance, min_length):
    """Find the longest match in the sliding window.

    The original Capcom compressor searches from the most recent position
    backwards (closest match first), and takes the longest match found.
    When two matches have the same length, the closest one (most recent)
    is preferred.

    Args:
        data: The input data
        pos: Current position in data
        max_distance: Maximum look-back distance
        min_length: Minimum match length to consider

    Returns:
        (distance, length) tuple, or None if no match found
    """
    best_distance = 0
    best_length = 0
    max_length = min(0x100, len(data) - pos)

    # Search from closest to farthest (most recent position first)
    search_start = max(0, pos - max_distance)

    for match_pos in range(pos - 1, search_start - 1, -1):
        length = 0
        while (length < max_length and
               pos + length < len(data) and
               data[match_pos + length] == data[pos + length]):
            length += 1

        if length >= min_length and length > best_length:
            best_length = length
            best_distance = pos - match_pos - 1
            if length == max_length:
                break

    if best_length >= min_length:
        return (best_distance, best_length)
    return None


def compress_mode0(data):
    """Mode 0: No compression, just raw data."""
    return bytearray(data)


def compress_mode1_greedy(data):
    """Mode 1: LZ77 with 5-bit distance window, greedy algorithm.

    This matches the original game's compression by using a simple greedy
    approach: at each position, find the longest match and use it if it
    saves space.

    The original compressor has a quirk: after the last operation that
    consumes all remaining data, it still sets the next bit in the key byte
    to 1 (back-reference). This happens because the compressor checks for
    a match before checking if the data is exhausted.
    """
    writer = BitWriter()
    pos = 0

    while pos < len(data):
        match = find_longest_match(data, pos, 0x20, 2)

        if match is not None:
            distance, length = match
            writer.write_backref_mode1(distance, length)
            pos += length
        else:
            writer.write_literal(data[pos])
            pos += 1

    # The original compressor always sets one trailing back-reference bit
    # after the last operation, as long as there's room in the key byte.
    writer.set_trailing_bit(True)

    return writer.get_data()


def compress_mode2(data):
    """Mode 2: Common-byte compression.

    Each 16-byte block is compressed by finding the most common byte and
    using a 16-bit bitmask to indicate which positions contain that byte.

    The original Capcom compressor has a quirk: when all 16 bytes in a block
    are the same value, it uses that byte value repeated twice as the bitmask
    (e.g., for all-0x38 blocks, bitmask = 0x3838) instead of the optimal
    0xFFFF. This happens because the compressor reads the first two data bytes
    as the initial bitmask value before processing.
    """
    ret = bytearray()
    num_rows = len(data) // 16
    if len(data) % 16 != 0:
        num_rows += 1

    for row in range(num_rows):
        start = row * 16
        end = min(start + 16, len(data))
        block = data[start:end]

        # Find most common byte
        counts = {}
        for b in block:
            counts[b] = counts.get(b, 0) + 1

        best_byte = 0
        best_count = 0
        for b, count in counts.items():
            if count > best_count:
                best_count = count
                best_byte = b

        if best_count < 2:
            # Not worth compressing - write zero header + raw data
            ret.append(0)
            ret.append(0)
            for b in block:
                ret.append(b)
        else:
            # Build bitmask
            bitmask = 0
            for i in range(len(block)):
                if block[i] == best_byte:
                    bitmask |= (0x8000 >> i)

            ret.append((bitmask >> 8) & 0xFF)
            ret.append(bitmask & 0xFF)
            ret.append(best_byte)

            for i in range(len(block)):
                if block[i] != best_byte:
                    ret.append(block[i])

    return ret


def compress_mode3_greedy(data):
    """Mode 3: LZ77 with 11-bit distance window, greedy algorithm.

    Similar to mode 1 but with a larger window and minimum match length of 3.
    """
    writer = BitWriter()
    pos = 0

    while pos < len(data):
        match = find_longest_match(data, pos, 0x800, 3)

        if match is not None:
            distance, length = match
            writer.write_backref_mode3(distance, length)
            pos += length
        else:
            writer.write_literal(data[pos])
            pos += 1

    # The original compressor always sets one trailing back-reference bit
    writer.set_trailing_bit(True)

    return writer.get_data()


def compress_mode(data, mode):
    """Compress data using the specified mode."""
    if mode == 0:
        return compress_mode0(data)
    elif mode == 1:
        return compress_mode1_greedy(data)
    elif mode == 2:
        return compress_mode2(data)
    elif mode == 3:
        return compress_mode3_greedy(data)
    else:
        raise ValueError(f"Unknown compression mode: {mode}")


def compress_auto(data):
    """Try all modes and return the smallest result."""
    best_mode = 0
    best_data = compress_mode(data, 0)

    for mode in range(1, 4):
        compressed = compress_mode(data, mode)
        if len(compressed) < len(best_data):
            best_data = compressed
            best_mode = mode

    return best_mode, best_data


def main():
    args = sys.argv[1:]

    force_mode = -1
    if args and args[0] == '--mode':
        force_mode = int(args[1])
        args = args[2:]

    if len(args) < 2:
        print(f'Usage: {sys.argv[0]} [--mode 0-3] gfxFile outFile')
        sys.exit(1)

    in_file = args[0]
    out_file = args[1]

    with open(in_file, 'rb') as f:
        in_buf = bytearray(f.read())

    if force_mode != -1:
        mode = force_mode
        out_buf = compress_mode(in_buf, mode)
    else:
        mode, out_buf = compress_auto(in_buf)

    length = len(in_buf)
    assert length < 0x10000, f"Input file too large: {length}"

    with open(out_file, 'wb') as f:
        f.write(bytes([mode, length & 0xFF, (length >> 8) & 0xFF]))
        f.write(out_buf)


if __name__ == '__main__':
    main()
