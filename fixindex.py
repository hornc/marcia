#!/usr/bin/python

import sys

"""Takes a single raw MARC record as input and attempts to fix its index."""

DEBUG = False

def add_one_to_len(index):
    """Adjust index Array by adding one.
       Overly simple off-by-one fix, but works in most cases."""
    for i,tag in enumerate(index):
        tag[1] = "%04d" % (int(tag[1]) + 1)
        tag[2] = "%05d" % (int(tag[2]) + i)
    return index

def step_through_and_fix(index, data):
    """Check the index represents the data, and fix if not."""
    separator = '\x1e'
    calculated_offset = 0
    for i,tag in enumerate(index):
        # Correct fixed len field 008
        if tag[0] == '008' and int(tag[1]) != 41:
            tag[1] = '0041'

        # If current offset not correct, set it to calculated offset.
        if data[int(tag[2])] != separator:
            tag[2] = "%05d" % calculated_offset

        assert data[calculated_offset] == separator
        assert int(tag[2]) == calculated_offset

        # If offset + len does not end on a separator, incr. len by one until it is found
        while data[calculated_offset + int(tag[1])] != separator:
            tag[1] = "%04d" % (int(tag[1]) + 1)

        if DEBUG:
            print "Tag: %s" % tag[0]
            print "Len: %s" % tag[1]
            print "Offset: %i" % int(tag[2])
            print "Offset + len: %i" % (int(tag[1]) + int(tag[2]))
            print data[int(tag[2])]
            print "%s == %i" % (tag[2], calculated_offset)

        calculated_offset += int(tag[1])
    return index

def recreate_index(index):
    """Takes as input an Array of [[tag, tag_len, offset], ... ]
       returns binary index."""
    output = ""
    for t in index:
        output += t[0] + t[1] + t[2]
    return output

def fix_index(f):
    f.seek(0)
    leader = f.read(24)
    length = leader[:5]

    field_len     = leader[20]
    start_pos_len = leader[21]

    if DEBUG:
        print leader
        print length
        print field_len
        print start_pos_len

    index = []
    while True:
        tag = f.read(3)
        if tag[0] == chr(0x1e):
            if DEBUG:
                print "END OF INDEX."
            break
        tag_len = f.read(4)
        offset  = f.read(5)
        index.append([tag, tag_len, offset])

        if DEBUG: 
            print "%s: len %s, offset %s" % (tag, tag_len, offset)
    f.seek(-3, 1) # back to end of index, at the 0x1E byte
    data = f.read() # read rest of file (data section)
    if DEBUG:
        print "ORIGINAL INDEX: %s" % index

    fixed = step_through_and_fix(index, data)
    return leader + recreate_index(fixed) + data

if __name__ == '__main__':

    filename = sys.argv[1] # binary MARC filename to read

    with open(filename, 'rb') as f:
        fixed_marc = fix_index(f)
        sys.stdout.write(fixed_marc)