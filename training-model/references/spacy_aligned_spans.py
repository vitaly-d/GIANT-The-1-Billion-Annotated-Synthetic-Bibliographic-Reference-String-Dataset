from spacy.tokens import Span

# https://github.com/explosion/spaCy/blob/2d89dd9db898e66058bf965e1b483b0019ce1b35/spacy/training/example.pyx#L296
# that has been modified to support '\n' within a span

_space_translation = str.maketrans({" ": "", "\n": "", "\t": ""})


def _get_aligned_spans(doc, spans, align, allow_overlap):
    seen = set()
    output = []
    for span in spans:
        indices = align[span.start : span.end]
        if not allow_overlap:
            indices = [idx for idx in indices if idx not in seen]
        if len(indices) >= 1:
            aligned_span = Span(doc, indices[0], indices[-1] + 1, label=span.label)
            target_text = span.text.lower().strip().translate(_space_translation)
            our_text = aligned_span.text.lower().strip().translate(_space_translation)
            if our_text == target_text:
                output.append(aligned_span)
                seen.update(indices)
    return output


def get_aligned_spans_y2x(example, y_spans, allow_overlap=False):
    return _get_aligned_spans(example.x, y_spans, example.alignment.y2x, allow_overlap)
