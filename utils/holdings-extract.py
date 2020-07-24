#!/usr/bin/env python3
"""
Extract holdings local barcode id from binary holdings MARC 876$p to a .tsv
control_number, library_barcode
"""

import sys
from pymarc import MARCReader

fname = sys.argv[1]

with open(fname, 'rb') as marcdata:
    records = MARCReader(marcdata, to_unicode=True, permissive=True) 
    for i, record in enumerate(records):
        if record['876']:
            #print('HOLDING found!')
            #Aprint(record)
            bibid = record['004'].value()
            for barcode in record['876']:
                #print(barcode)
                if barcode[0] == 'p':
                    print('\t'.join([str(a) for a in [bibid, barcode[1]]]))
