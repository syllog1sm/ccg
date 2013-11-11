from _Node import Node
from _Printer import Printer

class Sentence(Node):
    _printer = Printer()
    def __str__(self):
        return self._printer(self)
        
    def parent(self):
        """
        Raises an error, because the root node has no parent
        """
        raise AttributeError, "Cannot retrieve the parent of the root node! Current parse state:\n\n%s" % self.prettyPrint()
        
    def performOperation(self, operation):
        """
        Accept a Visitor and call it on each child
        Goofy name/design is legacy from when I didn't know how to code :(
        """
        operation.newStructure()
        operation.actOn(self)
        for node in self.depthList():
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

    def isRoot(self):
        return True

    def _connectNodes(self, nodes, parentage):
        # Build the tree
        offsets = sorted(nodes.keys())
        # Skip the top node
        offsets.pop(0)
        for key in offsets:
            node = nodes[key]
            parent = nodes[parentage[node]]
            parent.attachChild(node, len(parent))
