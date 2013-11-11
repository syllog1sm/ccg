from _AutoFileWriter import AutoFileWriter
import os
from os.path import join as pjoin

class PargFileWriter(AutoFileWriter):


    def writeFile(self, fileID, sentences):
        path = self._getPath(fileID)
        output = open(path, 'w')
        for sentence in sentences:
            output.write(sentence + '\n')
        output.close()

    def getSentenceStr(self, sentence):
        idLine = self._getIDLine(sentence)
        deps = []
        for word in sentence.listWords():
            for argHead, depType, argNum in word.parg.goldDependencies():
                depStr = self._makeDep(word, argHead, argNum, depType)
                deps.append(depStr)
        deps.sort()
        deps.insert(0, idLine)
        deps.append('<\s>')
        return '\n'.join(deps)
        

    def _getPath(self, fileID):
        dirSect = fileID[4:6]
        directory = pjoin(self.directory, dirSect)
        if not os.path.exists(directory):
            os.mkdir(directory)
        return pjoin(directory, fileID.replace('auto', 'parg'))

    def _getIDLine(self, sentence):
        idLine = '<s id="%s"> %d' % (sentence.globalID, sentence.getWord(-1).wordID)
        return idLine
        

    def _makeDep(self, head, arg, argNum, depType):
        """
        A depedency between the ith word and the jth word (wordI and wordJ)
        where the jth word has the lexical (functor) category catJ, and the
        ith word is head of the constituent which fills the kth argument slot
        of catJ is described as:
        i j cat_j arg_k word_i word_j
        """
        i = arg.wordID
        j = head.wordID
        catJ = str(head.parg)
        argK = argNum
        wordI = arg.text
        wordJ = head.text
        dep = '%d \t %d \t %s \t %d \t %s %s' % (i, j, catJ, argNum, wordI, wordJ)
        if depType != 'L':
            dep = dep + ' ' + depType
        return dep
