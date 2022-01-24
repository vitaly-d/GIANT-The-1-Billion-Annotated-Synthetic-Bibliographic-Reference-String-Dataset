import json
from json.decoder import JSONDecodeError
import logging
from pathlib import Path
from typing import Sequence

import requests
from requests.exceptions import RequestException

log = logging.Logger(__name__)


def styles_list(url="http://localhost:3000/styles"):
    """returns list of supported styles"""
    return requests.get(url).json()


def make_bibliography(
    references: Path, style_ids: Sequence[int] = [22], url="http://localhost:3000"
):
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
    except RequestException as e:
        log.error("Cannot convert %s to json: %s", references, e)


if __name__ == "__main__":
    bibliography = make_bibliography(
        Path("../../dataset-creation/inputFiles/sampleCrossref.json")
    )
    print(bibliography)
