# Generate annotated CSLs

```
cd ../../dataset-creation

mkdir cslSmallWithTags
node generateAnnotatedStyles.js
```

> the dir with original CSLs, `const cslFolder`, is hard-coded within generateAnnotatedStyles.js


# Convert json downloaded from crossref

```
rm -rf train.ref dev.ref

python convert_annotations_to_spacy.py --help
python convert_annotations_to_spacy.py ../../dataset-creation/crossref/out --parallel 4 --csl-processor-path ../../dataset-creation/processManuscript.js

mkdir dev.ref
mv train.ref/references.0.spacy dev.ref
mv train.ref/references.7.spacy dev.ref

```

# spacy train


## Init config

```
python -m spacy init fill-config base_config_trf.cfg config.cfg -c bib_tokenizers.py

```

## train

```
python -m spacy train config.cfg --output ./output -c bib_tokenizers.py  --gpu-id 0
```

##Push the model to the HuggingFace Hub

```
$ nvim output/model-best/meta.json
  3   "name":"bib_references_trf",
  4   "version":"1.0.0",

$ python -m spacy package ./output/model-best ./output --build wheel -c bib_tokenizers.py

$ nix-env -iA nixpkgs.git-lfs
$ pip install -U spacy-huggingface-hub

$ cd output/en_bib_references_trf-1.0.0/dist
$ huggingface-cli login
$ python -m spacy huggingface-hub push en_bib_references_trf-1.0.0-py3-none-any.whl
```

