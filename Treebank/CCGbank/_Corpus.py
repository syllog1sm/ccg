import sys

from _Node import Node
from _File import File
from _Sentence import Sentence

class Corpus(Node):
    def parent(self):
        """
        Raises an error, because the root node has no parent
        """
        raise AttributeError, "Cannot retrieve the parent of the root node. Current parse state:\n\n%s" % self.prettyPrint()
        
    def attachChild(self, newChild):
        """
        Append a file
        """
        # Security isn't really an issue for Corpus, so just stick
        # it onto the list
        self._children.append(newChild)

        
    def performOperation(self, operation):
        """
        Accept a Visitor and call it on each child
        Goofy name/design is legacy from when I didn't know how to code :(
        """
        operation.newStructure()
        operation.actOn(self)
        for node in self.children():
            operation.actOn(node)
            
    def child(self, index):
        """
        Read a file by zero-index offset
        """
        path = self._children[index]
        print >> sys.stderr, path
        return self.fileClass(path=path)
     
    
    def children(self):
        """
        Generator to iterate through children
        """
        for i in xrange(len(self._children)):
            yield self.child(i)
    
    def file(self, key):
        """
        Read a file by path
        """
        return self.fileClass(path=key)
            
    def sentence(self, key):
        filename, sentenceKey = key.split('~')
        file_ = self.file(filename)
        return file_.sentence(key)

    def sentences(self):
        for child in self.children():
            for sentence in child.children():
                yield sentence
