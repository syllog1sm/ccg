import sys
import re
import os.path

import ccg.lexicon
from ._Corpus import Corpus
from ._CCGNode import CCGNode
from ._CCGFile import CCGFile



class CCGbank(Corpus, CCGNode):
    fileClass = CCGFile
    def __init__(self, path=None, **kwargs):
        self._children = []
        self.path = path
        for fileLoc in self._getFileList(self.path):
            self.attachChild(fileLoc)
        ccg.lexicon.load(os.path.join(path, 'markedup'))

    def child(self, index):
        """
        Read a file by zero-index offset
        """
        path = self._children[index]
        print >> sys.stderr, path
        return self.fileClass(path=path)

    def sentence(self, key):
        fileName, sentID = key.split('.')
        section = fileName[4:6]
        fileID = os.path.join(self.path, 'data', 'AUTO', section, fileName +
                              '.auto')
        f = self.file(fileID)
        #pargLoc = fileID.rsplit('/', 2)[0].replace('AUTO', 'PARG')
        #f.addPargDeps(pargLoc)
        return f.sentence(key)

    def tokens(self):
        """
        Generate tokens without parsing the files properly
        """
        tokenRE = re.compile(r'<L (\S+) \S+ (\S+) (\S+) \S+>')
        for path in self._children:
            string = open(path).read()
            for cat, pos, form in tokenRE.findall(string):
                yield form, pos, cat

    def section(self, sec):
        for i, fileLoc in enumerate(self._children):
            path, fileName = os.path.split(fileLoc)
            if int(fileName[4:6]) == sec:
                yield self.child(i)


    def section00(self):
        for i in xrange(99):
            yield self.child(i)

    def twoTo21(self):
        for i in xrange(199, 2074):
            yield self.child(i)

    def section23(self):
        for i in xrange(2157, 2257):
            yield self.child(i)

    def section24(self):
        for i in xrange(2257, self.length()):
            yield self.child(i)

    def _getFileList(self, location):
        """
        Get all files below location
        """
        paths = []
        for path in [os.path.join(location, f) for f in os.listdir(location)]:
            if path.endswith('CVS'):
                continue
            elif path.startswith('.'):
                continue
            if os.path.isdir(path):
                paths.extend(self._getFileList(path))
            elif path.endswith('.mrg') or path.endswith('.auto'):
                paths.append(path)
        paths.sort()
        return paths

            
