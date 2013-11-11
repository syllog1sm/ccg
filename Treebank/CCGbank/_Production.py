"""
Update a subtree to reflect its parent category

We do this by detecting the type of production

Unary
Unlicensed -- Does not conform to any ccg rule
Adjunction -- The functor category is an adjunct
Auxiliary -- The functor category is an auxiliary
Application -- The functor category is a predicate applying to the argument
Composition, result change -- The result cat of the parent has changed
Composition, argument change -- The argument structure of the parent has changed

The detection algorithm also finds the functor category (the category whose
result is preserved in the case of composition)
"""
import ccg.category
from copy import deepcopy as dcopy
import re
class _Production(object):
    """
    Represents a production rule, of a given type. The parent can then be
    replaced and the changes reflected in the children, in a way that's
    customised according to the rule type
    """
    def __init__(self, left, right, parent, functorPos = None):
        self.left = ccg.category.from_string(str(left))
        self.right = ccg.category.from_string(str(right))
        self.parent = dcopy(parent)
        if functorPos != None:
            self._functor = functorPos
        else:
            self._functor = self.findFunctor(left, right, parent)
        self.unify()

    def unify(self):
        pass
    
    def _getFunctor(self):
        if self._functor == 0:
            return self.left
        else:
            return self.right

    def _setFunctor(self, functor):
        if self._functor == 0:
            self.left = functor
        else:
            self.right = functor

    def _getArg(self):
        if self._functor == 1:
            return self.left
        else:
            return self.right

    def _setArg(self, arg):
        if self._functor == 1:
            self.left = arg
        else:
            self.right = arg

    def replaceResult(self, cat, newResult):
        argument = dcopy(cat.argument)
        slash = cat.slash
        conj = cat.conj
        result = dcopy(newResult)
        return ccg.ComplexCategory(result, argument, slash, conj)

    def addArgs(self, cat, args):
        cat = dcopy(cat)
        args.reverse()
        for arg, slash, morph in args:
            cat = ccg.ComplexCategory(cat, arg, slash, False)
            cat.morph = dcopy(morph)
        return cat

    def __str__(self):
        return "%s %s --> %s %s" % (self.label, self.parent, self.left, self.right)

    def _removeFeatures(self, cat, removeFeat):
        if cat.isComplex():
            cat.morph = None
            for result, argument, slash, morph in cat.deconstruct():
                self._removeFeatures(result, removeFeat)
                self._removeFeatures(argument, removeFeat)
        else:
            if removeFeat:
                cat.feature = ''
            cat.morph = None

    @property
    def head(self):
        return self._getHead()


    functor = property(_getFunctor, _setFunctor)
    argument = property(_getArg, _setArg)

class Application(_Production):
    label = 'a'
    def findFunctor(left, right, parent):
        candidates = [(left, '/', right, 0), (right, '\\', left, 1)]
        for functor, slash, arg, position in candidates:
            if functor.isComplex() \
            and functor.slash == slash \
            and functor.argument == arg \
            and functor.result == parent \
            and not functor.isAdjunct():
                return position
        else:
            return -1

    def unify(self):
        self.functor.argument.unify(self.argument)

    findFunctor = staticmethod(findFunctor)

    def replace(self, new):
        self.functor = self.replaceResult(self.functor, new)
        return self.left, self.right

    def _getHead(self):
        return self.functor

class TRaiseApplication(Application):
    label = 'tra'
    def findFunctor(left, right, parent):
        direction = Application.findFunctor(left, right, parent)
        if direction == -1:
            return direction
        else:
            functor = [left, right][direction]
            if functor.isTypeRaise():
                return direction
            else:
                return -1
    findFunctor = staticmethod(findFunctor)

    def unify(self):
        pass

    def replace(self, new):
        x = dcopy(self.argument.argument)
        y = dcopy(new)
        featLessY = dcopy(y)
        self._removeFeatures(featLessY, True)
        if self._functor == 0:
            innerSlash = '\\'
            outerSlash = '/'
        else:
            innerSlash = '/'
            outerSlash = '\\'
        tRaiseArgStr = r'(%s%s%s)' % (featLessY.strAsPiece(), innerSlash, x.strAsPiece())
        catStr = '%s%s%s' % (featLessY.strAsPiece(), outerSlash, tRaiseArgStr)
        self.functor = ccg.category.from_string(catStr)
        self.argument = self.addArgs(dcopy(y), [(dcopy(x), innerSlash, None)])
        return self.left, self.right

    def _getHead(self):
        return self.argument
        




