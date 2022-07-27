import io
import logging
import math
import timeit
from typing import Optional

import gradio as gr
import numpy as np
import spacy
from spacy import displacy
from spacy.matcher import Matcher
from spacy.training import Example

from bib_tokenizers import create_references_tokenizer
from schema import spankey_sentence_start, tags_ent

# 1.0.1
# pip install https://huggingface.co/vitaly/en_bib_references_trf/resolve/main/en_bib_references_trf-any-py3-none-any.whl
# MODEL = "en_bib_references_trf"
MODEL = "output/model-best"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
_LOG_STR_LEN = 16

nlp = spacy.load(MODEL)
# return score for each token:
# with threshold set to zero each suggested span is returned, and span == token,
# because suggester is configured to suggest spans with len(span) == 1:
#     [components.spancat.suggester]
#     @misc = "spacy.ngram_suggester.v1"
#     sizes = [1]
nlp.get_pipe("spancat").cfg["threshold"] = 0.0  #  see )
log.info("spancat config: %s", nlp.get_pipe("spancat").cfg)


def create_bib_item_start_scorer_for_doc(doc):
    """
    the spancat pipe based scorer
    """

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
            if i >= 0 and i < len(doc)
        )

    return scorer


nlp_blank = spacy.blank("en")
nlp_blank.tokenizer = create_references_tokenizer()(nlp_blank)
# nlp_blank.tokenizer = nlp.tokenizer


def _tokenize_test(nlp):
    _text = """MNRAS, 216, 51P
Comito"""
    tokens = [f"'{t}'" for t in nlp(_text)]
    log.info("tokens: %s", tokens)
    return tokens


assert len(_tokenize_test(nlp)) == len(
    _tokenize_test(nlp_blank)
), "Check that the same tokenizer is used for both: trained model (in its config) and nlp_blank"


def _token_index_in_norm_doc(
    token_index_in_target_doc: int, alignment_data: np.ndarray
) -> Optional[int]:

    index_in_norm_doc = np.where(alignment_data == token_index_in_target_doc)
    if type(index_in_norm_doc) == tuple:
        index_in_norm_doc = index_in_norm_doc[0]  # depends on numpy version...

        if index_in_norm_doc.size > 0:
            return index_in_norm_doc[0].item()


def split_up_references(
    references: str, is_eol_mode=True, ner=True, nlp=nlp, nlp_blank=nlp_blank
):
    """
    Args:
        references - a references section, ideally without a header
        nlp - a model that splits up references into separate sentences
        nlp_blank - a blank nlp with the same tokenizer/language
    """

    _timeit_start = timeit.default_timer()
    log.info(
        "start processing: '%s...'",
        references[: _LOG_STR_LEN if len(references) > _LOG_STR_LEN else -1],
    )

    target_doc = nlp_blank(references)
    target_tokens_idx = {
        offset: t.i for t in target_doc for offset in range(t.idx, t.idx + len(t))
    }
    f = io.StringIO(references)
    lines = [line for line in f]

    # disable unused components to speedup inference && parse normalized referenences
    disable = []
    if not is_eol_mode:
        disable.append("spancat")
    with nlp.select_pipes(disable=disable):
        # normalization applied: strip lines and remove any extra space between lines
        norm_doc = nlp(" ".join([line.strip() for line in lines if line.strip()]))

    # extremely useful spacy API for alignment normalized and target(created from non-modified input) docs
    example = Example(target_doc, norm_doc)

    # copy ner annotations:
    for label in tags_ent:
        target_doc.vocab[label]
    target_doc.ents = example.get_aligned_spans_y2x(norm_doc.ents)

    # set senter annotations
    if is_eol_mode:
        alignment_data = example.alignment.y2x.data

        # use SpanCat scores to set sentence boundaries on the target doc
        # init senter annotations
        for i, t in enumerate(target_doc):
            t.is_sent_start = i == 0

        spancat_token_scorer = create_bib_item_start_scorer_for_doc(norm_doc)

        def target_doc_token_scorer(token_index_in_target_doc):
            """
            returns max score if senter predicted sent start, orherwise spancat score
            """
            index_in_norm_doc = _token_index_in_norm_doc(
                token_index_in_target_doc, alignment_data
            )
            if index_in_norm_doc is not None:
                if target_doc[token_index_in_target_doc].is_sent_start:
                    return 1.0
                else:
                    span, score = spancat_token_scorer(index_in_norm_doc)
                    # print(span, score, index_in_norm_doc, is_sent_start)
                    return score
            return 0.0

        threshold = 0.5

        char_offset = 0
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

            score = target_doc_token_scorer(token_index_in_target_doc)
            # print(target_doc[token_index_in_target_doc], score)
            if score > threshold:
                target_doc[target_tokens_idx[char_offset]].is_sent_start = True

            char_offset += len(line)

        # try to miminize the variance of references lengths (in lines)
        step = 0
        sigma_prev = len(lines)
        while (
            step < 10
            and sigma_prev > 0.0
            and sigma_prev
            > (
                sigma := _level_off_references(
                    target_doc, target_doc_token_scorer, step=step
                )
            )
        ):
            step += 1
            sigma_prev = sigma

    else:
        # copy SentenceRecognizer annotations from doc without '\n' to the target doc
        sent_start = example.get_aligned("SENT_START")
        for i, t in enumerate(target_doc):
            target_doc[i].is_sent_start = sent_start[i] == 1

    log.info(
        "done: '%s...', elapsed: %s",
        references[: _LOG_STR_LEN if len(references) > _LOG_STR_LEN else -1],
        timeit.default_timer() - _timeit_start,
    )
    return target_doc


