# https://spacy.io/usage/training#data-augmentation
#
# Replaces ' ' with '\n[hanging_indent]' after author or title
#
from random import random
import numpy as np
import spacy
from spacy.training import Example, augment

from spacy_aligned_spans import get_aligned_spans_y2x


@spacy.registry.augmenters("spaces_augmenter.v1")
def create_augmenter(p=0.2, count=2, eol="\n", hanging_indent_geom_p=0.8):
    print(
        "create spaces augmenter: it replaces a space char to 'eol space*' or 'eol tab*",
        locals(),
    )

    def augment(nlp, example):

        # Original example followed by augmented example
        yield example

        if random() > p:
            return

        # Create augmented aug_doc

        _doc = example.reference
        _text = _doc.text
        spaces = [i for i, ch in enumerate(_text) if ch.isspace()]
        if not spaces:
            return

        # augment text by replacing spaces at randomly selected positions
        size = min(len(spaces), count)
        to_be_replaced = np.random.choice(spaces, size=size, replace=False)
        aug_text = [ch for ch in _text]
        for i in to_be_replaced:
            aug_text[i] = eol + (
                np.random.choice([" ", "\t"], size=1, p=[0.8, 0.2])[0].item()
                * (np.random.geometric(p=hanging_indent_geom_p, size=1)[0] - 1)
            )
        aug_text = "".join(aug_text)
        if aug_text == _text:
            return

        # ajust _supported_ annotations after changing the tokenization
        aug_doc = nlp.make_doc(aug_text)
        _aug_doc_to_doc = Example(aug_doc, _doc)
        # align and copy annotation
        try:
            # copy ner annotations:
            aug_doc.ents = get_aligned_spans_y2x(_aug_doc_to_doc, _doc.ents)
            # copy span categoriser annotation
            for key in aug_doc.spans:
                aug_doc.spans[key] = get_aligned_spans_y2x(
                    _aug_doc_to_doc, _doc.spans[key]
                )
            # copy sentencerecognizer annotations
            sent_start = _aug_doc_to_doc.get_aligned("SENT_START")
            for i in range(len(aug_doc)):
                aug_doc[i].is_sent_start = sent_start[i] == 1

            yield Example(nlp.make_doc(aug_text), aug_doc)
        except:
            # print("Cannot aligh entities: ", _text, aug_text)
            pass

    return augment


if __name__ == "__main__":
    augment = create_augmenter(p=1, count=1000, eol="\n", hanging_indent_geom_p=0.5)
    nlp = spacy.load("en_core_web_sm")
    doc = nlp("Apple Computers is looking at buying U.K. startup for $1 billion")
    example = Example(doc, doc)
    for example in augment(nlp, example):
        print([f"{t.text}{t.whitespace_}|{t.ent_iob_}" for t in example.reference])
