from typing import Iterable

import io


def preprocess_merge_lines(text) -> str:
    """
    In [7]: text = "I \t like   \n   cheese."
    In [8]: merge_lines(text)
    Out[8]: 'I \t like cheese.'
    """
    f = io.StringIO(text)
    lines = (line for line in f)
    return preprocess_merge_lines_list(lines)


def preprocess_merge_lines_list(lines: Iterable[str]) -> str:
    return " ".join((line.strip() for line in lines if line.strip()))