def _level_off_references(doc, token_scorer, step=1):
    """
    Problem:
    if a model that predicts the reference boundaries was .99 accurate,
    the success rate for real papers would be still relative low
    given that a typical bibliography consists of dozens of references.

    This function attemps to detect references that contain more lines than
    others and split them somehow... The result will not neccessary be better.
    """

    lengths = np.array([len(ref.text.strip().split("\n")) for ref in doc.sents])
    median = np.median(lengths).item()
    mean = np.mean(lengths).item()
    sigma = np.std(
        lengths
    ).item()  # read this: https://stackoverflow.com/questions/27600207/why-does-numpy-std-give-a-different-result-to-matlab-std

    log.info("step: %s, median: %s, mean: %s, sigma: %s", step, median, mean, sigma)
    if sigma == 0.0:
        return sigma

    sent_starts = []
    matcher = Matcher(nlp.vocab)
    pattern = [
        # {"TEXT": {"REGEX": "^(.*)(\\n)+(.*)$"}, "IS_SPACE": True},
        {"TEXT": {"REGEX": "^(.*\\n.*)+$"}, "IS_SPACE": True},
        {"IS_SPACE": True, "OP": "*"},
        {"IS_SPACE": False},
    ]
    matcher.add("line_start", [pattern])
    for n, ref in enumerate(doc.sents):
        # print([f"'{t}'" for t in ref])
        surprising = (lengths[n] - mean) / sigma
        if surprising > 1:
            log.info("surprising: %s: %s", surprising, ref.text[:_LOG_STR_LEN])
            scores = [token_scorer(t.i) for t in ref]
            median_score = np.median(scores)

            # for each first non-space token on each line
            start = None  # next reference start is we decided to split up the ref span
            for _, eol, token_i_after_eol in matcher(ref):
                i = token_i_after_eol - 1

                score_peak = math.log10(scores[i] / median_score)
                log.info(
                    "line start: token=%s, score=%s, median_score=%s, ahead=%s, score_peak=%s",
                    ref[i],
                    scores[i],
                    median_score,
                    len(ref[token_i_after_eol:]),
                    score_peak
                )

                # risky if score is too low.. minimize variance using the predicted spancat score
                # sum oranges and apples..
                score_is_enough_to_split = scores[i]>.1 or score_peak + surprising > 3
                if score_is_enough_to_split and len(ref[token_i_after_eol:]) > 10:
                    sent_starts.append(ref[i])
                    start = i  # needed only for reviewing ner entities, see below
                    continue

                # minimize variance using ner output, a bit less risky - to support
                # an edge case if a new line starts with citation number of names and
                # prev lines already contain names and title
                before_eol_ents = [
                    ent.label_ for ent in ref[0 if start is None else start : eol].ents
                ]
                # entities after eol, if any
                after_eol_ents = [ent.label_ for ent in ref[eol:].ents][:2]
                if (
                    set(before_eol_ents) & set(["issued", "title", "container-title"])
                    and set(before_eol_ents) & set(["family", "given"])
                    and set(after_eol_ents)
                    & set(
                        [
                            "family",
                            "given",
                            "citation-number",
                            "citation-label",
                        ]
                    )
                ):
                    log.info("splitting up using NER predictions: %s", ref[i])
                    sent_starts.append(ref[i])
                    start = i

    for t in sent_starts:
        t.is_sent_start = True

    return sigma


