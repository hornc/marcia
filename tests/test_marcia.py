import marcia as m
from lxml import etree

def marc():
   """Generates a test MARC XML.
      MARC-IA requires at least one controlfield and one datafield to function.
   """
   data = '''<record xmlns="http://www.loc.gov/MARC21/slim">
     <leader>00971cam a2200289 a 4500</leader>
     <controlfield tag="008">820312s1983    alu          s00110 eng  </controlfield>
     <datafield tag="245" ind1="1" ind2="0">
       <subfield code="a">Test Record</subfield>
     </datafield>
   </record>'''
   return data

def test_marc_xml():
    data = marc() 
    root = etree.fromstring(data)
    basic_marc = m.MarcXml(root)
    assert basic_marc

def test_ia_marc_xml():
    data = marc()
    ocaid = "test_ocaid"
    root = etree.fromstring(data)
    basic_ia_marc = m.IAMarcXml(ocaid, root)
    assert basic_ia_marc