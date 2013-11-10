from collections import defaultdict
import re

import ccg.category
import ccg.rules

class SuperCat(object):
    """
    A top-level category, participating in a derivation. Manages
    variable coindexation between a CCG category and HLDS terms.
    Tracks variable coindexation
    during productions. Unlike Category objects, is mutable.
    """
    def __init__(self, category, hlds=None, word_bindings=None):
        if isinstance(category, str):
            category = ccg.category.from_string(category)
        elif isinstance(category, SuperCat):
            category = category.category
        else:
            assert isinstance(category, ccg.category.Category)
        # Have a unique variable ID for each category variable.
        # Store the mapping from unique IDs to category vars and vice versa
        var_table = {}
        for var in category.cats_by_var:
            var_id = Variable()
            var_table[var] = set([var_id])
        self._var_table = var_table
        self.category = category
        self.hlds_children = defaultdict(set)
        self.hlds_parents = defaultdict(set)
        self.hlds_passed = set()
        self.srl_annot = set()
    

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        elif hasattr(self.category, attr):
            return getattr(self.category, attr)
        else:
            raise AttributeError(attr)
 
    def __eq__(self, other):
        return self.category == other

    def __ne__(self, other):
        return self.category != other

    def __str__(self):
        return str(self.category)

    def __hash__(self):
        return hash(self.category)

    def __repr__(self):
        return repr(self.category)

    def global_annotated(self):
        annotated = self.annotated.replace('*}', '}')
        for var in self.cats_by_var:
            global_vars = [v for v in self._var_table[var] if v.word is not None]
            try:
                global_vars = sorted(global_vars, key=lambda gv: gv.word)
            except:
                raise
            global_str = '{%s}' % ','.join(str(v) for v in global_vars)
            var_str = ccg.category.VARS[var]
            annotated = annotated.replace('{%s}' % var_str, global_str)
        return annotated

    def bind_vars(self, other, self_cat, other_cat):
        """
        Unify the global variables of a piece of this scat against
        the piece of another scat. Use the other's variable
        table to retrieve the other's global variables.
        """
        assert self_cat == other_cat
        to_unify = set()
        for path, self_piece in self_cat.cats.items():
            other_piece = other_cat.cats[path]
            self_var = self_piece.var
            other_var = other_piece.var
            if not self.can_unify(other, self_var, other_var):
                return False
            to_unify.add((self_piece.var, other_piece.var))
        for self_var, other_var in to_unify:
            self_cats = self_cat.cats_by_var[self_var]
            other_cats = other_cat.cats_by_var[other_var]
            self.unify_globals_at_var(other, self_var, other_var)
        return True

    def add_hlds_child(self, relation, global_var):
        """
        Set a child dependency
        """
        self.hlds_children[global_var].add(relation)

    def add_hlds_parent(self, relation, global_var):
        self.hlds_parents[global_var].add(relation)

    def add_hlds_passed(self, parent_var, relation, child_var):
        self.hlds_passed.add((parent_var, relation, child_var))
        
   
    def get_vars(self, cat=None):
        if cat is None:
            cat = self
        return set(v.get_ref() for v in self._var_table[cat.var])

    def add_var(self, i, var):
        ref = var.get_ref()
        self._var_table[i] = set(v.get_ref() for v in self._var_table[i])
        self._var_table[i].add(ref)

    def unify_globals_at_var(self, other, var, other_var=None):
        if other_var is None:
            other_var = var
        s_vars = self._var_table[var]
        o_vars = other._var_table[other_var]
        if len(s_vars) == len(o_vars) == 1:
            list(s_vars)[0].unify(list(o_vars)[0])
        else:
            list(s_vars)[0].unify(list(o_vars)[0])
            # The unification is not complete here, which may cause problems.
            # But cannot unify other to both in self, or self vars will
            # be unified to each other :(
            var_set = set([v.get_ref() for v in s_vars.union(o_vars)])
            self._var_table[var] = var_set
            other._var_table[other_var] = var_set

    def can_unify(self, other, var, other_var):
        s_vars = self._var_table[var]
        s_words = set([s_var.word for s_var in s_vars])
        o_vars = other._var_table[other_var]
        for s_var in s_vars:
            s_word = s_var.word
            if not s_word:
                continue
            for o_var in o_vars:
                o_word = o_var.word
                # Patch for conjunction, see wsj_0047.11 for eg
                # May be bad idea?
                if o_word and o_word not in s_words:
                    return False
        return True


    def has_head(self, word, cat=None):
        for v in self.get_vars(cat):
            if v.word is word:
                return True
        else:
            return False

    def has_dep(self, word):
        if self.has_head(word):
            return False
        for r, a, s, k in self.deconstruct():
            if self.has_head(word, a):
                return True
        return False

    def add_head(self, word):
        s_vars = self.get_vars()
        #assert len(s_vars) == 1
        for v in s_vars:
            # Sadly this fails too often :(
            # When it does it indicates a real problem, but the problems
            # are quite difficult to solve...
            #assert not v.word
            v.word = word

    def heads(self, cat=None):
        if cat is None:
            cat = self
        return sorted(set([v.word for v in self.get_vars(cat) if v.word]))

    def deconstruct(self):
        for r, a, s, k in self.category.deconstruct():
            k = dict(k)
            k['arg_global_vars'] = self.get_vars(a)
            yield r, a, s, k


    def cats_at_global(self, global_var):
        """
        Find all cats whose vars map to this var's value.
        Can't simply have a reverse index, because var's values change
        on unification
        """
        cats = set()
        val = global_var.val
        for cat_var, var_set in self._var_table.items():
            for var in var_set:
                if var.val == val:
                    for cat in self.cats_by_var[cat_var]:
                        cats.add(cat)
        return cats

    def all_globals(self):
        global_vars = set()
        for var_set in self._var_table.values():
            global_vars.update(v.get_ref() for v in var_set)
        return global_vars

    def map_letters_to_words(self):
        """
        Return a dictionary mapping letter-variables e.g. _, Y, Z
        to word sets, e.g. {'_': set(Pierre, Holly)}, where
        Pierre and Holly are CCGLeaf instances
        """
        mapping = {}
        for var, cats in self.cats_by_var.items():
            letter_var = ccg.category.VARS[var]
            heads = self.heads(cats[0])
            mapping[letter_var] = heads
        return mapping

    def add_srl_annot_from_srl_string(self, srl_annot_str):
        """
        Populate the srl_annot set with triples from an 
        srl_string. srl_strings look like X'P:A0'Y_X'P:A1'Z
        """
        assert not self.srl_annot, '%s %s' % (self.srl_annot, self.annotated)
        if srl_annot_str == '@':
            return None
        for srl_triple in srl_annot_str.split('_'):
            if not srl_triple:
                continue
            srl_triple = srl_triple.replace('X', '_')
            srl_triple = srl_triple.replace('E_T', 'EXT')
            head_letter, label, child_letter = srl_triple.split("'")
            head_var = ccg.category.VARS.index(head_letter)
            child_var = ccg.category.VARS.index(child_letter)
            if head_var not in self._var_table or child_var not in self._var_table:
                err = "Var not found from srl_string %s for cat %s"
                raise StandardError, err % (srl_string, self.annotated)
            srl_tuple = tuple(srl_triple.split("'"))
            self.srl_annot.add(srl_tuple)



    def convert_hlds_to_srl_annot(self):
        """
        For each SRL label bound to the category, print
        X label Y, where X and Y are the local variables
        for the head and child.
        """
        labels = set()
        for var, srl_labels in self.hlds_parents.items():
            for cat in self.cats_at_global(var):
                for label in srl_labels:
                    # Child of hlds_parents is always own lexical variable
                    labels.add((ccg.category.VARS[cat.var], label, '_'))
        for var, srl_labels in self.hlds_children.items():
            for cat in self.cats_at_global(var):
                for label in srl_labels:
                    # Parent of hlds_children is always own lexical variable
                    labels.add(('_', label, ccg.category.VARS[cat.var]))
        for var1, label, var2 in self.hlds_passed:
            for cat1 in self.cats_at_global(var1):
                for cat2 in self.cats_at_global(var2):
                    labels.add((ccg.category.VARS[cat1.var], label,
                                ccg.category.VARS[cat2.var]))
        self.srl_annot = labels


    annot_strip_re = re.compile(r'<\d>')
    var_find_re = re.compile(r'(?<={)[A-Z]')
    def srl_string(self):
        """
        Create an annotated string referencing semantic roles, and
        markedup entries for the role dependencies
        """
        triple_strs = ["'".join(triple).replace('_', 'X') for triple in
                       self.srl_annot]
        triple_strs.sort()
        stag_annot =  '_'.join(triple_strs)
        stag_str = '%s@%s' % (self.string, stag_annot)
        seen_vars = set()
        roles = []
        for head, label, child in self.srl_annot:
            if head == '_' and child == '_':
                roles.append(('_', label, ' %l %l'))
                continue
            elif head == '_':
                var = child
                lf = '%l %f'
            elif child == '_':
                var = head
                lf = '%f %l'
            else:
                raise Exception
            seen_vars.add(var)
            roles.append((var, label, lf))
        for var, cats in self.cats_by_var.items():
            var = ccg.category.VARS[var]
            if var == 0 or var in seen_vars:
                continue
            for cat in cats:
                if cat.arg_idx:
                    seen_vars.add(var)
                    roles.append((var, 'ignore', ''))
        var_to_args = {}
        for v in self.var_find_re.findall(self.annotated):
            if v in seen_vars:
                var_to_args.setdefault(v, len(var_to_args) + 1)
        roles = ['%d %s %s' % (var_to_args.get(v, 0), l, lf) for v, l, lf in roles]
        roles.sort()
        annotated = self.annot_strip_re.sub('', self.annotated)
        # Add argument numbers to string
        # We need to do the replacement at the rightmost point,
        # so reverse the string and add the replacement backwards
        annotated = ''.join(reversed(annotated))
        # Remove the *'s, as they're irrelevant to us
        # Um why do we need the rightmost point?
        for var, arg_num in var_to_args.items():
            var_annot = '}%s{' % var
            #var_annot = '{%s}' % var
            assert var_annot in annotated, annotated + ' ' + var_annot
            var_arg = ('>%d<' % arg_num) + var_annot
            #var_arg = '%s<%d>' % (var_annot, arg_num)
            annotated = annotated.replace(var_annot, var_arg, 1)
        annotated = annotated.replace('*', '')
        annotated = ''.join(reversed(annotated)) # Unreverse now that we're done
        # Append the @ annotation to the annotated string
        annotated = '%s@%s' % (annotated, stag_annot)
        return len(var_to_args), stag_str, annotated, roles
    
    def srl_deps_from_annot(self):
        var_map = dict((var, i) for i, var in enumerate(ccg.category.VARS))
        for head_var, label, child_var in sorted(self.srl_annot):
            head_globals = self._var_table[var_map[head_var]]
            child_globals = self._var_table[var_map[child_var]]
            for head_global in head_globals:
                for child_global in child_globals:
                    if head_global.word and child_global.word:
                        yield head_global.word, label, child_global.word


