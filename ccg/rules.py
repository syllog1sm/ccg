from collections import defaultdict

from ccg.category import from_string, Category
import ccg
import re

VARS = ['_', 'Y', 'Z', 'W', 'V', 'U', 'T', 'S']
_ARG_IDX_RE = re.compile(r'<\d>')
MAX_COMP_DEPTH = 3


class Production(object):
    """
    A CCG production rule. Tracks combinators used,
    unification, and manages change propagation.
    """
    combinators = ['add_conj', 'do_conj',
                   'fapply', 'bapply', 'bcomp', 'fcomp',
                   'bxcomp', 'fxcomp',
                   'left_punct', 'right_punct', 'comma_conj']
    def __init__(self, left, right, parent=None, rule=None):
        assert left
        self.left = left
        self.right = right
        self._y = None
        self._x = None
        if rule:
            combinator = getattr(self, rule)
            result, depth = combinator(left, right)
        else:
            rule, result, depth = self.get_rule(left, right, parent)
            self.depth = depth
        self.result = result
        if not right:
            pass
        elif left.is_adjunct and rule.startswith('f') and self._y and \
            self._y.var == right.var:
            rule = 'fadjunct'
        elif right.is_adjunct and rule.startswith('b') and self._y and \
                self._y.var == left.var:
            rule = 'badjunct'
        elif left.is_type_raise and rule.startswith('f'):
            rule = 'ftraise_comp'
        elif right.is_type_raise and rule.startswith('b'):
            rule = 'btraise_comp'
        self.rule = rule
        self.parent = parent
        self.force_dep = True

    def __str__(self):
        return '%s %s --> %s (%s)' % (self.left, self.right, self.parent,
                                      self.rule)

    def get_rule(self, left, right, parent = None):
        if right is None:
            assert parent
            unary_rules = [('traise', self.traise), ('unary', self.unary)]
            for rule, combinator in unary_rules:
                result, depth = combinator(parent, left)
                if result and parent.exact_eq(result):
                    return rule, result, depth
            else:
                return 'unary', None, 0
        for rule in self.combinators:
            combinator = getattr(self, rule)
            result, depth = combinator(left, right)
            if result and ((not parent) or parent.exact_eq(result)):
                return rule, result, depth
        else:
            if parent:
                result, depth = self.binary(left, right, parent)
                if result and parent.exact_eq(result):
                    return 'binary', result, 0
            return 'invalid', parent, 0


    def replace(self, new):
        if not isinstance(new, ccg.scat.SuperCat):
            new = ccg.scat.SuperCat(new)
        assert self.parent
        if self.rule == 'fapply':
            left, right = self._apply_replace(self.left, self.right, new)
        elif self.rule == 'bapply':
            right, left = self._apply_replace(self.right, self.left, new)
        elif self.rule == 'fcomp' or self.rule == 'fxcomp':
            left, right = self._comp_replace(self.left, self.right, new)
        elif self.rule == 'bcomp' or self.rule == 'bxcomp':
            right, left = self._comp_replace(self.right, self.left, new)
        elif self.rule == 'fadjunct':
            left, right = self._adjunct_replace(self.left, self.right, new)
        elif self.rule == 'badjunct':
            right, left = self._adjunct_replace(self.right, self.left, new)
        elif self.rule == 'left_punct':
            left = self.left
            right = new
        elif self.rule == 'ftraise_comp':
            left, right = self._traise_comp_replace(self.left, self.right, new)
        elif self.rule == 'btraise_comp':
            right, left = self._traise_comp_replace(self.right, self.left, new)
        elif self.rule == 'right_punct':
            right = self.right
            left = new
        elif new.conj and \
                (self.rule == 'add_conj' or self.rule == 'comma_conj'):
            left = self.left
            right = ccg.scat.change_kwarg(new, conj=False)
        elif self.rule == 'do_conj':
            left = new
            right = ccg.scat.change_kwarg(new, conj=True)
        elif self.rule == 'traise':
            left = self._traise_replace(self.left, new)
            right = None
        elif self.rule == 'unary':
            left = self.left
            right = self.right
        elif self.rule == 'invalid' or self.rule == 'unary':
            left = self.left
            right = self.right
        else:
            raise Exception(self.rule)
        self.left = left
        self.right = right
        self.parent = new
        return left, right

    def _apply_replace(self, func, arg, new):
        # Special case for determiners where new has grown an argument
        determiners = ['NP/N', 'NP/(N/PP)', 'PP/NP']
        if func in determiners and new.is_complex and \
           new.inner_result == self.parent.inner_result:
            args = [(a, s, k) for r, a, s, k in new.deconstruct()]
            new_arg = ccg.scat.add_args(arg, args)
            return func, new_arg
        if func.result.feat_var: # Preserve feature passing
            new = ccg.scat.change_kwarg(new, feature='',
                                        feat_var=func.result.feat_var)
        new_func = ccg.scat.replace_result(func, new)
        return new_func, arg

    def _adjunct_replace(self, func, arg, new):
        new_func = ccg.scat.make_adjunct(new, func.slash, True)
        return new_func, new
            
    def _comp_replace(self, func, arg, new):
        # If new isn't complex we can't compose. Just use application.
        if not new.is_complex:
            functor = ccg.scat.add_arg(new, func.slash, arg, **func.kwargs)
            self.rule = 'fapply'
            return functor, arg
        # Y category must be the same as before, as it's not in the parent
        # Give the argument and result the Ys they each had originally
        res_y = func.argument
        for arg_y, slash, z, _ in arg.deconstruct():
            if arg_y == res_y:
                break
        else:
            if func.argument == arg:
                res_y = arg
            else:
                raise Exception
        orig_x = func.result
        # Get the new Z (or Zs in the case of generalised comp)
        dollars = []
        for res, arg, slash, kwargs in new.deconstruct():
            dollars.append((arg, slash, kwargs))
            if res.is_adjunct:
                break
            #if res == 'S\NP':
            #    break
        else:
            # Don't accumulate arguments on adjuncts or determiners
            if func != 'NP/N' and not func.is_adjunct:
                res = new.result
                dollars = [(new.argument, new.slash, new.kwargs)]
        if orig_x.feat_var: # Preserves feature-passing
                        res = ccg.scat.change_kwarg(res, feature='',
                                        feat_var=orig_x.feat_var,
                                        var=orig_x.var)
        if func.is_adjunct:
            if new.is_adjunct:
                functor = ccg.scat.SuperCat(new)
            elif new.inner_result.var != new.var:
                if any(c == 'S\NP' for p, c in new.cats.items() if not any(p)):
                    functor = ccg.scat.make_adjunct(ccg.VP, func.slash)
                else:
                    functor = ccg.scat.make_adjunct(new.inner_result, func.slash)
            else:
                functor = ccg.scat.make_adjunct(new, func.slash)
            return functor, ccg.scat.SuperCat(new)
        functor = ccg.scat.add_arg(res, func.slash, res_y, **func.kwargs)
        dollars.reverse()
        argument = ccg.scat.add_args(arg_y, dollars)
        return functor, argument

    def _traise_replace(self, child, new):
        assert new.is_type_raise
        left = ccg.scat.SuperCat(new.argument.argument)
        new.bind_vars(new, new.argument.argument, left)
        return left

    def _traise_comp_replace(self, func, arg, new):
        # Type-raise-type-raise composition is a special case used for
        # argument cluster coordination. It's dangerous to clobber it
        # with a non-type-raised new category.
        if arg.is_type_raise and not new.is_type_raise:
            assert func.is_type_raise
            raise Exception("Should not replace raise-raise composition with"
                            "non-raised category.")
        # New == T/$
        # Func == T/(T\R)
        # Arg == (T\R)/$
        r = func.argument.argument
        dollars = []
        for t, z, slash, kwargs in new.deconstruct():
            dollars.append((z, slash, kwargs))
            if t.is_adjunct:
                break
        else:
            if not new.is_complex:
                t = new
        # Now, where do we place the R relative to the $s? Let's say we have
        # R=(/PP) and $s=[(/NP), (\NP)] (where last will be added first)
        # We could redefine T to T\NP, so that we get
        # an argument cat of (T\NP)/PP)/NP. OR, we could keep T, and get
        # ((T/PP)\NP)/NP. They're equivalent, but the latter will get
        # non-standard cats. So what we must do is check whether the slashes
        # for the last dollar and the R disagree. If they do, we should redefine
        # T to append the last dollar, which is popped.
        if dollars and dollars[-1][1] == '\\' and func.argument.slash == '/':
            last_arg, last_slash, last_kwarg = dollars.pop()
            t = ccg.scat.add_arg(t, last_slash, last_arg, **last_kwarg)
        dollars.append((r, func.argument.slash, {}))
        dollars.reverse()
        functor = ccg.scat.type_raise(t, func.slash, r)
        argument = ccg.scat.add_args(t, dollars)
        return functor, argument
        



    def fapply(self, left, right):
        if not self._check_dir(left, '/'):
            return False, 0
        return self._application(left, right)

    def bapply(self, left, right):
        if not self._check_dir(right, '\\'):
            return False, 0
        return self._application(right, left)

    def fcomp(self, left, right): # Don't do general for now
        if not self._check_dir(left, '/') or not self._check_dir(right, '/'):
            return False, 0
        return self._composition(left, right)

    def bcomp(self, left, right):
        if not self._check_dir(left, '\\') or not self._check_dir(right, '\\'):
            return False, 0
        return self._composition(right, left)

    def fxcomp(self, left, right):
        if not left.is_complex or not right.is_complex:
            return False, 0
        if not self._check_dir(left, '/'):
            return False, 0
        return self._composition(left, right, crossing=True)

    def bxcomp(self, left, right):
        if not left.is_complex and self._check_dir(right, '\\'):
            return False, 0
        return self._composition(right, left, crossing=True)

    def add_conj(self, left, right):
        """
        Multi-variables for conj is so far a failure. Make conjuncted
        constituents headed by the conjunction
        """
        if left != ccg.CONJ or right.conj:
            return False, 0
        return self._do_add_conj(left, right)

    def _do_add_conj(self, left, right):
        # This should take care of variable binding too
        scat = ccg.scat.change_kwarg(right, conj=True)
        return scat, 0

    def comma_conj(self, left, right):
        if left != ccg.COMMA and left != ccg.SEMI_COLON and left != ccg.COLON:
            return False, 0
        return self._do_add_conj(left, right)

    def do_conj(self, left, right):
        if not right.conj:
            return False, 0
        if left.conj:
            return False, 0
        new_right = ccg.scat.change_kwarg(right, conj=False)
        if not new_right.exact_eq(left):
            return False, 0
        for path, right_cat in new_right.cats.items():
            if right_cat.var > 0:
                new_right.unify_globals_at_var(left, right_cat.var,
                                               left.cats[path].var)
        for var in left.get_vars():
            new_right.add_var(0, var)
        return new_right, 0

    def left_punct(self, left, right):
        if not left.is_punct:
            return False, 0
        return right, 0

    def right_punct(self, left, right):
        if not right.is_punct:
            return False, 0
        return left, 0

    def traise(self, parent, child):
        # Type raising
        if not parent.is_complex:
            return False, 0
        if not parent.argument.is_complex:
            return False, 0
        if not parent.result.exact_eq(parent.argument.result):
            return False, 0
        if not parent.argument.argument.exact_eq(child):
            return False, 0
        result = ccg.scat.type_raise(parent.result, parent.slash, child)
        result.bind_vars(child, result.argument.argument, child.category)
        return result, 0

    def unary(self, parent, child):
        key = (parent.string, child.string)
        if key not in TypeChanging.rules:
            return False, 0
        else:
            result = ccg.scat.SuperCat(parent.category)
            bindings = TypeChanging.rules[key]
            for parent_var, child_var in bindings:
                try:
                    result.unify_globals_at_var(child, parent_var, child_var)
                except KeyError:
                    raise
            return result, 0
    
    def binary(self, left, right, parent):
        key = (parent.string, left.string, right.string)
        if key not in BinaryTypeChanging.rules:
            return False, 0
        else:
            bindings = BinaryTypeChanging.rules[key]
            result = ccg.scat.SuperCat(parent.category)
            for parent_var, left_var, right_var in bindings:
                if left_var is None:
                    assert right_var is not None
                    try:
                        result.unify_globals_at_var(
                            right, parent_var, right_var)
                    except KeyError:
                        raise
                elif right_var is None:
                    assert left_var is not None
                    try:
                        result.unify_globals_at_var(left, parent_var, left_var)
                    except KeyError:
                        raise
                else:
                    raise Exception
            return result, 0

    def _application(self, functor, argument):
        if functor.conj or argument.conj:
            return False, 0
        if functor.argument != argument:
            return False, 0
        has_bound = functor.bind_vars(argument, functor.argument, argument.category)
        if not has_bound:
            return False, 0
        result = functor.result
        c1_to_c2, c2_to_c1 = self._var_to_feats(functor.argument, argument)
        result, var_map = minimise_vars(result, c1_to_c2)
        self._x = functor.result
        self._y = argument
        result_scat = ccg.scat.SuperCat(result)
        functor.bind_vars(result_scat, functor.result, result_scat.category)
        return result_scat, 0

    def _composition(self, functor, arg, crossing = False):
        if functor.conj or arg.conj:
            return False, 0
        if not functor.is_complex or not arg.is_complex:
            return False, 0
        depth = 0
        # X/Y (Y/Z_1)/Z_2 etc
        x_y = functor.argument
        self._x = functor.result
        yz = arg
        zs = []

        while depth < MAX_COMP_DEPTH and yz.is_complex:
            zs.append((yz.argument, yz.slash, yz.kwargs.copy()))
            if yz.result != x_y:
                yz = yz.result
                depth += 1
            else:
                self._y = yz.result
                break
        else:
            return False, 0

        # For non-crossing composition, the slashes must be consistent.
        # For crossing composition, they must be inconsistent.
        if all(s == functor.slash for (arg, s, k) in zs) == crossing:
            return False, 0
        functor.bind_vars(arg, x_y, self._y)
        max_var = max(functor.cats_by_var) + 1
        arg_to_final = self._map_vars(x_y, yz.result, max_var, arg.cats_by_var)
        curr_cat = functor.result
        for z, slash, kwargs in reversed(zs):
            z = remap_vars(z, arg_to_final)
            kwargs['var'] = arg_to_final.get(kwargs.get('var', 99), max_var)
            curr_cat = Category(curr_cat, slash, z, **kwargs)

        c1_to_c2, c2_to_c1 = self._var_to_feats(functor.argument, yz.result)
        c1_to_c2.update(c2_to_c1)
        result, var_map = minimise_vars(curr_cat, c1_to_c2)

        # Bind the global variables
        scat = ccg.scat.SuperCat(result)

        # Take outer var from arg
        scat.unify_globals_at_var(arg, 0)

        arg_res = arg
        for result, z, _, _ in scat.deconstruct():
            scat.bind_vars(arg, z, arg_res.argument)
            if result == functor.result:
                scat.bind_vars(functor, result, functor.result)
                break
            arg_res = arg_res.result
        return scat, depth

    def _check_dir(self, cat, slash):
        if not cat.is_complex:
            return False
        if cat.slash != slash:
            return False
        return True

    def _map_vars(self, func_u, arg_u, next_var, arg_vars):
        # Map variables from argument to functor
        arg_to_final = {}
        for path, acat in arg_u.cats.items():
            fcat = func_u.cats[path]
            arg_to_final[acat.var] = fcat.var
        for var in arg_vars:
            if var not in arg_to_final:
                arg_to_final[var] = next_var
                next_var += 1
        return arg_to_final

    def _var_to_feats(self, cat1, cat2):
        """
        Map feature variables to feature values for the unified pieces
        """
        c1_to_c2 = {}
        c2_to_c1 = {}
        for path, sub1 in cat1.cats.items():
            sub2 = cat2.cats[path]
            if sub1.feat_var and sub2.feature:
                c1_to_c2[sub1.feat_var] = sub2.feature
            elif sub2.feat_var and sub1.feature:
                c2_to_c1[sub2.feat_var] = sub1.feature
        return c1_to_c2, c2_to_c1

