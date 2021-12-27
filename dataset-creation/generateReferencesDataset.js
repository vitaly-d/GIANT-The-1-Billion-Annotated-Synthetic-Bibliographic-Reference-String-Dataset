//Author: M.Schibel 2018 & M. Grennan 2018
//Modified by: VD to split up into the 'generateStylesWithTags' / 'generateDataset' parts
//License: CC0 1.0 Universal - https://creativecommons.org/publicdomain/zero/1.0/ (in other words: feel free to use it)

function csvline(fields) {
  var string = "";
  for (var i = 0; i < fields.length; i++) {
    string += '"' + fields[i].replace(/\n/g, '').replace(/\"/g, '""') + "\",";
  }
  return string;
}
Array.prototype.remove = function(from, to) {
  var rest = this.slice((to || from) + 1 || this.length);
  this.length = from < 0 ? this.length + from : from;
  return this.push.apply(this, rest);
};

function escapeXml(unsafe) {
  //https://stackoverflow.com/questions/7918868/how-to-escape-xml-entities-in-javascript
  return unsafe.replace(/[<>&'"]/g, function(c) {
    switch (c) {
      case '<':
        return '&lt;';
      case '>':
        return '&gt;';
      case '&':
        return '&amp;';
      case '\'':
        return '&apos;';
      case '"':
        return '&quot;';
    }
  });
}

function escapeXml2(unsafe) {
  return escapeXml(escapeXml(unsafe));
}

function makebib(styleString, keys) {
  try {
    var engine = sys.newEngine(styleString, 'en-US');
    engine.setOutputFormat("text");
    // var citation = {
	// properties: {
	    // noteIndex: 0
	// },
	// citationItems: [
	     // {
		 // id: '1' // A work by Richard Snoakes
	     // },
	     // {
		 // id: '2' // A work by Richard Snoakes
	     // },
	     // {
		 // id: '3' // A work by Richard Snoakes
	     // }
	 // ]
    // }
    // // var citationsPre = [ ["citation-quaTheb4", 1], ["citation-mileiK4k", 2] ];
    // // var citationsPost = [ ["citation-adaNgoh1", 4] ];
    // citationsPre = []
    // citationsPost = []
    // console.log("about to call processCitationCluster")
    // var _c = engine.processCitationCluster(citation, citationsPre, citationsPost);
    // console.log("processCitationCluster has been called")  
    // console.log(JSON.stringify(_c))
    
    engine.updateItems(keys);

    var bib = engine.makeBibliography();
    // console.log(JSON.stringify(bib[0], null, 2));
    
    
    return bib[1];


  } catch (error) {
    failedBibs.add(csls[i]);
  }
}

// to store failed citation styles
var failedBibs = new Set();
var beforeTime = Date.now()

// dependancies
var fs = require('fs');
var citeproc = require("citeproc-js-node");
var xmldom = require('xmldom').DOMParser;

//needed for tagged output
var xml = new xmldom();
var XMLSerializer = require('xmldom').XMLSerializer;
var serializer = new XMLSerializer();

//taken from http://docs.citationstyles.org/en/1.0.1/specification.html#appendix-iii-types
var articleTypeDict = {
  "article": 0,
  "article-magazine": 1,
  "article-newspaper": 2,
  "article-journal": 3,
  "bill": 4,
  "book": 5,
  "broadcast": 6,
  "chapter": 7,
  "dataset": 8,
  "entry": 9,
  "entry-dictionary": 10,
  "entry-encyclopedia": 11,
  "figure": 12,
  "graphic": 13,
  "interview": 14,
  "legislation": 15,
  "legal_case": 16,
  "manuscript": 17,
  "map": 18,
  "motion_picture": 19,
  "musical_score": 20,
  "pamphlet": 21,
  "paper-conference": 22,
  "patent": 23,
  "post": 24,
  "post-weblog": 25,
  "personal_communication": 26,
  "report": 27,
  "review": 28,
  "review-book": 29,
  "song": 30,
  "speech": 31,
  "thesis": 32,
  "treaty": 33,
  "webpage": 34,
  "proceedings-article": 35,
  "reference-entry": 36,
  "journal-issue": 37,
  "reference-book": 38,
  "dissertation": 39,
  "posted-content": 40,
  "standard": 41,
  "other": 42,
  "monograph": 43,
  "book-part": 44,
  "peer-review": 45,
  "journal": 46,
  "proceedings": 47,
  "book-series": 48,
  "report-series": 49,
  "book-section": 50,
  "book-set": 51,
  "journal-volume": 52,
  "proceedings-series": 53
}

// index to add new elements to dictionary
var nextIndex = Object.keys(articleTypeDict).length - 1;

//to log any added articleTypes
var addedArticleTypes = {};

//This folder should have all the CSL files
const cslFolder = './cslWithTags/';

//1. Start reading input file
if (process.argv[2]) {
  var fileName = './inputFiles/' + process.argv[2];
  var fileNameRoot = process.argv[2];
  fs.appendFileSync('log.txt', "Reading input file: " + fileNameRoot + "\n");
} else {

  var fileName = './cr20.json';
}

console.time("readrawfile");
var data = fs.readFileSync(fileName, 'utf8');
data = data.replace(/</g, "&lt;").replace(/>/g, "&rt;");
console.timeEnd("readrawfile");

var lines = data.split('\n');

//2. cut it into pieces if specified
if (process.argv[3]) {
  var treshhold = parseInt(process.argv[3]);
  var multiplier = 50;
  lines = lines.slice(multiplier * treshhold, multiplier * (1 + treshhold));
  console.log("Treshold" + treshhold + " count " + lines.length + "until" + (multiplier * (1 + treshhold) - 1));
  fs.appendFileSync('log.txt', "Treshold" + treshhold + " count\n");
}
var counter = 0;
var count = lines.length;

var crossref = require("./crossref2citeprocjson.js");
var citations = crossref.crossref2citeproc(lines);

var files = fs.readdirSync(cslFolder);
var csls = [];
for (var i in files) {
  if ((files[i] + "").slice(-4) == ".csl") {
    csls.push(files[i].slice(0, -4));
  }
}

// https://groups.google.com/forum/#!topic/zotero-dev/2i_-1EZZbUU
var citationKeys = Object.keys(citations);

//create bibtex bibliography
console.log("creating bibtex");
var sys = new citeproc.simpleSys();
var enUS = fs.readFileSync('./locales/locales-en-US.xml', 'utf8');
sys.addLocale('en-US', enUS);
sys.items = citations;


// var styleString = fs.readFileSync('bibtex.csl_', 'utf8').replace(/<sort>([\s\S]*?)<\/sort>/g, '');
// var engine = sys.newEngine(styleString, 'en-US');
// engine.setOutputFormat("text");
// engine.updateItems(citationKeys);
// var bibtex = engine.makeBibliography();
// bibtex = bibtex[1];
// console.log(JSON.stringify(bibtex, null, 2));
//bibtex done


// for each citation style
for (var i = 0, len = csls.length; i < len; i++) {
// for (var i = 0, len = 3; i < len; i++) {

  // read an annotated style from cslFolder
  
  var stylePath = cslFolder + csls[i] + ".csl";
  console.log("Using...", stylePath);
  var styleStringAnnotated = fs.readFileSync(stylePath, 'utf8');

  // style that produces references WITH annotations is in styleStringAnnotated. 
  // Generate bibliography:

  var outputFilePath = "./outputFiles/" + csls[i] + "/"
  if (!fs.existsSync(outputFilePath)){
    fs.mkdirSync(outputFilePath);
  }
  var outputFileName = "output_" + fileNameRoot.replace(".json", "") + ".csv";
  var outputFile = outputFilePath + outputFileName;
  // var output = "";
  //clear the file and start creating the output file
  fs.writeFileSync(outputFile, "");
  fs.appendFileSync('log.txt', "Writing file: " + outputFileName + "\n");

  //create header, add in additional headers here as required
  fs.appendFileSync(outputFile, csvline(["doi", "articleType", "citationStyle", "citationStringAnnotated"]) + "\n");

  
  var annotatedstrings = makebib(styleStringAnnotated, citationKeys);
  
  for (var c = 0; c < annotatedstrings.length; c++) {

    // to include citation strings, uncomment lines below
    // var string = makebib(styleString, ["" + c]);
    // if (string != undefined && string.length && string[0] != undefined) {
    //   string = string[0];
    // } else {
    //   string = "";
    // }

    //The issue with two double issued tags
    // var annotatedstring = makebib(styleStringAnnotated, ["" + c]);
    var annotatedstring = annotatedstrings[c];
    if (annotatedstring != undefined && annotatedstring.length) {
      annotatedstring = annotatedstring.replace(/<\/issued>([^<]*)<issued>/g, "$1").replace(/&amp;/g, "&");

      var currentArticleType = citations[c]["type"];

      // if ArticleType not in dictionary, append to end of dictionary
      if (!(currentArticleType in articleTypeDict)) {
        articleTypeDict[currentArticleType] = nextIndex;
        addedArticleTypes[currentArticleType] = nextIndex;
        nextIndex += 1;
        fs.appendFileSync('log.txt', "Added the following to ArticleType dictionary: " +
          currentArticleType + " at index: " + nextIndex.toString());
      }

      fs.appendFileSync(outputFile, csvline([
        citations[c]["DOI"],
        articleTypeDict[currentArticleType].toString(), //ArticleType index
        i.toString(), //citationStyle index
        annotatedstring,
        // string, //uncomment to include citation string
      ]) + "\n");
    } else {
      annotatedstring = "";
    }
  }
}

var totalTime = (Date.now() - beforeTime) / 60000; //convert from ms to minutes

var failedBibsValues = failedBibs.values()

if (failedBibs.size != 0) {
  fs.appendFileSync('log.txt', "\nThe following citation styles failed: \n");
  for (var i = 0; i < failedBibs.size; i++) {
    fs.appendFileSync('log.txt', failedBibsValues.next().value + "\n");
  }
}

fs.appendFileSync('log.txt', "\nTime taken: " + totalTime.toString() + " mins" + "\n");
fs.appendFileSync('log.txt', "----------------------------------------- \n");

console.log("Completed")
console.log("-----------------------")
