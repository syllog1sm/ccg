import unittest
import ccg
import ccg.category
import ccg.lexicon
ccg.lexicon.load()

class TestAtomicRE(unittest.TestCase):
    def test_basic(self):
        basic = [('NP', 'NP', '', False, None)]
        self._run(basic)

    def test_feats(self):
        feats = [('NP[nb]', 'NP', '[nb]', False, None),
                 ('PP[dcl]', 'PP', '[dcl]', False, None)
                ]
        self._run(feats)

    def test_conj(self):
        conj = [('NP[conj]', 'NP', '', True, None)]
        self._run(conj)

    def test_hat(self):
        hat = [('N^NP', 'NP', '', False, 'NP',
                'N^S[dcl]', 'NP', '', False, 'S[dcl]',
                'N^S[dcl][conj]', 'N', '', True, 'S[dcl]')]

    def test_feat_conj(self):
        feat_conj = [('NP[nom][conj]', 'NP', '[nom]', True, None)]
        self._run(feat_conj)

    def test_var(self):
        cat = ccg.category.from_string('NP{_}')
        self.assertEqual(cat.string, 'NP')
        self.assertEqual(cat.var, 0)
        
    def _run(self, cases):
        for cat, atom, feat, conj, hat in cases:
            category = ccg.category.from_string(cat)
            self.assertEqual(atom, category.cat)
            if feat != '[nb]':
                self.assertEqual(feat, category.feature)
            self.assertEqual(conj, category.conj)
            self.assertEqual(hat, category.hat)


class TestComplex(unittest.TestCase):
    def test_basic(self):
        basic = [(r'(S[dcl]\NP)/NP', 'S[dcl]\NP', 'NP', None)]
        self._run(basic)

    def test_hat(self):
        hat = [(r'((S[dcl]\NP)/NP)^(NP\NP)', 'S[dcl]\NP', 'NP', 'NP\NP'),
               (r'NP^PP/N', 'NP^PP', 'N', None),
               (r'N^NP^(S/S)/NP', 'N^NP^(S/S)', 'NP', None),
               (r'N^(S[dcl]^NP/NP)/NP[conj]', 'N^(S[dcl]^NP/NP)', 'NP',
                None),
               (r'(NP/PP)^(S/S)/NP', '(NP/PP)^(S/S)', 'NP', None)]
        self._run(hat)

    def test_conj(self):
        category = ccg.category.from_string('(S\NP)\(S\NP)[conj]')
        self.assertEqual(category.conj, True)
        category = ccg.category.from_string('S[dcl]\NP[conj]')
        self.assertEqual(len(category.cats_by_var), 2)

    def test_complex(self):
        c = ('(((S[wq]{_}/PP{Y}<1>){_}/((S[q]{Z}<2>/PP{Y*}){Z}'
             '/(S[adj]{W*}\NP{V}){W*}){Z}){_}/(S[adj]{W}<3>'
             '\NP{V}){W}){_}')
        cat = ccg.category.from_string(c)
        self.assertEqual(c, cat.annotated)

    def _run(self, cases):
        for cat, result, argument, hat in cases:
            category = ccg.category.from_string(cat)
            self.assertEqual(cat, category.string)
            self.assertEqual(result, category.result.string)
            self.assertEqual(argument, category.argument.string)
            self.assertEqual(str(hat), str(category.hat))

    def test_safety(self):
        cat = ccg.category.from_string(r'(S[dcl]\NP)/NP')
        #cat.result = _parse.Category('NP')
        
    def test_var(self):
        cat = ccg.category.from_string('(S[dcl]{_}\NP{Y}){_}')
        self.assertEqual(cat.string, 'S[dcl]\NP')
        self.assertEqual(cat.var, 0)
        self.assertEqual(cat.argument.var, 1)
        cat = ccg.category.from_string('((S[X]{Y}\NP{Z}){Y}/(S[X]{Y}\NP{Z}){Y}){_}')
        self.assertEqual(cat.string, '(S\NP)/(S\NP)')
        self.assertEqual(cat.result.result.var, 1)
        self.assertEqual(cat.argument.argument.var, 2)
        self.assertEqual(cat.argument.result.var, 1)
        self.assertEqual(cat.result.argument.var, 2)
        cat = ccg.category.from_string('(N{_}^(S[X]{Y}\S[X]{Y}){_}/NP{Y}){_}')
        self.assertEqual(cat.string, 'N^(S\S)/NP')
        self.assertEqual(cat.result.hat.result.var, 1)

    def test_multi_var(self):
        cat = ccg.category.from_string('(PP{Y,_}/NP{Y}){_}')
        assert cat.var == 0
        assert cat.var2 == -1
        assert cat.result.var == 1
        assert cat.result.var2 == 0
        assert cat.annotated == '(PP{Y,_}/NP{Y}){_}'

    def test_variable_guessing(self):
        cat_str = r'PP/(S[to]\NP)'
        assert cat_str not in ccg.lexicon.CATS
        cat = ccg.category.from_string(r'PP/(S[to]\NP)')
        # Need to fix this somehow
        assert cat.annotated != r'(PP{_}/(S[to]{_}\NP{Y}<1>){_}){_}'

if __name__ == "__main__":
    unittest.main()
