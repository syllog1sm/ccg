import unittest
import os.path

from ccg import rules
import ccg.scat
import ccg.category
import ccg.lexicon
import Treebank.CCGbank

ccg.lexicon.load()

#class TestCatPaths(unittest.TestCase):
#    def test_tv(self):
#        cat = ccg.scat.SuperCat('((S[dcl]{_}\NP{Y}){_}/NP{Y}){_}')
#        self.assertEqual(cat.cats[(0, 0)], 'S[dcl]')
#        self.assertEqual(cat.cats[(1, )], 'NP')
#        self.assertEqual(cat.cats[(0, 1)], 'NP')
#        self.assertEqual(cat.active_features[(0, 0)], 'S[dcl]')
#        self.assertEqual(cat.cats_by_var[1], ['NP', 'NP'])
#        self.assertEqual([str(c) for c in cat.cats_by_var[0]],
#                         ['(S[dcl]\NP)/NP', 'S[dcl]\NP', 'S[dcl]'])

#    def test_adv(self):
#        cat = ccg.scat.SuperCat('((S[X]{Y}\NP{Z}){Y}/(S[X]{Y}\NP{Z}){Y}){_}')
#        self.assertEqual(cat.cats[(0, 0)], 'S')
#        self.assertEqual(cat.cats[(1, 1)], 'NP')
#        self.assertEqual(
#            [str(c) for c in cat.cats_by_var[1]],
#            ['S\NP', 'S', 'S\NP', 'S'])
class MockToken(str):
    def __init__(self, text):
        self.text = text
        str.__init__(self, text)



