from _Node import Node

class Leaf(Node):
    """
    A leaf of the parse tree -- ie, a word, punctuation or trace
    Cannot attach or retrieve children
    """
    def __hash__(self):
        return self.wordID

    def isLeaf(self):
        return True
    
    def attachChild(self, newChild, index = None):
        raise AttachmentError, "Cannot add node\n\n%s\n\nto leaf:\n\n%s\n\nLeaves cannot have children." \
        % (newChild.prettyPrint(), self.prettyPrint())

    def length(self, constraint = None):
        return 0
        
    def child(self, index):
        """
        Raises an error, because leaf nodes have no children
        """
        raise AttributeError, "Cannot retrieve children from leaf nodes! Attempted on leaf:\n\n%s" % self.prettyPrint()
        
    def detachChild(self, node):
        """
        Raises an error, because leaf nodes have no children
        """
        raise AttributeError, "Cannot remove children from leaf nodes! Attempted on leaf:\n\n%s" % self.prettyPrint()
        
    def prettyPrint(self):
        return "(%s %s)" % (self.label, self.text) 
    
    def listWords(self):
        return [self]
        
    def lemma(self):
        """
        Get lemma from COMLEX entry, otherwise text
        """
        if self.metadata.get('COMLEX'):
            return self.metadata['COMLEX'][0].features['ORTH'][0][1:-1]
        elif self.label in ['NNP', 'NNPS']:
            return self.text
        else:
            return self.text.lower()

    def isTrace(self):
        return bool(self.label == '-NONE-')
        

    def isPunct(self):
        punct = {
        ',': True,
        ':': True,
        '.': True,
        ';': True,
        'RRB': True,
        'LRB': True
        }
        return bool(self.label in punct)

    def nextWord(self):
        words = self.root().listWords()
        nextID = self.wordID + 1
        if nextID == len(words):
            return None
        else:
            assert self is not words[self.wordID+1]
            return words[self.wordID+1]

    def prevWord(self):
        if self.wordID == 0:
            return None
        words = self.root().listWords()
        return words[self.wordID - 1]
