"""
Test category replacement, for changeLabel
"""
import unittest
import os.path
import random

import ccg.scat
import ccg.rules
import ccg.lexicon
import ccg.grammar

ccg.lexicon.load()

class TestReplace(unittest.TestCase):
    def test_fapply_basic(self):
        c1 = ccg.scat.SuperCat('PP/NP')
        c2 = ccg.scat.SuperCat('NP')
        parent = ccg.scat.SuperCat('PP')
        production = ccg.rules.Production(c1, c2, parent)
        production.replace(ccg.scat.SuperCat('NP'))
        assert production.left == 'NP/NP'
        assert production.left.annotated == '(NP{_}/NP{Y}<1>){_}'
        
    def test_fapply_adjunct(self):
        c1 = ccg.scat.SuperCat('N/N')
        c2 = ccg.scat.SuperCat('N')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('PP'))
        assert production.left == 'PP/PP'
        assert production.left.annotated == '(PP{Y}/PP{Y}){_}'
        assert production.right == 'PP'
        
    def test_fapply_adjunct_feature(self):
        c1 = ccg.scat.SuperCat('S/S')
        c2 = ccg.scat.SuperCat('S[dcl]')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('N[num]'))
        assert production.left.annotated == '(N[X]{Y}/N[X]{Y}){_}'
        assert production.right == 'N[num]'
        assert production.parent == 'N[num]'
        assert ccg.rules.fapply(production.left, production.right) == 'N[num]'

    def test_fcomp_adjunct(self):
        c1 = ccg.scat.SuperCat('NP/NP')
        c2 = ccg.scat.SuperCat('NP/N')
        parent = ccg.scat.SuperCat('NP/N')
        production = ccg.rules.Production(c1, c2, parent=parent)
        production.replace('(S[adj]\NP)/(S[adj]\NP)')
        production.replace(parent)
        self.assertEqual(production.left, c1)
        self.assertEqual(production.right, c2)

    def test_bapply_basic(self):
        c1 = ccg.scat.SuperCat('NP')
        c2 = ccg.scat.SuperCat('S[dcl]\NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('S[em]'))
        assert production.right == 'S[em]\NP'
        assert production.right.annotated == '(S[em]{_}\NP{Y}<1>){_}'

    def test_fcomp_basic(self):
        c1 = ccg.scat.SuperCat('NP/N')
        c2 = ccg.scat.SuperCat('N/N')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        assert production.rule == 'fcomp'
        production.replace(ccg.scat.SuperCat('PP/N'))
        assert production.left == 'PP/N'
        c1 = ccg.scat.SuperCat('NP/N')
        c2 = ccg.scat.SuperCat('(N/PP)/S[em]')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('(NP/S[em])/PP'))
        assert production.left == 'NP/N'
        assert production.right == '(N/S[em])/PP'
        c1 = ccg.scat.SuperCat('NP/N')
        c2 = ccg.scat.SuperCat('(N/PP)/S[em]')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('((PP{_}/PP{Y}){_}/S[em]{Z}){_}'))
        self.assertEqual(production.left, 'PP/N')
        self.assertEqual(production.right, '(N/PP)/S[em]')

    def test_fcomp2(self):
        c1 = ccg.scat.SuperCat('((S[dcl]\NP)/PP)/PP')
        c2 = ccg.scat.SuperCat('PP/NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        assert production.rule == 'fcomp'
        production.replace(ccg.scat.SuperCat('((S[ng]\NP)/NP)/NP'))
        self.assertEqual(production.right, 'PP/NP')

    def test_bxcomp(self):
        # (NP\NP)/NP NP\NP --> (NP\NP)/NP
        # (((S[dcl]\NP)/(S[to]\NP))/PP)/NP
        c1 = ccg.scat.SuperCat('(NP\NP)/NP')
        c2 = ccg.scat.SuperCat('NP\NP')
        production = ccg.rules.Production(c1, c2, rule='bxcomp')
        production.parent = production.result
        assert production.parent == '(NP\NP)/NP'
        production.replace('(((S[dcl]\NP)/(S[to]\NP))/PP)/NP')
        self.assertEqual(production.left, '(((S[dcl]\NP)/(S[to]\NP))/PP)/NP')
        self.assertEqual(production.right, '(S\NP)\(S\NP)')
        production.replace('(NP\NP)/NP')
        print production.rule
        self.assertEqual(production.left.string, c1.string)
        self.assertEqual(production.right.string, c2.string)



    def test_fcomp_aux(self):
        # (S[dcl]\NP)/(S[ng]\NP) (S[ng]\NP)/NP --> (S[dcl]\NP)/NP
        # to:
        # (S/S)/(S[ng]\NP) (S[ng]\NP)/S[dcl] --> (S/S)/S[dcl]
        c1 = ccg.scat.SuperCat('(S[dcl]\NP)/(S[ng]\NP)')
        c2 = ccg.scat.SuperCat('(S[ng]\NP)/NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        assert production.rule == 'fcomp'
        assert production.parent == '(S[dcl]\NP)/NP'
        production.replace(ccg.scat.SuperCat('(S/S)/S[dcl]'))
        self.assertEqual(production.left, '(S/S)/(S[ng]\NP)')
        self.assertEqual(production.right, '(S[ng]\NP)/S[dcl]')
    
    def test_bcomp_traise(self):
        # ((S[dcl]\NP)/PP)/NP (S\NP)\((S\NP)/PP) --> (S[dcl]\NP)/NP
        # (((S[b]\NP)/PP)/(S[b]\NP))/NP (S\NP)\((S\NP)/PP)
        # --> ((S[b]\NP)/(S[b]\NP))/NP
        c1 = ccg.scat.SuperCat('((S[dcl]\NP)/PP)/NP')
        c2 = ccg.scat.SuperCat('(S\NP)\((S\NP)/PP)')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('((S[b]\NP)/(S[b]\NP))/NP'))
        self.assertEqual(production.left, '(((S[b]\NP)/PP)/(S[b]\NP))/NP')

    def test_badjunct(self):
        # (S[pt]\NP)/S[em] (S\NP)\(S\NP) --> (S[pt]\NP)/S[em]
        # PP
        # New left: PP
        # New right: PP\PP
        # (S[pt]\NP)/S[em] (S[pt]\NP)/S[em]
        # ((S\NP)/S)\((S\NP)/S) (S\NP)\(S\NP)
        # badjunct
        c1 = ccg.scat.SuperCat('(S[pt]\NP)/S[em]')
        c2 = ccg.scat.SuperCat('(S\NP)\(S\NP)')
        production = ccg.rules.Production(c1, c2, rule='bxcomp')
        production.parent = production.result
        assert production.rule == 'badjunct'
        production.replace(ccg.scat.SuperCat('PP'))
        production.replace(ccg.scat.SuperCat('(S[pt]\NP)/S[em]'))
        self.assertEqual(production.left, c1)
        self.assertEqual(production.right.string, c2.string)



    def test_make_adjunct(self):
        cat = ccg.scat.SuperCat('N/N')
        stripped = ccg.rules.strip_features(cat)
        self.assertEqual(stripped.annotated, '(N[X]{Y}/N[X]{Y}<1>){_}')
        adjunct = ccg.scat.make_adjunct(cat, '/')
        self.assertEqual(adjunct, '(N/N)/(N/N)')
        
    def test_punct(self):
        c1 = ccg.scat.SuperCat('PP/NP')
        c2 = ccg.scat.SuperCat("RQU")
        parent = ccg.scat.SuperCat('PP/NP')
        production = ccg.rules.Production(c1, c2, parent=parent)
        production.replace(ccg.scat.SuperCat('S[dcl]\NP'))
        assert production.right == "RQU"
        assert production.left == 'S[dcl]\NP'
        c1 = ccg.scat.SuperCat(',')
        c2 = ccg.scat.SuperCat('(S\NP)/(S\NP)')
        production = ccg.rules.Production(c1, c2, rule='left_punct')
        production.parent = production.result
        assert production.parent.annotated == c2.annotated
        production.replace(ccg.scat.SuperCat('NP/N'))
        assert production.left == ','
        assert production.right.annotated == '(NP{Y}/N{Y}<1>){_}'
    
    def test_add_conj(self):
        c1 = ccg.scat.SuperCat('conj')
        c2 = ccg.scat.SuperCat('PP/NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('S[dcl]\NP[conj]'))
        assert production.right == 'S[dcl]\NP'
        assert production.left == 'conj'

    def test_do_conj(self):
        c1 = ccg.scat.SuperCat('S[dcl]\NP')
        c2 = ccg.scat.SuperCat('S[dcl]\NP[conj]')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace('(S[dcl]\NP)/NP')
        assert production.left == '(S[dcl]\NP)/NP'
        assert production.right == '(S[dcl]\NP)/NP[conj]'

    def test_type_raise1(self):
        c1 = ccg.scat.SuperCat('S/(S\NP)')
        c2 = ccg.scat.SuperCat('(S[dcl]\NP)/NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace('((S[dcl]\NP)/NP)/NP')
        self.assertEqual(production.left, c1.string)
        self.assertEqual(production.left.annotated, c1.annotated)

    def test_type_raise2(self):
        # S/(S\NP) (S[dcl]\NP)/NP --> S[dcl]/NP
        # (N/N)/((N/N)\NP) ((N/N)\NP)/N --> (N/N)/N
        c1 = ccg.scat.SuperCat('S/(S\NP)')
        c2 = ccg.scat.SuperCat('(S[dcl]\NP)/NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        assert production.rule == 'ftraise_comp'
        production.replace('(N/N)/N')
        self.assertEqual(production.left, '(N/N)/((N/N)\NP)')
        self.assertEqual(production.right, '((N/N)\NP)/N')
        production.replace('S[dcl]/NP')
        self.assertEqual(production.right, c2)
        self.assertEqual(production.left, c1)

    def test_type_raise3(self):
        # (S[pss]\NP)/(S[adj]\NP) (S\NP)\((S\NP)/(S[adj]\NP)) -->
        # S[pss]\NP
        # ((S/S)/(S[ad]\NP))\NP (S/S)\((S/S)/(S[adj]\NP)) -->
        # (S/S)\NP
        c1 = ccg.scat.SuperCat('(S[pss]\NP)/(S[adj]\NP)')
        c2 = ccg.scat.SuperCat('(S\NP)\((S\NP)/(S[adj]\NP))')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace(ccg.scat.SuperCat('(S/S)\NP'))
        self.assertEqual(production.left.string,
                         '((S/S)\NP)/(S[adj]\NP)')
        self.assertEqual(production.right.string,
                         '((S/S)\NP)\(((S/S)\NP)/(S[adj]\NP))')
        production.replace(ccg.scat.SuperCat('S[pss]\NP'))
        self.assertEqual(production.left.string, c1.string)

    def test_type_raise4(self):
        # ((S[pt]\NP)/PP)/NP (S\NP)\((S\NP)/PP) --> (S[pt]\NP)/NP
        # ((S[q]/PP)/(S[pss]\NP))/NP S\(S/PP) -->
        # (S[q]/(S[pss]\NP))/NP
        c1 = ccg.scat.SuperCat('((S[pt]\NP)/PP)/NP')
        c2 = ccg.scat.SuperCat('(S\NP)\((S\NP)/PP)')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        assert production.rule == 'btraise_comp'
        production.replace(ccg.scat.SuperCat('(S[q]/(S[pss]\NP))/NP'))
        self.assertEqual(production.left.string, '((S[q]/PP)/(S[pss]\NP))/NP')
        self.assertEqual(production.right.string, 'S\(S/PP)')
        production.replace(ccg.scat.SuperCat('(S[pt]\NP)/NP'))
        self.assertEqual(production.left.string, c1.string)
        self.assertEqual(production.right.string, c2.string)




    def test_feature_passing(self):
        c1 = ccg.scat.SuperCat('(S[X]{Y}/(S[X]{Y}/NP{_}){Y}){_}')
        c2 = ccg.scat.SuperCat('S[dcl]/NP')
        production = ccg.rules.Production(c1, c2)
        production.parent = production.result
        production.replace('S[ng]')
        self.assertEqual(production.left, c1)

    def test_replace_bug(self):
        # (S[b]\NP)/(S[ng]\NP) S[ng]\NP --> S[b]\NP
        # (((S[b]\NP)/(S[to]\NP))/(S[adj]\NP))/NP[expl]
        left = ccg.scat.SuperCat('(S[b]\NP)/(S[ng]\NP)')
        right = ccg.scat.SuperCat('S[ng]\NP')
        parent = ccg.scat.SuperCat('S[b]\NP')
        production = ccg.rules.Production(left, right, parent=parent)
        replacement = ccg.scat.SuperCat(
            '(((S[b]\NP)/(S[to]\NP))/(S[adj]\NP))/NP[expl]')
        production.replace(replacement)


    def test_determiner_apply_replace(self):
        left = ccg.scat.SuperCat('NP/N')
        right = ccg.scat.SuperCat('N')
        production = ccg.rules.Production(left, right)
        production.parent = production.result
        replacement = ccg.scat.SuperCat('NP/PP')
        production.replace(replacement)
        self.assertEqual(production.left.annotated, '(NP{Y}/N{Y}<1>){_}')
        self.assertEqual(production.right.annotated, '(N{_}/PP{Y}<1>){_}')


    def test_possessive_apply_replace(self):
        left = ccg.scat.SuperCat('NP/(N/PP)')
        right = ccg.scat.SuperCat('N/PP')
        production = ccg.rules.Production(left, right)
        production.parent = production.result
        replacement = ccg.scat.SuperCat('NP/PP')
        production.replace(replacement)
        self.assertEqual(production.left, 'NP/(N/PP)')
        self.assertEqual(production.right, '(N/PP)/PP')

    def test_all_round_trips(self):
        """
        Test a round-trip replacement for every production rule
        """
        random.seed(0)
        grammar_loc = os.path.join(os.path.split(__file__)[0],
                                   'wsjfull.grammar')
        cats = ccg.lexicon.CATS.values()
        for parent, left, right, freq in ccg.grammar.read(grammar_loc):
            if right is None:
                continue
            if left not in ccg.lexicon.CATS or \
               right not in ccg.lexicon.CATS:
                continue
            # Ignore these productions, where I prefer my answer:
            # 5: (PP/NP)/(PP/NP) PP/NP --> PP/NP RTed to PP/PP PP/NP --> PP/NP
            if parent == 'PP/NP' and left == '(PP/NP)/(PP/NP)' \
               and right == 'PP/NP':
                continue
            # 4: ((S[adj]\NP)/PP)/((S[adj]\NP)/PP) (S[adj]\NP)/PP 
            # --> (S[adj]\NP)/PP RTed to (S[adj]\NP)/(S[adj]\NP) on left
            if left == '((S[adj]\NP)/PP)/((S[adj]\NP)/PP)' \
               and right == '(S[adj]\NP)/PP' and parent == '(S[adj]\NP)/PP':
                continue
            # 2: ((S[dcl]\NP)/(S[adj]\NP))/NP (S\NP)\(((S\NP)/(S[adj]\NP))/NP)
            # --> S[dcl]\NP
            # Broken category
            if right == '(S\NP)\(((S\NP)/(S[adj]\NP))/NP)':
                continue
            #print "%d: %s %s --> %s" % (freq, left, right, parent)
            c1 = ccg.scat.SuperCat(left)
            c1_annot = c1.annotated
            c1_str = c1.string
            c2 = ccg.scat.SuperCat(right)
            c2_annot = c2.annotated
            c2_str = c2.string
            parent = ccg.scat.SuperCat(parent)
            production = ccg.rules.Production(c1, c2, parent=parent)
            if production.left.is_type_raise \
               and production.right.is_type_raise:
                continue
            rule = production.rule
            replace_with = random.choice(cats)
            replacement = ccg.scat.SuperCat(replace_with)
            if parent.conj:
                replacement = ccg.scat.change_kwarg(replacement, conj=True)
            production.replace(replacement)
            # Don't expect RT if replacement forces rule change
            if production.rule != rule:
                continue
            #print 'New left: %s' % production.left.string
            #print 'New right: %s' % production.right.string
            production.replace(parent)
            # Accept (S\NP)|(S\NP) for S|S
            if production.left.string == '(S\NP)/(S\NP)' and c1_str == 'S/S':
                continue
            elif production.right.string == '(S\NP)\(S\NP)' and c2_str == 'S\S':
                continue
            self.assertEqual(production.left.string, c1_str)
            self.assertEqual(production.right.string, c2_str)



if __name__ == '__main__':
    unittest.main()
