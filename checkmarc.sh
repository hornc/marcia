#!/bin/bash

# Quick script to check for issues with IA MARC XML

count() { echo $#; }
id_list() {
  # Split MARC filelist on <space> and strip extension to give bare OCAID.
  echo $@ | tr " " "\n" | sed -n 's/_marc.xml//p'
 }

red="\e[31m"
yellow="\e[33m"
clr="\e[0m"

# Check Ids without MARC XML if <itemlist> provided
if [ $1 ] && [ -e $1 ]; then
  missing_marc=$(comm -23 <(sort $1) <(ls *_marc.xml | sort))
  echo -e "\n$red!!! $(count $missing_marc) items did not have MARC XML.$clr"
  echo "     Writing list to 'no_marc.txt'"
  id_list $missing_marc > no_marc.txt
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

egrep --color $bad_unicode *_marc.xml

if [ $? -eq 0 ]; then
  bad_marc8_list=$(egrep -l $bad_unicode *_marc.xml)
  echo -e "\n$red!!! $(count $bad_marc8_list) MARCs have potential MARC8 -> Unicode issues:$clr"
  echo "     Writing list to 'bad_unicode.txt'"
  id_list $bad_marc8_list > bad_unicode.txt

  echo -e "\n${yellow}Try re-converting from raw MARC with Yaz using '-f marc8 -t utf8' options.$clr"
fi

# Bad MARC indexes in source records:

bad_index=$(egrep -l "at end of field length=40" *_marc.xml)

if [ $(count $bad_index) -ne 0 ]; then
  echo -e "\n$red!!! $(count $bad_index) MARCs had a corrupt source index:$clr"
  echo "     Writing list to 'bad_index.txt'"
  id_list $bad_index > bad_index.txt
fi


# Other XML comments:

other_xml_comments=$(egrep -l '\-\->' /dev/null $(grep -L "at end of field length=40" *_marc.xml))

if [ $(count $other_xml_comments) -ne 0 ]; then
  echo -e "\n$yellow!!! $(count $other_xml_comments) MARCs contain other XML comments, which indicates conversion problems:$clr"
  echo "     Writing list to 'xml_comments.txt'"
  id_list $other_xml_comments > xml_comments.txt
fi

