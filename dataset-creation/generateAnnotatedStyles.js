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

// to store failed citation styles
var failedBibs = new Set();
var beforeTime = Date.now()

// dependancies
var fs = require('fs');
var xmldom = require('xmldom').DOMParser;
const path = require('path');

//needed for tagged output
var xml = new xmldom();
var XMLSerializer = require('xmldom').XMLSerializer;
var serializer = new XMLSerializer();


//This folder should have all the CSL files
//const cslFolder = './cslSmall/';

var args = process.argv.slice(2);
var cslFolder = "./cslSmall"
if (args.length > 0){
    cslFolder = args[0]
}
const cslFolderAnnotated = cslFolder + 'WithTags/';
console.log("cslFolder:", cslFolder, "cslFolderAnnotated:", cslFolderAnnotated)

var files = fs.readdirSync(cslFolder);
var csls = [];
for (var i in files) {
  if ((files[i] + "").slice(-4) == ".csl") {
    csls.push(files[i].slice(0, -4));
  }
}


// for each citation style
for (var i = 0, len = csls.length; i < len; i++) {
  console.log(i + ". " + csls[i]);
  var styleString = fs.readFileSync(path.join(cslFolder, csls[i] + '.csl'), 'utf8');

  // styleString = styleString.replace(/<([^>]*)(\sdefault-locale=\".+?\"(\s|))(.*?)>/, '<$1$3>'); //prevent error caused by default locale https://github.com/Juris-M/citeproc-js/issues/81
  styleString = styleString.replace(/<sort>([\s\S]*?)<\/sort>/g, ''); //remove sorting
  // styleString = styleString.replace(/<text variable=\"citation-number\"(.*?)\/>/g, ''); //remove citation number at the beginning of the string
  // styleString = styleString.replace(/disambiguate-add-year-suffix=\"true\"/g, ''); //remove year suffix such as 2006b

  // bib = makebib(styleString);

  var variable, newprefix, newsuffix;

  var doc = xml.parseFromString(styleString, 'application/xml');

  // console.log(doc.documentElement.nodeName ,  doc.documentElement.getAttribute("version"))

  var xmlname = doc.getElementsByTagName("name");
  for (var a = 0; a < xmlname.length; a++) {

    if (xmlname[a].parentNode.parentNode.tagName != "info") {
      var namepart = xmlname[a].getElementsByTagName("name-part");
      var has = {
        family: false,
        given: false
      };
      for (var z = 0; z < namepart.length; z++) {
        has[namepart[z].getAttribute("name")] = true;
      }

      if (!has.family) {
        var family = doc.createElement("name-part");
        family.setAttribute("name", "family");
        xmlname[a].appendChild(family);
      }
      if (!has.given) {
        var given = doc.createElement("name-part");
        given.setAttribute("name", "given");
        xmlname[a].appendChild(given);
      }
    }
  }
  for (var a = 0; a < 5; a++) {
    var tagname = ["text", "date", "names", "name-part", "date-part"][a];
    var text = doc.getElementsByTagName(tagname);

    for (id in text) {

      try {
        if (tagname.slice(-5) == "-part") {
          variable = text[id].getAttribute("name");
        } else {
          variable = text[id].getAttribute("variable");
        }
      } catch (error) {
        variable = null;
      }
      newprefix = "";
      newsuffix = "";
      if (variable) {
	// console.log(variable)  
        newprefix = "<" + variable + ">";
        newsuffix = "</" + variable + ">"; //match(/[a-zA-Z0-9_-]+/)[0]
      }

      try {
	if (variable=="DOI"){
	    // try to avoid the DOI span within URL: https://doi.org/<DOI>10.1021/es991246a</DOI> 
	    // a bit complicated because prefix could be any string. Let's assume that urls does not contain spaces 
	    var doi_parts = escapeXml2(text[id].getAttribute("prefix")).split(" ")
	    if (doi_parts.length > 1){
		text[id].setAttribute("prefix", doi_parts.slice(0,-1).join(" ") + " " + newprefix + doi_parts[doi_parts.length-1]);
	    }else{
		text[id].setAttribute("prefix", newprefix + escapeXml2(text[id].getAttribute("prefix")));
	    }
	}
        else{
	    text[id].setAttribute("prefix", escapeXml2(text[id].getAttribute("prefix")) + newprefix);
	}
        text[id].setAttribute("suffix", newsuffix + escapeXml2(text[id].getAttribute("suffix")));
        if (text[id].getAttribute("value")) {
          text[id].setAttribute("value", escapeXml2(text[id].getAttribute("value")));
        }
      } catch (error) {
        failedBibs.add(csls[i]);
      }
    }
  }
  var styleStringAnnotated = serializer.serializeToString(doc);

  var stylePathAnnotated = cslFolderAnnotated + csls[i] + ".csl"
  console.log("Writing " + stylePathAnnotated)
  fs.writeFileSync(stylePathAnnotated, styleStringAnnotated);

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
