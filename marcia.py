#!/usr/bin/python

import argparse
import collections
import os
import re
import subprocess
import sys
from lxml import etree

MARC21_NS = "http://www.loc.gov/MARC21/slim"
NS = {'m': MARC21_NS}
DEBUG = False
UNICODE_CHECK = False

class MarcXml(object):
    def __init__(self, xml):
        self.data = xml

    def add_modifying_agency(self, orgcode):
        """Appends a modifying agency, subfield d, to 040, if it is not already last in the list."""
        if self.get_datafield('040') == []:
            self.set_datafield('040')
        cataloging_sources = self.get_datafield('040')[0]
        modifiers = cataloging_sources.xpath('m:subfield[@code="d"]', namespaces=NS)
        if modifiers == [] or modifiers[-1].text != orgcode:
            sub = etree.Element('{%s}subfield' % MARC21_NS, {'code': 'd'})
            sub.text = orgcode
            cataloging_sources.append(sub)

    def catalog_language(self):
        lang = self.data.xpath('m:datafield[@tag="040"]/m:subfield[@code="b"]', namespaces=NS)
        if lang != []:
            return lang[0].text.lower()
        return 'eng'

    def comments(self):
        return self.data.xpath('//comment()')

    def convert_440(self):
        """Perform conversion of formerly valid 440 - Series Statement/Added Entry-Title
           to current fields, 490 + 830.
           see http://www.loc.gov/marc/bibliographic/bd440.html : "CONVERSION TO CURRENT FIELDS".
        """

        def concatenate_subfields(field, subfields):
            """Concatenates the text of <subfields> into one string."""
            output = ""
            for s in subfields:
                subfield = field.xpath('m:subfield[@code="%s"]' % s, namespaces=NS)
                if subfield:
                    output += subfield[0].text
            return output

        statements = self.get_datafield('440')

        for statement in statements:
            # Create new 490 from 440
            a = concatenate_subfields(statement, ['a', 'n', 'p'])
            data = {'a': a}
            for s in ['v', 'x', '6', '8']:
                subfield = statement.xpath('m:subfield[@code="%s"]' % s, namespaces=NS)
                if subfield:
                    data[s] = subfield[0].text
            self.set_datafield('490', ind1='1', ind2=' ', subfields=data)
            # convert original 440 to 830
            statement.set('tag', '830')
        # If there was a 440$6, we need to convert the corrensponding 880$6 to point to the new 830
        #    see https://www.loc.gov/marc/bibliographic/ecbdcntf.html for $6 Linkage details
        for reference in self.data.xpath('m:datafield[@tag="880"]/m:subfield[@code="6"]', namespaces=NS):
            if '440' in reference.text:
                reference.text = reference.text.replace('440', '830')

    def clear_controlfield(self, tag):
        """Completely clears all controlfields with a specific tag."""
        for e in self.get_controlfield(tag):
            self.data.remove(e)

    def clear_datafield(self, tag):
        """Completely clears all datafields with a specific tag."""
        for e in self.get_datafield(tag):
            self.data.remove(e)

    def clear_subfield(self, tag, subfield_code):
        """Clears all subfields of <subfield_code> on all tags of <tag>."""
        field = self.get_datafield(tag)
        for f in field:
            target = f.xpath('m:subfield[@code="%s"]' % subfield_code, namespaces=NS)
            for t in target:
                f.remove(t)

    def controlfields(self):
        """Returns ALL controlfields, and data offset."""
        offset = self.leader_pos() # leader
        return (self.data.xpath('m:controlfield', namespaces=NS), offset)

    def datafields(self):
        """Returns ALL datafields, and data offset."""
        controlfields = self.controlfields()
        offset = len(controlfields[0]) + controlfields[1] 
        return (self.data.xpath('m:datafield', namespaces=NS), offset)

    def is_online_resource(self):
        """Returns True if record is an online resource."""
        field = self.get_controlfield('008')
        return field and field[0].text[23] == 'o'

    def insert(self, field, fields):
        """Inserts a field (control or data) in tag order."""
        field_offset = fields[1]
        tag = field.get('tag')
        for i,f in enumerate(fields[0]):
            if int(f.get('tag')) > int(tag): 
                # Insert before current field
                self.data.insert(i + field_offset, field)
                break
            elif i == (len(fields[0]) - 1):
                # Insert after last field
                self.data.insert(len(fields[0]) + field_offset, field)

    def get_datafield(self, tag):
        """Returns a list of <tag> datafields."""
        return self.data.xpath('m:datafield[@tag="%s"]' % tag, namespaces=NS)
        
    def get_controlfield(self, tag):
        """Returns a list of <tag> controlfields."""
        return self.data.xpath('m:controlfield[@tag="%s"]' % tag, namespaces=NS)

    def leader_pos(self):
        """Return the offset of the leader. Normally 1, unless there are XML comments."""
        leader = self.get_leader()
        for i in range(0, len(self.data)):
            if self.data[i] == leader:
                return i+1

    def get_leader(self):
        leader = self.data.xpath("m:leader", namespaces=NS)
        if len(leader) == 1:
            return leader[0]

    def set_leader(self, pos, char):
        """Set the Leader character at <pos> to <char>."""
        leader = self.get_leader()
        leader.text = leader.text[:pos] + char + leader.text[pos+1:]

    def transaction_update(self, datetime):
        """Updates the Date and Time of Latest Transaction (field 005).
           datetime format = YYYYMMDDhhmmss.0
        """
        assert len(datetime) == 16, "Expecting 16 char datetime, got '%s'." % datetime
        self.set_controlfield('005', datetime)
        return datetime

    def set_controlfield(self, tag, value):
        """Sets (overwrite if already exists) a MARC XML controlfield.
           usage:
               set_controlfield('006', 'abcd')
        """
        self.clear_controlfield(tag)
        field = etree.Element('{%s}controlfield' % MARC21_NS, {'tag': tag}, nsmap={None: MARC21_NS})
        field.text = value
        self.insert(field, self.controlfields())

    def add_data(self, tag, **kwargs):
        """Adds a datafield without overwriting any existing content."""
        self.set_datafield(tag, **kwargs)

    def set_datafield(self, tag, **kwargs):
        """Sets a new MARC XML datafield.
           usage:
               set_datafield('300', ind1=' ', ind2=' ', subfields={'a': '1 online resource'})
        """
        ind1 = kwargs.get('ind1', ' ')
        ind2 = kwargs.get('ind2', ' ')
        field = etree.Element('{%s}datafield' % MARC21_NS, {'ind1': ind1, 'ind2': ind2, 'tag': tag}, nsmap={None: MARC21_NS})
        for code,v in kwargs.get('subfields', {}).iteritems():
            sub = etree.Element('{%s}subfield' % MARC21_NS, {'code': code})
            sub.text = v
            field.append(sub)
        self.insert(field, self.datafields())

