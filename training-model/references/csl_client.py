from io import StringIO
import json
from json.decoder import JSONDecodeError
import logging
from pathlib import Path
from typing import Any, List, Sequence

import requests
from requests.exceptions import RequestException

from crossref_json_example import crossref_json

log = logging.Logger(__name__)

def base_url(port=3000) -> str:
        return f"http://localhost:{port}"


URL = base_url()

def styles_list(url=URL):
    """returns list of supported styles"""
    return requests.get(f"{url}/styles").json()


def make_bibliography(
    references: Path, style_ids: Sequence[int] = [0], url=URL
) -> List[Any]:
    try:


        with open(references, "rb") as references_stream:
            files = {
                "references": (references.name, references_stream, "applicaion/json"),
                "styles": (None, json.dumps(style_ids)),
                "crossref": (None, "on"),
            }
            r = requests.post(url, files=files)

        r.raise_for_status()
        return r.json()
    except JSONDecodeError as e:
        log.error("Cannot decode json response for %s: %s", references, e)
        raise e
    except RequestException as e:
        log.error("Cannot convert %s to json: %s", references, e)
        raise e


def _review_styles(crossref_json=crossref_json):

    files = {
        "references": ("references.jsonl", StringIO(crossref_json), "applicaion/json"),
        "styles": (None, json.dumps(list(range(len(styles_list(url=URL)))))),
        "crossref": (None, "on"),
    }
    r = requests.post(URL, files=files)
    r.raise_for_status()

    from convert_annotations_to_spacy import references_to_spacy_doc

    errors = []
    for rendered in r.json():
        style = rendered["style"]

        if "references" not in rendered:
            errors.append(style)
            continue

        references = rendered["references"]
        doc = references_to_spacy_doc(references, style)
        if doc:
            print(f"{style}:\n{doc.text}")
        else:
            print(f"{style}: ERROR")

    print("Not working styles:", len(errors))


if __name__ == "__main__":
    bibliography = make_bibliography(
        Path("../../dataset-creation/inputFiles/sampleCrossref.json")
    )
    print(bibliography)

    print("Available styles:")
    _review_styles()