def text_analysis(text: str, more_than_one_ref_per_line: bool):

    if not text or not text.strip():
        return "<div style='max-width:100%; overflow:auto; color:grey'><p>Unparsed Bibliography Section is empty</p></div>"

    doc_with_linebreaks = split_up_references(
        text, is_eol_mode=not more_than_one_ref_per_line, nlp=nlp, nlp_blank=nlp_blank
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
    more_than_one_ref_per_line = gr.components.Checkbox(
        value=False,
        label="My bibliography may contain more than one reference per line - the model will make a prediction for each token: more predictions, more chances to make a mistake",
    )
    html = gr.components.HTML(label="Parsed Bib Items")
    textbox.change(
        fn=text_analysis, inputs=[textbox, more_than_one_ref_per_line], outputs=[html]
    )
    more_than_one_ref_per_line.change(
        fn=text_analysis, inputs=[textbox, more_than_one_ref_per_line], outputs=[html]
    )

    gr.Examples(
        examples=[
            [  # https://arxiv.org/pdf/1910.01108v4.pdf
                """Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova. Bert: Pre-training of deep bidirectional transformers for language understanding. In NAACL-HLT, 2018.
Alec Radford, Jeffrey Wu, Rewon Child, David Luan, Dario Amodei, and Ilya Sutskever. Language models are unsupervised multitask learners. 2019.
Yinhan Liu, Myle Ott, Naman Goyal, Jingfei Du, Mandar S. Joshi, Danqi Chen, Omer Levy, Mike Lewis, Luke S. Zettlemoyer, and Veselin Stoyanov. Roberta: A robustly optimized bert pretraining approach. ArXiv, abs/1907.11692, 2019.
Roy Schwartz, Jesse Dodge, Noah A. Smith, and Oren Etzioni. Green ai. ArXiv, abs/1907.10597, 2019. Emma Strubell, Ananya Ganesh, and Andrew McCallum. Energy and policy considerations for deep learning in
nlp. In ACL, 2019.
Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser,
and Illia Polosukhin. Attention is all you need. In NIPS, 2017.
Thomas Wolf, Lysandre Debut, Victor Sanh, Julien Chaumond, Clement Delangue, Anthony Moi, Pierric Cistac, Tim Rault, Rémi Louf, Morgan Funtowicz, and Jamie Brew. Transformers: State-of-the-art natural language processing, 2019.
Cristian Bucila, Rich Caruana, and Alexandru Niculescu-Mizil. Model compression. In KDD, 2006.
Geoffrey E. Hinton, Oriol Vinyals, and Jeffrey Dean. Distilling the knowledge in a neural network. ArXiv,
abs/1503.02531, 2015.
Yukun Zhu, Ryan Kiros, Richard S. Zemel, Ruslan Salakhutdinov, Raquel Urtasun, Antonio Torralba, and Sanja Fidler. Aligning books and movies: Towards story-like visual explanations by watching movies and reading books. 2015 IEEE International Conference on Computer Vision (ICCV), pages 19–27, 2015.
Alex Wang, Amanpreet Singh, Julian Michael, Felix Hill, Omer Levy, and Samuel R. Bowman. Glue: A multi-task benchmark and analysis platform for natural language understanding. In ICLR, 2018.
Matthew E. Peters, Mark Neumann, Mohit Iyyer, Matt Gardner, Christopher Clark, Kenton Lee, and Luke Zettlemoyer. Deep contextualized word representations. In NAACL, 2018.
Alex Wang, Ian F. Tenney, Yada Pruksachatkun, Katherin Yu, Jan Hula, Patrick Xia, Raghu Pappagari, Shuning Jin, R. Thomas McCoy, Roma Patel, Yinghui Huang, Jason Phang, Edouard Grave, Najoung Kim, Phu Mon Htut, Thibault F’evry, Berlin Chen, Nikita Nangia, Haokun Liu, Anhad Mohananey, Shikha Bordia, Nicolas Patry, Ellie Pavlick, and Samuel R. Bowman. jiant 1.1: A software toolkit for research on general-purpose text understanding models. http://jiant.info/, 2019.
Andrew L. Maas, Raymond E. Daly, Peter T. Pham, Dan Huang, Andrew Y. Ng, and Christopher Potts. Learning word vectors for sentiment analysis. In ACL, 2011.
Pranav Rajpurkar, Jian Zhang, Konstantin Lopyrev, and Percy Liang. Squad: 100, 000+ questions for machine comprehension of text. In EMNLP, 2016."""
            ],
            [  # https://isg.beel.org/blog/2019/12/10/giant-the-1-billion-annotated-synthetic-bibliographic-reference-string-dataset-for-deep-citation-parsing-pre-print/
                """Crossref, https://www.crossref.org
A JavaScript implementation of the Citation Style Language (CSL),
https://github.com/Juris-M/citeproc-js
Oﬃcial repository for Citation Style Language (CSL),
https://github.com/citation-style-language/styles
Anzaroot, S., McCallum, A.: A New Dataset for fine-Grained Citation field Extraction (2013)
Councill, I.G., Giles, C.L., Kan, M.Y.: Parscit: an open-source crf reference string parsing package. In: LREC. vol. 8, pp. 661–667 (2008)
Fedoryszak, M., Tkaczyk, D., Bolikowski, L.: Large scale citation matching using apache hadoop. In: International Conference on Theory and Practice of Digital Libraries. pp. 362–365. Springer (2013)
Hetzner, E.: A simple method for citation metadata extraction using hidden markov models. In: Proceedings of the 8th ACM/IEEE-CS joint conference on Digital libraries. pp. 280–284. ACM (2008)
Lample, G., Ballesteros, M., Subramanian, S., Kawakami, K., Dyer, C.: Neural architectures for named entity recognition. arXiv preprint arXiv:1603.01360 (2016)
Lopez, P.: Grobid: Combining automatic bibliographic data recognition and term extraction for scholarship publications. In: International conference on theory and practice of digital libraries. pp. 473–474. Springer (2009)
Ma, X., Hovy, E.: End-to-end sequence labeling via bi-directional lstm-cnns-crf. arXiv preprint arXiv:1603.01354 (2016)
Mikolov, T., Sutskever, I., Chen, K., Corrado, G.S., Dean, J.: Distributed representations of words and phrases and their compositionality. In: Advances in neural information processing systems. pp. 3111–3119 (2013)
Ojokoh, B., Zhang, M., Tang, J.: A trigram hidden markov model for metadata extraction from heterogeneous references. Information Sciences 181(9), 1538–1551
(2011)
Okada, T., Takasu, A., Adachi, J.: Bibliographic component extraction using support vector machines and hidden markov models. In: International Conference on
Theory and Practice of Digital Libraries. pp. 501–512. Springer (2004)
Prasad, A., Kaur, M., Kan, M.Y.: Neural parscit: a deep learning-based reference string parser. International Journal on Digital Libraries 19(4), 323–337 (2018)
Rodrigues Alves, D., Colavizza, G., Kaplan, F.: Deep reference mining from scholarly literature in the arts and humanities. Frontiers in Research Metrics and Analytics 3, 21 (2018)
Tkaczyk, D., Collins, A., Sheridan, P., Beel, J.: Machine learning vs. rules and out-of-the-box vs. retrained: An evaluation of open-source bibliographic reference and citation parsers. In: Proceedings of the 18th ACM/IEEE on joint conference on digital libraries. pp. 99–108. ACM (2018)
Tkaczyk, D., Szostek, P., Dendek, P.J., Fedoryszak, M., Bolikowski, L.: Cermine– automatic extraction of metadata and references from scientific literature. In: 2014 11th IAPR International Workshop on Document Analysis Systems. pp. 217–221. IEEE (2014)
Yin, P., Zhang, M., Deng, Z., Yang, D.: Metadata extraction from bibliographies using bigram hmm. In: International Conference on Asian Digital Libraries. pp.
310–319. Springer (2004)
Zhang, X., Zou, J., Le, D.X., Thoma, G.R.: A structural svm approach for reference parsing. BMC bioinformatics 12(3), S7 (2011)"""
            ],
            [  # https://arxiv.org/pdf/1706.03762.pdf
                """[28] Romain Paulus, Caiming Xiong, and Richard Socher. A deep reinforced model for abstractive
summarization. arXiv preprint arXiv:1705.04304, 2017.
[29] Slav Petrov, Leon Barrett, Romain Thibaux, and Dan Klein. Learning accurate, compact,
and interpretable tree annotation. In Proceedings of the 21st International Conference on
Computational Linguistics and 44th Annual Meeting of the ACL, pages 433–440. ACL, July
2006.
[30] Ofir Press and Lior Wolf. Using the output embedding to improve language models. arXiv preprint
arXiv:1608.05859, 2016.
[31] Rico Sennrich, Barry Haddow, and Alexandra Birch. Neural machine translation of rare words
with subword units. arXiv preprint arXiv:1508.07909, 2015.
[32] Noam Shazeer, Azalia Mirhoseini, Krzysztof Maziarz, Andy Davis, Quoc Le, Geoffrey Hinton,
and Jeff Dean. Outrageously large neural networks: The sparsely-gated mixture-of-experts
layer. arXiv preprint arXiv:1701.06538, 2017.
[33] Nitish Srivastava, Geoffrey E Hinton, Alex Krizhevsky, Ilya Sutskever, and Ruslan Salakhutdi-
nov. Dropout: a simple way to prevent neural networks from overfitting. Journal of Machine
Learning Research, 15(1):1929–1958, 2014.
[34] Sainbayar Sukhbaatar, Arthur Szlam, Jason Weston, and Rob Fergus. End-to-end memory
networks. In C. Cortes, N. D. Lawrence, D. D. Lee, M. Sugiyama, and R. Garnett, editors,
Advances in Neural Information Processing Systems 28, pages 2440–2448. Curran Associates,
Inc., 2015.
[35] Ilya Sutskever, Oriol Vinyals, and Quoc VV Le. Sequence to sequence learning with neural
networks. In Advances in Neural Information Processing Systems, pages 3104–3112, 2014.
[36] Christian Szegedy, Vincent Vanhoucke, Sergey Ioffe, Jonathon Shlens, and Zbigniew Wojna.
Rethinking the inception architecture for computer vision. CoRR, abs/1512.00567, 2015.
[37] Vinyals & Kaiser, Koo, Petrov, Sutskever, and Hinton. Grammar as a foreign language. In
Advances in Neural Information Processing Systems, 2015.
[38] Yonghui Wu, Mike Schuster, Zhifeng Chen, Quoc V Le, Mohammad Norouzi, Wolfgang
Macherey, Maxim Krikun, Yuan Cao, Qin Gao, Klaus Macherey, et al. Google’s neural machine
translation system: Bridging the gap between human and machine translation. arXiv preprint
arXiv:1609.08144, 2016."""
            ],
            [
                """[Ein05] Albert Einstein. Zur Elektrodynamik bewegter K ̈orper. (German)
[On the electrodynamics of moving bodies]. Annalen der Physik,
322(10):891–921, 1905. 
[GMS93] Michel Goossens, Frank Mittelbach, and Alexander Samarin. The LATEX Companion. Addison-Wesley, Reading, Massachusetts, 1993. 
[Knu] Donald Knuth. Knuth: Computers and typesetting."""
            ],
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
        ],
        inputs=textbox,
    )
gr.close_all()
demo.launch(share=False, server_name="0.0.0.0", server_port=7080)
