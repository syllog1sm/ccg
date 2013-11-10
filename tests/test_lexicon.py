import unittest

import ccg.lexicon

class LexiconTests(unittest.TestCase):
    def test_entry(self):
        lexicon = ccg.lexicon._Lexicon()
        entry = """((S\NP)\(S\NP))/NP
  2 (((S[X]{Y}\NP{Z}){Y}\(S[X]{Y}<1>\NP{Z}){Y}){_}/NP{W}<2>){_}
  1 ncmod _ %f %li
  2 dobj %l %f"""
        stag, annotated = lexicon._parse_entry(entry)
        self.assertEqual(stag, '((S\NP)\(S\NP))/NP')
        self.assertEqual(annotated,
            '(((S[X]{Y}\NP{Z}){Y}\(S[X]{Y}<1>\NP{Z}){Y}){_}/NP{W}<2>){_}')

    def test_all_annotated(self):
        lexicon = ccg.lexicon._Lexicon()
        for key, cat in lexicon.items():
            if '{' in key:
                if key != cat.annotated:
                    print cat.string
                self.assertEqual(key.replace('[nb]', ''),
                                 cat.annotated.replace('[nb]', ''))

    def test_all_supertags(self):
        lexicon = ccg.lexicon._Lexicon()
        for key, cat in lexicon.items():
            if '{' not in key:
                self.assertEqual(key.replace('[nb]', ''),
                                 cat.string.replace('[nb]', ''))

    def test_load(self):
        ccg.lexicon.load()
        cat = ccg.category.from_string('S[dcl]\NP')
        self.assertEqual(cat.annotated, '(S[dcl]{_}\NP{Y}<1>){_}')


if __name__ == '__main__':
    unittest.main()
