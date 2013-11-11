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
                production = ccg.rules.Production(curLab, sibLab, parLab)
                result = production.result
                if result and result.exact_eq(parLab):
                    parent.label = result
                current = parent
                assert current.label
        
        unifyBranch(self.child(0))
        # Now bind the variables to the words
        for word in self.listWords():
            word.stag.add_head(word)
        # Fix conjunctions
        # This is truly an evil hack, but it's very difficult to get it right.
        # We first find conjunction nodes and get their conjuncted variables
        # plus the set of nodes _outside_ their subtree (note that this
        # "outside the subtree" part is what makes this so hard to do in
        # pure unification)
        # Once we have them, we search the nodes outside for variable sets
        # that contain one but not all of the conjuncts, and then restore
        # the missing ones.
        conjVarSets = []
        nodeSet = set(self.depthList())
        for conjNode in nodeSet:
            if conjNode.length() < 2:
                continue
            if not conjNode.child(1).label.conj:
                continue
            varSet = set(v.get_ref() for v in conjNode.label.get_vars())
            nodesBelowConj = set(conjNode.depthList())
            nodesBelowConj.add(conjNode)
            nodesToCheck = nodeSet - nodesBelowConj
            conjVarSets.append((varSet, nodesToCheck))
        
        for conjVars, nodes in conjVarSets:
            for node in nodes:
                if node.isLeaf() or node.isRoot():
                    continue
                scat = node.label
                for var, varSet in scat._var_table.items():
                    varSet = set(v.get_ref() for v in varSet)
                    if not varSet.intersection(conjVars):
                        continue
                    words = set(v.word for v in varSet if v.word)
                    for conjVar in conjVars:
                        if conjVar.word not in words:
                            scat.add_var(var, conjVar)

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
        if cat.endswith('/'):
            cat = cat[1:-2]
        if '@' in cat:
            cat, srl_annot_str = cat.split('@')
        else:
            srl_annot_str = ''
        # Check whether the @ is on the annotCat instead
        if not srl_annot_str and '@' in annotCat:
            annotCat, srl_annot_str = annotCat.split('@')
        if cat.endswith('/'):
            cat = cat[1:-2]
        cat = ccg.scat.SuperCat(cat)
        for srl_triple in srl_annot_str.split('_'):
            if not srl_triple:
                continue
            cat.srl_annot.add(tuple(srl_triple.replace('X', '_').split("'")))
        parent = CCGNode(label=cat, headIdx=0)
        leaf = CCGLeaf(label=ptbPos, pos=ccgPos, text=text,
                       parg=cat, wordID=wordID)
        parent.attachChild(leaf)
        return parent
