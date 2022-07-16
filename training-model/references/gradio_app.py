import spacy
from spacy import displacy

import gradio as gr
from bib_tokenizers import create_references_tokenizer


def split_up_references(references: str, nlp, nlp_blank=spacy.blank("en")):
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

    doc_with_linebreaks = nlp_blank(references)
    # senter annotations
    for t in doc:
        if t.is_sent_start:
            span = doc_with_linebreaks.char_span(t.idx, t.idx + len(t))
            span[0].is_sent_start = True
    if doc_with_linebreaks and not doc_with_linebreaks[0].is_sent_start:
        # 1st token
        doc_with_linebreaks[0].is_sent_start = True

    # ner annotations:
    doc_with_linebreaks.ents = [
        doc_with_linebreaks.char_span(ent.start_char, ent.end_char, ent.label_)
        for ent in doc.ents
    ]

    return doc_with_linebreaks


nlp = spacy.load("output/model-best")
nlp_blank = spacy.blank("en")
nlp_blank.tokenizer = create_references_tokenizer()(nlp_blank)


def text_analysis(text):

    html = ""

    doc_with_linebreaks = split_up_references(text, nlp, nlp_blank)
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
    [gr.inputs.Textbox(placeholder="Enter bibliography here...", lines=20)],
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
    layout="vertical",  # TBD: vertical seems does not work
    allow_flagging="never",
).launch(share=False, server_name="0.0.0.0", server_port=7080)