class Composition(_Production):
    label = 'c'
    def findFunctor(left, right, parent):
        """
        Composition is of the form X/Y Y/$ -> X|$ or Y|$ X\Y

        We call the X|Y category the functor.
        """
        if (not left.isComplex()) or (not right.isComplex()):
            return -1
        if left.conj or right.conj:
            return -1
        oLeft = left
        left = dcopy(left)
        right = dcopy(right)
        if right.slash == '\\':
            for result, argument, slash, morph in left.deconstruct():
                if right.argument.unify(result):
                    return 1
        elif left.slash == '/' and right.slash == '/':
            for result, argument, slash, morph in right.deconstruct():
                if left.argument.unify(result) and slash == '/':
                    return 0
        return -1

    findFunctor = staticmethod(findFunctor)

    def unify(self):
        yCat = self.functor.argument
        for potentialY, argument, slash, morph in self.argument.deconstruct():
            if yCat.unify(potentialY):
                break
        else:
            raise StandardError
        self._y = yCat
        self._x = self.functor.result
        
    

    def replace(self, new, xCat = None):
        """
        Get the X and $ components of the new category, and change children
        accordingly. Note that because the Y element is not represented in the
        parent, this must be invariant. So we're going to be replacing the result
        of the functor, and/or the $ of the arguments.
        """
        # If new is atomic, we really can't do much composing
        # Make it apply into the new category instead
        if not new.isComplex():
            if self._functor == 0:
                slash = '/'
            else:
                slash = '\\'
            newFunc = ccg.ComplexCategory(dcopy(new), dcopy(self.argument), slash, False)
            self.functor = newFunc
            return self.left, self.right
        # If no X supplied, try the old X
        if not xCat:
            xCat = dcopy(self._x)
        # Take a copy of new so that unification doesn't mess things up
        new = dcopy(new)
        oldResults = self._getResultArgs(self.parent)
        dollarCats = []
        # Handle general comp
        for result, argument, slash, morph in new.deconstruct():
            dollarCats.append((argument, slash, morph))
            # So pass first round
            # Unify to pass features and morph
            if xCat.unify(result):
                break
        else:
            # Otherwise, make it non-generalised composition
            xCat = dcopy(new.result)
            dollarCats = [(new.argument, new.slash, new.morph)]
        functor = self.functor
        
        self.functor = self.addArgs(xCat, [(functor.argument, functor.slash, functor.morph)])
        self.argument = self.addArgs(functor.argument, dollarCats)
        return (self.left, self.right)
        

    def _getResultArgs(category):
        """
        Pair a result with the arguments up to that point
        """
        results = {}
        args = []
        for result, argument, slash, morph in category.deconstruct():
            args.append((argument, slash, morph))
            # Use featureless because we don't want to deal with feature passing, eg
            # S[dcl]/NP --> S/(S\NP) (S[dcl]\NP)/NP
            results[result] = list(args)
            
        return results

    _getResultArgs = staticmethod(_getResultArgs)

    def _getHead(self):
        # Follow the C&C parser's wrong policy of always left heading
        return self.left


class Determination(Application, Composition):
    """
    Purely for the infuriating NP -> NP[nb]/N N rule
    """
    label = 't'
    def findFunctor(left, right, parent):
        if str(left) == 'NP[nb]/N' and str(right) == 'N' and str(parent) == 'NP':
            return 0
        elif left.isComplex() and not left.isAdjunct() and not ccg.isIdentical(left.innerResult(), ccg.N) and ccg.isIdentical(left.argument, ccg.N) and ccg.isIdentical(ccg.N, right):
            return 0
        else:
            return -1

    def replace(self, new):
        if ccg.isIdentical(new, ccg.NP):
            self.functor = ccg.category.from_string('NP[nb]/N')
            return self.left, self.right
        # If possible, prefer to use composition than to stick args onto the NP
        if new.innerResult() == 'NP':
            self._x = self.functor.result
            Composition.replace(self, new)
        else:
            Application.replace(self, new)

    findFunctor = staticmethod(findFunctor)

    def _getHead(self):
        return self.argument

