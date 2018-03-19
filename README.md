# marcia
A collection of scripts for MARC conversion and checking for the [Internet Archive](https://github.com/internetarchive)

**REQUIREMENTS:**
* [ia-client](https://github.com/jjjake/internetarchive)	>= 1.7.7
* yaz-marcdump	>= 5.23.1	part of [yaz](https://www.indexdata.com/resources/software/yaz/)
* [GNU Parallel](https://www.gnu.org/software/parallel/)

**SCRIPTS:**
* **checkmarc.sh**
  Bash script to check for obvious issues with MARC XML:
  
  **USAGE:** `checkmarc.sh [<itemlist>]`
  
  **OUTPUT:**
  * Items with with missing MARC records (if `<itemlist>` provided). Ouputs: ` no_marc.txt`
  * Obvious signs of bad MARC8 -> unicode conversions. Outputs: `bad_unicode.txt`
  * Bad raw MARC to MARC XML conversion (often a sign of bad MARC indexes). Outputs: `bad_index.txt`

* **fixmarc.sh**
  Script to bulk fix index and unicode issues with IA MARC records.
  Assumes it is being run in a directory containing MARC XML records named `<ocaid>_archive_marc.xml`
  on which the `checkmarc.sh` script (above) has been run to generate itemlists:
    * `bad_unicode.txt` 
    * `bad_index.txt`
  
  **USAGE:** `fixmarc.sh` 

  **Output:**
    * Backs up MARC XML and binary MARC to `./backup`
    * regenerates good source MARC XML (`<ocaid>_marc.xml`)
    * and good indexed binary MARC (`<ocaid>_meta.mrc`)

  **NOTE:** These are fixed _SOURCE_ MARC records and need to be uploaded
  back to archive.org to enable correct archive.org MARCs generated
  by fetchmarc.php. This can be done using the following [ia-client](https://github.com/jjjake/internetarchive) commands:
  ```
  while read f;do ia upload $f ${f}_marc.xml; done < bad_unicode.txt
  while read f;do ia upload $f ${f}_meta.mrc ${f}_marc.xml; done < bad_index.txt
  ```

* **fixindex.py**
  Takes a single raw MARC record as input and attempts to fix its index. Output to STDOUT. Used by `fixmarc.sh` above.

  **USAGE:** `fixindex.py <binary MARC filename to fix>`

* **[DEPRECATED] marcia.py** (MARC IA)
  Now deprectated. All functionality performed by this script is now incorporated into archive.org's fetchmarc endpoint, so Internet Archive online resource MARC can be downloaded directly. e.g. https://archive.org/download/adventuresoftoms00twaiiala/adventuresoftoms00twaiiala_archive_marc.xml Keeping this code here for reference / testing if needed.

  Convert MARC XML to Internet Archive online resource MARC. Outputs raw MARC to STDOUT (similar to `yaz-marcdump`).
  Can also output MARC XML with `-o marcxml` option.

  **USAGE:** `marcia.py <MARC XML filename to convert>`
