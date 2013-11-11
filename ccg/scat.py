from collections import defaultdict

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
            if var == 0 and category.conj:
                var_id = ConjVariable()
            else:
                var_id = Variable()
            var_table[var] = var_id
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
            global_var = self._var_table[var]
            global_str = '{%s}' % global_var
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
        for path, self_piece in self_cat.cats.items():
            other_piece = other_cat.cats[path]
            self_global = self.get_var(self_piece)
            other_global = other.get_var(other_piece)
            self_global.unify(other_global)

    def conjunct_var_to(self, other):
        self_var = self.get_var().get_ref()
        other_var = other.get_var().get_ref()
        other_var.add(self_var)

    def add_hlds_child(self, relation, global_var):
        """
        Set a child dependency
        """
        self.hlds_children[global_var].add(relation)

    def add_hlds_parent(self, relation, global_var):
        self.hlds_parents[global_var].add(relation)

    def add_hlds_passed(self, parent_var, relation, child_var):
        self.hlds_passed.add((parent_var, relation, child_var))
        
   
    def get_var(self, cat=None):
        if cat is None:
            cat = self
        return self._var_table[cat.var]

    def get_var2(self, cat=None):
        if cat is None:
            cat = self
        return self._var_table[cat.var2]


    def cats_at_global(self, global_var):
        """
        Find all cats whose vars map to this var's value.
        Can't simply have a reverse index, because var's values change
        on unification
        """
        cats = set()
        val = global_var.val
        for cat_var, var in self._var_table.items():
            if var.val == val:
                for cat in self.cats_by_var[cat_var]:
                    cats.add(cat)
        return cats

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

    def srl_string(self):
        return '_'.join('|'.join(triple).replace('_', 'X')
                        for triple in self.srl_annot)
    
    def srl_deps_from_annot(self):
        var_map = dict((var, i) for i, var in enumerate(ccg.category.VARS))
        for head_var, label, child_var in sorted(self.srl_annot):
            head_global = self._var_table[var_map[head_var]]
            child_global = self._var_table[var_map[child_var]]
            if head_global.word and child_global.word:
                yield head_global.word, label, child_global.word



class Variable(object):
    _next = 0
    def __init__(self):
        Variable._next += 1
        self._val = Variable._next
        self._ref = None
        self._word = None
        self._conjuncted = set()

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
        if ref._conjuncted:
            # But what if the refs of these words are something
            # else? Can't just take 'ref', because that points
            # to the conjunction node!
            # In other words, let's say we have var A as
            # variable, and var C as the conjunction.
            # Var A points to var C(A,D). But then what if
            # var A unifies with var B, such that A->B->C?
            # Now we have var C(A,D) when really we want
            # var C(B,D) --- but we can't just follow
            # A->B without getting A->B->C.
            return ','.join(other._word.text
                            if other._word else other._val
                            for other in sorted(ref._conjuncted))
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
        if isinstance(other_ref, ConjVariable):
            assert self_ref not in other_ref.conjuncted
            self_ref._ref = other_ref
        else:
            assert other_ref not in self_ref._conjuncted
            other_ref._ref = self_ref
        if other_ref._word and not self_ref._word:
            self_ref._word = other_ref._word
        if self_ref._word and not other_ref._word:
            other_ref._word = self_ref._word

class ConjVariable(Variable):
    def __init__(self):
        Variable.__init__(self)
        self._conjuncted = set()

    @property
    def conjuncted(self):
        return self.get_ref()._conjuncted

    def add(self, other):
        self.conjuncted.add(other.get_ref())

    def unify(self, other):
        if self is other:
            return None
        self_ref = self.get_ref()
        other_ref = other.get_ref()
        if self_ref is other_ref:
            return None
        if isinstance(other_ref, ConjVariable):
            self_ref._ref = other_ref
        else:
            other_ref._ref = self_ref
        if other_ref._word and not self_ref._word:
            self_ref._word = other_ref._word
        if self_ref._word and not other_ref._word:
            other_ref._word = self_ref._word
        self_ref._conjuncted.update(other_ref._conjuncted)
        other_ref._conjuncted.update(self_ref._conjuncted)
  

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
        res = ccg.category.Category(res, slash, arg, **kwargs)
    assert res.var == 0
    return SuperCat(res)

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



def add_arg(result, slash, arg, **kwargs):
    # Assume that extra arg is never coindexed to something
    new_arg = change_kwarg(arg, var=result.next_var)
    category = ccg.category.Category(result, slash,
                                     new_arg, **kwargs)
    new_scat = SuperCat(category)
    if hasattr(result, 'bind_vars'):
        new_scat.bind_vars(result, new_scat.result, result.category)
    if hasattr(new_arg, 'bind_vars'):
        new_scat.bind_vars(new_arg, new_scat.argument, new_arg.category)
    return new_scat

def make_adjunct(cat, slash, force_dep=True):
    # Decide which category to base adjunct on
    if cat.is_complex:
        for res, arg, s, hat in reversed(list(cat.deconstruct())):
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
    argument = add_arg(t_cat, inner_slash, arg_cat, var=t_cat.var)
    return add_arg(t_cat, slash, argument, var=arg_cat.var)
