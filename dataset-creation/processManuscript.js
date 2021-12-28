// dependancies
var fs = require("fs");
var citeproc = require("citeproc-js-node");

// to store failed citation styles
var failedBibs = new Set();

//This folder should have all the CSL files
const cslFolder = "./cslWithTags/";

var crossref = require("./crossref2citeprocjson.js");
const { stringify } = require("querystring");
// reads crossref csl json from fileName & returns sys with items in csl-json
//   see: https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html#ordinary-fields
//   see: https://citeproc-js.readthedocs.io/en/latest/running.html#required-sys-functions
function load_references(fileName) {
  console.time("readrawfile");
  var data = fs.readFileSync(fileName, "utf8");
  data = data.replace(/</g, "&lt;").replace(/>/g, "&rt;");
  console.timeEnd("readrawfile");
  lines = data.split("\n");
  bibliography = crossref.crossref2citeproc(lines);

  var sys = new citeproc.simpleSys();
  var enUS = fs.readFileSync("./locales/locales-en-US.xml", "utf8");
  sys.addLocale("en-US", enUS);
  sys.items = bibliography;

  return sys;
}

// returns list of CSL templates from cslFolder
function readCSLs(cslFolder) {
  var files = fs.readdirSync(cslFolder);
  var csls = [];
  for (var i in files) {
    if ((files[i] + "").slice(-4) == ".csl") {
      csls.push(files[i].slice(0, -4));
    }
  }
  return csls;
}

// sys - the sys object with all manuscript references loaded
// stylePath - path of CSL language template
// citations - ragged array of citations, e.g, [["ref1", "ref2"], ["ref2"], ["ref3", "ref4", "ref5"]],
// that, depending on styleString, can be rendered in a manuscript as "some text 1,2 some text 2 some text 3-5 some text"
function makebib(sys, stylePath, citations) {
  try {
    var styleString = fs.readFileSync(stylePath, "utf8");
    var engine = sys.newEngine(styleString, "en-US");
    engine.setOutputFormat("text");
    // // var citationsPre = [ ["citation-quaTheb4", 1], ["citation-mileiK4k", 2] ];
    // // var citationsPost = [ ["citation-adaNgoh1", 4] ];
    // citationsPre = []
    // citationsPost = []
    // console.log("about to call processCitationCluster")
    // var _c = engine.processCitationCluster(citation, citationsPre, citationsPost);

    keys = [];
    for (var ref in sys.items) {
      keys.push(ref["id"]);
    }

    console.log(citations);
    if (citations === undefined) {
      engine.updateItems(keys);
    } else {
      for (var i = 0; i < citations.length; i++) {
        citationItems = [];
        for (refId of citations[i]) {
          citationItems.push({ id: refId });
        }

        var citation = {
	    properties: {
            noteIndex: 1,
          },
          citationItems: citationItems,
        };
        console.log(JSON.stringify(citation));
        _c = engine.appendCitationCluster(citation);
        console.log(JSON.stringify(_c));
      }
    }

    var bib = engine.makeBibliography();
    console.log(JSON.stringify(bib[0], null, 2));

    return bib[1];
  } catch (error) {
    failedBibs.add(stylePath);
    console.log("Cannot process:", stylePath, error);
  }
}

sys = load_references("inputFiles/sampleCrossref.json");
csls = readCSLs(cslFolder);

var stylePath = cslFolder + csls[2] + ".csl";
console.log("Using...", stylePath);

//references = makebib(sys, stylePath);
references = makebib(sys, stylePath, [
  ["0", "1", "2"],
  ["3", "4"],
  ["5", "6", "7"],
  ["8"],
  ["9"],
]);
for (var ref of references) {
  console.log(JSON.stringify(ref));
}