class TestRules(unittest.TestCase):
    def test_fapply_basic(self):
        cat1 = ccg.scat.SuperCat(r'(NP{Y}/N{Y}){_}')
        cat2 = ccg.scat.SuperCat(r'N{_}')
        self.do_rule(rules.fapply, cat1, cat2, 'NP{_}')

    def test_fapply_feature(self):
        cat1 = ccg.scat.SuperCat('S/S')
        cat2 = ccg.scat.SuperCat('S[dcl]')
        self.do_rule(rules.fapply, cat1, cat2, 'S[dcl]{_}')
        self.do_rule(rules.fapply,
          ccg.scat.SuperCat('(S\NP)/(S\NP)'),
          ccg.scat.SuperCat(r'(S[pss]{_}\NP{Y}){_}'),
          '(S[pss]{_}\NP{Y}){_}')

    def test_bapply_basic(self):
        cat1 = ccg.scat.SuperCat(r'NP{_}')
        cat2 = ccg.scat.SuperCat(r'(S[dcl]{_}\NP{Y}){_}')
        self.do_rule(rules.bapply, cat1, cat2, 'S[dcl]{_}')
    
    def test_bapply_feature(self):
        cat1 = ccg.scat.SuperCat(r'S[ng]{_}')
        cat2 = ccg.scat.SuperCat(r'(S[X]{Y}\S[X]{Y}){_}')
        self.do_rule(rules.bapply, cat1, cat2, 'S[ng]{_}')

    def test_fcomp_basic(self):
        cat1 = ccg.scat.SuperCat(r'(NP{Y}/N{Y}){_}')
        cat2 = ccg.scat.SuperCat(r'(N{_}/PP{Y}){_}')
        self.do_rule(rules.fcomp, cat1, cat2, '(NP{_}/PP{Y}){_}')
    
    def test_fcomp_feature(self):
        cat1 = ccg.scat.SuperCat(r'(S[X]{Y}/S[X]{Y}){_}')
        cat2 = ccg.scat.SuperCat(r'(S[dcl]{_}/S[dcl]{Y}){_}')
        self.do_rule(rules.fcomp, cat1, cat2, '(S[dcl]{_}/S[dcl]{Y}){_}')
        cat1 = ccg.scat.SuperCat(r'((S[X]{Y}\NP{Z}){Y}/(S[X]{Y}\NP{Z}){Y}){_}')
        cat2 = ccg.scat.SuperCat(r'((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}')
        self.do_rule(rules.fcomp, cat1, cat2,
                      '((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}')

    def test_bcomp_basic(self):
        c1 = ccg.scat.SuperCat(r'(NP{Y}\NP{Y}){_}')
        c2 = ccg.scat.SuperCat(r'(S[dcl]{_}\NP{Y}){_}')
        self.do_rule(rules.bcomp, c1, c2, '(S[dcl]{Y}\NP{Z}){_}')
    
    def test_bcomp_feature(self):
        c1 = ccg.scat.SuperCat(r'(S[dcl]{_}\NP{Y}){_}')
        c2 = ccg.scat.SuperCat(r'(S[X]{Y}\S[X]{Y}){_}')
        self.do_rule(rules.bcomp, c1, c2, '(S[dcl]{_}\NP{Y}){_}')

    def test_bxcomp_basic(self):
        c1 = ccg.scat.SuperCat(r'((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}')
        c2 = ccg.scat.SuperCat(r'((S[X]{Y}\NP{Z}){Y}\(S[X]{Y}\NP{Z}){Y}){_}')
        self.do_rule(rules.bxcomp, c1, c2, c1.annotated)

    def test_gfcomp_basic(self):
        c1 = ccg.scat.SuperCat(r'(PP{_}/S[em]{Y}){_}')
        c2 = ccg.scat.SuperCat(r'((S[em]{_}/NP{Y}){_}/Q{Z}){_}')
        self.do_rule(rules.fcomp, c1, c2, '((PP{Y}/NP{Z}){_}/Q{W}){_}')

    def test_gfcomp_feature(self):
        c1 = ccg.scat.SuperCat(r'S/S')
        c2 = ccg.scat.SuperCat(r'(S[dcl]\NP)/NP')
        self.assertFalse(rules.fcomp(c1, c2))
        self.do_rule(rules.fxcomp, c1, c2, '((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}')

    def test_gbxcomp_cross_slash(self):
        c1 = ccg.scat.SuperCat(r'(S[dcl]\NP)/NP')
        c2 = ccg.scat.SuperCat(r'S\S')
        self.assertFalse(rules.bcomp(c1, c2))
        self.do_rule(rules.bxcomp, c1, c2, '((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}')

    def test_gbxcomp_basic(self):
        c1 = ccg.scat.SuperCat(r'((NP{_}/PP{Y}){_}/S[em]{Z}){_}')
        c2 = ccg.scat.SuperCat(r'S[dcl]\NP')
        self.do_rule(rules.bxcomp, c1, c2, '((S[dcl]{Y}/PP{Z}){_}/S[em]{W}){_}')

    def test_bgxcomp_feature(self):
        c1 = ccg.scat.SuperCat('((S[dcl]\NP)/NP)/NP')
        c2 = ccg.scat.SuperCat('(S\NP)\(S\NP)')
        self.do_rule(rules.bxcomp, c1, c2, r'(((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}/NP{W}){_}')
        c1 = ccg.scat.SuperCat('((S[dcl]\NP[expl])/(NP\NP))/NP')
        c2 = ccg.scat.SuperCat('(S\NP)\(S\NP)')
        self.do_rule(rules.bxcomp, c1, c2,
                     r'(((S[dcl]{_}\NP[expl]{Y}){_}/(NP{Z}\NP{Z}){W}){_}/NP{V}){_}')
        c1 = ccg.scat.SuperCat('((S[dcl]\NP[expl])/S[for])/(S[adj]\NP)')
        c2 = ccg.scat.SuperCat('(S\NP)\((S\NP)/S[for])')
        self.do_rule(rules.bxcomp, c1, c2, '((S[dcl]{_}\NP[expl]{Y}){_}/(S[adj]{Z}\NP{W}){Z}){_}')
        c1 = ccg.scat.SuperCat('(S[qem]/S[dcl])\((NP\NP)/NP)')
        c2 = ccg.scat.SuperCat('S\S')
        self.do_rule(rules.bxcomp, c1, c2, '((S[qem]{_}/S[dcl]{Y}){_}\\((NP{Z}\\NP{Z}){W}/NP{V}){U}){_}')

    def test_add_conj(self):
        c1 = ccg.scat.SuperCat('conj')
        c2 = ccg.scat.SuperCat('S[dcl]{_}^(S[X]{Y}\S[X]{Y}){_}')
        result = rules.add_conj(c1, c2)
        self.assertEqual(result.string, 'S[dcl]^(S\S)[conj]')
        c1 = ccg.scat.SuperCat('conj')
        c2 = ccg.scat.SuperCat('S[dcl]\NP')
        result = rules.add_conj(c1, c2)
        self.assertEqual(result.annotated,
                         '((S[dcl]{Y}\NP{Z}<1>){_}\(S[dcl]{W}\NP{Z}<1>){W}){_}')
        c1 = ccg.scat.SuperCat('conj')
        c2 = ccg.scat.SuperCat('S[pss]\NP')
        result = rules.add_conj(c1, c2)

    def test_add_conj_head(self):
        c1 = ccg.scat.SuperCat('conj')
        c1.add_head(MockToken('and'))
        c2 = ccg.scat.SuperCat('NP')
        c2_head = MockToken('thing')
        c2.add_head(c2_head)
        result = rules.add_conj(c1, c2)
        self.assertTrue(result.has_head(c2_head))

    def test_do_conj(self):
        c1 = ccg.scat.SuperCat('S[X]\NP')
        c2 = ccg.scat.SuperCat('S[dcl]\NP[conj]')
        self.assertEqual(c2.annotated,
            '((S[dcl]{Y}\NP{Z}<1>){_}\(S[dcl]{W}\NP{Z}<1>){W}){_}')
        self.assertEqual(c2.annotated, 
            '((S[dcl]{Y}\NP{Z}<1>){_}\(S[dcl]{W}\NP{Z}<1>){W}){_}')
        self.assertFalse(rules.do_conj(c1, c2))
        c1 = ccg.scat.SuperCat('S[dcl]\NP')
        c1_head = MockToken('plays')
        c1.add_head(c1_head)
        c2_head = MockToken('is')
        c2.add_head(c2_head)
        result = rules.do_conj(c1, c2)
        self.assertEqual(result, 'S[dcl]\NP')
        self.assertTrue(result.has_head(c1_head))
        self.assertTrue(result.has_head(c2_head))

    def test_comma_conj(self):
        c1 = ccg.scat.SuperCat(':')
        c2 = ccg.scat.SuperCat('NP')
        self.assertEqual(rules.comma_conj(c1, c2).string, 'NP[conj]')

    def test_fcomp_tr(self):
        c1 = ccg.scat.SuperCat('(S[X]{Y}/(S[X]{Y}\NP{_}){Y}){_}')
        c2 = ccg.scat.SuperCat('(S[dcl]\NP)/NP')
        result = rules.fcomp(c1, c2)
        self.assertEqual(result, 'S[dcl]/NP')

    def test_feature(self):
        c1 = ccg.scat.SuperCat('(N{_}/N[num]){_}')
        c2 = ccg.scat.SuperCat('N[num]')
        self.do_rule(rules.fapply, c1, c2, 'N{_}')
                         

    def do_rule(self, rule, cat1, cat2, expected):
        cat1str = cat1.string
        cat2str = cat2.string
        result = rule(cat1, cat2)
        self.assertEqual(result, expected)
        self.assertEqual(str(cat1), cat1str)
        self.assertEqual(str(cat2), cat2str)
        self.assertEqual(result.annotated, expected)


    #def test_traise(self):
    #    c1 = ccg.scat.SuperCat('NP')
    #    par = ccg.scat.SuperCat('Q/(Q\NP)')
    #    result = rules.traise(c1, par)
    #    self.assertEqual(result, 'Q/(Q\NP)')
    #    self.assertEqual(result.annotated, '(Q{Y}/(Q{Y}\NP{_}){Y}){_}')
    

    def test_minimise(self):
        cat = ccg.category.from_string('((S[dcl]{Y}\NP{Z}){Y}/NP{W}){Y}')
        min, var_map = rules.minimise_vars(cat, {})
        self.assertEqual(min.annotated, '((S[dcl]{_}\NP{Y}){_}/NP{Z}){_}')
        cat = ccg.category.from_string('(S[dcl]{Y}\NP{Z}){Y}')
        min, var_map = rules.minimise_vars(cat, {})
        self.assertEqual(min.annotated, '(S[dcl]{_}\NP{Y}){_}')

    def test_badjunct_global(self):
        c1 = ccg.scat.SuperCat('S[pss]\NP')
        c2 = ccg.scat.SuperCat('(S\NP)\(S\NP)')
        parent = ccg.scat.SuperCat('S[pss]\NP')
        production = ccg.rules.Production(c1, c2, parent)

    def test_parent_annotation(self):
        c1 = ccg.scat.SuperCat('((S[dcl]\NP)/(S[to]\NP))/NP')
        c2 = ccg.scat.SuperCat('NP')
        parent = ccg.scat.SuperCat('(S[dcl]\NP)/(S[to]\NP)')
        production = ccg.rules.Production(c1, c2, parent)
        self.assertEqual(production.result.annotated,
                         '((S[dcl]{_}\NP[Y]{Y}<1>){_}/(S[to]{Z}<2>\NP[Y]{W*}){Z}){_}')

