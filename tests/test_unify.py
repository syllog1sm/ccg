import unittest

import ccg.rules
import ccg.scat
import ccg.lexicon
import Treebank.CCGbank

ccg.lexicon.load()

class TestUnify(unittest.TestCase):
    def test_fapply_adjunct(self):
        c1 = ccg.scat.SuperCat('N/N')
        c2 = ccg.scat.SuperCat('N')
        parent = ccg.scat.SuperCat('N')
        production = ccg.rules.Production(c1, c2, parent)
        parent.bind_vars(production.result, parent.category,
                         production.result.category)
        left_arg_global_vars = c1.get_vars(c1.argument)
        self.assertEqual(left_arg_global_vars, parent.get_vars(parent))
    
    def test_fcomp(self):
        c1 = ccg.scat.SuperCat('(S[dcl]\NP)/(S[pss]\NP)')
        c2 = ccg.scat.SuperCat('(S[pss]\NP)/NP')
        parent = ccg.scat.SuperCat('(S[dcl]\NP)/NP')
        production = ccg.rules.Production(c1, c2, parent)
        parent.bind_vars(production.result, parent.category,
                         production.result.category)
        left_arg_global_vars = c1.get_vars(c1.argument)
        right_result_global_vars = c2.get_vars(c2.result)
        self.assertEqual(right_result_global_vars, left_arg_global_vars)
        laa_global_vars = c1.get_vars(c1.argument.argument)
        ra_global_vars = c2.get_vars(c2.result.argument)
        self.assertEqual(laa_global_vars, ra_global_vars)
        self.assertFalse(laa_global_vars == left_arg_global_vars)
        self.assertEqual(parent.get_vars(parent.result.argument),
                         c1.get_vars(c1.result.argument))

    def test_fapply_sentence(self):
        sent_str = ("(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 1> "
        "(<L NP/N NNP NNP Ms. NP_254/N_254>) (<L N NNP NNP Haag N>) ) (<T "
        "S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBZ VBZ plays "
        "(S[dcl]\NP_241)/NP_242>) (<L NP NNP NNP Elianti NP>) )"
        " ) (<L . . . . .>) )")
        sent = Treebank.CCGbank.CCGSentence(string=sent_str, globalID=0,
                                            localID=0)
        sent.unify_vars()
        ms, haag, plays, elianti, period = [w.stag for w in sent.listWords()]
        self.assertEqual(ms.get_vars(ms.argument),
                         haag.get_vars(ms))
        self.assertEqual(haag.get_vars(haag),
                         plays.get_vars(plays.result.argument))
        self.assertEqual(plays.get_vars((plays.argument)),
                         elianti.get_vars(elianti))


if __name__ == '__main__':
    unittest.main()
