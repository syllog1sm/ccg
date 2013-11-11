import re
import sys

from ._CCGNode import CCGNode
from ._CCGLeaf import CCGLeaf
from ._Sentence import Sentence
import ccg.scat

class CCGSentence(Sentence, CCGNode):
    def __init__(self, **kwargs):
        if 'string' in kwargs:
            node = self._parseString(kwargs.pop('string'))
        elif 'node' in kwargs:
            node = kwargs.pop('node')
        globalID = kwargs.pop('globalID')
        self.localID = kwargs.pop('localID')
        CCGNode.__init__(self, label="S", headIdx=0, **kwargs)
        self.globalID = globalID
        self.attachChild(node)
        self.headIdx = 0
        

    def sibling(self):
        return None

    def addPargDeps(self, pargDeps):
        headDeps = {}
        for pargDep in pargDeps:
            if len(pargDep) == 6:
                i, j, catJ, argK, formI, formJ = pargDep
                if formI == '-colon-':
                    formI = ':'
                if formJ == '-colon-':
                    formJ = ':'
                depType = 'L'
            elif len(pargDep) == 7:
                i, j, catJ, argK, formI, formJ, depType = pargDep
            else:
                print pargDeps
                raise StandardError
            i = int(i)
            j = int(j)
            argK = int(argK)
            arg = self.getWord(i)
            head = self.getWord(j)
            if arg.text != formI or head.text != formJ:
                if formI == 'null' or formJ == 'null':
                    continue
                #else:
                #    print >> sys.stderr, "Mismatched dependency"
                #    return None
                print self.globalID
                print '\n'.join('%d-%s' % (w.wordID, w.text) for w in self.listWords())
                print arg
                print head
                print formI
                print formJ
                print pargDep
                print '\n'.join([' '.join(d) for d in pargDeps])
                print self
                raise StandardError, "Mismatched dependency"
            headDeps.setdefault(head, {}).setdefault(argK, []).append((arg, depType))
        # Initialise dependencies, so there's a slot there for unfilled deps
        for word in self.listWords():
            goldDeps = []
            for arg in word.parg.arguments:
                goldDeps.append([])
            word.parg.goldDeps = goldDeps
        for head, itsDeps in headDeps.items():
            cat = head.parg
            for argNum, deps in itsDeps.items():
                for dep in deps:
                    try:
                        cat.goldDeps[argNum - 1].append(dep)
                    except IndexError:
                    #    print >> sys.stderr, "Index error"
                    #    return None
                        print self.globalID
                        print '\n'.join('%d-%s' % (w.wordID, w.text) for w in self.listWords())
                        print head
                        print cat
                        print cat.arguments
                        print itsDeps
                        print cat.goldDeps
                        for p in pargDeps:
                            print p
                        cat.goldDeps[argNum - 1].append(dep)

    def unify_vars(self):
        """
        Traverse the nodes in the sentence, and unify their variables
        so that all nodes that have unified during the derivation have
        the same gloval variable.

        The nodes must be traversed bottom-up, and node labels must be
        replaced by the rule-product of their children. This is done
        because the parent nodes' annotations are not provided, and
        cannot be guessed. For example, in wsj_0200.0,
        there is the production:
            (S[dcl]\NP)/(S[to]\NP) --> (((S[dcl]\NP)/(S[to]\NP))/NP NP
        The annotation of the parent is _not_ the same as the one
        in the markedup file for that category --- in
        "it expects that to happen", "it" and "that" must not be
        coindexed.
        """
        def unifyBranch(node):
            """
            Start at bottom left corner of the tree. Walk
            upwards, at each point unifying the sibling
            by calling this function.
            """
            current = node.getWord(0).parent()
            while current is not node:
                sibling = current.sibling()
                parent = current.parent()
                if sibling and not sibling.child(0).isLeaf():
                    unifyBranch(sibling)

                curLab = current.label
                assert curLab
                sibLab = sibling.label if sibling else None
                parLab = parent.label
                if not sibLab:
                    production = ccg.rules.Production(curLab, sibLab, parLab)
                else:
                    if parent.label.conj:
                        production = ccg.rules.Production(curLab, sibLab, parLab)
                    else:
                        production = ccg.rules.Production(curLab, sibLab)
                if str(production.result) == str(parent.label):
                    parent.label = production.result
                current = parent
                assert current.label
        unifyBranch(self.child(0))
        # Now bind the variables to the words
        for word in self.listWords():
            word.stag.get_var().word = word
        return None

    # This returns 4 groups for compatibility with the
    # Root.parseString method
    bracketsRE = re.compile(r'(\()<([^>]+)>|()(\))')
    def _parseString(self, text):
        # The algorithm here is roughly, find and build the nodes,
        # and keep track of the parent. Then, later, connect the nodes together
        # into a tree
        # This is very similar to Root's, but it's not worth making
        # both unreadable/slow to shoe-horn them together...
        openBrackets = []
        parentage = {}
        nodes = {}
        nWords = 0
        for match in self.bracketsRE.finditer(text):
            open_, nodeData, null, close = match.groups()
            if open_:
                assert not close
                openBrackets.append((nodeData, match.start()))
            else:
                assert close
                try:
                    nodeData, start = openBrackets.pop()
                except:
                    print text
                    raise
                if nodeData.startswith('L'):
                    newNode = self._makeLeaf(nodeData, nWords)
                    nWords += 1
                else:
                    newNode = self._makeNode(nodeData)
                if openBrackets:
                    parentStart = openBrackets[-1][1]
                    parentage[newNode] = parentStart
                else:
                    top = newNode
                nodes[start] = newNode
        # Can use Root's method for this bit
        self._connectNodes(nodes, parentage)
        return top

    def _makeNode(self, nodeData):
        try:
            T, cat, headIdx, nChildren = nodeData.split()
        except:
            print >> sys.stderr, nodeData
            raise
        return CCGNode(label=ccg.scat.SuperCat(cat), headIdx=int(headIdx))

    def _makeLeaf(self, nodeData, wordID):
        L, cat, ccgPos, ptbPos, text, annotCat = nodeData.split()
        if cat == '((S[b]\NP)/NP)/':
            cat = '(S[b]\NP)/NP'
            print annotCat
            if annotCat == '((S[b]\NP_199)/NP_200)/_201':
                annotCat = '(S[b]\NP_199)/NP_200'
            elif annotCat == '((S[b]\NP_266)/NP_267)/_268':
                annotCat = '(S[b]\NP_266)/NP_267'
        if '@' in annotCat:
            annotCat, srl_annot_str = annotCat.split('@')
        else:
            srl_annot_str = ''
        cat = ccg.scat.SuperCat(cat)
        for srl_triple in srl_annot_str.split('_'):
            if not srl_triple:
                continue
            cat.srl_annot.add(tuple(srl_triple.replace('X', '_').split('|')))
        parent = CCGNode(label=cat, headIdx=0)
        leaf = CCGLeaf(label=ptbPos, pos=ccgPos, text=text,
                       parg=cat, wordID=wordID)
        parent.attachChild(leaf)
        return parent
        
                            
                            
        
                    
                

    
