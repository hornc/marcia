#!/usr/bin/python

import argparse
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

    def transaction_update(self, datetime):
        """Updates the Date and Time of Latest Transaction (field 005).
           datetime format = YYYYMMDDhhmmss.0
        """
        assert len(datetime) == 16, "Expecting 16 char datetime, got '%s'." % datetime
        self.set_controlfield('005', datetime)
        return datetime

    def set_controlfield(self, tag, value):
        """Sets (overwrite if alreading exists) a MARC XML controlfield.
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
    ORG_CODE = "CaSfIA"
    MODIFIED = "20171215095542.0"
    def __init__(self, ocaid, xml, **kwargs):
        super(IAMarcXml, self).__init__(xml)
        self.ocaid = ocaid

        self.olid = kwargs.get('olid', None)
        self.volume = kwargs.get('volume', None)

        self.set_controlfield('001', ocaid)
        self.set_controlfield('003', self.ORG_CODE)

        # ----- 005 Date and Time of Latest Transaction
        self.transaction_update(self.MODIFIED)

        # ----- 006 Fixed-Length Data Elements-Additional Material Characteristics 
        material_characteristics = "m     o  d"
        self.set_controlfield('006', material_characteristics)

        # ----- 007 - Physical Description Fixed Field-General Information
        electronic_resource = "cr||||||||||||"
        self.set_controlfield('007', electronic_resource)

        # ----- 008 Fixed Length Control Field
        # Critical: Set resource type to Online Resource
        self.set_online_resource()

        # ----- 035 System Control Number
        # Remove old OCLC System Control Number
        # WARNING: Once OCLC#s are properly re-assigned, this needs to be removed!
        self.clear_datafield('035')

        # ----- 040 - Cataloging Source, add IA as modifying agency
        self.add_modifying_agency(self.ORG_CODE)

        # ----- 245 Title Statement 
        # Delete the 245 subfield h.  Use of $h [electronic resource] is old coding and is no longer used.
        self.clear_subfield('245', 'h')

        # ----- 300 Physical Characteristics
        # Critical: Add "1 online resource" at the beginning of every 300 field in subfield a.
        # TODO: check parenthesis use, add test cases, check abbreviations(?)
        physical_description = self.get_datafield('300')

        if len(physical_description) == 0:
            self.set_datafield('300', subfields={'a': '1 online resource'})
        elif 'online resource' not in physical_description[0].text:
            try:
                self.fix_physical_description(physical_description[0])
            except IndexError as e:
                raise Exception, "Problem with 300 Physical Description in %s. Corrupt MARC?\n%s" % (ocaid, etree.tostring(physical_description[0]))

        # ----- 856, Electronic Location and Access
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
            if self.volume:
                subfields['3'] = "Volume %s" % self.volume
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
           Expands some abbreviations in line with current catalogin practice."""
        # remove physical dimensions
        dimensions = physical_description.xpath('m:subfield[@code="c"]', namespaces=NS)
        for d in dimensions:
            physical_description.remove(d)

        # add online resource count, if not already present
        a = physical_description.xpath('m:subfield[@code="a"]', namespaces=NS)[0]
        last = physical_description.xpath('m:subfield', namespaces=NS)[-1]
        if 'online resource' not in a.text:
            a.text = "1 online resource (%s" % a.text
            # add closing parenthesis to last subfield
            last.text = re.sub(r'[ ;]*$', '', last.text) + ')'

        # expand various abbreviations
        a.text = re.sub(r'p\.', 'pages', a.text)
        a.text = re.sub(r'([0-9]+)page', r'\1 page', a.text)
        last.text = re.sub(r'ill\.|illus\.', 'illustrations', last.text)
        last.text = re.sub(r'col[\.,]', 'color', last.text)
        last.text = re.sub(r'ports\.', 'portraits', last.text)
        last.text = re.sub(r'fold\.', 'folded', last.text)

    def set_online_resource(self):
        fixed_len = self.get_controlfield('008')[0]
        fixed_len.text = fixed_len.text[:23] + 'o' + fixed_len.text[24:]

    def strip_custom_fields(self):
        """Removes all 9xx datafields."""
        remove = self.data.xpath('m:datafield[starts-with(@tag,"9")]', namespaces=NS)
        for r in remove:
            self.data.remove(r)

    def validate(self):
        """Performs validation on the IA MARC record."""
        controlfields = ['001', '003', '005', '006', '007', '008']
        for field in controlfields:
            count = len(self.get_controlfield(field))
            assert count == 1, "Expecting exactly one %s controlfield in %s, got %i\n" % (field, self.ocaid, count)
        assert self.get_controlfield('003')[0].text == self.ORG_CODE
        fixed_len = self.get_controlfield('008')[0]
        assert fixed_len.text[23] == 'o'
        assert len(fixed_len.text) == 40, "Expecting controlfield 008 to have 40 characters, has %i\n" % len(fixed_len.text)

        title_statement = self.get_datafield('245')[0]
        assert not title_statement.xpath('m:subfield[@code="h"]', namespaces=NS)

        physical_description_count = len(self.get_datafield('300'))
        assert physical_description_count == 1, "Record %s should have one 300 Physical Description field. Has %i.\n" % (self.ocaid, physical_description_count)
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
        raise Exception, "Unable to open MARC XML%s\n" % filename

    # Look for IA metadata to populate openlibrary url and volume number
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
        if metadata.xpath("volume") != []:
            meta['volume'] = metadata.xpath("volume")[0].text
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

