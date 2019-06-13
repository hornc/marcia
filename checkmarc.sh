#!/bin/bash

# Quick script to check for issues with IA MARC XML

count() { echo $#; }
id_list() {
  # Split MARC filelist on <space> and strip extension to give bare OCAID.
  echo $@ | tr " " "\n" | sed -n 's/\(_archive\)\?_marc.xml//p'
 }

red="\e[31m"
yellow="\e[33m"
clr="\e[0m"

# Check Ids without MARC XML if <itemlist> provided
if [ $1 ] && [ -e $1 ]; then
  missing_marc=$(comm -23 <(sort $1) <(ls *_marc.xml | sed -n 's/\(_archive\)\?_marc.xml//p' | sort))
  if [ $(count $missing_marc) -ne "0" ]; then
    echo -e "\n$red!!! $(count $missing_marc) items did not have MARC XML.$clr"
    echo "     Writing list to 'no_marc.txt'"
    echo $missing_marc | tr " " "\n" > no_marc.txt
  fi
elif [ $1 ]; then
  echo -e "\n$red!!! Itemlist '$1' not found!$clr"
fi

# Unicode conversion errors:

# regex to catch common signs of MARC8 conversion issues
bad_unicode="Ã[0-9]{4}" # > ©YYYY
bad_unicode+="|â[AeE]"  # > acute + vowel likely to be an encoding error
bad_unicode+="|á[AE]"   # > grave + vowel likely to be an encoding error
bad_unicode+="|ðc"      # > ç
bad_unicode+="|¶"       # > œ
bad_unicode+="|\(B[^a-z)]{,2}<" # unconverted non-Latin MARC8 charsets in 880 fields

# add checks for utf8 decoded as marc8 too
bad_source="℗♭||£̀Đ|Ì§|[¿♯]±|©[♭·ʹþ¡ĐƯðơ]"
# and utf8 decoded as Win1225
bad_source+="|Ã[«¦¢§³¡¼µ±¤ª£¨]"
bad_source+="|[ÅÄ]«|Ì§"     # u/i macron | combining cedilla

egrep --color $bad_unicode *_marc.xml

if [ $? -eq 0 ]; then
  bad_marc8_list=$(egrep -l $bad_unicode *_marc.xml)
  echo -e "\n$red!!! $(count $bad_marc8_list) MARCs have potential MARC8 -> Unicode issues:$clr"
  echo "     Writing list to 'bad_unicode.txt'"
  id_list $bad_marc8_list > bad_unicode.txt

  echo -e "\n${yellow}Try re-converting from raw MARC with Yaz using '-f marc8 -t utf8' options.$clr"
fi

# Bad MARC indexes in source records:

bad_index=$(egrep -l "(at end of field length=40|No separator at)" *_marc.xml)

if [ $(count $bad_index) -ne 0 ]; then
  echo -e "\n$red!!! $(count $bad_index) MARCs had a corrupt source index:$clr"
  echo "     Writing list to 'bad_index.txt'"
  id_list $bad_index > bad_index.txt
fi

# Other issues, to handle later:
bad_source_list=$(egrep -l $bad_source *_archive_marc.xml)
if [ $? -eq 0 ]; then
  id_list $bad_source_list > bad_source.txt
  echo -e "\n$red!!! $(count $bad_source_list) MARC have likely corrupt binary MARC!$clr"
fi

empty_tag=$(grep -l 'tag=""' *_archive_marc.xml)
if [ $? -eq 0 ]; then
  id_list $empty_tag > bad_tag.txt
fi

# Other XML comments:

other_xml_comments=$(egrep -l '\-\->' /dev/null $(grep -L "at end of field length=40" *_marc.xml))

if [ $(count $other_xml_comments) -ne 0 ]; then
  echo -e "\n$yellow!!! $(count $other_xml_comments) MARCs contain other XML comments, which indicates conversion problems:$clr"
  echo "     Writing list to 'xml_comments.txt'"
  id_list $other_xml_comments > xml_comments.txt
fi

# Multiple volumes in one MARC record
sed 's/_archive_marc.xml//' < <(egrep -l '([0-9X]{10,13} |"[qc]">.*)\(v(ol)?\. [0-9]' *.xml) > multi_volumes.txt

# Multiple 008 fields
grep -c 'controlfield tag="008"' *.xml | egrep -v ':[01]$' | sed 's/_archive_marc.*$//' > multi_008.txt

# Move records to exlude to their own directories
if true; then
	mkdir bad_records
	mkdir multi_volumes
	for f in $(cat bad_index.txt bad_source.txt bad_unicode.txt multi_008.txt | sort | uniq); do mv ${f}_archive_marc.xml bad_records/. ;done
	for f in $(cat multi_volumes.txt); do mv ${f}_archive_marc.xml multi_volumes/. ;done
fi

