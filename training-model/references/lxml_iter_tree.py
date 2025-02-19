import logging
from typing import Optional, Sequence
from xml.sax.saxutils import unescape

from lxml import etree

log = logging.getLogger(__name__)


def iter_elements_with_text(node):
    """
    Args:
        node: etree element

    yields:
        (eventType:str, node:Union[str, etree.Element])

    Supported event types:
        "start": etree Element before any content, including text, within the element is yielded
        "end": the same etree element after i's content it yielded
        "text": text, both element.text and element.tail

    Idea: https://stackoverflow.com/questions/24071072/iterate-over-both-text-and-elements-in-lxml-etree
    """

    yield "start", node

    text = node.text if node.text else None
    if text:
        yield "text", text

    for child in node:
        yield from iter_elements_with_text(child)

    yield "end", node

    tail = node.tail if node.tail else None
    if tail:
        yield "text", tail


def parse(xml_string):
    """
    Args:
     xml_string: XML-escaped text with annotations XML-tags used as text span annotations
    returns:
     lxml elements tree or None
    raises:
     etree.XMLSyntaxError
    """
    parser = etree.HTMLParser()
    return etree.fromstring(xml_string, parser)


def get_text(root):
    return unescape("".join(root.itertext()))


def annotations(element, tags_to_be_included: Optional[Sequence[str]] = None):
    """
    performs non-destructive parsing
    and converts xml tags into tuples
          `(tag, start, end)`
    where `start` and `end` are character offsets in XML-unescaped text
           that you can get by calling get_text(element)

    Args:
        element: etree element
        tags_to_be_included: optional filter that allows to specify tags
                             the annotation will be yielded for
    """
    text = []
    stack = []
    for event, t in iter_elements_with_text(element):
        if "text" == event:
            text.append(unescape(t))
        elif "start" == event:
            stack.append((t.tag, len("".join(text))))
        elif "end" == event:
            _start = stack.pop()
            tag, start, end = _start[0], _start[1], len("".join(text))
            # print(tag)
            assert tag == t.tag
            if tags_to_be_included and tag not in tags_to_be_included:
                continue
            yield (tag, start, end)

    assert "".join(text) == get_text(element)
