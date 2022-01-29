from io import StringIO
import json
from json.decoder import JSONDecodeError
import logging
from pathlib import Path
from typing import Sequence

import requests
from requests.exceptions import RequestException

log = logging.Logger(__name__)
URL = "http://localhost:3000"

def styles_list(url=URL):
    """returns list of supported styles"""
    return requests.get(f"{URL}/styles").json()

def make_bibliography(
        references: Path, style_ids: Sequence[int] = [0], url=URL
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


def _review_styles():
    crossref_json = r"""
{"indexed":{"date-parts":[[2019,2,14]],"date-time":"2019-02-14T16:02:48Z","timestamp":1550160168449},"reference-count":40,"publisher":"Elsevier BV","license":[{"URL":"https:\/\/www.elsevier.com\/tdm\/userlicense\/1.0\/","start":{"date-parts":[[2016,2,1]],"date-time":"2016-02-01T00:00:00Z","timestamp":1454284800000},"delay-in-days":0,"content-version":"tdm"}],"funder":[{"name":"National Science Centre (Poland)","award":["DEC-2012\/07\/B\/ST8\/04019"]}],"content-domain":{"domain":["elsevier.com","sciencedirect.com"],"crossmark-restriction":true},"published-print":{"date-parts":[[2016,2]]},"DOI":"10.1016\/j.jlumin.2015.09.036","type":"article-journal","created":{"date-parts":[[2015,10,25]],"date-time":"2015-10-25T12:56:01Z","timestamp":1445777761000},"page":"795-800","update-policy":"http:\/\/dx.doi.org\/10.1016\/elsevier_cm_policy","source":"Crossref","is-referenced-by-count":26,"title":"Investigation of upconversion luminescence in antimony\u2013germanate double-clad two cores optical fiber co-doped with Yb3+\/Tm3+ and Yb3+\/Ho3+ ions","prefix":"10.1016","volume":"170","author":[{"given":"J.","family":"Zmojda","sequence":"first","affiliation":[]},{"given":"M.","family":"Kochanowicz","sequence":"additional","affiliation":[]},{"given":"P.","family":"Miluski","sequence":"additional","affiliation":[]},{"given":"J.","family":"Dorosz","sequence":"additional","affiliation":[]},{"given":"J.","family":"Pisarska","sequence":"additional","affiliation":[]},{"given":"W.A.","family":"Pisarski","sequence":"additional","affiliation":[]},{"given":"D.","family":"Dorosz","sequence":"additional","affiliation":[]}],"member":"78","container-title":"Journal of Luminescence","original-title":[],"language":"en","link":[{"URL":"https:\/\/api.elsevier.com\/content\/article\/PII:S0022231315005475?httpAccept=text\/xml","content-type":"text\/xml","content-version":"vor","intended-application":"text-mining"},{"URL":"https:\/\/api.elsevier.com\/content\/article\/PII:S0022231315005475?httpAccept=text\/plain","content-type":"text\/plain","content-version":"vor","intended-application":"text-mining"}],"deposited":{"date-parts":[[2018,9,18]],"date-time":"2018-09-18T09:29:40Z","timestamp":1537262980000},"score":1.0,"subtitle":[],"short-title":[],"issued":{"date-parts":[[2016,2]]},"references-count":40,"alternative-id":["S0022231315005475"],"URL":"http:\/\/dx.doi.org\/10.1016\/j.jlumin.2015.09.036","relation":{},"ISSN":["0022-2313"],"subject":["Biophysics","Atomic and Molecular Physics, and Optics","Biochemistry","General Chemistry","Condensed Matter Physics"],"container-title-short":"Journal of Luminescence","assertion":[{"value":"Elsevier","name":"publisher","label":"This article is maintained by"},{"value":"Investigation of upconversion luminescence in antimony\u2013germanate double-clad two cores optical fiber co-doped with Yb3+\/Tm3+ and Yb3+\/Ho3+ ions","name":"articletitle","label":"Article Title"},{"value":"Journal of Luminescence","name":"journaltitle","label":"Journal Title"},{"value":"https:\/\/doi.org\/10.1016\/j.jlumin.2015.09.036","name":"articlelink","label":"CrossRef DOI link to publisher maintained version"},{"value":"article","name":"content_type","label":"Content Type"},{"value":"Copyright \u00a9 2015 Elsevier B.V. All rights reserved.","name":"copyright","label":"Copyright"}]}"""

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

        if "\n" in doc.text.strip():
            print(style, "\n", doc.text)

    print("Not working styles:", len(errors))
        



if __name__ == "__main__":
    bibliography = make_bibliography(
        Path("../../dataset-creation/inputFiles/sampleCrossref.json")
    )
    print(bibliography)

    print("Available styles:")
    print(_review_styles())
