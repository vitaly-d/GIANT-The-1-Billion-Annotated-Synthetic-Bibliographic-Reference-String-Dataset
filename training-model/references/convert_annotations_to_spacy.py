from pathlib import Path
from typing import List, Optional, Sequence

from lxml import etree
from numpy.random import randint
import spacy
from spacy.tokens import Doc, DocBin
import typer

from csl_client import make_bibliography, styles_list
from lxml_iter_tree import annotations
from schema import tags_span

NUM_STYLES_FOR_DOC = 10

blank_nlp = spacy.blank("en")


def references_to_spacy(references, style: str) -> Optional[Doc]:
    xml = f"<references><bib>{'</bib><bib>'.join(references)}</bib></references>"
    try:
        parser = etree.HTMLParser()
        root = etree.fromstring(xml, parser)
    except etree.XMLSyntaxError as e:
        print("cannot parse ", references, e)
        return
    # create doc from text
    doc = blank_nlp("".join(root.itertext()))
    # add annotations: they are overlapped spans
    spans = [
        doc.char_span(start, end, label=tag, alignment_mode="contract")
        for tag, start, end in annotations(root, tags_to_be_included=tags_span)
    ]
    from pprint import pprint

    pprint([(span.label_, span.text) for span in spans if span])


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
            doc = references_to_spacy(references, style)


if __name__ == "__main__":
    typer.run(main)
