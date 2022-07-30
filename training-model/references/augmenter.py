# https://spacy.io/usage/training#data-augmentation
#
# Replaces ' ' with '\n[hanging_indent]' after author or title
#
from random import random
import numpy as np
import spacy
from spacy.training import Example, augment

from spacy_aligned_spans import get_aligned_spans_y2x


@spacy.registry.augmenters("space_augmenter.v1")
def create_augmenter(p=0.2, count=2, orth="\n", hanging_indent_geom_p=0.8):
    print("create spaces augmenter", locals())

    def augment(nlp, example):

        if random() > p:
            yield example
            return

        # Create augmented aug_doc

        _doc = example.reference
        _text = _doc.text
        spaces = [i for i, ch in enumerate(_text) if ch.isspace()]
        if not spaces:
            yield example
            return

        size = min(len(spaces), count)
        to_be_replaced = np.random.choice(spaces, size=size, replace=False)

        aug_text = [ch for ch in _text]
        for i in to_be_replaced:
            aug_text[i] = orth + (
                np.random.choice([" ", "\t"], size=1, p=[0.8, 0.2])[0].item()
                * (np.random.geometric(p=hanging_indent_geom_p, size=1)[0] - 1)
            )

        aug_text = "".join(aug_text)

        aug_doc = nlp.make_doc(aug_text)
        if aug_text == _text:
            yield example
            return

        # ajust _supported_ annotations after changing the tokenization
        example = Example(aug_doc, _doc)

        # copy ner annotations:
        try:
            aug_doc.ents = get_aligned_spans_y2x(example, _doc.ents)
            # copy span categoriser annotation
            for key in aug_doc.spans:
                aug_doc.spans[key] = get_aligned_spans_y2x(example, _doc.spans[key])
            # copy sentencerecognizer annotations
            sent_start = example.get_aligned("SENT_START")
            for i in range(len(aug_doc)):
                aug_doc[i].is_sent_start = sent_start[i] == 1

            # Original example followed by augmented example
            yield Example(nlp.make_doc(aug_text), aug_doc)
        except:
            # print("Cannot aligh entities: ", _text, aug_text)
            pass

        yield example

    return augment


if __name__ == "__main__":
    augment = create_augmenter(p=1, count=1000, orth="\n", hanging_indent_geom_p=0.5)
    nlp = spacy.load("en_core_web_sm")
    doc = nlp("Apple Computers is looking at buying U.K. startup for $1 billion")
    example = Example(doc, doc)
    for example in augment(nlp, example):
        print([f"{t.text}{t.whitespace_}|{t.ent_iob_}" for t in example.reference])
