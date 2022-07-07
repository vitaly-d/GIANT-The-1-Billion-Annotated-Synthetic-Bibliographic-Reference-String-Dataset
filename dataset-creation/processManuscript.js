// dependancies
var fs = require("fs");
var citeproc = require("citeproc-js-node");

// to store failed citation styles
var failedBibs = new Set();

//This folder should have all the CSL files
const path = require('path');
const defaultCslFolder = "./cslWithTags/";

var crossref_converter = require("./crossref2citeprocjson.js");
// reads crossref csl json from fileName & returns sys with items in csl-json
//   see: https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html#ordinary-fields
//   see: https://citeproc-js.readthedocs.io/en/latest/running.html#required-sys-functions
function load_references(fileName, crossref = true) {
  var data = fs.readFileSync(fileName, "utf8");
  return load_references_from_string(data, crossref);
}

function load_references_from_string(data, crossref = true) {
  // console.time("readrawfile");
  if (crossref) {
    data = data.replace(/</g, "&lt;").replace(/>/g, "&rt;");
    lines = data.split("\n");
    bibliography = crossref_converter.crossref2citeproc(lines);
  } else {
    bibliography = JSON.parse(data);
    // TBD crossref2citeproc cleanups CSL Json: removes empty authors, etc. Do we need it here?
    //     Or a client has to send correct CSL JSON?
    // lines = [];
    // for (item of bibliography){
    // lines.push(JSON.stringify(item));
    // }
    // bibliography = crossref.crossref2citeproc(lines)
  }

  // console.log(JSON.stringify(bibliography, undefined, 2));
  // console.timeEnd("readrawfile");
  var sys = new citeproc.simpleSys();
  var enUS = fs.readFileSync("./locales/locales-en-US.xml", "utf8");
  sys.addLocale("en-US", enUS);
  sys.items = Object.assign(
    {},
    ...bibliography.map((item) => ({ [item.id]: item }))
  );

   sys.retrieveLocale = function (lang){
     // console.log("retrieveLocale", lang); 
     return fs.readFileSync("./locales/locales-" + lang + ".xml", "utf-8")
   };
   
  

  return sys;
}

// returns list of CSL styles from cslFolder
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

    rendered_citations = [];
    if (citations === undefined) {
      var citationKeys = Object.keys(sys.items);
      engine.updateItems(citationKeys);
    } else {
      for (var i = 0; i < citations.length; i++) {
        var citationItems = [];
        for (refId of citations[i]) {
          citationItems.push({ id: refId });
        }

        var citation = {
          properties: {
            noteIndex: i + 1,
          },
          citationItems: citationItems,
        };
        console.log(JSON.stringify(citation));
        _c = engine.appendCitationCluster(citation);
        //console.log(JSON.stringify(_c));
        rendered_citations.push(_c[0][1]);
      }
    }

    var bib = engine.makeBibliography();
    //console.log(JSON.stringify(bib[0], null, 2));

    // if (bib[1] === undefined){
    //   console.log("WARNING: bibliography is undefined, style: " + stylePath)
    // }

    return {
      citations: rendered_citations,
      references: bib[1],
    };
  } catch (error) {
    // failedBibs.add(stylePath);
    // console.log("Cannot process:", stylePath, error, JSON.stringify(citations, undefined, 2));
    console.log("Cannot process:", stylePath, error);

  }
}

//
// HTTP Peer
//

// CLS templates dictionary: {cslFolder, csls}
const csls = {};

//
var express = require("express");

var app = express();

const multer = require("multer");
const {Console} = require("console");
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });
const cpUpload = upload.fields([
  { name: "references", maxCount: 1 },
  { name: "citations", maxCount: 1 },
]);
app.post("/", cpUpload, function (req, res) {
  // list of references in csl-json or in CrossRef jsonl
  references_list_str = req.files["references"][0].buffer.toString();
  references_list_name = req.files["references"][0].originalname
  // optional citation clusters (of not provided, all references will be included into bibliography)
  citations_ragged_array = req.files["citations"]
    ? JSON.parse(req.files["citations"][0].buffer.toString())
    : undefined;

  // input format: csl-json by default, CrossRef citeproc-json if crossref field is on, see crossref/crossrefDownload.py
  var crossref = "on" == req.body.crossref || "on" == req.query.crossref;
  
  var cslFolder = path.normalize(req.query.styles_dir || req.body.styles_dir || defaultCslFolder)
  if (!(cslFolder in csls)){
      console.log("Read CSLs from", cslFolder)  
      csls[cslFolder] = readCSLs(cslFolder)
  }
  // array of indexes of styles applied to the manuscript, see the '/styles' peer
  var styles = req.body["styles"];
  if (styles === undefined) {
    styles = [22];
  } else {
    styles = JSON.parse(styles);
  }

  // console.log("Processing", crossref ? "CrossRef citeproc-json" : "csl-json");
  sys = load_references_from_string(references_list_str, crossref);
  var rendered_bibliographies = [];
  for (style of styles) {
    var stylePath = path.join(cslFolder, csls[cslFolder][style] + ".csl");
    // console.log("rendering bibliograpgy using", stylePath);
    try {
      references = makebib(sys, stylePath, citations_ragged_array);
      references["style"] = csls[cslFolder][style];
      rendered_bibliographies.push(references);
    } catch (exception) {
      console.error(
        "ERROR: Cannot process " + references_list_name + " using style csls[" + style + "] == " + csls[style] 
      );
    }
  }
  res.json(rendered_bibliographies);
});

app.get("/styles", function (req, res) {
  var cslFolder = path.normalize(req.query.styles_dir || defaultCslFolder)
  if (!(cslFolder in csls)){
      console.log("Read CSLs from", cslFolder)  
      csls[cslFolder] = readCSLs(cslFolder)
  }
  res.json(csls[cslFolder]);
});
app.set("json spaces", 2);
var args = process.argv.slice(2);
port = 8082
if (args.length > 0){
    port = parseInt(args[0])
}
console.log("starting at http://0.0.0.0:" + port)
app.listen(port, "0.0.0.0");