class AdjunctDetermination(Application):
    """
    Handle cases like ((S\NP)\(S\NP))/N
    """
    label = 'jt'

    def findFunctor(left, right, parent):
        if parent.isAdjunct() and left.result == parent and right == ccg.N:
            return 0
        else:
            return -1

    findFunctor = staticmethod(findFunctor)

    def replace(self, new):
        if ccg.isIdentical(new, ccg.NP):
            self.functor = ccg.category.from_string(r'NP[nb]/N')
            return self.left, self.right
        elif new.isAdjunct():
            self.functor = ccg.addArg(new, self.right, '/')
        else:
            # Define this when I've got an example
            # wsj_0029.13 -- noisy, requires fixing
            self.functor = ccg.addArg(new, self.right, '/')
            #print self
            #print new
            #raise StandardError

    def _getHead(self):
        return self.argument



class TRaiseComp(Composition):
    """
    Composition between a type raised category and an argument
    """
    label = 'r'
    def findFunctor(left, right, parent):
        answer = Composition.findFunctor(left, right, parent)
        if answer == 0:
            if TRaiseComp.isTypeRaise(left, '/', '\\'):
                return 0
        if answer == 1:
            if TRaiseComp.isTypeRaise(right, '\\', '/'):
                return 1
        return -1

    def replace(self, new):
        left, right = Composition.replace(self, new)
        self._removeFeatures(self.functor, True)
        if new.isAdjunct():
            # To produce an adjunct we can't have features on the argument
            self._removeFeatures(self.argument, True)

    def isTypeRaise(cat, slash1, slash2):
        if cat.isComplex() and cat.slash == slash1 and cat.argument.isComplex() and cat.argument.slash == slash2:
            if ccg.isIdentical(cat.result, cat.argument.result):
                return True
        return False

    findFunctor = staticmethod(findFunctor)
    isTypeRaise = staticmethod(isTypeRaise)

    def _getHead(self):
        # Cover cases like N/(N\N) (N\N)/N
        if self.left.isTypeRaise() and self.right.isTypeRaise():
            return self.left
        else:
            return self.argument
    
        
class Adjunction(_Production):
    """
    Adjunction is of the form X/X X$ -> X$ or X$ X\X -> X$
    """
    label = 'd'
    def findFunctor(left, right, parent):
        if left.conj or right.conj:
            return -1
        candidates = [(left, right, 0), (right, left, 1)]
        for adjunct, head, position in candidates:
            if adjunct.isAdjunct() and head == parent:
                # Test that adjunct applies
                # Guards against composition cases like (S[b]\NP)/NP NP/NP
                adjArg = adjunct.argument
                if adjArg == head:
                    return position
                for result, argument, slash, morph in head.deconstruct():
                    if adjArg == result:
                        return position
        else:
            return -1
        
    findFunctor = staticmethod(findFunctor)
    
    def replace(self, new, forceApp = False):
        global complexAdj
        
        # Under forceApp, composition is disallowed -- so the argument,
        # functor components and parent must all be identical
        if forceApp:
            self.argument = dcopy(new)
            self.functor = ccg.ComplexCategory(dcopy(new), dcopy(new), self.functor.slash, False)
            return None
        args = []
        if not new.isComplex():
            x = new
        elif new.isAdjunct():
            x = new
        # The complexAdj flag indicates whether to replicate CCGbank analysis and use
        # (S\NP)|(S\NP) adjuncts. Otherwise the natural thing is S\S adjuncts
        elif complexAdj and ccg.VP == new:
            x = new
        # For parser compatibility, don't backwards compose into NP
        elif self._functor == 1 and new.innerResult() != 'S':
            x = new
        else:
            lastCat = new
            lastArgs = []
            # Select either: an adjunct, S\NP, or an atom
            for result, argument, slash, morph in new.deconstruct():
                args.append((argument, slash, morph))
                # Ensure the slash directions work
                # If the functor's to the left, cannot cross-compose into a backslash -- unless not complexAdj!s
                if complexAdj and self._functor == 0 and slash == '\\':
                    continue
	            # Don't back-cross compose into non-S
	        if self._functor == 1 and slash == '/' and result.innerResult() != 'S':
                    continue
                # Taken this out for the (S[dcl]\S[dcl])\NP S\S test case, but might need it again
                if result.isAdjunct():
                    x = result
                    break
                elif complexAdj and result == r'S\NP':
                    x = result
                    break
                elif not result.isComplex():
                    x = result
                    break
                # In case the slashes don't work out for a while (ie cross composition), store the last valid
                # place to compose into, and its arg set
                lastCat = result
                lastArgs = list(args)
            else:
                x = lastCat
                args = lastArgs
        x = dcopy(x)
        newArg = self.addArgs(x, args)
        # If the new label has a morph category, add it to the argument, as per wsj_1057.57
        if new == newArg:
            newArg.morph = dcopy(new.morph)
        # If we currently have features on the old X, don't remove them
        # This can cause entropy reduction, as per wsj_1824.28
        oldX = self.functor.argument
        if x.morphLess() == oldX.morphLess():
            removeFeat = False
        else:
            removeFeat = True
        self._removeFeatures(x, removeFeat)
        newFunctor = ccg.ComplexCategory(x, x, self.functor.slash, False)
        self.functor = newFunctor
        self.argument = newArg

    def _getHead(self):
        return self.argument

