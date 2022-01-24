import typer
from pathlib import Path
from csl_client import make_bibliography, styles_list
from numpy.random import randint
from typing import List

import spacy
from spacy.tokens import Doc, DocBin

NUM_STYLES_FOR_DOC = 10

blank_nlp = spacy.blank("en")


def main(crossref_dir: Path):
    styles: List[str] = styles_list()
    len_styles = len(styles)
    print(f"CSL processor supports {len_styles} styles")

    for f in list(crossref_dir.glob("**/*.json")):
        bibliographies = make_bibliography(
            f, randint(0, len_styles, NUM_STYLES_FOR_DOC).tolist()
        )
        for bibliography in bibliographies:
            if "references" not in bibliography:
                print("a problem for style ", bibliography["style"])
                continue
            references = bibliography["references"]
            style = bibliography["style"]
            print(f, style, len(references))


if __name__ == "__main__":
    typer.run(main)
