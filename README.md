# marcia
A collection of scripts for MARC conversion and checking for the [Internet Archive](https://github.com/internetarchive)
  
* **checkmarc.sh**
  Bash script to check for obvious issues with MARC XML:
  
  **USAGE:** `checkmarc.sh [<itemlist>]`
  * Items with with missing MARC records (if `<itemlist>` provided). Ouputs: ` no_marc.txt`
  * Obvious signs of bad MARC8 -> unicode conversions. Outputs: `bad_unicode.txt`
  * Bad raw MARC to MARC XML conversion (often a sign of bad MARC indexes). Outputs: `bad_index.txt`

* **fixindex.py**
  Takes a single raw MARC record as input and attempts to fix its index. Output to STDOUT.

  **USAGE:** `fixindex.py <binary MARC filename to fix>`

* **[DEPRECATED] marcia.py** (MARC IA)
  Now deprectated. All functionality performed by this script is now incorporated into archive.org's fetchmarc endpoint, so Internet Archive online resource MARC can be downloaded directly. e.g. https://archive.org/download/adventuresoftoms00twaiiala/adventuresoftoms00twaiiala_archive_marc.xml Keeping this code here for reference / testing if needed.

  Convert MARC XML to Internet Archive online resource MARC. Outputs raw MARC to STDOUT (similar to `yaz-marcdump`).
  Can also output MARC XML with `-o marcxml` option.

  **USAGE:** `marcia.py <MARC XML filename to convert>`