class TypeChanging(object):
    # Note which variables to bind
    rules = {
        ('NP', 'N'): [(0, 0)],
        ('NP\NP', 'S[dcl]\NP'): [(0, 0), (1, 1)],
        ('NP\NP', 'S[pss]\NP'): [(0, 0), (1, 1)],
        ('NP\NP', 'S[adj]\NP'): [(0, 0), (1, 1)],
        ('NP\NP', 'S[ng]\NP'): [(0, 0), (1, 1)],
        ('NP\NP', 'S[to]\NP'): [(0, 0), (1, 1)],
        ('N\N', 'S[pss]\NP'): [(0, 0), (1, 1)],
        ('N\N', 'S[ng]\NP'): [(0, 0), (1, 1)],
        ('N\N', 'S[adj]\NP'): [(0, 0), (1, 1)],
        ('N\N', 'S[dcl]/NP'): [(0, 0), (1, 1)],
        ('(S\NP)\(S\NP)', 'S\NP'): [(0, 0), (2, 1)],
        ('(S\NP)\(S\NP)', 'S[ng]\NP'): [(0, 0), (2, 1)],
        ('(S\NP)/(S\NP)', 'S\NP'): [(0, 0), (2, 1)],
        ('NP\NP', 'S[dcl]/NP'): [(0, 0), (1, 1)],
        ('NP', 'S\NP'): [(0, 0)],
        ('S/S', 'S\NP'): [(0, 0)],
        ('NP\NP', 'S'): [(0, 0)],
        ('S/S', 'S\NP'): [(0, 0)],
        ('S/S', 'S\NP'): [(0, 0)],
        ('NP/PP', 'N/PP'): [(0, 0), (1, 1)],
        ('(NP/PP)/PP', '(N/PP)/PP'): [(0, 0), (1, 1), (2, 2)],
        ('((NP/PP)/PP)/PP', '((N/PP)/PP)/PP'): [(0, 0), (1, 1), (2, 2), (3, 3)]
        }

