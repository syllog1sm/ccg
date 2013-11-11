from _Node import Node

class File(Node):
    """
    A file in a treebank
    """
    def __init__(self, **kwargs):
        self._IDDict = {}
        Node.__init__(self, **kwargs)

    def attachChild(self, newChild):
        """
        Append a sentence
        """
        # Security isn't really an issue for Files, so just append the new
        # Sentence without complaint
        self._children.append(newChild)
        self._IDDict[newChild.globalID] = newChild
    
    def detachChild(self, node):
        """
        Delete a sentence
        """
        self._children.remove(node)
        self._IDDict.pop(node.globalID)
    
    def sentence(self, key):
        """
        Retrieve a sentence by key
        """
        return self._IDDict[key]
    
    def prettyPrint(self):
        return "(%d %s)" % (self.localID, '\n\n\n'.join([child.prettyPrint() for child in self.children()]))
        
    def performOperation(self, operation):
        """
        Accept a Visitor and call it on each child
        Goofy name/design is legacy from when I didn't know how to code :(
        """
        operation.newStructure()
        operation.actOn(self)
        for node in getattr(self, operation.listType)():
            try:
                operation.actOn(node)
            # Give operations the opportunity to signal
            # when the work is complete
            except Break:
                break
        while operation.moreChanges:
            operation.actOn(self)
            for node in getattr(self, operation.listType)():
                try:
                    operation.actOn(node)
                # Give operations the opportunity to signal
                # when the work is complete
                except Break:
                    break
