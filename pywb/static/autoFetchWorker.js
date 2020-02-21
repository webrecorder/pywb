'use strict';
// thanks wombat
var STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/gi;
var IMPORT_REGEX = /(@import\s*[\\"']*)([^)'";]+)([\\"']*\s*;?)/gi;
var srcsetSplit = /\s*(\S*\s+[\d.]+[wx]),|(?:\s*,(?:\s+|(?=https?:)))/;
var MaxRunningFetches = 15;
var DataURLPrefix = 'data:';
var seen = {};
// array of URLs to be fetched
var queue = [];
var runningFetches = 0;
// a URL to resolve relative URLs found in the cssText of CSSMedia rules.
var currentResolver = null;

var config = {
  havePromise: typeof self.Promise !== 'undefined',
  haveFetch: typeof self.fetch !== 'undefined',
  proxyMode: false,
  mod: null,
  prefix: null,
  prefixMod: null,
  relative: null,
  rwRe: null,
  defaultFetchOptions: {
    cache: 'force-cache',
    mode: 'cors'
  }
};

if (!config.havePromise) {
  // not kewl we must polyfill Promise
  self.Promise = function(executor) {
    executor(noop, noop);
  };
  self.Promise.prototype.then = function(cb) {
    if (cb) cb();
    return this;
  };
  self.Promise.prototype.catch = function() {
    return this;
  };
  self.Promise.all = function(values) {
    return new Promise(noop);
  };
}

if (!config.haveFetch) {
  // not kewl we must polyfill fetch.
  self.fetch = function(url) {
    return new Promise(function(resolve) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);
      xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
          if (!config.havePromise) {
            fetchDone();
          }
          resolve();
        }
      };
      xhr.send();
    });
  };
}

if (location.search.indexOf('init') !== -1) {
  (function() {
    var init;
    if (typeof self.URL === 'function') {
      var loc = new self.URL(location.href);
      init = JSON.parse(loc.searchParams.get('init'));
    } else {
      var search = decodeURIComponent(location.search.split('?')[1]).split('&');
      init = JSON.parse(search[0].substr(search[0].indexOf('=') + 1));
      init.prefix = decodeURIComponent(init.prefix);
      init.baseURI = decodeURIComponent(init.prefix);
    }
    config.prefix = init.prefix;
    config.mod = init.mod;
    config.prefixMod = init.prefix + init.mod;
    config.rwRe = new RegExp(init.rwRe);
    config.relative = init.prefix.split(location.origin)[1];
    config.schemeless = '/' + config.relative;
  })();
} else {
  config.proxyMode = true;
  config.defaultFetchOptions.mode = 'no-cors';
}

self.onmessage = function(event) {
  var data = event.data;
  switch (data.type) {
    case 'values':
      autoFetch(data);
      break;
    case 'fetch-all':
      justFetch(data);
      break;
  }
};

function noop() {}

function fetchDone() {
  runningFetches -= 1;
  fetchFromQ();
}

function fetchErrored(err) {
  console.warn("Fetch Failed: " + err);
  fetchDone();
}

/**
 * Fetches the supplied URL and increments the {@link runningFetches} variable
 * to represent an inflight request.
 * If the url to be fetched is an object then its a fetch-as-page and the
 * fetch is configured using its supplied options and url properties.
 *
 * Otherwise, the fetch is made using cache mode force-cache and if we
 * are operating in proxy mode the fetch mode no-cors is used.
 * @param {string|Object} toBeFetched - The URL to be fetched
 */
function fetchURL(toBeFetched) {
  runningFetches += 1;

  var url;
  var options = config.defaultFetchOptions;

  if (typeof toBeFetched === 'object') {
    url = toBeFetched.url;
    options = toBeFetched.options;
  } else {
    url = toBeFetched;
  }

  fetch(url, options)
    .then(fetchDone)
    .catch(fetchErrored);
}

function queueOrFetch(toBeFetched) {
  var url = typeof toBeFetched === 'object' ? toBeFetched.url : toBeFetched;
  if (!url || url.indexOf(DataURLPrefix) === 0 || seen[url] != null) {
    return;
  }
  seen[url] = true;
  if (runningFetches >= MaxRunningFetches) {
    queue.push(toBeFetched);
    return;
  }
  fetchURL(toBeFetched);
}

