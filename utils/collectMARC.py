#!/usr/bin/env python
"""
collectMARC
For an input list of archive.org identifiers, collect all IA specific (electronic resource) MARCs
into a single MARC XML collection.
"""

import io
import sys
from internetarchive import download
from pymarc import map_xml, XMLWriter


class Collection:
    def __init__(self, outfile='output.xml'):
        self.writer = XMLWriter(open(outfile, 'wb'))

    def collect(self, record):
        self.writer.write(record)

    def close(self):
        self.writer.close()


if __name__ == '__main__':
    fname = sys.argv[1]
    outfile = ''.join(fname.split('.')[:-1]) + '.xml'
    c = Collection(outfile)
    print(f'Downloading MARC XML from items listed in {fname}, and writing to a collection: {outfile}...')
    with open(fname, 'r') as f:
        for id_ in f.readlines():
            id_ = id_.strip()
            response_list = download(id_, id_ + '_archive_marc.xml', on_the_fly=True, return_responses=True)
            xml = io.BytesIO(response_list[0].content)
            map_xml(c.collect, xml)
    c.close()  # Important; need to close the Collection for valid XML!
