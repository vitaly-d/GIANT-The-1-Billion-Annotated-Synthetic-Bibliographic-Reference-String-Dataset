# non-overlapped spans generated by CSL. Can be considered as annotations for the NER task
tags_ent = [
    "citation-number",
    "citation-label",
    "family",
    "given",
    "title",
    "container-title",
    "issued",
    "URL",
    "DOI",
    # add in lowercase as well: html parser changes the tags case
    "url",
    "doi",
    "publisher",
    "page",
    "publisher-place",
    "number-of-pages",
    "collection-title",
    "collection-number",
    "genre",
    "authority",
    "volume",
    # "title-short", it is a valid tag, but we ended up with the only one in the dataset...
    "number",
    "note",
    "archive",
    "archive_location",
]

# spans which may enclose other annotated spans. Spacy allows to store overlapped spans within doc.spans
tags_span = [
    "author",
    "year",
    "month",
    "day",
    "issued",
    "bib",
] + tags_ent

# span tag used for adding sentence boundaries annotations: an annotated CSL style encloses each bib item with <bib>..</bib>
tag_sentence_start = "bib"

spankey_sentence_start = "sc"
