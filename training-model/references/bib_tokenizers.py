import spacy
from spacy.lang.char_classes import LIST_ELLIPSES
from spacy.lang.char_classes import HYPHENS, LIST_ICONS
from spacy.lang.char_classes import (
    ALPHA,
    ALPHA_LOWER,
    ALPHA_UPPER,
    CONCAT_QUOTES,
    PUNCT,
)
from spacy.util import compile_infix_regex, registry

infixes = (
    LIST_ELLIPSES
    + LIST_ICONS
    + [
        r"(?<=[0-9])[+\-\*^](?=[0-9-])",
        r"(?<=[{al}{q}])\.(?=[{au}{q}])".format(
            al=ALPHA_LOWER, au=ALPHA_UPPER, q=CONCAT_QUOTES
        ),
        r"(?<=[{a}]),(?=[{a}])".format(a=ALPHA),
        r"(?<=[{a}])(?:{h})(?=[{a}])".format(a=ALPHA, h=HYPHENS),
        r"(?<=[{a}0-9])[:<>=/](?=[{a}])".format(a=ALPHA),
        # [10]R. Nakamura and T. Kenzaka
        # (10)R. Nakamura and T. Kenzaka
        # 10.R. Nakamura and T. Kenzaka
        r"(?<=[{a}0-9])[:<>\]\)\.](?=[{a}])".format(a=ALPHA),
        # 10R. Nakamura and T. Kenzaka
        r"(?<=[0-9])(?=[{a}])".format(a=ALPHA),
    ]
)


@spacy.registry.tokenizers("references_tokenizer")
def create_references_tokenizer():
    def create_tokenizer(nlp):

        default_tokenizer_cfg = {"tokenizer": {"@tokenizers": "spacy.Tokenizer.v1"}}

        create_default_tokenizer = registry.resolve(default_tokenizer_cfg)["tokenizer"]
        tokenizer = create_default_tokenizer(nlp)

        infix_re = compile_infix_regex(infixes)
        tokenizer.infix_finditer = infix_re.finditer

        for s in [
            "[10]R. Nakamura and T. Kenzaka",
            "(10)R. Nakamura and T. Kenzaka",
            "10.R. Nakamura and T. Kenzaka",
            "10R. Nakamura and T. Kenzaka",
        ]:
            print(s, [t for t in tokenizer(s)])

        return tokenizer

    return create_tokenizer