class AdjComp(_Production):
    """
    Composition of adjuncts of the form X|X X|X -> X|X
    """
    label = 'o'
    def findFunctor(left, right, parent):
        if left.conj or right.conj or parent.conj:
            return -1
        if left.isAdjunct() and right.isAdjunct() and parent.isAdjunct():
            if left.argument == right.argument == parent.argument:
                if right.slash == '\\':
                    return 1
                elif left.slash == '/':
                    return 0
        return -1

    def replace(self, new):
        if new.isAdjunct():
            x = new.result
            functor = ccg.ComplexCategory(dcopy(x), dcopy(x), self.functor.slash, False)
            argument = ccg.ComplexCategory(dcopy(x), dcopy(x), self.argument.slash, False)
            self.functor = functor
            self.argument = argument
        else:
            x = new
            functor = ccg.ComplexCategory(dcopy(x), dcopy(x), self.functor.slash, False)
            argument = dcopy(x)
            self.functor = functor
            self.argument = argument

    findFunctor = staticmethod(findFunctor)

    def _getHead(self):
        # Doesn't matter, but follow C&C parser's incorrect left head policy
        return self.left

class AddConj(_Production):
    label = 'n'
    def findFunctor(left, right, parent):
        if not parent.conj:
            return -1
        if left.conj or right.conj:
            return -1
        elif left == ccg.conj:
            functor = 0
            arg = right
        elif right == ccg.conj:
            functor = 1
            arg = left
        elif left.isPunct():
            functor = 0
            arg = right
        elif right.isPunct():
            functor = 1
            arg = left
        else:
            return -1
        parentStr = str(parent).replace('[conj]', '')
        if str(arg) != parentStr:
            return -1
        else:
            return functor
        
    findFunctor = staticmethod(findFunctor)

    def replace(self, new):
        self.argument = dcopy(new)
        self.argument.conj = False

    def _getHead(self):
        return self.argument

class Conjunction(_Production):
    label = 'j'
    def findFunctor(left, right, parent):
        if parent.conj:
            return -1
        elif left.conj:
            return 0
        elif right.conj:
            return 1
        else:
            return -1

    findFunctor = staticmethod(findFunctor)
        
    def replace(self, new):
        functor = dcopy(new)
        functor.conj = True
        self.functor = functor
        self.argument = dcopy(new)

    def _getHead(self):
        # Follow CCGbank in heading to the left
        return self.left

class Auxiliary(_Production):
    label = 'x'
    def findFunctor(left, right, parent):
        # Recent change, might break something
        if left.isTrueAux():
            return 0
        elif right.isTrueAux():
            return 1
        else:
            return -1

    findFunctor = staticmethod(findFunctor)

    def replace(self, new):
        # Wrong: need feature from functor result
        self.argument = dcopy(new)

    def _getHead(self):
        # Depart from CCGbank in taking the argument
        return self.argument
    
class Punctuation(_Production):
    label = 'p'
    def findFunctor(left, right, parent):
        """
        Functor is the punctuation symbol. Ensure this isn't conjunctive punctuation.
        """
        if left.isPunct():
            if not ccg.isIdentical(right, parent):
                return -1
            else:
                return 0
        elif right.isPunct():
            if not ccg.isIdentical(left, parent):
                return -1
            else:
                return 1
        return -1
    findFunctor = staticmethod(findFunctor)
    
    def replace(self, new):
        self.argument = dcopy(new)

    def _getHead(self):
        return self.argument

