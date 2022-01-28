# https://spacy.io/usage/training#data-augmentation
#
# Replaces ' ' with '\n[hanging_indent]' after author or title
# 
# Problem to solve:
# References could be multi-line. E.g., see https://libhelp.ncl.ac.uk/faq/183908 :
# "In order to create a hanging indent on the second line of each reference in your bibliography (i.e. in order to get your author names to stand out)"

from random import random

import spacy
from spacy.tokens import Doc
from spacy.training import Example

def insert_hanging_indent(example_dict, pos, orth = "\n  "): 

    example_dict["doc_annotation"]["entities"].insert(pos, "O" )
    example_dict["token_annotation"]["ORTH"].insert(pos, orth)
    if pos > 0:
        example_dict["token_annotation"]["SPACY"][pos-1] = False 
    example_dict["token_annotation"]["SPACY"].insert(pos, False )
    example_dict["token_annotation"]["TAG"].insert(pos, "")
    example_dict["token_annotation"]["LEMMA"].insert(pos, "")
    example_dict["token_annotation"]["POS"].insert(pos, "")
    example_dict["token_annotation"]["MORPH"].insert(pos, "")
    example_dict["token_annotation"]["DEP"].insert(pos, "")
    example_dict["token_annotation"]["SENT_START"].insert(pos, 0)
    example_dict["token_annotation"]["HEAD"] = list(range(len(example_dict["token_annotation"]["ORTH"])))


@spacy.registry.augmenters("hanging_indent_augmenter.v1")
def create_augmenter(level =.1, orth = "\n", insert_after_span_names = ["title", "author"]):
    """
    create augmenter. It will work only if example.reference.spans["bib"] contains `insert_after` spans 
    """
    def augment(nlp, example):
        
        if random() > level:
            # no augment, just return example
            yield example
            return

        # Create augmented training example
        example_dict = example.to_dict()
        
        _doc = example.reference
        for span in reversed(_doc.spans["bib"]):
            if span.label_ in insert_after_span_names:
                
                # print(span.label_, span)
                pos = span.end
                # try to keep punctuation on prev previous line"
                for i in range(pos, len(_doc)):
                    # print(span, _doc[i], _doc[i].is_punct)
                    if _doc[i].is_punct:
                        pos += 1
                    else:
                        break
                    
                insert_hanging_indent(example_dict, pos, orth)

        # Original example followed by augmented example
        yield example
        doc = Doc(nlp.vocab, example_dict["token_annotation"]["ORTH"], example_dict["token_annotation"]["SPACY"])
        yield Example.from_dict(doc, example_dict)

    return augment
