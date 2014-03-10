/*
Copyright(c) 2013-2014 Ilya Kreymer. Released under the GNU General Public License.

This file is part of pywb.

    pywb is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pywb is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pywb.  If not, see <http://www.gnu.org/licenses/>.
*/

//============================================
// Wombat JS-Rewriting Library
//============================================

var WB_wombat_replayPrefix;
var WB_wombat_replayDatePrefix;
var WB_wombat_captureDatePart;
var WB_wombat_origHost;

	
function WB_StripPort(str)
{
  var hostWithPort = str.match(/^http:\/\/[\w\d@.-]+:\d+/);
  if (hostWithPort) {
     var hostName = hostWithPort[0].substr(0, hostWithPort[0].lastIndexOf(':'));
     return hostName + str.substr(hostWithPort[0].length);
  }

  return str;
}

function WB_IsHostUrl(str)
{
  // Good guess that's its a hostname
  if (str.indexOf("www.") == 0) {
    return true;
  }
  
  // hostname:port (port required)
  var matches = str.match(/^[\w-]+(\.[\w-_]+)+(:\d+)(\/|$)/);
  if (matches && (matches[0].length < 64)) {
    return true;
  }
  
  // ip:port
  matches = str.match(/^\d+\.\d+\.\d+\.\d+(:\d+)?(\/|$)/);
  if (matches && (matches[0].length < 64)) {
    return true;
  }

  return false;
}

function WB_RewriteUrl(url)
{
  var httpPrefix = "http://";
  var httpsPrefix = "https://";

  // If not dealing with a string, just return it
  if (!url || (typeof url) != "string") {
    return url;
  }
  
  // If starts with prefix, no rewriting needed
  // Only check replay prefix (no date) as date may be different for each capture
  if (url.indexOf(WB_wombat_replayPrefix) == 0) {
    return url;
  }
  
  // If server relative url, add prefix and original host
  if (url.charAt(0) == "/") {
    
    // Already a relative url, don't make any changes!
    if (url.indexOf(WB_wombat_captureDatePart) >= 0) {
      return url;
    }
    
    return WB_wombat_replayDatePrefix + WB_wombat_origHost + url;
  }
  
  // If full url starting with http://, add prefix
  if (url.indexOf(httpPrefix) == 0 || url.indexOf(httpsPrefix) == 0) {
    return WB_wombat_replayDatePrefix + url;
  }
  
  // May or may not be a hostname, call function to determine
  // If it is, add the prefix and make sure port is removed
  if (WB_IsHostUrl(url)) {
    return WB_wombat_replayDatePrefix + httpPrefix + url;
  }

  return url;
}

function WB_CopyObjectFields(obj)
{
  var newObj = {};
  
  for (prop in obj) {
    if ((typeof obj[prop]) != "function") {
      newObj[prop] = obj[prop];
    }
  }
  
  return newObj;
}

function WB_ExtractOrig(href)
{
  if (!href) {
    return "";
  }
  href = href.toString();
  var index = href.indexOf("/http", 1);
  if (index > 0) {
    return href.substr(index + 1);
  } else {
    return href;
  }
}
  
function WB_CopyLocationObj(loc)
{
  var newLoc = WB_CopyObjectFields(loc);
  
  newLoc._origLoc = loc;
  newLoc._origHref = loc.href;
  
  // Rewrite replace and assign functions
  newLoc.replace = function(url) { this._origLoc.replace(WB_RewriteUrl(url)); }
  newLoc.assign = function(url) { this._origLoc.assign(WB_RewriteUrl(url)); }
  newLoc.reload = loc.reload;
  
  // Adapted from:
  // https://gist.github.com/jlong/2428561
  var parser = document.createElement('a');
  parser.href = WB_ExtractOrig(newLoc._origHref);

  newLoc.hash = parser.hash;
  newLoc.host = parser.host;
  newLoc.hostname = parser.hostname;
  newLoc.href = parser.href;

  if (newLoc.origin) {
    newLoc.origin = parser.origin;
  }

  newLoc.pathname = parser.pathname;
  newLoc.port = parser.port
  newLoc.protocol = parser.protocol;
  newLoc.search = parser.search;
  
  newLoc.toString = function() { return this.href; }
  
  return newLoc;
}

