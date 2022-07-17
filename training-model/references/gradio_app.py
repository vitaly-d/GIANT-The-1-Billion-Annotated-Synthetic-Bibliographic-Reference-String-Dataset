import io
import gradio as gr
import spacy
from spacy import displacy

from bib_tokenizers import create_references_tokenizer


nlp = spacy.load("output/model-best")
# return score for each token:
# with threshold set to zero each suggested span is returned, and span == token,
# because suggester is configured to suggest spans with len(span) == 1:
#     [components.spancat.suggester]
#     @misc = "spacy.ngram_suggester.v1"
#     sizes = [1]
nlp.get_pipe("spancat").cfg["threshold"] = 0.0  #  see )
print(nlp.get_pipe("spancat").cfg)


def create_bib_item_start_scorer_for_doc(doc, spanskey="sc"):

    span_group = doc.spans[spanskey]
    assert not span_group.has_overlap
    assert len(span_group) == len(
        doc
    ), "Check suggester config and the spancat threshold to make sure that spangroup contains single token span for each token"

    spans_idx = {
        offset: span.start
        for span in span_group
        for offset in range(span.start_char, span.end_char + 1)
    }

    def scorer(char_offset, fuzzy_in_tokens=(0, 0)):
        i = spans_idx[char_offset]

        span = span_group[i]
        assert i == span.start

        # fuzzines might improve fault tolerance if the model made a small mistake,
        # e.g., if a number from prev line is classified as "citation number",
        #    see example at https://www.deeplearningbook.org/contents/bib.html
        # if fuzzy == (0,0), it return score for the selected span only
        return span, max(
            span_group.attrs["scores"][i]
            for i in range(i - fuzzy_in_tokens[0], i + fuzzy_in_tokens[1] + 1)
            if i >= 0 and i < len(doc.text)
        )

    return scorer


nlp_blank = spacy.blank("en")
nlp_blank.tokenizer = create_references_tokenizer()(nlp_blank)


def split_up_references(
    references: str, nlp, nlp_blank=spacy.blank("en"), is_eol_mode=False
):
    """
    Args:
        references - a references section, ideally without a header
        nlp - a model that splits up references into separate sentences
        nlp_blank - a blank nlp with the same tokenizer/language
    """

    normalized_references = references.replace("\n", " ")

    # the model trained on 'normalized' references - the ones without '\n'
    doc = nlp(normalized_references)

    # 'transfer' annotations from doc without '\n' (normalized references) to the original doc
    # the problem here is that docs differ in a number of tokens
    # however, it should be easy to align on characters level because both '\n' and ' ' are whitespace, so spans have the same boundaries

    target_doc = nlp_blank(references)
    target_tokens_idx = {
        offset: t.i for t in target_doc for offset in range(t.idx, t.idx + len(t))
    }

    # senter annotations
    for i, t in enumerate(target_doc):
        t.is_sent_start = i == 0
    if is_eol_mode:
        # use SpanCat scores to set sentence boundaries on the target doc
        char_offset = 0
        f = io.StringIO(references)
        token_scorer = create_bib_item_start_scorer_for_doc(doc)
        threshold = 0.5
        lines = [line for line in f]
        lines_len_in_tokens = [
            _len for _len in map(lambda line: len(nlp_blank.tokenizer(line)), lines)
        ]
        for line_num, line in enumerate(lines):
            fuzzy = (
                0 if line_num == 0 else lines_len_in_tokens[line_num - 1] // 4,
                lines_len_in_tokens[line_num] // 4,
            )
            _, score = token_scorer(char_offset, fuzzy_in_tokens=fuzzy)
            if score > threshold:
                target_doc[target_tokens_idx[char_offset]].is_sent_start = True
            char_offset += len(line)
    else:
        # copy SentenceRecognizer annotations from doc without '\n' to the target doc
        for t in doc:
            if t.is_sent_start:
                target_doc[target_tokens_idx[t.idx]].is_sent_start = True

    # copy ner annotations:
    target_doc.ents = [
        target_doc.char_span(ent.start_char, ent.end_char, ent.label_)
        for ent in doc.ents
        # remove entities crossing sentence boundaries
        if not any([t.is_sent_start for t in ent if t.i != ent.start])
    ]

    return target_doc


