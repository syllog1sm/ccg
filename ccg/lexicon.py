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
            self.add_entry(supertag, annotated)
            self.add_entry(supertag.replace('[nb]', ''), annotated.replace('[nb]', ''))

    def add_entry(self, supertag, annotated):
        annotated = annotated.split('@')[0]
        if supertag in self and annotated != self[supertag].annotated:
            #print supertag
            #print annotated
            #print self[supertag].annotated
            return None
        if '{R}' in annotated:
           return None 
        try:
            category = ccg.category.from_string(annotated)
        except:
            print entry
            raise
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

class MarkedupEntry(object):
    def __init__(self, markedup_str):
        self.string = markedup_str
        lines = [l for l in markedup_str.split('\n')
                if not l.strip().startswith('#')]
        bare_category = lines.pop(0)
        n_slots, annotated_category = lines.pop(0).strip().split(' ')
        if lines and lines[0].startswith('  !'):
            alt_markedup = lines.pop(0)[4:]
        else:
            alt_markedup = ''
        slots = defaultdict(list)
        for line in lines:
            slot = Slot(line)
            slots[slot.n].append(slot)

        self.category = ccg.category.from_string(bare_category)
        self.annotated = ccg.category.from_string(annotated_category)
        self.n_grs = int(n_slots)
        if alt_markedup:
            self.alt_annotated = ccg.category.from_string(alt_markedup)
        else:
            self.alt_annotated = self.annotated
        self.grs = slots


class Slot(object):
    def __init__(self, slot_str):
        pieces = slot_str.strip().split(' ')
        if pieces and pieces[-1].startswith('='):
            self.constraint_name = pieces.pop(-1)
            self.constraint_group = CONSTRAINT_GROUPS.get(self.constraint_name, set())
        else:
            self.constraint_name = None
            self.constraint_group = set()

        if not pieces[-1].startswith('%') and pieces[-1] != 'ignore':
            self.subtype2 = pieces.pop(-1)
        else:
            self.subtype2 = None

        self.words = [p for p in pieces if p.startswith('%')]
        pieces = [p for p in pieces if not p.startswith('%')]

        self.n = int(pieces.pop(0))
        self.label = pieces.pop(0)
        if pieces:
            self.subtype1 = pieces.pop(0)
        else:
            self.subtype1 = None
        assert not pieces



