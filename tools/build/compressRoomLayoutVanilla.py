#!/usr/bin/python3
"""
Vanilla-matching room layout compressor for Oracle of Ages/Seasons.

This implements the greedy dictionary compression algorithm used by the
original Capcom tools, producing byte-identical output for large room layouts.

Room layouts use 4 compression modes:
  Mode 0: Raw (uncompressed)
  Mode 1: Common-byte with 1-byte key (8 bytes per group)
  Mode 2: Common-byte with 2-byte key (16 bytes per group)
  Mode 3: Dictionary-based compression (for large rooms)

For small rooms, modes 0-2 are used (handled by compressRoomLayout.py).
For large rooms, mode 3 (dictionary) is used.

The dictionary compression format:
  - Key byte with 8 flag bits (LSB first)
  - Flag bit 0 = literal byte
  - Flag bit 1 = dictionary reference (16-bit: 12-bit offset | 4-bit length-3)
  - Match length range: 3-18 bytes
"""

import sys
import os

sys.path.append(os.path.dirname(__file__) + '/..')
from common import *


class DictBitWriter:
    """Writes a bit stream for dictionary compression.

    Unlike GFX compression which uses MSB-first bit order, dictionary
    compression uses LSB-first bit order.
    """

    def __init__(self):
        self.data = bytearray()
        self.key_pos = -1
        self.bit_count = 8

    def _ensure_key_byte(self):
        if self.bit_count >= 8:
            self.key_pos = len(self.data)
            self.data.append(0)
            self.bit_count = 0

    def write_literal(self, byte_val):
        self._ensure_key_byte()
        # Flag bit 0 = literal (already 0)
        self.bit_count += 1
        self.data.append(byte_val)

    def write_dict_ref(self, dict_offset, length):
        """Write a dictionary reference.

        Args:
            dict_offset: Offset into the dictionary (0-4095)
            length: Match length (3-18)
        """
        self._ensure_key_byte()
        self.data[self.key_pos] |= (1 << self.bit_count)
        self.bit_count += 1

        assert 0 <= dict_offset < 0x1000
        assert 3 <= length <= 0x12

        word = dict_offset | ((length - 3) << 12)
        self.data.append(word & 0xFF)
        self.data.append((word >> 8) & 0xFF)

    def set_trailing_bit(self, is_ref):
        """Set a trailing bit without emitting data."""
        if self.bit_count >= 8:
            return
        if is_ref:
            self.data[self.key_pos] |= (1 << self.bit_count)
        self.bit_count += 1

    def get_data(self):
        return self.data


def build_dictionary_mapping(dictionary, max_len=0x12):
    """Build a mapping from byte sequences to dictionary offsets."""
    mapping = {}
    dict_len = min(len(dictionary), 0x1000)
    for i in range(dict_len - 2):
        for j in range(i + 3, min(i + max_len + 1, dict_len + 1)):
            key = bytes(dictionary[i:j])
            if key not in mapping:
                mapping[key] = i
    return mapping


def find_longest_dict_match(data, pos, dictionary_mapping, dictionary):
    """Find the longest match in the dictionary using greedy search.

    The original compressor finds the longest dictionary entry that starts
    with the bytes at the current position. It does NOT limit the match
    length to the remaining data - it can encode matches that extend past
    the end of the input. The decompressor handles this by stopping when
    the output buffer is full.

    Args:
        data: Input data
        pos: Current position
        dictionary_mapping: Mapping from byte sequences to dictionary offsets
        dictionary: The raw dictionary data

    Returns:
        (dict_offset, length) or None
    """
    remaining = len(data) - pos
    if remaining < 3:
        # Need at least 3 bytes to match, but we might not have them
        # Check if we can still find a match with what we have
        if remaining <= 0:
            return None

    # First, find the longest exact match within the remaining data
    max_exact = min(0x12, remaining)
    best_offset = None
    best_length = 0

    for length in range(max_exact, 2, -1):
        key = bytes(data[pos:pos + length])
        offset = dictionary_mapping.get(key)
        if offset is not None:
            best_offset = offset
            best_length = length
            break

    if best_offset is None:
        return None

    # The original compressor can encode matches longer than the remaining data.
    # It finds the longest dictionary entry that starts with the matched bytes,
    # even if the match extends past the end of the input data.
    # The decompressor stops when the output buffer is full.
    if best_length == remaining and best_length < 0x12:
        dict_offset = best_offset
        # Check how far the same byte pattern continues in the dictionary
        # The matched data is data[pos:pos+best_length]
        # We need to find how far dictionary[dict_offset:] continues to match
        # Since we're past the end of data, we check if the dictionary
        # continues with the same pattern (the original compressor just
        # looks up the longest dictionary entry starting with the matched prefix)
        max_dict_len = min(0x12, len(dictionary) - dict_offset)
        # Find the longest entry in the dictionary mapping that starts at this offset
        for ext_len in range(max_dict_len, best_length, -1):
            ext_key = bytes(dictionary[dict_offset:dict_offset + ext_len])
            if ext_key in dictionary_mapping and dictionary_mapping[ext_key] == dict_offset:
                best_length = ext_len
                break

    return (best_offset, best_length)


def compress_dictionary_greedy(data, dictionary_mapping, dictionary):
    """Compress data using dictionary-based greedy algorithm."""
    writer = DictBitWriter()
    pos = 0

    while pos < len(data):
        match = find_longest_dict_match(data, pos, dictionary_mapping, dictionary)

        if match is not None:
            offset, length = match
            writer.write_dict_ref(offset, length)
            pos += min(length, len(data) - pos)  # Don't advance past end
        else:
            writer.write_literal(data[pos])
            pos += 1

    return writer.get_data()


def main():
    if len(sys.argv) < 5:
        print('Usage: %s roomLayout.bin output.cmp -d dictionary.bin' % sys.argv[0])
        sys.exit(1)

    in_file = sys.argv[1]
    out_file = sys.argv[2]

    # Parse arguments
    dictionary_file = None
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '-d' and i + 1 < len(sys.argv):
            dictionary_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    with open(in_file, 'rb') as f:
        layout_data = bytearray(f.read())

    if dictionary_file is None:
        print("Error: dictionary file required for vanilla compression")
        sys.exit(1)

    with open(dictionary_file, 'rb') as f:
        dictionary = bytearray(f.read())

    dictionary_mapping = build_dictionary_mapping(dictionary)
    compressed = compress_dictionary_greedy(layout_data, dictionary_mapping, dictionary)

    if len(compressed) > 0xb0:
        print('WARNING: compressed size of "%s" is greater than 0xb0' % out_file)

    with open(out_file, 'wb') as f:
        f.write(bytes([3]))  # Mode 3 = dictionary compression
        f.write(compressed)


if __name__ == '__main__':
    main()
