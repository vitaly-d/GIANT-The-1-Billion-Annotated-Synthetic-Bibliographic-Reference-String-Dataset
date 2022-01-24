FROM python:3.9-slim-buster as base


# setup dependencies
RUN apt-get -y update
RUN apt-get -y install xz-utils zip unzip curl


# install python dependencies
# RUN pip3 install -U pip
# COPY ./requirements.txt .
# RUN pip3 install -r requirements.txt && pip3 cache purge && rm -rf /root/.cache


# install Node
ARG node_version=v16.13.1
ARG node_distro=linux-x64
RUN echo "Downloading https://nodejs.org/dist/${node_version}/node-${node_version}-${node_distro}.tar.xz"
RUN mkdir -p /usr/local/lib/nodejs \
&& curl -L https://nodejs.org/dist/${node_version}/node-${node_version}-${node_distro}.tar.xz | tar xJv -C /usr/local/lib/nodejs
ENV PATH=/usr/local/lib/nodejs/node-${node_version}-${node_distro}/bin:$PATH

FROM base
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

EXPOSE 3000
CMD node processManuscript.js
