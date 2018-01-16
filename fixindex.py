#!/usr/bin/python

import sys

"""Takes a single raw MARC record as input and attempts to fix its index."""

DEBUG = False

def recreate_index(index):
    """ Array of [tag, tag_len, offset]"""
    output =""
    for t in index:
        output += t[0] + t[1] + t[2]
    return output

def add_one_to_len(index):
    """ Adjust index"""
    for i,t in enumerate(index):
        t[1] = "%04d" % (int(t[1]) + 1)
        t[2] = "%05d" % (int(t[2]) + i)

    return index

if __name__ == '__main__':

    filename = sys.argv[1] # binary MARC to read

    with open(filename, 'rb') as f:
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
        data = f.read() # read rest of file
        if DEBUG:
            print "INDEX: %s" % index

        fixed = add_one_to_len(index)
        sys.stdout.write(leader+recreate_index(fixed)+data)
