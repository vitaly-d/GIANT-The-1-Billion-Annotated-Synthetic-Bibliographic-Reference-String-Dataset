import logging
from pathlib import Path
from typing import List, Optional

from lxml import etree
from numpy.random import randint
import spacy
from spacy.tokens import Doc, DocBin
import typer

from csl_client import make_bibliography, styles_list
from lxml_iter_tree import annotations
from schema import tag_sentence_start, tags_span

NUM_STYLES_FOR_DOC = 10

log = logging.getLogger(__name__)
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
    # doc.char_span can return None if character indices can't be snaped to token boundaries
    spans = [span for span in spans if span]

    doc.spans["bib"] = spans

    for span in spans:
        if span.label_ == tag_sentence_start:
            span[0].is_sent_start = True

    from pprint import pprint

    pprint([(span.label_, span.text) for span in spans if span])

    return doc


def split_up_large_doc(doc: Doc, max_tokens=512) -> List[Doc]:
    # TODO
    return [doc]


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
            if doc:
                docs = split_up_large_doc(doc)
                # TODO save as DocBin
            else:
                log.warning("Can't process %s", f)


if __name__ == "__main__":
    typer.run(main)
