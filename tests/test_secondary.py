import unittest

import ccg.category
import ccg.lexicon

ccg.lexicon.load()

class TestSecondary(unittest.TestCase):
    def test_inner_result(self):
        c = ccg.category.from_string('(S[dcl]\NP)/NP')
        self.assertEqual(c.inner_result.annotated, 'S[dcl]{_}')
        c = ccg.category.from_string('((S\NP)\(S\NP))/NP')
        self.assertEqual(c.inner_result.annotated, 'S[X]{Y}')
        c = ccg.category.from_string('NP')
        self.assertEqual(c.inner_result, 'NP')

    def test_is_predicate(self):
        c = ccg.category.from_string('PP/NP')
        self.assertFalse(c.is_predicate)
        c = ccg.category.from_string('S[dcl]\NP')
        self.assertTrue(c.is_predicate)
        c = ccg.category.from_string(r'(S[adj]\NP)/(S[adj]\NP)')
        self.assertFalse(c.is_predicate)

    def test_is_adjunct(self):
        c = ccg.category.from_string('(S\NP)\(S\NP)')
        self.assertTrue(c.is_adjunct)
        c = ccg.category.from_string('((S[X]{Y}\NP{Z}){Y}/'
                                     '(S[X]{Y}\NP{Z*}){Y}<1>){_}')
        self.assertTrue(c.is_adjunct)
        c = ccg.category.from_string('(S[X]{_}/S[X]{Y}){_}')
        self.assertFalse(c.is_adjunct)
        c = ccg.category.from_string('(PP{Y}/PP{Y}){_}')
        self.assertTrue(c.is_adjunct)

    def test_has_adjunct(self):
        c = ccg.category.from_string('((S\NP)\(S\NP))/NP')
        self.assertTrue(c.has_adjunct)
        c = ccg.category.from_string('NP/N')
        self.assertFalse(c.has_adjunct)

    def test_is_aux(self):
        c = ccg.category.from_string('(S[dcl]\NP)/(S[dcl]\NP)')
        self.assertTrue(c.is_aux)
        c = ccg.category.from_string('(S[adj]\NP)/(S[adj]\NP)')
        self.assertTrue(c.is_aux)
        c = ccg.category.from_string('PP/NP')
        self.assertFalse(c.is_aux)

    def test_is_true_aux(self):
        c = ccg.category.from_string('(S[dcl]\NP)/(S[dcl]\NP)')
        self.assertTrue(c.is_true_aux)
        c = ccg.category.from_string('(S[adj]\NP)/(S[adj]\NP)')
        self.assertFalse(c.is_true_aux)
        c = ccg.category.from_string('PP/NP')
        self.assertFalse(c.is_true_aux)


    def test_srl_annot_string(self):
        stag = ccg.scat.SuperCat('(S[dcl]\NP)/NP')
        stag.srl_annot.add(('_', 'A0', 'Y'))
        stag.srl_annot.add(('Z', 'AM-TMP', '_'))
        n, stag_str, annotated, roles = stag.srl_string()
        assert n == 2
        self.assertEqual(stag_str, "(S[dcl]\\NP)/NP@X'A0'Y_Z'AM-TMP'X")
        self.assertEqual(annotated,
                         "((S[dcl]{_}\\NP{Y}<1>){_}/NP{Z}<2>){_}@X'A0'Y_Z'AM-TMP'X")
        assert roles == ['1 A0 %l %f', '2 AM-TMP %f %l']


if __name__ == '__main__':
    unittest.main()
