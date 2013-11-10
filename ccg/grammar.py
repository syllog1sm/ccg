def read(loc):
    productions = []
    for line in open(loc):
        if not line.strip():
            continue
        freq, production = line.strip().split(' # ')
        production = production.replace('[nb]', '')
        parent, children = production.split(' --> ')
        children = children.split()
        left = children[0]
        if left == '((S[b]\NP)/NP)/':
            left = '(S[b]\NP)/NP'
        if len(children) == 2:
            right = children[1]
        else:
            right = None
        productions.append((parent, left, right, int(freq)))
    return productions


