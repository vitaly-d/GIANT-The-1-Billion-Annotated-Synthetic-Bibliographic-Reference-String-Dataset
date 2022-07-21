import io

import gradio as gr
import numpy as np
import spacy
from spacy import displacy
from spacy.training import Example, alignment

from bib_tokenizers import create_references_tokenizer
from schema import spankey_sentence_start, tag_sentence_start, tags_ent


nlp = None
nlp = spacy.load("output/model-best")
# return score for each token:
# with threshold set to zero each suggested span is returned, and span == token,
# because suggester is configured to suggest spans with len(span) == 1:
#     [components.spancat.suggester]
#     @misc = "spacy.ngram_suggester.v1"
#     sizes = [1]
nlp.get_pipe("spancat").cfg["threshold"] = 0.0  #  see )
print(nlp.get_pipe("spancat").cfg)


def create_bib_item_start_scorer_for_doc(doc):

    span_group = doc.spans[spankey_sentence_start]
    assert not span_group.has_overlap
    assert len(span_group) == len(
        doc
    ), "Check suggester config and the spancat threshold to make sure that spangroup contains single token span for each token"

    def scorer(token_index_in_doc, fuzzy_in_tokens=(0, 0)):
        i = token_index_in_doc

        span = span_group[i]  # our spans are one token length
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
    references: str, is_eol_mode=False, nlp=nlp, nlp_blank=nlp_blank
):
    """
    Args:
        references - a references section, ideally without a header
        nlp - a model that splits up references into separate sentences
        nlp_blank - a blank nlp with the same tokenizer/language
    """

    target_doc = nlp_blank(references)
    target_tokens_idx = {
        offset: t.i for t in target_doc for offset in range(t.idx, t.idx + len(t))
    }
    f = io.StringIO(references)
    lines = [line for line in f]

    # strip lines and remove any extra space between lines
    norm_doc = nlp(" ".join([line.strip() for line in lines if line.strip()]))

    example = Example(target_doc, norm_doc)

    if is_eol_mode:
        alignment_data = example.alignment.y2x.data
        print(alignment_data)

        # use SpanCat scores to set sentence boundaries on the target doc
        # init senter annotations
        for i, t in enumerate(target_doc):
            t.is_sent_start = i == 0

        char_offset = 0
        token_scorer = create_bib_item_start_scorer_for_doc(norm_doc)
        threshold = 0.5
        for line_num, line in enumerate(lines):
            if not line.strip():
                # ignore empty line
                char_offset += len(line)
                continue

            token_index_in_target_doc = target_tokens_idx[char_offset]
            # scroll to the first non-space (if the line starts from space):
            while (
                token_index_in_target_doc < len(target_doc)
                and target_doc[token_index_in_target_doc].is_space
            ):
                token_index_in_target_doc += 1

            index_in_norm_doc = np.where(alignment_data == token_index_in_target_doc)
            if type(index_in_norm_doc) == tuple:
                index_in_norm_doc = index_in_norm_doc[0]  # depends on numpy version...

            if index_in_norm_doc.size > 0:
                index_in_norm_doc = index_in_norm_doc[0].item()
                span, score = token_scorer(index_in_norm_doc)
                print(span, score, index_in_norm_doc)
                if score > threshold:
                    target_doc[target_tokens_idx[char_offset]].is_sent_start = True
            char_offset += len(line)
    else:
        # copy SentenceRecognizer annotations from doc without '\n' to the target doc
        sent_start = example.get_aligned("SENT_START")
        for i, t in enumerate(target_doc):
            target_doc[i].is_sent_start = sent_start[i] == 1

    # copy ner annotations:
    for label in tags_ent:
        target_doc.vocab[label]
    target_doc.ents = example.get_aligned_spans_y2x(norm_doc.ents)

    return target_doc


