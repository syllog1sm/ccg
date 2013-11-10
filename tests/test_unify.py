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


    def mest_variables(self):
        sent_str = ("(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T S/S 1 2> (<T NP 1 2> "
        "(<L NP/N DT DT No NP_636/N_636>) (<L N NNS NNS dummies N>) ) "
        "(<L , , , , ,>) ) (<T S[dcl] 1 2> (<T NP 1 2> (<L NP/N DT DT the NP_636/N_636>) "
        "(<L N NNS NNS drivers N>) ) (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/S[dcl] 0 2> "
        "(<L ((S[dcl]\NP)/S[dcl])/PR VBD VBD pointed ((S[dcl]\NP_190)/S[dcl]_191)/PR>) "
        "(<L PR RP RP out PR>) ) (<T S[dcl] 1 2> (<L NP PRP PRP they NP>) (<T S[dcl]\NP "
        "1 2> (<L (S\NP)/(S\NP) RB RB still (S_123\NP_124)_123/(S_123\NP_124)_123>) "
        "(<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBD VBD had (S[dcl]\NP_112)/NP_113>) "
        "(<T NP 0 1> (<T N 0 2> (<T N/PP 0 2> (<L (N/PP)/PP NN NN space (N/PP_684)/PP_685>) "
        "(<T PP 1 2> (<L PP/NP IN IN on PP_111/NP_111>) (<T NP 1 2> (<L NP/N PRP$ PRP$ their "
        "NP_636/N_636>) (<L N NNS NNS machines N>) ) ) ) (<T PP 1 2> (<L PP/NP IN IN for "
        "PP_111/NP_111>) (<T NP 0 2> (<T NP 1 2> (<T NP/(N/PP) 1 2> (<T NP 1 2> (<L NP/N DT "
        "DT another NP_636/N_636>) (<L N NN NN sponsor N>) ) (<L (NP/(N/PP))\NP POS POS 's "
        "(NP_682/(N_682/PP_683:B)_682)\NP_683>) ) (<L N/PP NN NN name N/PP_543>) ) "
        "(<T NP[conj] 1 2> (<L conj CC CC or conj>) (<T NP 0 1> (<L N CD CD two N>) ) "
        ") ) ) ) ) ) ) ) ) ) ) (<L . . . . .>) )")
        sent = Treebank.CCGbank.CCGSentence(string=sent_str, globalID=0, localID=0)
        sent.unify_vars()
        for word in sent.listWords():
            assert word.stag.has_head(word), word.text + ' ' + word.stag.global_annotated()

    def test_variables_short(self):
        sent_str = ("(<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T S/S 1 2> (<T NP 1 2> "
        "(<L NP/N DT DT No NP_636/N_636>) (<L N NNS NNS dummies N>) ) "
        "(<L , , , , ,>) ) (<T S[dcl] 1 2> (<T NP 1 2> (<L NP/N DT DT the NP_636/N_636>) "
        "(<L N NNS NNS drivers N>) ) (<T S[dcl]\NP 0 2> (<T (S[dcl]\NP)/S[dcl] 0 2> "
        "(<L ((S[dcl]\NP)/S[dcl])/PR VBD VBD pointed ((S[dcl]\NP_190)/S[dcl]_191)/PR>) "
        "(<L PR RP RP out PR>) ) (<T S[dcl] 1 2> (<L NP PRP PRP they NP>) (<T S[dcl]\NP "
        "1 2> (<L (S\NP)/(S\NP) RB RB still (S_123\NP_124)_123/(S_123\NP_124)_123>) "
        "(<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBD VBD had (S[dcl]\NP_112)/NP_113>) "
        "(<T NP 0 1> (<T N 0 2> (<T N/PP 0 2> (<L (N/PP)/PP NN NN space (N/PP_684)/PP_685>) "
        "(<T PP 1 2> (<L PP/NP IN IN on PP_111/NP_111>) (<T NP 1 2> (<L NP/N PRP$ PRP$ their "
        "NP_636/N_636>) (<L N NNS NNS machines N>) ) ) ) (<T PP 1 2> (<L PP/NP IN IN for "
        "PP_111/NP_111>) (<T NP 0 2> (<T NP 1 2> (<T NP/(N/PP) 1 2> (<T NP 1 2> (<L NP/N DT "
        "DT another NP_636/N_636>) (<L N NN NN sponsor N>) ) (<L (NP/(N/PP))\NP POS POS 's "
        "(NP_682/(N_682/PP_683:B)_682)\NP_683>) ) (<L N/PP NN NN name N/PP_543>) ) "
        "(<T NP[conj] 1 2> (<L conj CC CC or conj>) (<T NP 0 1> (<L N CD CD two N>) ) "
        ") ) ) ) ) ) ) ) ) ) ) (<L . . . . .>) )")
        sent = Treebank.CCGbank.CCGSentence(string=sent_str, globalID=0, localID=0)
        for node in sent.depthList():
            if node.isLeaf(): continue
            if node.label == 'PP/NP' and node.head().text == 'for':
                sibling = node.sibling()
                assert sibling.getWord(0).text == 'another'
        another_sponsor = sibling
        sponsor = sibling.getWord(1).parent()
        another_sponsor.child(0).prune()
        another_sponsor.child(0).prune()
        sponsor.reattach(another_sponsor)

        sent.unify_vars()
        print sent
        for word in sent.listWords():
            print word.stag.annotated
            print word.stag.global_annotated()
        for word in sent.listWords():
            assert word.stag.has_head(word), word.text + ' ' + word.stag.global_annotated()


if __name__ == '__main__':
    unittest.main()
