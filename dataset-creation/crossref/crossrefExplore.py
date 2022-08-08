import srsly
import typer
from pathlib import Path
from collections import Counter


def main(citeproc_jsonl_dir):

    types = []
    for jsonl_path in Path(citeproc_jsonl_dir).glob("**/*.json"):
        try:
            for sample in srsly.read_jsonl(jsonl_path):
                # https://docs.citationstyles.org/en/stable/specification.html#appendix-iii-types
                type = sample["type"]
                types.append(type)
                if type not in ["journal-article", "book-chapter"]:
                    print(type, sample.get("DOI", ""))
        except:
            print("CANNOT READ", jsonl_path)

    print(Counter(types))


if __name__ == "__main__":
    typer.run(main)