class UnHat(_Production):
    label = 'h'
    
    def findFunctor(left, right, parent):
        if right:
            return -1
        if not ccg.isIdentical(parent, left.morph):
            return -1
        return 0

    findFunctor = staticmethod(findFunctor)

    def replace(self, new):
        self.functor = self.functor
        self.functor.morph = dcopy(new)
        
    
    

class Unary(_Production):
    label = 'u'
    def findFunctor(left, right, parent):
        if not right:
            return 0
        else:
            return -1

    findFunctor = staticmethod(findFunctor)


    def replace(self, new):
        pass

    def _getHead(self):
        return self.left



class Invalid(_Production):
    label = 'i'
    def findFunctor(left, right, parent):
        """
        Functor is arbitrarily the left side, unless involves conj or punct

        This is order dependent on the other rules, as we do not want to check that the production is
        in fact invalid.
        """
        if right == ccg.conj or right.isPunct():
            return 1
        else:
            return 0
        

    findFunctor = staticmethod(findFunctor)

    def replace(self, new):
        """
        Conj and punct cases are particularly common for invalid, so
        percolate the new label down for these
        """
        if self.functor == ccg.conj or self.functor.isPunct():
            # Provide exception case for transformation punctuation
            if self.functor == ',' and new.isAdjunct():
                return None
            self.argument = dcopy(new)
            self.argument.conj = None
        else:
            pass

    def _getHead(self):
        return self.functor

def Production(left, right, parent):
    """
    Allocate a Production
    """
    binary = [AdjunctDetermination,
              Determination,
                   TRaiseApplication,
                   Application,
                   AdjComp,
                   Adjunction,
                   TRaiseComp,
                   Composition,
                   Conjunction,
                   AddConj,
                   Punctuation,
                   Invalid]
    unary = [UnHat, Unary]
    productions = binary if right else unary
    for productionClass in productions:
        functorPos = productionClass.findFunctor(left, right, parent)
        if functorPos != -1:
            return productionClass(left, right, parent, functorPos)
            
        
    
def testLabels():
    """
    Check production type assignment against manually annotated production rules
    """
    location = '/home/mhonn/code/mhonn/Treebank/CCGBank/productionTypes.txt'
    for label, parent, left, right, line in readProductions(location):
        if label == 'x':
            continue
        if not label:
            continue
        if label and not right and label != 'u':
            print line
            raise StandardError
        if right:
            production = Production(left, right, parent)
            if production.label != label:
                print "Incorrect: %s" % production.label
                print line
                raise StandardError
            else:
                print "Correct! %s" % line
        
def testReplacements():
    location = '/home/mhonn/code/mhonn/Treebank/CCGBank/productionTypes.txt'
    for label, parent, left, right, line in readProductions(location):
#        if line != 'd 20352 # S[dcl]\NP --> S[dcl]\NP (S\NP)\(S\NP)':
#            continue
#        if label == 'x': continue
        if not label:
            break
        if right:
            production = Production(left, right, parent)
            production.replace(parent)
            if label != production.label:
                print line
                print production
            if not ccg.isIdentical(production.left, left) or not ccg.isIdentical(production.right, right):
                print line
                print production
             
def readProductions(location):
    for line in open(location):
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        front, production = line.split(' # ')
        pieces = front.split()
        freq = int(pieces.pop())
        if pieces:
            label = pieces[0]
        else:
            label = None
        parent, children = production.split(' --> ')
        parent = ccg.category.from_string(parent)
        pieces = children.split()
        left = ccg.category.from_string(pieces.pop(0))
        if pieces:
            right = ccg.category.from_string(pieces[0])
        else:
            right = None
        yield label, parent, left, right, line

def setComplexAdj(value):
    global complexAdj
    complexAdj = value

complexAdj = True
if __name__ == '__main__':
    if 1:
        parent = ccg.category.from_string(r'NP\NP')
        cat1 = ccg.category.from_string(r'(S[dc]\NP)^(NP\NP)')
        cat2 = None
        production = Production(cat1, cat2, parent)
        print production
        production.replace(ccg.category.from_string(r'N\N'))
        print production.label
        print production.left
        print production.right
    if 0:
        cat1 = ccg.category.from_string('NP[nb]/N')
        cat2 = ccg.category.from_string('N')
        result = ccg.category.from_string('NP')
        production = Production(cat1, cat2, result)
        production.replace(ccg.category.from_string('NP/(S\NP)'))
        print production.label
        print production.left
        print production.right
    if 0:
        testReplacements()
