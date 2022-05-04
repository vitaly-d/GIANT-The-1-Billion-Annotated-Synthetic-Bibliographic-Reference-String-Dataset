#FROM python:3.9-slim-buster as base
FROM node:16-slim

# setup dependencies
RUN apt-get -y update
RUN apt-get -y install xz-utils zip unzip curl

# FROM base
WORKDIR /usr/src/app

COPY . .

# install node deps
RUN mkdir -p node_modules \
&& cd node_modules \
&& npm install --save npmlog xmldom citeproc-js-node citation-js express multer
# alternatively you can 'RUN tar xjf node_modules.tar.bz2' 

RUN echo 'node generateCSVcitationdataset.js tags sampleCrossref.json \n\
sh ./createCitations.sh \n\
node processManuscript.js \n\
' >> ~/.bash_history 

ARG port=8082
ENV PORT=${port}
EXPOSE ${port}
CMD node processManuscript.js ${PORT}
