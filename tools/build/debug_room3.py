#!/usr/bin/python3
import sys, os
sys.path.append(os.path.dirname(__file__) + '/..')
sys.path.append(os.path.dirname(__file__))
from compressRoomLayoutVanilla import build_dictionary_mapping, find_longest_dict_match

d = bytearray(open('rooms/seasons/dictionary5.bin', 'rb').read())
s = bytearray(open('rooms/seasons/large/room0500.bin', 'rb').read())

m = build_dictionary_mapping(d)

# Find what match the compressor finds at the last position
# The source is 176 bytes. The last match should cover the end.
# Let's trace through the compression
pos = 0
ops = []
while pos < len(s):
    match = find_longest_dict_match(s, pos, m)
    if match:
        offset, length = match
        ops.append(('ref', offset, length, pos))
        pos += length
    else:
        ops.append(('lit', s[pos], pos))
        pos += 1

print("Total ops:", len(ops))
for op in ops[-5:]:
    print("  ", op)
print("Final pos:", pos)