class IAMarcXml(MarcXml):
    ORG_CODE = 'CaSfIA'
    MODIFIED = '20180220154542.0'
    def __init__(self, ocaid, xml, **kwargs):
        super(IAMarcXml, self).__init__(xml)
        self.ocaid = ocaid

        # check for corrupt index
        if self.has_corrupt_index():
            raise Exception('Corrupt index found!')

        self.olid      = kwargs.get('olid', None)
        self.volume    = kwargs.get('volume', None)
        self.city      = kwargs.get('city', None)
        self.publisher = kwargs.get('publisher', None)
        self.date      = kwargs.get('date', None)

        originally_ebook = self.is_online_resource()

        # ----- Leader
        # Fix invalid characters in pos 18, Descriptive cataloging form
        leader = self.get_leader()
        if leader.text[18] == '1':
            replacement = 'i' # i - ISBD punctuation included
            self.set_leader(18, replacement)

        self.set_controlfield('001', ocaid)
        self.set_controlfield('003', self.ORG_CODE)

        # ----- Strip Local or Obsolete Fields
        self.clear_controlfield('004')
        strip_fields = ['011', '014', '019', '029', '037', '039', '044', '049', '051', '059', '069', '079', '089', '333', '349', '659']
        # strip non digit datafields early
        strip_fields += [ field.get('tag') for field in self.data.xpath("m:datafield[translate(@tag, '0123456789', '') != '']", namespaces=NS) ]
        for f in strip_fields:
            self.clear_datafield(f)

        # ----- 005 Date and Time of Latest Transaction
        self.transaction_update(self.MODIFIED)

        # ----- 006 Fixed-Length Data Elements-Additional Material Characteristics 
        material_characteristics = 'm     o  d'
        self.set_controlfield('006', material_characteristics)

        # ----- 007 - Physical Description Fixed Field-General Information
        electronic_resource = 'cr||||||||||||'
        self.set_controlfield('007', electronic_resource)

        # ----- 008 Fixed Length Control Field
        # Critical: Set resource type to Online Resource
        self.set_online_resource()

        # Ensure Continuing dates are not applied to Monographs

        fixed_lengths = self.get_controlfield('008')
        if fixed_lengths:
            fixed_length = fixed_lengths[0]
            continuing_dates = fixed_length.text[6] == 'c'
            monograph        = self.get_leader().text[7] == 'm'
            if continuing_dates and monograph:
                date1 = fixed_length.text[7:11]
                date2 = fixed_length.text[11:15]
                if date2 == '    ':
                    # 's', Single known date/probable date
                    correction = 's'
                elif int(date2) > int(date1):
                    pub_date = self.data.xpath('m:datafield[@tag="260"]/m:subfield[@code="c"]', namespaces=NS)
                    if pub_date and '[' in pub_date[0].text:
                        # questionable dates
                        correction = 'q'
                    else:
                        # no attempt
                        correction = ' '
                else:
                    # 't', Publication date and copyright date
                    assert date2 != '9999',  'Perhaps item is a real serial?'
                    assert int(date1) > int(date2), 'Copyright date is after publication date?'
                    correction = 't'
                fixed_length.text = fixed_length.text[:6] + correction + fixed_length.text[7:]

        # ----- 010 Library of Congress Control Number
        # ----- 020 ISBN
        # Convert subfield 'a' > 'z' if not originally an e-book
        if not originally_ebook:
            lccns = self.get_datafield('010')
            isbns = self.get_datafield('020')
            for item in lccns + isbns:
                original_id = item.xpath('m:subfield[@code="a"]', namespaces=NS)
                for original in original_id:
                    original.set('code', 'z')

        # ----- 035 System Control Number
        # Remove old OCLC System Control Number
        # WARNING: Once OCLC's are properly re-assigned, this needs to be removed!
        self.clear_datafield('035')

        # ----- 040 - Cataloging Source, add IA as modifying agency
        self.add_modifying_agency(self.ORG_CODE)
        # remove invalid ETHICS_ISBD from 040$e (Description conventions)
        for code in self.data.xpath('m:datafield[@tag="040"]/m:subfield[@code="e"]', namespaces=NS):
            if code.text == 'ETHICS-ISBD':
                code.getparent().remove(code)

        # ----- 050 - Library of Congress Call Number
        # ----- 082 - Dewey Decimal Classification Number
        # Change Second Indicator - Source of call number/Source of classification number
        #  from '0 - Assigned by LC' to '4 - Assigned by agency other than LC'
        lccns = self.get_datafield('050')
        deweys = self.get_datafield('082')
        for item in lccns + deweys:
            if item.get('ind2') == '0':
                item.set('ind2', '4')

        # ----- 245 Title Statement 
        # Delete the 245 subfield h.  Use of $h [electronic resource] is old coding and is no longer used.
        self.clear_subfield('245', 'h')

        # ----- 260 / 264 "Publisher details" if not present, create 260 from metadata ------
        if self.data.xpath('m:datafield[@tag="260" or @tag="264"]/m:subfield[@code="a"]', namespaces=NS) == []:
            subfields = collections.OrderedDict()
            if self.city:
                subfields['a'] = self.city + (' :' if self.publisher else ' ,')
            if self.publisher:
                subfields['b'] = self.publisher + ' ;'
            if self.date:
                subfields['c'] = self.date + '.'
            if subfields != {}:
                self.set_datafield('260', subfields=subfields);

        # ----- 300 Physical Characteristics
        # Critical: Add "1 online resource" at the beginning of every 300 field in subfield a.
        # TODO: check parenthesis use, add test cases, check abbreviations
        physical_description = self.get_datafield('300')

        if len(physical_description) == 0:
            self.set_datafield('300', subfields={'a': '1 online resource'})
        elif 'online resource' not in physical_description[0].text:
            try:
                self.fix_physical_description(physical_description[0])
            except IndexError as e:
                raise Exception, "Problem with 300 Physical Description in %s. Corrupt MARC?\n%s" % (ocaid, etree.tostring(physical_description[0]))

        # ----- 440, Series Statement/Added Entry-Title, convert to 490, Series Statement + 830, Series Added Entry-Uniform Title
        # see http://www.loc.gov/marc/bibliographic/bd440.html : "CONVERSION TO CURRENT FIELDS"
        self.convert_440()

        # ----- 856, Electronic Location and Access
        if originally_ebook:
            self.clear_datafield('856')
        self.fix_locations()

        # ----- 9xx Custom Fields
        self.strip_custom_fields()

        # Finally, check everything is OK:
        self.validate()

    def get_location_by_text(self, text):
        """Finds and returns an 856 Electronic Location and Access field by $z (public note)."""
        for loc in self.get_datafield('856'):
            desc = loc.xpath('m:subfield[@code="z"]', namespaces=NS)
            if desc and desc[0].text == text:
                return loc

    def fix_locations(self):
        """Make corrections to any existing 856 Electronic Location and Access fields.
           1) ind2 = 0 for IA resource URI
           2) prefer https rather than http
           3) avoid / reduce redirects
           
        """
        IA_TEXT = "Free eBook from the Internet Archive"
        OL_TEXT = "Additional information and access via Open Library"

        locations = self.get_datafield('856')
        ia_location = self.get_location_by_text(IA_TEXT)
        ol_location = self.get_location_by_text(OL_TEXT)

        if ia_location is not None:
            #self.data.remove(ia_location) # remove or replace?
            ia_location.set('ind2', '0')
            uri = ia_location.xpath('m:subfield[@code="u"]', namespaces=NS)[0]
            uri.text = uri.text.replace('http://archive', 'https://archive')
        else:
            subfields = {'u': "https://archive.org/details/%s" % self.ocaid,
                         'z': IA_TEXT}
            #Add $3 Materials Specified, e.g. cu31924088466184
            #if self.volume:
            #    subfields['3'] = "Volume %s" % self.volume
            self.add_data('856', ind1='4', ind2='0',
                          subfields = subfields)
        if ol_location is not None:
            uri = ol_location.xpath('m:subfield[@code="u"]', namespaces=NS)[0]
            uri.text = uri.text.replace('http://www.openlibrary', 'https://openlibrary')
        elif self.olid:
            self.add_data('856', ind1='4', ind2='2',
                          subfields = {'u': "https://openlibrary.org/books/%s" % self.olid,
                                       'z': OL_TEXT})

    def fix_physical_description(self, physical_description):
        """Removes physical dimensions from electronic resources.
           Adds '1 online resource' to 300$a.
           Expands some abbreviations in line with current cataloging practice."""
        # remove physical dimensions
        dimensions = physical_description.xpath('m:subfield[@code="c"]', namespaces=NS)
        for d in dimensions:
            physical_description.remove(d)

        # add online resource count, if not already present
        a = physical_description.xpath('m:subfield[@code="a"]', namespaces=NS)
        if a == []: # a subfield does not exist, create it
            sub = etree.Element('{%s}subfield' % MARC21_NS, {'code': 'a'})
            sub.text = ''
            physical_description.insert(0, sub)
            a = physical_description.xpath('m:subfield[@code="a"]', namespaces=NS)

        a = a[0]
        if not a.text: # rare case where empty subfield exists
            a.text = ''
        last = physical_description.xpath('m:subfield', namespaces=NS)[-1]
        if 'online resource' not in a.text:
            a.text = "1 online resource (%s" % a.text
            # add closing parenthesis to last subfield
            last.text = re.sub(r'[ :;]*$', '', last.text) + ')'

        # expand various abbreviations
        if self.catalog_language() == 'eng':
            a.text = re.sub(r'p\.', 'pages', a.text)
            a.text = re.sub(r'([0-9]+)page', r'\1 page', a.text)
        last.text = self.expand_abbreviations(last.text, self.catalog_language())

    def expand_abbreviations(self, text, language):
        if language == 'eng':
            text = re.sub(r'ill\.|illus\.', 'illustrations', text)
            text = re.sub(r'col[\.,]', 'color', text)
            text = re.sub(r'ports\.', 'portraits', text)
            text = re.sub(r'fold\.', 'folded', text)
            text = re.sub(r'diagrs\.', 'diagrams', text)
        return text

    def has_corrupt_index(self):
        for c in self.comments():
            if DEBUG:
                print "]%s[" % c.text
            # Needs to catch both
            #  Separator but not at end of field length=40
            #  No separator at end of field length=40
            # which indicate a problem with the 008 fixed length field
            if 'at end of field length=40' in c.text:
                return True
        return False

    def set_online_resource(self):
        fixed_len = self.get_controlfield('008')
        if fixed_len:
            fixed_len[0].text = fixed_len[0].text[:23] + 'o' + fixed_len[0].text[24:]

    def strip_custom_fields(self):
        """Removes all 9xx and 09X datafields."""
        remove = self.data.xpath('m:datafield[starts-with(@tag,"9")]', namespaces=NS)
        remove += self.data.xpath('m:datafield[starts-with(@tag,"09")]', namespaces=NS)
        for r in remove:
            self.data.remove(r)

    def validate(self):
        """Performs validation on the IA MARC record."""
        controlfields = ['001', '003', '005', '006', '007', '008']
        for field in controlfields:
            count = len(self.get_controlfield(field))
            assert count == 1, "Expecting exactly one %s controlfield in %s, got %i\n" % (field, self.ocaid, count)
        assert self.get_controlfield('003')[0].text == self.ORG_CODE
        assert self.get_controlfield('004') == []
        fixed_len = self.get_controlfield('008')[0]
        assert fixed_len.text[23] == 'o'
        assert len(fixed_len.text) == 40, "Expecting controlfield 008 to have 40 characters, has %i\n" % len(fixed_len.text)

        #assert self.data.xpath('m:datafield[@tag="260" or @tag="264"]', namespaces=NS) != [], "Records needs to have publisher data to avoid being flagged as 'sparse'"

        title_statement = self.get_datafield('245')[0]
        assert not title_statement.xpath('m:subfield[@code="h"]', namespaces=NS)

        assert self.get_datafield('440') == []
        # Unicode check
        if UNICODE_CHECK:
            assert(self.get_leader().text[9] == 'a') # 'a'=Unicode, ' '=MARC8

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert MARC XML to Internet Archive online resource MARC.')
    parser.add_argument('filename', help='MARC XML to process, <ociad>_marc.xml')
    parser.add_argument('-o', '--output', default='marc', choices=['marc', 'marcxml'], help='Output format, marc or marcxml')
    parser.add_argument('-n', '--suppress_output', action='store_true', help='Suppress output, only show errors and warnings')
    #parser.add_argument('-d', '--debug', action='store_true', help='Debug output')
    #parser.add_argument('-u', '--unicode', action='store_true', help='Perform unicode check on input MARC')

    args = parser.parse_args()
    filename = args.filename
    ocaid = re.search(r'([^//]+?)(_archive)?_marc.xml', filename).group(1)

    try:
        doc = etree.parse(filename)
    except IOError as e:
        raise Exception, "Unable to open MARC XML: %s\n" % filename

    # Look for IA metadata to populate openlibrary url
    metadata_filename = os.path.join(os.path.dirname(filename), "%s_meta.xml" % (ocaid))
    meta = {}
    try:
        metadata = etree.parse(metadata_filename)
        if metadata.xpath("openlibrary") != []:
            meta['old_olid'] = metadata.xpath("openlibrary")[0].text
            if DEBUG:
                print "DEBUG old_olid: %s" % meta['old_olid']
        if metadata.xpath("openlibrary_edition") != []:
            meta['olid'] = metadata.xpath("openlibrary_edition")[0].text
        fields = ['city', 'publisher', 'date', 'volume']
        for f in fields:
            if metadata.xpath(f) != []:
                meta[f] = metadata.xpath(f)[0].text
    except IOError as e:
        #TODO: Metadata should be optional? Use it if it is there, still produce a good MARC if not. Log a warning just in case?
        #print "METADATA %s NOT FOUND" % metadata_filename
        pass
        #raise Exception, "Unable to open metadata %s\n" % metadata_filename

    root = doc.getroot()

    # If MARC XML is a collection rather than a record, select the first(hopefully only!) record
    if root.tag == "{%s}collection" % MARC21_NS:
        doc = root[0]
        root = doc

    try:
        record = IAMarcXml(ocaid, root, **meta)
    except Exception as e:
        e.args += (filename,)
        raise

    if DEBUG:
        print record.get_leader()
        print "TITLE STATEMENT: %s" % etree.tostring(record.get_datafield('245')[0])

    # ---- Write output
    # Use yaz-marcdump to convert modified XML to marc
    if not args.suppress_output:
        p = subprocess.Popen(["yaz-marcdump", "-imarcxml", "-o%s" % args.output, "/proc/self/fd/0"], stdin=subprocess.PIPE)
        result = p.communicate(etree.tostring(record.data))

