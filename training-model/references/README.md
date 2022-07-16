# Convert json downloaded from crossref

```
rm -rf train.ref dev.ref

python convert_annotations_to_spacy.py ~/Code/transformation-data/datasource/crossref/citeproc-json --output-dir train.ref --parallel 4 --csl-processor-path ../../dataset-creation/processManuscript.js

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
