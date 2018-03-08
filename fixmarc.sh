#!/bin/bash

# Script to fix index and unicode issues with IA MARC records.

# Requires:
#   parallel
#   ia-client (>= 1.7.7)
#   yaz-marcdump (>= 5.23.1)

# Assumes it is being run in a directory containing MARC XML records named <ocaid>_archive_marc.xml
# on which the checkmarc.sh script has been run to generate itemlists:
#   bad_unicode.txt 
#   bad_index.txt

# Output:
#   Backs up MARC XML and binary MARC to ./backup
#   regenerates good source MARC XML (<ocaid>_marc.xml)
#   and good indexed binary MARC (<ocaid>_meta.mrc)
# NOTE: These are fixed _SOURCE_ MARC records and need to be uploaded
# back to archive.org to enable correct archive.org MARCs generated
# by fetchmarc.php.

echo Fetching source binary MARC for Unicode and index problem items from archive.org
parallel --joblog get_raw.log 'ia download {} {}_meta.mrc --no-directories -C' < <(cat bad_unicode.txt  bad_index.txt)

if [ -d "backup" ]; then
  echo ./backup directory already found, assuming backups alread made.
else
  echo Backing up original MARC XML to ./backup/
  mkdir backup
  cp bad_index.txt bad_index_orig.txt
  cp bad_unicode.txt bad_unicode_orig.txt
  while read f;do mv ${f}_archive_marc.xml backup; done < <(cat bad_unicode.txt  bad_index.txt)
fi

# Fix MARC indexes using fixmarc.py
while read f;do fixindex.py ${f}_meta.mrc > ${f}_fixed.mrc;yaz-marcdump -imarc -omarcxml ${f}_fixed.mrc > ${f}_marc.xml;done < bad_index.txt

# Copy original .mrc to backup/ and replace with fixed
while read f;do mv ${f}_meta.mrc backup/.;mv ${f}_fixed.mrc ${f}_meta.mrc; done < bad_index.txt

# Fix unicode:
while read f;do yaz-marcdump -imarc -omarcxml -fmarc8 -tutf8 ${f}_meta.mrc > ${f}_marc.xml; done < bad_unicode.txt

echo Done fixing records from bad_unicode.txt and bad_index.txt itemlists.
echo " "
echo NOTE: These are fixed _SOURCE_ MARC records and need to be uploaded
echo back to archive.org to enable correct archive.org MARCs generated
echo by fetchmarc.php.
