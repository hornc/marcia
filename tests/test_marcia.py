import marcia as m
from lxml import etree

MARC21_NS = "http://www.loc.gov/MARC21/slim"
NS = {'m': MARC21_NS}

def marc(content=''):
   """Generates a test MARC XML.
      MARC-IA requires at least one controlfield and one datafield to function.
   """
   data = '''<record xmlns="http://www.loc.gov/MARC21/slim">
     <leader>00971cam a2200289 a 4500</leader>
     <controlfield tag="008">820312s1983    alu          s00110 eng  </controlfield>
     <datafield tag="245" ind1="1" ind2="0">
       <subfield code="a">Test Record</subfield>
     </datafield>
     %s
   </record>''' % content
   return data

def test_marc_xml():
    data = marc() 
    root = etree.fromstring(data)
    basic_marc = m.MarcXml(root)
    assert basic_marc

def test_ia_marc_xml():
    data = marc()
    ocaid = 'test_ocaid'
    root = etree.fromstring(data)
    basic_ia_marc = m.IAMarcXml(ocaid, root)
    assert basic_ia_marc

def test_catalog_language():
    lang_xml = "<datafield tag='040'><subfield code='b'>GER</subfield></datafield>"
    data = marc(lang_xml)
    root = etree.fromstring(data)
    ia_marc = m.IAMarcXml('catalog_lang', root)
    assert ia_marc.catalog_language() == 'ger'

def test_catalog_language_default():
    data = marc()
    root = etree.fromstring(data)
    ia_marc = m.IAMarcXml('catalog_lang', root)
    assert ia_marc.catalog_language() == 'eng'

def test_publisher_from_meta():
    metaxml = {'publisher': 'DK Pub.',
              'city': 'New York',
              'date': '1996'}
    data = marc()
    root = etree.fromstring(data)
    iamarc = m.IAMarcXml('test', root, **metaxml)
    assert iamarc.get_datafield('260')[0].xpath('m:subfield[@code="a"]', namespaces=NS)[0].text == 'New York :'
    assert iamarc.get_datafield('260')[0].xpath('m:subfield[@code="b"]', namespaces=NS)[0].text == 'DK Pub. ;'
    assert iamarc.get_datafield('260')[0].xpath('m:subfield[@code="c"]', namespaces=NS)[0].text == '1996.'

def test_strip_nonword_tags():
    xml = "<datafield tag='.880'/>"
    data = marc(xml)
    root = etree.fromstring(data)
    ia_marc = m.IAMarcXml('strip', root)
    assert ia_marc.get_datafield('.880') == []
