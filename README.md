* Overview

Manipulate Combinatory Categorial Grammar categories and derivations, for natural language processing research.

The library is quite feature rich, but has a pretty messy API, and some bugs.

The "killer feature" is the implementation of the CCG grammar rules and variable binding. After sentence.unify_vars()
has been called, all categories will have all slots bound to "global" variables, which are unified to other
variable bindings, and may have words attached.

Aside from ugliness, there are two main sources of remaining problems:

1) Coordination is very difficult to get right with respect to unification, as we need a set of words, and we don't necessarily
unify when we coordinate (think "red bus and green train". We do not unify "bus" and "train"!).

2) When a word is missing from the "markedup" file, we do a terrible job of guessing its annotation.