class Variable(object):
    _next = 0
    def __init__(self):
        Variable._next += 1
        self._val = Variable._next
        self._ref = None
        self._word = None

    def __eq__(self, other):
        return self.val == other.val

    def __ne__(self, other):
        return not self == other

    def __cmp__(self, other):
        return cmp(self.val, other.val)

    def __hash__(self):
        return hash(self.val)

    @property
    def val(self):
        return self.get_ref()._val
    
    @property
    def word(self):
        return self.get_ref()._word

    @word.setter
    def word(self, word):
        self.get_ref()._word = word

    def get_ref(self):
        var = self
        while var._ref is not None:
            var = var._ref
        return var

    def __str__(self):
        ref = self.get_ref()
        if ref._word:
            return ref._word.text
        else:
            return 'v%d' % ref._val

    def __repr__(self):
        return str(self)

    def unify(self, other):
        if self is other:
            return None
        self_ref = self.get_ref()
        other_ref = other.get_ref()
        if self_ref is other_ref:
            return None
        ### nicky_random_debugging_destruction - commented out:
        ### wsj_0023.3 (percent) breaks with this assert statement. 33 % of ...
        ### assert not (self_ref._word and other_ref._word)
        other_ref._ref = self_ref
        if other_ref._word and not self_ref._word:
            self_ref._word = other_ref._word
        if self_ref._word and not other_ref._word:
            other_ref._word = self_ref._word


