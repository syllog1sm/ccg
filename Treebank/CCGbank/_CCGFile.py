import re
import sys
import os
import re

from ._File import File
from ._CCGNode import CCGNode
from ._CCGSentence import CCGSentence

class CCGFile(File, CCGNode):
    mmRE = re.compile(r'(?<=[/\\])[\.]')
    def __init__(self, **kwargs):
        if 'string' in kwargs:
            text = kwargs.pop('string')
            path = kwargs.pop('path')
        else:
            path = kwargs.pop('path')
            text = open(path).read()
        # Hack for mmccg version
        text = self.mmRE.sub('', text)
        # Sometimes sentences start (( instead of ( (. This is an error, correct it
        filename = path.split('/')[-1]
        self.path = path
        self.filename = filename
        self.ID = filename
        self._IDDict = {}
        CCGNode.__init__(self, label='File', headIdx=0, **kwargs)
        self._parseFile(text)

    def _parseFile(self, text):
        lines = text.strip().split('\n')
        while lines:
            idLine = lines.pop(0)
            sentence = lines.pop(0)
            self._addSentence(idLine, sentence)

    def _addSentence(self, idLine, sentStr):
        try:
            globalID = idLine.split(' ')[0].split('=')[1]
        except:
            print sentStr
            print >> sys.stderr, idLine
            raise
        sentence = CCGSentence(globalID=globalID, string=sentStr,
                               localID=self.length())
        self.attachChild(sentence)
        
    pargSentsRE = re.compile(r'<s id="[^"]+\.\d+"> \d+\n(?:(\d.+?)\n)?<\\s>', re.DOTALL)
    def addPargDeps(self, pargPath=None):
        pargPath = self.path.rsplit('/', 2)[0].replace('AUTO', 'PARG')
        section = self.ID[4:6]
        fileLoc = os.path.join(pargPath, section, self.ID.replace('auto', 'parg'))
        text = open(fileLoc).read().strip()
        for i, matchObj in enumerate(CCGFile.pargSentsRE.finditer(text)):
            if not matchObj.groups()[0]:
                continue
            pargSent = matchObj.groups()[0]
            deps = [dep.split() for dep in pargSent.split('\n')]
            sentence = self.child(i)
            sentence.addPargDeps(deps)