function fetchFromQ() {
  while (queue.length && runningFetches < MaxRunningFetches) {
    fetchURL(queue.shift());
  }
}

function maybeResolveURL(url, base) {
  // given a url and base url returns a resolved full URL or
  // null if resolution was unsuccessful
  try {
    var _url = new URL(url, base);
    return _url.href;
  } catch (e) {
    return null;
  }
}

function safeResolve(url, resolver) {
  // Guard against the exception thrown by the URL constructor if the URL or resolver is bad
  // if resolver is undefined/null then this function passes url through
  var resolvedURL = url;
  if (resolver) {
    try {
      var _url = new URL(url, resolver);
      return _url.href;
    } catch (e) {
      resolvedURL = url;
    }
  }
  return resolvedURL;
}

function maybeFixUpRelSchemelessPrefix(url) {
  // attempt to ensure rewritten relative or schemeless URLs become full URLS!
  // otherwise returns null if this did not happen
  if (url.indexOf(config.relative) === 0) {
    return url.replace(config.relative, config.prefix);
  }
  if (url.indexOf(config.schemeless) === 0) {
    return url.replace(config.schemeless, config.prefix);
  }
  return null;
}

function maybeFixUpURL(url, resolveOpts) {
  // attempt to fix up the url and do our best to ensure we can get dat 200 OK!
  if (config.rwRe.test(url)) {
    return url;
  }
  var mod = resolveOpts.mod || 'mp_';
  // first check for / (relative) or // (schemeless) rewritten urls
  var maybeFixed = maybeFixUpRelSchemelessPrefix(url);
  if (maybeFixed != null) {
    return maybeFixed;
  }
  // resolve URL against tag src
  if (resolveOpts.tagSrc != null) {
    maybeFixed = maybeResolveURL(url, resolveOpts.tagSrc);
    if (maybeFixed != null) {
      return config.prefix + mod + '/' + maybeFixed;
    }
  }
  // finally last attempt resolve the originating documents base URI
  if (resolveOpts.docBaseURI) {
    maybeFixed = maybeResolveURL(url, resolveOpts.docBaseURI);
    if (maybeFixed != null) {
      return config.prefix + mod + '/' + maybeFixed;
    }
  }
  // not much to do now.....
  return config.prefixMod + '/' + url;
}

function urlExtractor(match, n1, n2, n3, offset, string) {
  // Same function as style_replacer in wombat.rewrite_style, n2 is our URL
  queueOrFetch(n2);
  return n1 + n2 + n3;
}

function urlExtractorProxyMode(match, n1, n2, n3, offset, string) {
  // Same function as style_replacer in wombat.rewrite_style, n2 is our URL
  // this.currentResolver is set to the URL which the browser would normally
  // resolve relative urls with (URL of the stylesheet) in an exceptionless manner
  // (resolvedURL will be undefined if an error occurred)
  queueOrFetch(safeResolve(n2, currentResolver));
  return n1 + n2 + n3;
}

function handleMedia(mediaRules) {
  // this is a broken down rewrite_style
  if (mediaRules == null || mediaRules.length === 0) return;
  for (var i = 0; i < mediaRules.length; i++) {
    mediaRules[i]
      .replace(STYLE_REGEX, urlExtractor)
      .replace(IMPORT_REGEX, urlExtractor);
  }
}

function handleMediaProxyMode(mediaRules) {
  // this is a broken down rewrite_style
  if (mediaRules == null || mediaRules.length === 0) return;
  for (var i = 0; i < mediaRules.length; i++) {
    // set currentResolver to the value of this stylesheets URL, done to ensure we do not have to
    // create functions on each loop iteration because we potentially create a new `URL` object
    // twice per iteration
    currentResolver = mediaRules[i].resolve;
    mediaRules[i].cssText
      .replace(STYLE_REGEX, urlExtractorProxyMode)
      .replace(IMPORT_REGEX, urlExtractorProxyMode);
  }
}

function handleSrc(srcValues, context) {
  var resolveOpts = { docBaseURI: context.docBaseURI, mod: null };
  if (srcValues.value) {
    resolveOpts.mod = srcValues.mod;
    return queueOrFetch(maybeFixUpURL(srcValues.value.trim(), resolveOpts));
  }
  var len = srcValues.values.length;
  for (var i = 0; i < len; i++) {
    var value = srcValues.values[i];
    resolveOpts.mod = value.mod;
    queueOrFetch(maybeFixUpURL(value.src, resolveOpts));
  }
}