def text_analysis(text, is_eol_mode):

    html = ""

    doc_with_linebreaks = split_up_references(text, nlp, nlp_blank, is_eol_mode)

    for i, sent in enumerate(doc_with_linebreaks.sents):
        bib_item_doc = sent.as_doc()
        bib_item_doc.user_data = {"title": f"***** Bib Item {i+1}: *****"}
        html += displacy.render(bib_item_doc, style="ent")

    html = (
        "<div style='max-width:100%; max-height:360px; overflow:auto'>"
        + html
        + "</div>"
    )

    return html


iface = gr.Interface(
    text_analysis,
    [
        gr.components.Textbox(placeholder="Enter bibliography here...", lines=20),
        gr.components.Checkbox(
            label="One line cannot contain more than one bibitem (Multiline bibitems are supported regardless of this choice)"
        ),
    ],
    ["html"],
    examples=[
        [
            """[1] B. Foxman, R. Barlow, H. D'Arcy, B. Gillespie, and J. D. Sobel, "Urinary tract infection: self-reported incidence and associated costs," Ann Epidemiol, vol. 10, pp. 509-515, 2000. [2] B. Foxman, "Epidemiology of urinary tract infections: incidence, morbidity, and economic costs," Am J Med, vol. 113, pp. 5-13, 2002. [3] L. Nicolle, "Urinary tract infections in the elderly," Clin Geriatr Med, vol. 25, pp. 423-436, 2009."""
        ],
        [
            """Barth, Fredrik, ed.
	1969	Ethnic groups and boundaries: The social organization of culture difference. Oslo: Scandinavian University Press.
Bondokji, Neven
	2016	The Expectation Gap in Humanitarian Operations: Field Perspectives from Jordan. Asian Journal of Peace Building 4(1):1-28.
Bourdieu, Pierre
		The forms of capital In Handbook of Theory and Research for the Sociology of Education. J. Richardson, ed. Pp. 241-258. New York: Greenwood Publishesrs.
Carrion, Doris
	2015	Are Syrian Refguees a Security Threat to the MIddle East Vol. 2016. London Reuters.
CFR
	2016	The Global Humanitarian Regime: Priorities and Prospects for Reform. Council on Foerign Relations, International Institutues and Global Governance Program"""
        ],
        [
            """(2)	Hofmann, M.H. et al. Aberrant splicing caused by single nucleotide polymorphism c.516G>T [Q172H], a marker of CYP2B6*6, is responsible for decreased expression and activity of CYP2B6 in liver. J Pharmacol Exp Ther  325, 284-92 (2008).
(3) Zanger, U.M. & Klein, K. Pharmacogenetics of cytochrome P450 2B6 (CYP2B6): advances on polymorphisms, mechanisms, and clinical relevance. Front Genet  4, 24 (2013).
(4) Holzinger, E.R. et al. Genome-wide association study of plasma efavirenz pharmacokinetics in AIDS Clinical Trials Group protocols implicates several CYP2B6 variants. Pharmacogenet Genomics  22, 858-67 (2012).
"""
        ],
        [
            """[Ein05] Albert Einstein. Zur Elektrodynamik bewegter K ̈orper. (German)
[On the electrodynamics of moving bodies]. Annalen der Physik,
322(10):891–921, 1905. [GMS93] Michel Goossens, Frank Mittelbach, and Alexander Samarin. The LATEX Companion. Addison-Wesley, Reading, Massachusetts, 1993. [Knu] Donald Knuth. Knuth: Computers and typesetting."""
        ],
    ],
    allow_flagging="never",
).launch(share=False, server_name="0.0.0.0", server_port=7080)
