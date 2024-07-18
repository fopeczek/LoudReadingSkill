# Given the stream of characters, this module breaks the stream into pieces that make sense to be read aloud.
# Algorithm is based on the Knuth-Plass algorithm for line breaking in TeX.
# Input is cut into non-breakable parts (words) and breakable parts (spaces, punctuation).
#
# Analysis is done paragraph-after-paragraph, which is denoted as double newline.
#


from typing import Iterator


def tokenize(text: str) -> Iterator:
    pass
