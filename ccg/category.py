import re
from collections import defaultdict

import ccg.lexicon

VARS = ['_', 'Y', 'Z', 'W', 'V', 'U', 'T', 'S', 'R', 'P']
_FEATS = ['[dcl]', '[b]', '[pss]', '[ng]', '[pt]']
_ATOMIC_RE = re.compile(r'([a-zA-Z,\.;:]+)(\[[^\]]+\])?(\[conj\])?')
_AUX_RE = re.compile(r'\(S\[(\w+)\]\\NP\)/\(S\[(\w+)\]\\NP\)')
_PRED_RE = re.compile(r'\(*S\[(b|dcl|ng|pss|pt|to)\]')
_PUNCT = set([',', ':', ';', '.', "LQU", "RQU", "--", 'RRB', 'LRB'])


class Category(object):
    def __init__(self, result, slash='', argument=None, **kwargs):
        import ccg.scat
        if isinstance(result, ccg.scat.SuperCat):
            result = result.category
        if isinstance(argument, ccg.scat.SuperCat):
            argument = argument.category
        self.slash = slash
        self.argument = argument
        self.is_complex = bool(self.slash)
        if self.is_complex:
            self.result = result
        else:
            self.result = self
            self._cat = result if isinstance(result, str) else result.cat
        self.kwargs = kwargs
        self.hat = kwargs.get('hat')
        self.conj = kwargs.get('conj', False)
        self.var = kwargs.get('var', 0)
        self.var2 = kwargs.get('var2', -1)
        self.asterisk = kwargs.get('asterisk', False)
        self.feat_var = kwargs.get('feat_var')
        self.feature = kwargs.get('feature', '')
        self.arg_idx = kwargs.get('arg_idx')

        if self.is_complex:
            str_get = self._complex_strings
            cat_get = self._complex_cats
        else:
            str_get = self._atomic_strings
            cat_get = self._atomic_cats
        self.cats, self.cats_by_var, self.active_features = cat_get()
        self.next_var = max(self.cats_by_var) + 1
        self.cat, self.string, self.annotated = str_get()
        if not '^' in self.string:
            self.hatless = self.string
        else:
            self.hatless = None

        # Higher-order attributes. Could be properties, but I'm assuming
        # categories are immutable, and this should be more efficient
        self.str_as_piece = '(%s)' % self if (self.is_complex and not
                                              self.hat) else self.string
        # Result leaf is at (0, 0, ...) with the longest path
        self.inner_result = max((p, c) for p, c in self.cats.items()
                                if not any(p))[1]
        self.is_predicate = bool(_PRED_RE.match(self.string))
        self.is_adjunct = (self.result.exact_eq(self.argument) 
                           and self.result.var == self.argument.var
                           and all(c for (p, c) in self.result.cats.items()
                                   if self.argument.cats[p].var == c.var))
        self.has_adjunct = any(r[0].is_adjunct for r in self.deconstruct())
        self.is_aux = bool(_AUX_RE.match(self.string))
        self.is_true_aux = self.is_aux and self.inner_result.feature in _FEATS
        self.is_punct = (not self.is_complex and self.string in _PUNCT)
        self.is_type_raise = (self.is_complex
                              and self.argument.is_complex
                              and self.slash != self.argument.slash
                              and self.result.exact_eq(self.argument.result))
        self.forward = bool(self.is_complex and self.slash == '/')
        self.backward = bool(self.is_complex and self.slash == '\\')

    def __eq__(self, other):
        """
        Check whether the featureless version of the
        other category matches self. Note that this means
        equality is not commutative
        """
        if self is other:
            return True
        if isinstance(other, str):
            other = from_string(other)
        if self.is_complex != other.is_complex:
            return False
        # Fail on feature or hat if it's there and doesnt match
        if self.feature and other.feature and self.feature != other.feature:
            return False
        if self.hat and other.hat and self.hat != other.hat:
            return False
        if self.slash != other.slash:
            return False
        s_cats = self.cats
        o_cats = other.cats
        if len(s_cats.keys()) != len(o_cats.keys()):
            return False
        for path, s_cat in s_cats.items():
            if path not in o_cats:
                return False
            if s_cat.is_complex:
                continue
            o_cat = o_cats[path]
            if s_cat.cat != o_cat.cat:
                return False
            if (s_cat.feature and o_cat.feature 
                and s_cat.feature != o_cat.feature):
                return False
            if s_cat.hat and o_cat.hat and s_cat.hat != o_cat.hat:
                return False
        return True 

    def __ne__(self, other):
        """
        Apparently != doesn't call __eq__. Boo, hiss.
        """
        if not self == other:
            return True
        else:
            return False

    def __str__(self):
        return self.string

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return str(self)

    def __setattr__(self, attr, value):
        """
        Make Categories immutable by ensuring values
        that have been set can never be over-written
        """
        if attr in self.__dict__:
            raise AttributeError(attr)
        else:
            self.__dict__[attr] = value

    def exact_eq(self, other):
        if self is other:
            return True
        else:
            return str(self) == str(other)
        #elif isinstance(other, str):
        #    return self.string == other
        #elif isinstance(other, Category):
        #    return self.string == other.string
        #elif isinstance(other, ccg.scat.SuperCat):
        #    return self.string == other.string
        #else:
        #    return False

    def deconstruct(self):
        """
        Yields result, argument, slash and hat for
        each node on result branch of the category tree
        """
        cat = self
        while cat.is_complex:
            yield cat.result, cat.argument, cat.slash, cat.hat
            cat = cat.result

    # Backwards compatibility
    def isPredicate(self):
        return self.is_predicate

    def isAdjunct(self):
        return self.is_adjunct

    def isPunct(self):
        return self.is_punct

    def isAux(self):
        return self.is_aux

    def isTrueAux(self):
        return self.is_true_aux

    def isTypeRaise(self):
        return self.is_type_raise

    def adjunctResult(self):
        return self.adjunct_result

    def innerResult(self):
        return self.inner_result

    def isAux(self):
        return self.is_aux

    def isComplex(self):
        return self.is_complex

    @property
    def morph(self):
        return self.hat

    @property
    def hasMorph(self):
        return '^' in self.string

    def morphLess(self, as_piece=False):
        if as_piece and self.is_complex:
            return '(%s)' % self.hatless
        else:
            return self.hatless

    def featLess(self):
        return self.featless

    # Unsupported: heads, headGen, addHead, unify,
    # headShare, headRef, strAsPiece, dependencies,
    # goldDependencies, fullPrint


    def _atomic_strings(self):
        hat_str = '^%s' % self.hat.str_as_piece if self.hat else ''
        feat_str = self.feature
        pieces = [self._cat, feat_str, hat_str]

        feat_annot = self.feat_var if self.feat_var else self.feature
        hat_annot = '^%s' % self.hat.annotated if self.hat else ''
        asterisk = '*' if self.asterisk else ''
        var2 = ',%s' % VARS[self.var2] if self.var2 >= 0 else ''
        arg_idx = '<%s>' % self.arg_idx if self.arg_idx else ''
        var_str = '{%s%s%s}%s' % (VARS[self.var], var2, asterisk, arg_idx)
        annot_pieces = [self._cat, feat_annot, hat_annot, var_str]

        if self.conj:
            pieces.append('[conj]')
            annot_cat = '%s{Y}' % ''.join(annot_pieces[:-1])
            annotated = '(%s\%s){%s}' % (annot_cat, annot_cat, VARS[self.var])
        else:
            annotated = ''.join(annot_pieces)
        return self._cat, ''.join(pieces), annotated

    def _complex_strings(self):
        res_str = self.result.str_as_piece
        arg_str = self.argument.str_as_piece
        cat = '%s%s%s' % (res_str, self.slash, arg_str)
        if self.hat:
            cat = '(%s)^%s' % (cat, self.hat.str_as_piece)

        res_annot = self.result.annotated
        arg_annot = self.argument.annotated
        asterisk = '*' if self.asterisk else ''
        var2 = ',%s' % VARS[self.var2] if self.var2 >= 0 else ''
        arg_idx = '<%s>' % self.arg_idx if self.arg_idx else ''
        var_annot = '{%s%s%s}%s' % (VARS[self.var], var2, asterisk, arg_idx)
        hat_annot = '^%s' % self.hat.annotated if self.hat else ''
        annot_cat = '(%s%s%s)%s%s' % (res_annot, self.slash, arg_annot,
                                      var_annot, hat_annot)
        
        # All this effort to get the correct annotation for conj
        # categories, when it (probably?) doesn't matter...
        if self.conj:
            non_conj = from_string(cat)
            var_map = dict((v, v+1) for v in non_conj.cats_by_var)

            result = ccg.rules.remap_vars(non_conj, var_map)
            result_str = result.annotated[:-3] + '{_}'
            var_map = dict((v, v) for v in result.cats_by_var)
            var_map[1] = max(var_map.keys()) + 1
            arg = ccg.rules.remap_vars(result, var_map).annotated
            annot_cat = '(%s\%s){_}' % (result_str, arg)
            string = '%s[conj]' % cat
        else:
            string = cat
        return cat, string, annot_cat

 
    def _atomic_cats(self):
        cats = {(): self}
        cats_by_var = {self.var: [self]}
        if self.var2 >= 0:
            cats_by_var[self.var2] = [self]
        active_features = {(): self} if self.feature else {}
        return cats, cats_by_var, active_features

    def _complex_cats(self):
        # Get list of all cats in tree and their position
        cats = {tuple(): self}
        active_features = {}
        cats_by_var = defaultdict(list)
        cats_by_var[self.var].append(self)
        if self.var2 >= 0 and self.var2 != self.var:
            cats_by_var[self.var2].append(self)
        for piece, path_prefix in ((self.result, 0), (self.argument, 1)):
            for path, cat in piece.cats.items():
                cats[(path_prefix,) + path] = cat
            for var, cat_list in piece.cats_by_var.items():
                cats_by_var[var].extend(cat_list)
            for path, cat in piece.active_features.items():
                active_features[(path_prefix,) + path] = cat
        return cats, cats_by_var, active_features


