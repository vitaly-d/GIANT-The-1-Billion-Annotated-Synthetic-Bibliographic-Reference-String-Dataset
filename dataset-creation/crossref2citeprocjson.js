module.exports = {
crossref2citeproc : function(lines){
	var fs = require('fs');

var field = require("./fieldTypes.js");
var unknowns = [];

var emptyvalues = [" ","","null","NULL"," "];
var skiptypes = ["component","book-issue","undefined"];
var citations = [];
var citationcounter = 0;

// Counter({'journal-article': 418948, 'book-chapter': 80434, 'proceedings-article': 32358, 'component': 24468, 'dataset': 9850, 'reference-entry': 4852, 'book': 4187, 'journal-issue': 4091, 'posted-content': 3819, 'report': 2982, 'other': 2608, 'monograph': 2557, 'dissertation': 2166, 'standard': 1561, 'peer-review': 1093, 'reference-book': 966, 'proceedings': 243, None: 223, 'journal': 211, 'grant': 120, 'report-series': 78, 'book-part': 77, 'book-section': 66, 'journal-volume': 29, 'book-series': 13, 'proceedings-series': 1}) 
// csl-json: https://docs.citationstyles.org/en/stable/specification.html#appendix-iii-types  
types_dict = {
  "journal-article": 'article-journal',
  "book-chapter": 'chapter',
  "proceedings-article": 'paper-conference',
  "component": 'chapter', //TBD
  "reference-entry": 'entry',
  "journal-issue": 'periodical', //TBD
  "posted-content": 'webpage', //TBD post?
  "other": 'document',
  "monograph": 'article-journal', //TBD
  "peer-review": 'review',
  "reference-book": 'book',
  "proceedings": 'paper-conference',
  "journal": 'periodical',
  "grant": 'document',
  "report-series": 'report',
  "book-part": "chapter",
  "book-section": 'chapter'
}

for (var i = 0; i < lines.length; i++) {
  if (lines[i] === '') continue;
  var line
  try{
    line = JSON.parse(lines[i]);
  }
  catch(err){
    console.log("Cannot parse " + lines[i] + ":\n" + err)
    continue
  }

  if(line.type){
    csl_type = types_dict[line.type]
    if (csl_type){
        // console.log("type:", line.type, "->", csl_type);
	line.type = csl_type
    }
      
  }else{
    // None: 223
    line.type = "document";
  }
  if(skiptypes.indexOf(line.type) !== -1){
    continue;
  }

  citations[citationcounter] = {
    id: citationcounter,
   // zotero2bibtexType : line["type"],//I know it looks strange but it's needed for the bibtex.csl
  };

  //delete empty authors
  if(line.author != undefined){
    for(var a = 0; a < line["author"].length; a++){
      var empty_authors = []
      //delete affiliation if it's empty
      if(line["author"][a].hasOwnProperty("affiliation") && line["author"][a]["affiliation"].length == 0){
        delete line["author"][a]["affiliation"];
      }
      //delete author if it's empty
      //console.log("index:"+emptyvalues.indexOf(line["author"][a]["family"]));
      if(emptyvalues.indexOf(line["author"][a]["family"]) !== -1 && emptyvalues.indexOf(line["author"][a]["given"]) !== -1){
        empty_authors.push(a)
      }
    }
    for (a of empty_authors){
	line.author.splice(a, 1)
    }
    if(line["author"].length === 0){
      delete line["author"];
    }
  }

  //go through each property
  for (var prop in line) {
    var newprop = prop.replace("short-title", 'shortTitle').replace("short-container-title", 'container-title-short');
    // console.log(newprop);
    if (field.types.hasOwnProperty(newprop)) {
      var type = field.types[newprop];
      if (typeof type == "object") {
        type = "string";
      }
      if (type == "string" && (typeof line[prop] == "string" || typeof line[prop] == "number")) {
        citations[citationcounter][newprop] = line[prop]
      } else if (type == "string" && line[prop] && typeof line[prop] == "object") { //
        if(line[prop].length > 0){
        citations[citationcounter][newprop] = line[prop][0]
      }
      } else if (type == field.DATE && typeof line[prop] == "object") {
        citations[citationcounter][newprop] = line[prop]
      } else if (type == field.NAME_LIST && typeof line[prop] == "object") {
        citations[citationcounter][newprop] = line[prop]
      } else {
        console.log("Unknown format: "+ type + ";" + typeof line[prop] + ";" + newprop + ";" + line[prop]);
      }

      unknowns[newprop] = true;
    } else {
      unknowns[newprop] = "unknown";
    }
  }
  citationcounter++;
}

//console.log(unknowns);
//var newFile = "./cslCiteprocOutput/cslciteproc.json";
//fs.writeFileSync(newFile, JSON.stringify(citations));
//console.log('Saved JSON to ' + newFile);
return citations;
}}