def text_analysis(text, is_eol_mode):

    if not text:
        return "<div style='max-width:100%; overflow:auto; color:grey'><p>Unparsed Bibliography Section is empty</p></div>"

    doc_with_linebreaks = split_up_references(
        text, is_eol_mode=is_eol_mode, nlp=nlp, nlp_blank=nlp_blank
    )

    html = ""
    options = {
        "ents": tags_ent,
        "colors": {
            "citation-number": "yellow",
            "citation-label": "yellow",
            "family": "DeepSkyBlue",
            "given": "LightSkyBlue",
            "title": "PeachPuff",
            "container-title": "Moccasin",
            "publisher": "PaleTurquoise",
            "issued": "Gold",
        },
    }
    for i, sent in enumerate(doc_with_linebreaks.sents):
        bib_item_doc = sent.as_doc()
        ref = displacy.render(bib_item_doc, style="ent", options=options)
        html += f"<tr><td>{i}</td><td>{ref}</td></tr>"

    html = (
        """<div style='max-width:100%; max-height:720px; overflow:auto'>
        <style>table {
              font-family: arial, sans-serif;
              border-collapse: collapse;
              width: 100%;
            }

            td, th {
              border: 1px solid #b0b0b0;
              text-align: left;
              padding: 8px;
            }

            tr:nth-child(even) {
              background-color: #f2f2f2;
            }</style>"""
        + "<table><tr><th>Index</th><th>Parsed Reference</th></tr>"
        + html
        + "</table>"
        + "</div>"
    )

    return html


gr.close_all()
demo = gr.Blocks()
with demo:

    textbox = gr.components.Textbox(
        label="Unparsed Bibliography Section",
        placeholder="Enter bibliography here...",
        lines=20,
    )
    is_eol_mode = gr.components.Checkbox(
        label="a line does not contain more than one bibitem (Multiline bibitems are supported regardless of this choice)"
    )
    html = gr.components.HTML(label="Parsed Bib Items")
    textbox.change(fn=text_analysis, inputs=[textbox, is_eol_mode], outputs=[html])
    is_eol_mode.change(fn=text_analysis, inputs=[textbox, is_eol_mode], outputs=[html])

    gr.Examples(
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
322(10):891–921, 1905. 
[GMS93] Michel Goossens, Frank Mittelbach, and Alexander Samarin. The LATEX Companion. Addison-Wesley, Reading, Massachusetts, 1993. 
[Knu] Donald Knuth. Knuth: Computers and typesetting."""
            ],
            [
                """References.
Bartkiewicz, A., Szymczak, M., Cohen, R. J., & Richards, A. M. S. 2005, MN- RAS, 361, 623
Bartkiewicz, A., Szymczak, M., & van Langevelde, H. J. 2016, A&A, 587, A104
Benjamin, R. A., Churchwell, E., Babler, B. L., et al. 2003, PASP, 115, 953 
Beuther, H., Mottram, J. C., Ahmadi, A., et al. 2018, A&A, 617, A100
Beuther, H., Walsh, A. J., Thorwirth, S., et al. 2007, A&A, 466, 989
Brogan, C. L., Hunter, T. R., Cyganowski, C. J., et al. 2011, ApJ, 739, L16
Brown, A. T., Little, L. T., MacDonald, G. H., Riley, P. W., & Matheson, D. N.
1981, MNRAS, 195, 607
Brown, R. D. & Cragg, D. M. 1991, ApJ, 378, 445
Carrasco-González, C., Sanna, A., Rodríguez-Kamenetzky, A., et al. 2021, ApJ,
914, L1
Cesaroni, R., Walmsley, C. M., & Churchwell, E. 1992, A&A, 256, 618
Cheung, A. C., Rank, D. M., Townes, C. H., Thornton, D. D., & Welch, W. J.
1968, Phys. Rev. Lett., 21, 1701
Churchwell, E., Babler, B. L., Meade, M. R., et al. 2009, PASP, 121, 213
Cohen, R. J. & Brebner, G. C. 1985, MNRAS, 216, 51P
Comito, C., Schilke, P., Endesfelder, U., Jiménez-Serra, I., & Martín-Pintado, J.
2007, A&A, 469, 207
Curiel, S., Ho, P. T. P., Patel, N. A., et al. 2006, ApJ, 638, 878
Danby, G., Flower, D. R., Valiron, P., Schilke, P., & Walmsley, C. M. 1988,
MNRAS, 235, 229
De Buizer, J. M., Liu, M., Tan, J. C., et al. 2017, ApJ, 843, 33
De Buizer, J. M., Radomski, J. T., Telesco, C. M., & Piña, R. K. 2003, ApJ, 598,
1127
Dzib, S., Loinard, L., Rodríguez, L. F., Mioduszewski, A. J., & Torres, R. M.
2011, ApJ, 733, 71
Flower, D. R., Offer, A., & Schilke, P. 1990, MNRAS, 244, 4P
Galván-Madrid, R., Keto, E., Zhang, Q., et al. 2009, ApJ, 706, 1036"""
            ],
        ],
        inputs=textbox,
    )
gr.close_all()
demo.launch(share=False, server_name="0.0.0.0", server_port=7080)
