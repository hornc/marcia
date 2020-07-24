#!/usr/bin/env python3

"""
Takes a binary MARC file containg bibliographic records (possibly mixed with holdings records)
and adds a custom / local filed 976$a field for local barcode for importing.
"""

import sys
from pymarc import Field, MARCReader, MARCWriter

fnbiblio = sys.argv[1]
fnbarcode = sys.argv[2]

# Load .tsv of 001 ids to local barcodes
with open(fnbarcode, 'r') as bc:
    barcodes = {}
    for line in bc.readlines():
        id_, barcode = (v.strip() for v in line.strip().split('\t'))
        if id_ in barcodes:
            barcodes[id_].append(barcode)
        else:
            barcodes[id_] = [barcode]

m = 150  # max records to process (for DEBUG)
DEBUG = False
writer = None

# Load bibliographic MARC records to add barcodes
# Output written to file out.mrc
with open(fnbiblio, 'rb') as marcdata:
    writer = MARCWriter(open('out.mrc','wb'))
    records = MARCReader(marcdata, to_unicode=True)
    for i, record in enumerate(records):
        if record is None:
            print('None record')
            #continue
        if record['876']:
            #print('HOLDING found!')
            continue
        else:
            print('%s Biblio found' % i)
            enc = record.leader[9]
            if enc != ' ':
                 print('%s non MARC8 record found!' % i)
            
            id_ = record['001'].value().strip()
            barcode = barcodes.get(id_)
            if barcode:
                for b in barcode:
                    record.add_field(
                        Field(
                            tag = '976',
                            indicators = [' ', ' '],
                            subfields = [
                                'a', b
                            ]
                        )
                    )
            #print(record)
            record.leader = record.leader[:9] + 'a' + record.leader[10:]
            #record.force_utf8 = True
            writer.write(record)

            if DEBUG and i > m:
                break

if writer:
    print('Closing file')
    writer.close()
             
