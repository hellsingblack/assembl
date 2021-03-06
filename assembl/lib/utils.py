import re
import unidecode
from StringIO import StringIO


def get_eol(text):
    """Return the EOL character sequence used in the text."""
    line = StringIO(text).readline()
    return line[len(line.rstrip('\r\n')):]


def slugify(str):
    str = unidecode.unidecode(str).lower()
    return re.sub(r'\W+','-',str)
