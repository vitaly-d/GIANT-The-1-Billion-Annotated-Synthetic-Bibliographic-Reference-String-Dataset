from concurrent.futures import Future, ProcessPoolExecutor
import logging
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
from lxml import etree
from numpy.random import randint
import spacy
from spacy.tokens import Doc, DocBin
import typer
import numpy

from csl_client import make_bibliography, styles_list
from lxml_iter_tree import annotations
from schema import tag_sentence_start, tags_span, tags_ent

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

    # add not-overlapped spans as doc.ents for NER
    doc.set_ents([span for span in spans if span.label_ in tags_ent])

    # replace the 'bib' span with sentence boundaries annotations for Sentencizer
    spans_to_be_deleted = []
    for span in spans:
        if span.label_ == tag_sentence_start:
            span[0].is_sent_start = True
            spans_to_be_deleted.append(span)
    for span in spans_to_be_deleted:
        spans.remove(span)

    # add annotations as possible overlapped spans for SpanCategorizer
    doc.spans["bib"] = spans

    # from pprint import pprint
    # pprint([(span.label_, span.text) for span in spans if span])

    return doc


def convert(
    crossref_files: List[Path], docbin_path: Path = Path("bibliographies.docbin")
):
    styles: List[str] = styles_list()
    len_styles = len(styles)
    print(f"CSL processor supports {len_styles} styles")

    db = DocBin(store_user_data=True)
    for f in tqdm(crossref_files, desc=docbin_path.name):
        try:
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
                    db.add(doc)
                else:
                    log.warning("Can't process %s", f)
        except:
            log.exception("An exception while processing %s", f)

    db.to_disk(docbin_path)
    return docbin_path


def main(
    crossref_dir: Path, output_dir: Path = Path(), parts: int = 100, parallel: int = 2
):
    input_files = [path for path in crossref_dir.glob("**/*.json")]
    input_files_parts = [
        arr.tolist() for arr in numpy.array_split(numpy.array(input_files), parts)
    ]
    futures: List[Future] = []
    with ProcessPoolExecutor(parallel) as e:
        for i, input_files_part in enumerate(input_files_parts):
            futures.append(
                e.submit(
                    convert, input_files_part, output_dir / f"references.{i}.docbin"
                )
            )
        for f in futures:
            print("convert:done:", f.result())


if __name__ == "__main__":
    typer.run(main)
