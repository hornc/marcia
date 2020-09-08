import fixindex
import os
from subprocess import Popen, PIPE

DATA = os.path.join(os.path.dirname(__file__), 'test_data')

good_marc         = 'good_marc_00amyl.mrc'
moderate_bad_marc = 'moderate_bad_marc_00book1220882465.mrc' # regular off-by-one index
bad_marc          = 'bad_marc_adolphethiers00rena.mrc'       # index off by more than one?

def check_yaz_output(raw_marc):
    # Send input to Yaz from stdin
    p = Popen(['yaz-marcdump', '-imarc', '-omarcxml', '-n', '/proc/self/fd/0'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    yaz_output, yaz_error = p.communicate(raw_marc)
    return (yaz_output, yaz_error)

def test_fixindex_good_marc():
    """Passing an uncorrrupt index should make no changes."""
    with open(os.path.join(DATA, good_marc), 'rb') as f:
        output = fixindex.fix_index(f)
        f.seek(0)
        assert f.read() == output

def test_fixindex_moderate_bad_marc():
    """Index with regular off-by-one errors will not produce conversion comments from Yaz."""
    with open(os.path.join(DATA, moderate_bad_marc), 'rb') as f:
        fixed = fixindex.fix_index(f)
        yaz_output, yaz_error = check_yaz_output(fixed)
        assert "No separator at end of field" not in yaz_output
        assert "Separator but not at end of field" not in yaz_output

def test_fixindex_bad_marc():
    """Index with more broken index will not produce conversion comments from Yaz."""
    with open(os.path.join(DATA, bad_marc), 'rb') as f:
        fixed = fixindex.fix_index(f)
        yaz_output, yaz_error = check_yaz_output(fixed)
        print(yaz_output)
        assert "No separator at end of field" not in yaz_output
        assert "Separator but not at end of field" not in yaz_output
