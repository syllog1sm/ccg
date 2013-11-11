import re

from ._Leaf import Leaf
from ._CCGNode import CCGNode
import ccg.scat

class CCGLeaf(Leaf, CCGNode):
    neRE = re.compile(r'\|(?=[BI]-)')
    def __init__(self, **kwargs):
        textName = CCGLeaf.neRE.split(kwargs.pop('text'))
        if len(textName) == 2:
            text, entityTag = textName 
        else:
            text = textName[0]
            entityTag = ''
        self.text = text
        self.entity = entityTag
        self.pos = kwargs.pop('pos')
        self.parg = kwargs.pop('parg')
        self.wordID = kwargs.pop('wordID')
        self.srl_args = {}
        CCGNode.__init__(self, headIdx=0, **kwargs)
        
    def sibling(self):
        return None

    def validate(self):
        return True

    def isAdjunct(self):
        return False

    
    def isPunct(self):
        return bool(self.label in ccg.punct)

    def changeLabel(self, newLabel):
        """
        Change predicate-argument category
        """
        oldLabel = self.parg
        newLabel = ccg.scat.SuperCat(newLabel)
        #newLabel.goldDeps = oldLabel.goldDeps
        #for head in oldLabel.heads():
        #    newLabel.addHead(head)
        self.parg = newLabel

    def head(self):
        return self

    def heads(self):
        return [self]

    @property
    def stag(self):
        return self.parent().label