function handleSrcProxyMode(srcValues) {
  // preservation worker in proxy mode sends us the value of the srcset attribute of an element
  // and a URL to correctly resolve relative URLS. Thus we must recreate rewrite_srcset logic here
  if (srcValues == null || srcValues.length === 0) return;
  var srcVal;
  for (var i = 0; i < srcValues.length; i++) {
    srcVal = srcValues[i];
    queueOrFetch(safeResolve(srcVal.src, srcVal.resolve));
  }
}

function extractSrcSetNotPreSplit(ssV, resolveOpts) {
  if (!ssV) return;
  // was from extract from local doc so we need to duplicate  work
  var srcsetValues = ssV.split(srcsetSplit);
  for (var i = 0; i < srcsetValues.length; i++) {
    // grab the URL not width/height key
    if (srcsetValues[i]) {
      var value = srcsetValues[i].trim().split(' ')[0];
      var maybeResolvedURL = maybeFixUpURL(value.trim(), resolveOpts);
      queueOrFetch(maybeResolvedURL);
    }
  }
}

function extractSrcset(srcsets) {
  // was rewrite_srcset and only need to q
  for (var i = 0; i < srcsets.length; i++) {
    // grab the URL not width/height key
    var url = srcsets[i].split(' ')[0];
    queueOrFetch(url);
  }
}

function handleSrcset(srcset, context) {
  if (srcset == null) return;
  var resolveOpts = {
    docBaseURI: context.docBaseURI,
    mod: null,
    tagSrc: null
  };
  if (srcset.value) {
    // we have a single value, this srcset came from either
    // preserveDataSrcset (not presplit) preserveSrcset (presplit)
    resolveOpts.mod = srcset.mod;
    if (!srcset.presplit) {
      // extract URLs from the srcset string
      return extractSrcSetNotPreSplit(srcset.value, resolveOpts);
    }
    // we have an array of srcset URL strings
    return extractSrcset(srcset.value);
  }
  // we have an array of values, these srcsets came from extractFromLocalDoc
  var len = srcset.values.length;
  for (var i = 0; i < len; i++) {
    var ssv = srcset.values[i];
    resolveOpts.mod = ssv.mod;
    resolveOpts.tagSrc = ssv.tagSrc;
    extractSrcSetNotPreSplit(ssv.srcset, resolveOpts);
  }
}

function handleSrcsetProxyMode(srcsets) {
  // preservation worker in proxy mode sends us the value of the srcset attribute of an element
  // and a URL to correctly resolve relative URLS. Thus we must recreate rewrite_srcset logic here
  if (srcsets == null) return;
  var length = srcsets.length;
  var extractedSrcSet, srcsetValue, ssSplit, j;
  for (var i = 0; i < length; i++) {
    extractedSrcSet = srcsets[i];
    ssSplit = extractedSrcSet.srcset.split(srcsetSplit);
    for (j = 0; j < ssSplit.length; j++) {
      if (ssSplit[j]) {
        srcsetValue = ssSplit[j].trim();
        if (srcsetValue) {
          queueOrFetch(
            safeResolve(srcsetValue.split(' ')[0], extractedSrcSet.resolve)
          );
        }
      }
    }
  }
}

function autoFetch(data) {
  // we got a message and now we autofetch!
  // these calls turn into no ops if they have no work
  if (data.media) {
    if (config.proxyMode) {
      handleMediaProxyMode(data.media);
    } else {
      handleMedia(data.media);
    }
  }

  if (data.src) {
    if (config.proxyMode) {
      handleSrcProxyMode(data.src);
    } else {
      handleSrc(data.src, data.context || { docBaseURI: null });
    }
  }

  if (data.srcset) {
    if (config.proxyMode) {
      handleSrcsetProxyMode(data.srcset);
    } else {
      handleSrcset(data.srcset, data.context || { docBaseURI: null });
    }
  }
}

function justFetch(data) {
  // we got a message containing only urls to be fetched
  if (data == null || data.values == null) return;
  for (var i = 0; i < data.values.length; ++i) {
    queueOrFetch(data.values[i]);
  }
}
