
class Printer(object):
    """
    Print a parse tree with good formatting
    """
    
    def __call__(self, node):
        return self.actOn(node)
    
    def actOn(self, node):
        if node.isRoot():
            return self._visitRoot(node)
        else:
            raise Break
    
    def _isLeaf(self, node):
        return node.isLeaf()

    def _visitRoot(self, node):
        """
        Print each node's label, and track indentation
        """
        self._indentation = 0
        self._lines = []
        # Accrue print state
        self._printNode(node)
        # Ensure that brackets match
        assert self._indentation == 0
        return '\n'.join(self._lines)

            
    def _visitInternal(self, node):
        """
        The visitor must control iteration itself, so only works on root.
        """
        raise Break
            
    def _printNode(self, node):
        """
        Print indentation, a bracket, then the node label.
        Then print the node's children, then a close bracket.
        """
        indentation = '  '*self._indentation
        self._lines.append('%s(%s' % (indentation, node.label))
        self._indentation += 1
        for child in node.children():
            if self._isLeaf(child):
                self._printLeaf(child)
            else:
                self._printNode(child)
        self._lines[-1] = self._lines[-1] + ')'
        self._indentation -= 1

    def _printLeaf(self, node):
        self._lines[-1] = self._lines[-1] + ' %s' % (node.text)