def replace_result(scat, new_res):
    assert scat.is_complex
    arg = scat.argument
    var_map = {}
    res_vars = new_res.cats_by_var
    next_var = max(res_vars) + 1
    for var in arg.cats_by_var:
        if var in res_vars and var not in var_map:
            var_map[var] = next_var
            next_var += 1
    arg = ccg.rules.remap_vars(arg, var_map)
    new_cat = ccg.category.Category(new_res, scat.slash, arg, **scat.kwargs)
    return SuperCat(new_cat)

def replace_inner_result(scat, new_res):
    raise Exception("Not implemented yet")

def add_args(res, args, reorder = False):
    if reorder:
        res, args = reorder_args(res, args)
    for arg, slash, kwargs in args:
        if 'arg_global_var' in kwargs:
            global_var = kwargs.pop('arg_global_var')
        else:
            global_var = None
        res = add_arg(res, slash, arg, **kwargs)
        if global_var:
            # Unify the variable with the one passed in
            for var in res.get_vars(res.argument):
                var.unify(global_var)
    assert res.var == 0
    return res

def reorder_args(res, args):
    # Order args so that, for non-adjunct args, backward args are always added
    # first.
    backward = []
    forward = []
    for arg, slash, kwargs in args:
        #if kwargs.get('var', res.var) != res.var or kwargs.get('hat'):
        #    res = ccg.category.Category(res, slash, arg, **kwargs)
        if slash == '/':
            forward.append((arg, slash, kwargs))
        else:
            backward.append((arg, slash, kwargs))
    return res, backward + forward



