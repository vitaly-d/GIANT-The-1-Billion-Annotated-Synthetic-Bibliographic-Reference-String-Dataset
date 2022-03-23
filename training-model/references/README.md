# Convert json downloaded from crossref

```
rm -rf train.ref dev.ref

python convert_annotations_to_spacy.py ../../dataset-creation/crossref/out --output-dir train.ref --parallel 8

mkdir dev.ref
cp train.ref/references.0.spacy dev.ref
cp train.ref/references.7.spacy dev.ref

```



# spacy train


## Init config
```
python -m spacy init fill-config base_config_trf.cfg config.cfg

```

## train
```
python -m spacy train config.cfg --output ./output -c augmenter.py  --gpu-id 0
```