var_re = re.compile(r'\{(\w)(?:,(\w))?(\*)?\}$')
def from_string(cat_str, **kwargs):
    global VARS
    assert cat_str
    assert cat_str.count('(') == cat_str.count(')')
    cat_str = cat_str.replace('[nb]', '')
    if not kwargs and cat_str in ccg.lexicon.CATS:
        return ccg.lexicon.CATS[cat_str]
    # Add a kwarg to stop subpieces being looked up in CATS
    kwargs['top'] = False
    if cat_str.endswith('>'):
        kwargs['arg_idx'] = cat_str[-2]
        cat_str = cat_str[:-3]
    
    if cat_str.endswith('[conj]'):
        kwargs['conj'] = True
        cat_str = cat_str[:-6]
        if cat_str in ccg.lexicon.CATS:
            annotated = ccg.lexicon.CATS[cat_str].annotated
            return from_string(annotated, **kwargs)
    elif 'conj' not in kwargs:
        kwargs['conj'] = False

    # Handle top-level hat
    hat_idx = cat_str.find('^')
    if hat_idx != -1 and cat_str.endswith('{_}'):
        assert 'hat' not in kwargs
        base_str = cat_str[:hat_idx]
        if base_str.count('(') == base_str.count(')'):
            kwargs['hat'] = from_string(cat_str[hat_idx + 1:])
            return from_string(base_str, **kwargs)
        
    var_match = var_re.search(cat_str)
    if var_match is not None:
        var = var_match.group(1)
        var2 = var_match.group(2)
        kwargs['asterisk'] = var_match.group(3)
        kwargs['var'] = VARS.index(var)
        if var2:
            kwargs['var2'] = VARS.index(var2)
        cat_str = _strip_brackets(cat_str[:var_match.start()])
    
    if '/' not in cat_str and '\\' not in cat_str:
        category = _parse_atomic(cat_str, kwargs)
    else:
        category = _parse_complex(cat_str, kwargs)

    #if not kwargs and '{' in cat_str:
    #    print cat_str
    #    lexicon.CATS[cat_str] = category
    #    lexicon.CATS[category.string] = category
    return category

