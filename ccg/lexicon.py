"""
A lexicon loaded from a markedup file
"""
import os
import os.path
from collections import defaultdict

import ccg.category

_INIT_STR = "# now list the markedup categories" 
DEFAULT_PATH = os.path.join(os.path.split(__file__)[0], 'markedup')
CATS = {}


def load(path=DEFAULT_PATH):
    global CATS
    CATS = _Lexicon(path)

class _Lexicon(dict):
    def __init__(self, path=DEFAULT_PATH):
        dict.__init__(self)
        self.cats = defaultdict(int)
        for entry in self._split_entries(open(path).read()):
            if not entry:
                continue
            entry = entry.strip()
            supertag, annotated = self._parse_entry(entry)
            category = ccg.category.from_string(annotated)
            self[supertag] = category
            self[annotated] = category
            # Allow frequencies to be set
            self.cats[category] = 0

    def _split_entries(self, markedup):
        header, text = markedup.split(_INIT_STR)
        return text.split('\n\n')

    def _parse_entry(self, entry_str):
        lines = [line for line in entry_str.split('\n')
                 if not line.startswith('#')]
        supertag = lines[0]
        n_args, annotated = lines[1].strip().split()
        return supertag, annotated