class TestTrees(unittest.TestCase):
    def test_conj_plays(self):
        elianti = ('(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> '
                   '(<L N/N NNP NNP Ms. N_254/N_254>) (<L N NNP NNP Haag N>) '
                   ') ) (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/NP 1 2> '
                   '(<L (S[dcl]\NP)/NP VBZ VBZ plays (S[dcl]\NP_241)/NP_242>) '
                   '(<T (S[dcl]\NP)/NP[conj] 1 2> (<L conj CC CC and conj>) '
                   '(<L (S[dcl]\NP)/NP VBZ VBZ is (S[dcl]\NP_241)/NP_242>) ) ) '
                   '(<T NP 0 1> (<L N NNP NNP Elianti N>) ) ) )'
                   '(<L . . . . .>))')
        import Treebank.CCGbank
        sentence = Treebank.CCGbank.CCGSentence(string=elianti, globalID=0,
                                                localID=0)
        sentence.unify_vars()
        plays_and_is = sentence.getWord(2).parent().parent()
        annotated = plays_and_is.label.global_annotated()
        self.assertEqual(annotated,
                         '((S[dcl]{plays,is}\NP{Haag}<1>){plays,is}/NP{Elianti}<2>){plays,is}')

    def test_conj_elianti(self):
        elianti = ('(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> '
                   '(<L N/N NNP NNP Ms. N_254/N_254>) (<L N NNP NNP Haag N>) '
                  ') ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBZ VBZ plays '
                   '(S[dcl]\NP_241)/NP_242>) (<T NP 0 1> (<T N 1 2> '
                   '(<L N NNP NNP Elianti N>) (<T N[conj] 1 2> '
                   '(<L conj CC CC and conj>) (<L N NN NN Celamene NN>) ) )' 
                   ') ) ) (<L . . . . .>) )')
        sentence = Treebank.CCGbank.CCGSentence(string=elianti, globalID=0,
                                                localID=0)
        sentence.unify_vars()
        elianti_and_celamene = sentence.getWord(-2).parent().parent().parent()
        annotated = elianti_and_celamene.label.global_annotated()
        self.assertEqual(annotated, 'N{Elianti,Celamene}')

    def test_fcomp_sadj(self):
        c1 = ccg.scat.SuperCat(r'(S[dcl]\NP)/(S[adj]\NP)')
        c1_head = MockToken('is')
        c1.add_head(c1_head)
        c2 = ccg.scat.SuperCat(r'(S[adj]\NP)/NP')
        c2_head = MockToken('worth')
        c2.add_head(c2_head)
        production = ccg.rules.Production(c1, c2)
        assert production.result.has_head(c2_head)

    def test_lex_vars_stay(self):
        ccgbank_loc = '/home/matt/code/repos/data/CCGbank1.2'
        ccgbank = Treebank.CCGbank.CCGbank(path=ccgbank_loc)
        ccg.lexicon.load(os.path.join(ccgbank_loc, 'markedup'))
        asbestos = ccgbank.child(2).child(0)
        asbestos.unify_vars()
        for word in asbestos.listWords():
            self.assertTrue(word.stag.has_head(word))

if __name__ == '__main__':
    unittest.main()
