import ccg.category

def isIdentical(c1, c2):
    return c1.exact_eq(c2)

CONJ = ccg.category.from_string('conj')
conj = CONJ
COMMA = ccg.category.from_string(',{_}')
SEMI_COLON = ccg.category.from_string(';{_}')
COLON = ccg.category.from_string(':{_}')
N = ccg.category.from_string('N')
NP = ccg.category.from_string('NP')
VP = ccg.category.from_string('S\NP')
punct = {
        ',': True,
        ':': True,
        '.': True,
        ';': True,
        'RRB': True,
        'LRB': True,
        '-RRB-': True,
        '-LRB-': True,
        'LQU': True,
        'RQU': True,
        'PUNCT': True
    }