def _parse_atomic(cat_str, kwargs):
    if '^' in cat_str:
        cat_str, hat_str = cat_str.split('^', 1)
        kwargs['hat'] = from_string(hat_str)
    assert cat_str
    match = _ATOMIC_RE.match(cat_str)
    if match is None:
        raise StandardError(cat_str)
    atom, feature, conj = match.groups()
    if feature:
        if feature[1].isupper():
            kwargs['feat_var'] = feature
        else:
            kwargs['feature'] = feature
    return Category(atom, **kwargs)


def _parse_complex(cat_str, kwargs):
    depth = 0
    slashes = set(('/', '\\'))
    hats = []
    if not cat_str.count('(') == cat_str.count(')'):
        raise StandardError(cat_str)
    for i, c in enumerate(cat_str):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif depth == 0:
            if c in slashes:
                hats = []
                result = from_string(_strip_brackets(cat_str[:i]))
                slash = cat_str[i]
                argument = from_string(_strip_brackets(cat_str[i + 1:]))
                return Category(result, slash, argument, **kwargs)
            elif c == '^':
                hats.append(i)
        assert depth >= 0
    else:
        assert hats
        i = hats[0]
        kwargs['hat'] = from_string(_strip_brackets(cat_str[i + 1:]))
        return from_string(_strip_brackets(cat_str[:i]), **kwargs)


def _strip_brackets(cat_str):
    if not (cat_str.startswith('(') and cat_str.endswith(')')):
        return cat_str
    depth = 0
    for c in cat_str:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        if depth == 0 and (c == '/' or c == '\\' or c == '^'):
            return cat_str
    else:
        return cat_str[1:-1]


