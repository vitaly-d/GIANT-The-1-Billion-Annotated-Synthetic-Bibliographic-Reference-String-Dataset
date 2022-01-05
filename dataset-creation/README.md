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

 TODO

## Generate CLSs with tags
 
  `node generateAnnotatedStyles.js`



## processManuscript server

 `node processManuscript.js ` 

 processManuscript server exposes processManuscript.js as an HTTP peer:

- Process JSONL downloaded from CrossRef:
`curl -v -F references=@inputFiles/sampleCrossref.json -F citations=@inputFiles/sampleCrossref.citations.json -F crossref=on 192.168.2.22:3000`

OR

- Process csl-json:
`curl -v -F references=@cslCiteprocOutput/cslciteproc.json -F citations=@inputFiles/sampleCrossref.citations.json  192.168.2.22:3000`

OR

- Process bibtex using citations-js:

```
node_modules/citation-js/bin/cmd.js -i inputFiles/prompts.bib -s csl -f string -l en > cslCiteprocOutput/prompts.bib.json`
curl -v -F references=@cslCiteprocOutput/prompts.bib.json 192.168.2.22:3000
```
