#!/usr/bin/python3

import sys

"""
Takes a binary MARC21 file (containing one or more records) as input and attempts to fix its index.
If the indexes are okay, the file is returned without modification.

May not work on all corrupt indexes. Tends to do well if there is a consistent off-by-one in the data.

"""

DEBUG = False


def step_through_and_fix(index, data):
    """Check the index represents the data, and fix if not."""
    separator = 0x1e
    calculated_offset = 0
    for i,tag in enumerate(index):
        # Set current offset to calculated offset.
        tag[2] = ('%05d' % calculated_offset).encode('utf-8')

        assert data[calculated_offset] == separator

        # If offset + len does not end on a separator, incr. len by one until it is found
        while data[calculated_offset + int(tag[1])] != separator:
            tag[1] = ('%04d' % (int(tag[1]) + 1)).encode('utf-8')

        calculated_offset += int(tag[1])
    return index


def recreate_index(index):
    """Takes as input an Array of [[tag, tag_len, offset], ... ]
       returns binary index."""
    output = b''
    for tag in index:
        output += b''.join(tag)
    return output


def fix_index(f):
    record_start = f.tell()
    leader = f.read(24)
    if not leader:  # EOF
        return
    length = int(leader[:5])

    field_len     = leader[20]
    start_pos_len = leader[21]

    index = []
    while True:
        tag = f.read(3)
        if tag[0] == 0x1e:
            break
        tag_len = f.read(4)
        offset  = f.read(5)
        index.append([tag, tag_len, offset])

    f.seek(-3, 1)  # back to end of index, at the 0x1E byte
    base_addr = f.tell() - record_start + 1
    leader = leader[:14] + str(base_addr).encode('utf-8') + leader[17:]
    data = f.read(length - base_addr + 1)  # read rest of record (data section)
    if DEBUG:
        print("ORIGINAL INDEX: %s" % index)

    fixed = step_through_and_fix(index, data)
    return leader + recreate_index(fixed) + data


if __name__ == '__main__':

    filename = sys.argv[1]  # binary MARC filename to read

    with open(filename, 'rb') as f:
        f.seek(0)
        while True:
            fixed_marc = fix_index(f)
            if fixed_marc:
                sys.stdout.buffer.write(fixed_marc)
            else:
                break
