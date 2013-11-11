import hotshot.stats
import hotshot

import Treebank.CCGbank
import ccg.lexicon

def load_files():
    location = '/home/matt/code/repos/data/CCGbank1.2_np_v0.7'
    corpus = Treebank.CCGbank.CCGbank(path=location)
    ccg.lexicon.load()
    for i, child in enumerate(corpus.children()):
        if i == 100:
            break
        pass

def pfile(function):
    prof = hotshot.Profile('/tmp/test.prof')
    prof.runcall(function)
    prof.close()
    stats = hotshot.stats.load('/tmp/test.prof')
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats(20)

if __name__ == '__main__':
    pfile(load_files)