class BinaryTypeChanging(object):
    rules = {
        # For rebanking
        ('NP\NP', ',', 'S[pss]\NP'): [(0, None, 0), (1, None, 1)],
        ('NP\NP', ',', 'S[ng]\NP'): [(0, None, 0), (1, None, 1)],
        ('NP\NP', ',', 'S[adj]\NP'): [(0, None, 0), (1, None, 1)],
        ('NP\NP', ',', 'S[dcl]\NP'): [(0, None, 0), (1, None, 1)],
        ('NP\NP', ',', 'S[dcl]/NP'): [(0, None, 0), (1, None, 1)],
        ('S/S', 'S[dcl]/S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('(S\NP)\(S\NP)', ',', 'NP'): [(0, None, 0)],
        ('(S\NP)/(S\NP)', 'S[dcl]/S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('(S\NP)\(S\NP)', 'S[dcl]/S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('S/S', 'NP', ','): [(0, 0, None)],
        ('S\S', 'S[dcl]/S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('S/S', 'S[dcl]\S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('S[adj]\NP[conj]', 'conj', 'PP'): [(0, None, 0)],
        ('S[adj]\NP[conj]', 'conj', 'NP'): [(0, None, 0)],
        ('NP[conj]', 'conj', 'S[adj]\NP'): [(0, None, 0)],
        ('S/S', 'S[dcl]', ','): [(0, 0, None)],
        ('(S\NP)/(S\NP)', 'S[dcl]\S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('NP\NP', 'S[dcl]/S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('S[adj]\NP[conj]', 'conj', 'S[ng]\NP'): [(0, None, 0), (1, None, 1)],
        ('(S\NP)\(S\NP)', 'S[dcl]\S[dcl]', ','): [(0, 0, None), (1, 1, None)],
        ('S[pss]\NP[conj]', 'conj', 'S[ng]\NP'): [(0, None, 0), (1, None, 1)]
    }


def fapply(left, right):
    return Production(left, right, rule='fapply').result

def bapply(left, right):
    return Production(left, right, rule='bapply').result

def fcomp(left, right):
    return Production(left, right, rule='fcomp').result

def bcomp(left, right):
    return Production(left, right, rule='bcomp').result

def fxcomp(left, right):
    return Production(left, right, rule='fxcomp').result

def bxcomp(left, right):
    return Production(left, right, rule='bxcomp').result

def add_conj(left, right):
    return Production(left, right, rule='add_conj').result

def do_conj(left, right):
    return Production(left, right, rule='do_conj').result

def comma_conj(left, right):
    return Production(left, right, rule='comma_conj').result

def left_punct(left, right):
    return Production(left, right, rule='left_punct').result

def right_punct(left, right):
    return Production(left, right, rule='right_punct').result

def traise(left, parent):
    return Production(left, None, parent).result

def binary(left, right, parent):
    return Production(left, right, parent).result

def minimise_vars(cat, fvars, seen_vars = None, fvar_freqs = None):
    def _kwargs(cat):
        # nonlocal seen_vars, feat_vars, feat_vars
        kwargs = cat.kwargs.copy()
        kwargs['var'] = seen_vars[cat.var]
        kwargs['arg_idx'] = ''
        if cat.feat_var in fvars:
            kwargs['feat_var'] = ''
            kwargs['feature'] = fvars[cat.feat_var]
        elif fvar_freqs[cat.feat_var] == 1:
            kwargs['feat_var'] = ''
        return kwargs

    # Return the cat unchanged if there are no gaps in the vars
    # and we do not have a variable map, and last var is head
    if not seen_vars and not fvars and cat.var == 0:
        vars = cat.cats_by_var.keys()
        if len(vars) == max(vars) + 1:
            return cat, {}

    if seen_vars is None:
        seen_vars = defaultdict(lambda: len(seen_vars))
        seen_vars[cat.var] # Maps outer var to 0
        fvar_freqs = defaultdict(int)
        for c in cat.cats.values():
            if c.feat_var and c.feat_var not in fvars:
                fvar_freqs[c.feat_var] += 1

    if not cat.is_complex:
        return Category(cat.cat, **_kwargs(cat)), seen_vars

    cats = [(p, c) for p, c in cat.cats.items() if not any(p)]
    cats.sort()
    cats.reverse()
    inner = cats.pop(0)[1]
    curr_cat = Category(inner.cat, **_kwargs(inner))
    for path, cat in cats:
        if cat.argument.is_complex:
            arg, seen_vars = minimise_vars(cat.argument, fvars, seen_vars,
                                           fvar_freqs)
        else:
            arg = Category(cat.argument.cat, **_kwargs(cat.argument))
        curr_cat = Category(curr_cat, cat.slash, arg, **_kwargs(cat))
    return curr_cat, seen_vars

def remap_vars(cat, var_map):
    if not var_map:
        return cat
    kwargs = cat.kwargs.copy()
    kwargs['var'] = var_map.get(cat.var, max(var_map.values()) + 1)
    if cat.is_complex:
        result = remap_vars(cat.result, var_map)
        argument = remap_vars(cat.argument, var_map)
        return Category(result, cat.slash, argument, **kwargs)
    else:
        try:
            return Category(cat.cat, **kwargs)
        except:
            print cat.cat
            print kwargs
            raise

def strip_features(cat):
    def next_var():
        if not feat_map:
            return '[X]'
        else:
            return VARS[len(feat_map.keys())]
    feat_map = {}
    for c in cat.cats.values():
        if c.feature and c.feature not in feat_map:
            feat_map[c.feature] = next_var()
        assert not (c.feat_var and c.feat_var in feat_map)
    return feats_to_vars(cat, feat_map)

def feats_to_vars(cat, feat_map):
    if not feat_map:
        return cat
    kwargs = cat.kwargs.copy()
    if cat.feature and cat.feature != '[adj]':
        kwargs['feat_var'] = feat_map[cat.feature]
        kwargs['feature'] = ''
    if cat.is_complex:
        result = feats_to_vars(cat.result, feat_map)
        argument = feats_to_vars(cat.argument, feat_map)
        return ccg.scat.SuperCat(ccg.category.Category(result, cat.slash,
                                                       argument, **kwargs))
    else:
        return ccg.scat.SuperCat(ccg.category.Category(cat.cat, **kwargs))

