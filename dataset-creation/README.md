# Bibliographic References Dataset Creation tool

Based on https://github.com/BeelGroup/GIANT-The-1-Billion-Annotated-Synthetic-Bibliographic-Reference-String-Dataset

Similarities:
- Re-uses most of the code of the GIANT dataset
- Reuses CSL files from GIANT repo

Changes:
 - the goal is to generate not 'standalone' references strings, but 'references in a manuscript context':
    - citation-number is enabled
    - input:
	- the same list of CSL json bibliographic entries, but they are considered not as list of independed references, but as the manuscript bibliographic data, something similar to what can be defined in a bibtex file for a Latex manuscript   
    - output: each generated 'manuscript' consists of
	- list of references (aka the bibliography section)
	- list of citations (if citation id clusters are provided)


# How to use:

## Install
`cd dataset-creation` 

### on a dev machile (tested on Ubuntu 20.04)
 - install node
 - install deps: `tar xjf node-modules.tar.bz2`

### in Docker

`docker build . -t $USER/bib`

`docker run --rm -p3000:3000 $USER/bib`

## Generate CLSs with tags
 
  `node generateAnnotatedStyles.js`
>Note: this is an optional step because generated files are in the repo 



## processManuscript server

 `node processManuscript.js ` 

 processManuscript server exposes processManuscript.js as an HTTP peer:

The references input field is the name of a file with bibliographic references. It could be either in csl-json or in CrossRef citeproc format. `-F crossref=on` needs to be specified for CrossRef citeproc-json

The citations input field is a file name that contain the ragged array of citation clusters, for example, see inputFiles/sampleCrossref.citations.json

The `styles` input field allows to select styles to be applied to the references and citations. It is the list that consists indexes of CSL templates. You can see CSL templates and their indexes at `http://localhost:3000/styles`

### Examples:


#### Process JSONL downloaded from CrossRef:

`curl -v -F references=@inputFiles/sampleCrossref.json -F citations=@inputFiles/sampleCrossref.citations.json -F 'styles=[22,33]' -F crossref=on localhost:3000`


#### Process csl-json:

`curl -v -F references=@cslCiteprocOutput/cslciteproc.json -F citations=@inputFiles/sampleCrossref.citations.json -F 'styles=[22,33]' localhost:3000`


#### Process bibtex using citations-js:

```
node_modules/citation-js/bin/cmd.js -i inputFiles/prompts.bib -s csl -f string -l en > cslCiteprocOutput/prompts.bib.json`
curl -v -F references=@cslCiteprocOutput/prompts.bib.json -F 'styles=[22,33]' localhost:3000
```