def add_arg(result, slash, arg, revar=True, **kwargs):
    # Revar means to assume the extra arg is not coindexed to something
    if revar:
        arg = change_kwarg(arg, var=result.next_var)
    category = ccg.category.Category(result, slash,
                                     arg, **kwargs)
    new_scat = SuperCat(category)
    if hasattr(result, 'bind_vars'):
        new_scat.bind_vars(result, new_scat.result, result.category)
    if hasattr(arg, 'bind_vars'):
        new_scat.bind_vars(arg, new_scat.argument, arg.category)
    return new_scat

def make_adjunct(cat, slash, force_dep=True):
    # Decide which category to base adjunct on
    if cat.is_complex:
        for res, arg, s, _ in reversed(list(cat.deconstruct())):
            if force_dep and res.var != cat.var:
                continue
            # Don't reduce (S\NP)|(S\NP) to S|S
            if res.var == 0 and \
            not (res == 'S' and arg == 'NP' and s == '\\'):
                cat = res
                break
        else:
            cat = res if not force_dep else cat
    var_map = {0: cat.next_var}
    new_cat = ccg.rules.remap_vars(cat, var_map)
    new_cat = ccg.rules.strip_features(new_cat)
    return SuperCat(ccg.category.Category(new_cat, slash, new_cat, var=0))

def change_kwarg(cat, **kwargs):
    cat_kwargs = cat.kwargs.copy()
    cat_kwargs.update(kwargs)
    new_cat = ccg.category.Category(cat.result, cat.slash, cat.argument,
                                    **cat_kwargs)
    if hasattr(cat, 'bind_vars'):
        new_scat = SuperCat(new_cat)
        new_scat.bind_vars(cat, new_cat, cat.category)
        return new_scat
    else:
        return new_cat

def type_raise(t_cat, slash, arg_cat):
    t_cat = ccg.rules.strip_features(t_cat)
    next_var = arg_cat.next_var
    var_map = {}
    for var in t_cat.cats_by_var:
        var_map.setdefault(var, len(var_map.keys()) + next_var)
    t_cat = ccg.rules.remap_vars(t_cat, var_map)
    inner_slash = '\\' if  slash == '/' else '/'
    argument = add_arg(t_cat, inner_slash, arg_cat, var=t_cat.var, revar=False)
    return add_arg(t_cat, slash, argument, var=arg_cat.var)