function WB_wombat_updateLoc(reqHref, origHref, location)
{
  if (reqHref && (WB_ExtractOrig(origHref) != WB_ExtractOrig(reqHref))) {      
    var finalHref = WB_RewriteUrl(reqHref);
   
    location.href = finalHref;
  }  
}

function WB_wombat_checkLocationChange(wbLoc, isTop)
{
  var locType = (typeof wbLoc);
  
  var location = (isTop ? window.top.location : window.location);
	
  // String has been assigned to location, so assign it
  if (locType == "string") {
    WB_wombat_updateLoc(wbLoc, location.href, location)
    
  } else if (locType == "object") {
    WB_wombat_updateLoc(wbLoc.href, wbLoc._origHref, location);
  }
}

var wombat_updating = false;

function WB_wombat_checkLocations()
{
  if (wombat_updating) {
    return false;
  }
  
  wombat_updating = true;
  
  WB_wombat_checkLocationChange(window.WB_wombat_location, false);
  
  if (window.self.location != window.top.location) {
    WB_wombat_checkLocationChange(window.top.WB_wombat_location, true);
  }
  
  wombat_updating = false;
}

function WB_wombat_Init_SeededRandom(seed)
{
  // Adapted from:
  // http://indiegamr.com/generate-repeatable-random-numbers-in-js/

  Math.seed = seed;
  function seededRandom() {
    Math.seed = (Math.seed * 9301 + 49297) % 233280;
    var rnd = Math.seed / 233280;

    return rnd;
  }

  Math.random = seededRandom;
}

function WB_wombat_CopyHistoryFunc(history, funcName)
{
  origFunc = history[funcName];
  
  if (!origFunc) {
    return;
  }

  history['_orig_' + funcName] = origFunc;

  function rewrittenFunc(stateObj, title, url) {
    url = WB_RewriteUrl(url);
    return origFunc.call(history, stateObj, title, url);
  }

  history[funcName] = rewrittenFunc;

  return rewrittenFunc;
}

function WB_wombat_Init_AjaxOverride() {
  if (!window.XMLHttpRequest || !window.XMLHttpRequest.prototype ||
      !window.XMLHttpRequest.prototype.open) {
      return;
  }

  var orig = window.XMLHttpRequest.prototype.open;

  function openRewritten(sMethod, sUrl, bAsync, sUser, sPassword) {
    sUrl = WB_RewriteUrl(sUrl);
    return orig.call(this, sMethod, sUrl, bAsync, sUser, sPassword);
  }

  window.XMLHttpRequest.prototype.open = openRewritten;
}

function WB_wombat_Init(replayPrefix, captureDate, origHost, timestamp)
{
  WB_wombat_replayPrefix = replayPrefix;
  WB_wombat_replayDatePrefix = replayPrefix + captureDate + "/";
  WB_wombat_captureDatePart = "/" + captureDate + "/";
  
  WB_wombat_origHost = "http://" + origHost;

  // Location
  window.WB_wombat_location = WB_CopyLocationObj(window.self.location);
  document.WB_wombat_location = window.WB_wombat_location;


  if (window.self.location != window.top.location) {
    window.top.WB_wombat_location = WB_CopyLocationObj(window.top.location);
  }

  if (window.opener) {
    window.opener.WB_wombat_location = (window.opener ? WB_CopyLocationObj(window.opener.location) : null);
  }

  // Domain
  document.WB_wombat_domain = origHost;

  // History
  WB_wombat_CopyHistoryFunc(window.history, 'pushState');
  WB_wombat_CopyHistoryFunc(window.history, 'replaceState');

  // Ajax
  WB_wombat_Init_AjaxOverride();

  // Random
  WB_wombat_Init_SeededRandom(timestamp);
}

// Check quickly after page load
setTimeout(WB_wombat_checkLocations, 100);


// Check periodically every few seconds
setInterval(WB_wombat_checkLocations, 500);
