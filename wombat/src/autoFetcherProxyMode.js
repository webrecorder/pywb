import { autobind } from './wombatUtils';

/**
 * Create a new instance of AutoFetchWorkerProxyMode
 * @param {Wombat} wombat
 * @param {{isTop: boolean, workerURL: string}} config
 */
export default function AutoFetcherProxyMode(wombat, config) {
  if (!(this instanceof AutoFetcherProxyMode)) {
    return new AutoFetcherProxyMode(wombat, config);
  }
  /** @type {Wombat} */
  this.wombat = wombat;

  /** @type {?MutationObserver} */
  this.mutationObz = null;
  /** @type {?HTMLStyleElement} */
  this.styleTag = null;
  // specifically target the elements we desire
  /** @type {string} */
  this.elemSelector =
    'img[srcset], img[data-srcset], img[data-src], video[srcset], video[data-srcset], video[data-src], audio[srcset], audio[data-srcset], audio[data-src], ' +
    'picture > source[srcset], picture > source[data-srcset], picture > source[data-src], ' +
    'video > source[srcset], video > source[data-srcset], video > source[data-src], ' +
    'audio > source[srcset], audio > source[data-srcset], audio > source[data-src]';
  autobind(this);
  this._init(config, true);
}

/**
 * Initialize the auto fetch worker
 * @param {{isTop: boolean, workerURL: string}} config
 * @param {boolean} [first]
 * @private
 */
AutoFetcherProxyMode.prototype._init = function(config, first) {
  var afwpm = this;
  var wombat = this.wombat;
  if (document.readyState === 'complete') {
    this.styleTag = document.createElement('style');
    this.styleTag.id = '$wrStyleParser$';
    document.head.appendChild(this.styleTag);
    if (config.isTop) {
      // Cannot directly load our worker from the proxy origin into the current origin
      // however we fetch it from proxy origin and can blob it into the current origin :)
      fetch(config.workerURL).then(function(res) {
        res
          .text()
          .then(function(text) {
            var blob = new Blob([text], { type: 'text/javascript' });
            afwpm.worker = new wombat.$wbwindow.Worker(
              URL.createObjectURL(blob),
              { type: 'classic', credentials: 'include' }
            );
            afwpm.startChecking();
          })
          .catch(error => {
            console.error(
              'Could not create the backing worker for AutoFetchWorkerProxyMode'
            );
            console.error(error);
          });
      });
    } else {
      // add only the portions of the worker interface we use since we are not top and if in proxy mode start check polling
      this.worker = {
        postMessage: function(msg) {
          if (!msg.wb_type) {
            msg = { wb_type: 'aaworker', msg: msg };
          }
          wombat.$wbwindow.top.postMessage(msg, '*');
        },
        terminate: function() {}
      };
      this.startChecking();
    }
    return;
  }
  if (!first) return;
  var i = setInterval(function() {
    if (document.readyState === 'complete') {
      afwpm._init(config);
      clearInterval(i);
    }
  }, 1000);
};

/**
 * Initializes the mutation observer
 */
AutoFetcherProxyMode.prototype.startChecking = function() {
  this.extractFromLocalDoc();
  this.mutationObz = new MutationObserver(this.mutationCB);
  this.mutationObz.observe(document.documentElement, {
    characterData: false,
    characterDataOldValue: false,
    attributes: true,
    attributeOldValue: true,
    subtree: true,
    childList: true,
    attributeFilter: ['src', 'srcset']
  });
};

/**
 * Terminate the worker, a no op when not replay top
 */
AutoFetcherProxyMode.prototype.terminate = function() {
  this.worker.terminate();
};

/**
 * Sends the supplied array of URLs to the backing worker
 * @param {Array<string>} urls
 */
AutoFetcherProxyMode.prototype.justFetch = function(urls) {
  this.worker.postMessage({ type: 'fetch-all', values: urls });
};

/**
 * Sends the supplied msg to the backing worker
 * @param {Object} msg
 */
AutoFetcherProxyMode.prototype.postMessage = function(msg) {
  this.worker.postMessage(msg);
};

/**
 * Handles an style, link or text node that was mutated. If the text argument
 * is true the parent node of the text node is used otherwise the element itself
 * @param {*} elem
 * @param {Object} accum
 * @param {boolean} [text]
 * @return {void}
 */
AutoFetcherProxyMode.prototype.handleMutatedStyleElem = function(
  elem,
  accum,
  text
) {
  var baseURI = document.baseURI;
  var checkNode;
  if (text) {
    if (!elem.parentNode || elem.parentNode.localName !== 'style') return;
    checkNode = elem.parentNode;
  } else {
    checkNode = elem;
  }
  try {
    var extractedMedia = this.extractMediaRules(checkNode.sheet, baseURI);
    if (extractedMedia.length) {
      accum.media = accum.media.concat(extractedMedia);
      return;
    }
  } catch (e) {}
  if (!text && checkNode.href) {
    accum.deferred.push(this.fetchCSSAndExtract(checkNode.href));
  }
};

/**
 * Handles extracting the desired values from the mutated element
 * @param {*} elem
 * @param {Object} accum
 */
AutoFetcherProxyMode.prototype.handleMutatedElem = function(elem, accum) {
  var baseURI = document.baseURI;
  if (elem.nodeType === Node.TEXT_NODE) {
    return this.handleMutatedStyleElem(elem, accum, true);
  }
  switch (elem.localName) {
    case 'img':
    case 'video':
    case 'audio':
    case 'source':
      return this.handleDomElement(elem, baseURI, accum);
    case 'style':
    case 'link':
      return this.handleMutatedStyleElem(elem, accum);
  }
  return this.extractSrcSrcsetFrom(elem, baseURI, accum);
};

/**
 * Callback used for the mutation observer observe function
 * @param {Array<MutationRecord>} mutationList
 * @param {MutationObserver} observer
 */
AutoFetcherProxyMode.prototype.mutationCB = function(mutationList, observer) {
  var accum = { type: 'values', srcset: [], src: [], media: [], deferred: [] };
  for (var i = 0; i < mutationList.length; i++) {
    var mutation = mutationList[i];
    var mutationTarget = mutation.target;
    this.handleMutatedElem(mutationTarget, accum);
    if (mutation.type === 'childList' && mutation.addedNodes.length) {
      var addedLen = mutation.addedNodes.length;
      for (var j = 0; j < addedLen; j++) {
        this.handleMutatedElem(mutation.addedNodes[j], accum);
      }
    }
  }
  // send what we have extracted, if anything, to the worker for processing
  if (accum.deferred.length) {
    var deferred = accum.deferred;
    accum.deferred = null;
    Promise.all(deferred).then(this.handleDeferredSheetResults);
  }
  if (accum.srcset.length || accum.src.length || accum.media.length) {
    this.postMessage(accum);
  }
};

/**
 * Returns T/F indicating if the supplied stylesheet object is to be skipped
 * @param {StyleSheet} sheet
 * @return {boolean}
 */
AutoFetcherProxyMode.prototype.shouldSkipSheet = function(sheet) {
  // we skip extracting rules from sheets if they are from our parsing style or come from pywb
  if (sheet.id === '$wrStyleParser$') return true;
  return !!(
    sheet.href && sheet.href.indexOf(this.wombat.wb_info.proxy_magic) !== -1
  );
};

/**
 * Returns null if the supplied value is not usable for resolving rel URLs
 * otherwise returns the supplied value
 * @param {?string} srcV
 * @return {null|string}
 */
AutoFetcherProxyMode.prototype.validateSrcV = function(srcV) {
  if (!srcV || srcV.indexOf('data:') === 0 || srcV.indexOf('blob:') === 0) {
    return null;
  }
  return srcV;
};

/**
 * Because this JS in proxy mode operates as it would on the live web
 * the rules of CORS apply and we cannot rely on URLs being rewritten correctly
 * fetch the cross origin css file and then parse it using a style tag to get the rules
 * @param {string} cssURL
 * @return {Promise<Array>}
 */
AutoFetcherProxyMode.prototype.fetchCSSAndExtract = function(cssURL) {
  var url =
    location.protocol +
    '//' +
    this.wombat.wb_info.proxy_magic +
    '/proxy-fetch/' +
    cssURL;
  var afwpm = this;
  return fetch(url)
    .then(function(res) {
      return res.text().then(function(text) {
        afwpm.styleTag.textContent = text;
        return afwpm.extractMediaRules(afwpm.styleTag.sheet, cssURL);
      });
    })
    .catch(function(error) {
      return [];
    });
};

/**
 * Extracts CSSMedia rules from the supplied style sheet object
 * @param {CSSStyleSheet|StyleSheet} sheet
 * @param {string} baseURI
 * @return {Array<Object>}
 */
AutoFetcherProxyMode.prototype.extractMediaRules = function(sheet, baseURI) {
  // We are in proxy mode and must include a URL to resolve relative URLs in media rules
  var results = [];
  if (!sheet) return results;
  var rules;
  try {
    rules = sheet.cssRules || sheet.rules;
  } catch (e) {
    return results;
  }
  if (!rules || rules.length === 0) return results;
  var len = rules.length;
  var resolve = sheet.href || baseURI;
  for (var i = 0; i < len; ++i) {
    var rule = rules[i];
    if (rule.type === CSSRule.MEDIA_RULE) {
      results.push({ cssText: rule.cssText, resolve: resolve });
    }
  }
  return results;
};

/**
 * Returns the correct rewrite modifier for the supplied element
 * @param {Element} elem
 * @return {string}
 */
AutoFetcherProxyMode.prototype.rwMod = function(elem) {
  switch (elem.tagName) {
    case 'SOURCE':
      if (elem.parentElement && elem.parentElement.tagName === 'PICTURE') {
        return 'im_';
      }
      return 'oe_';
    case 'IMG':
      return 'im_';
  }
  return 'oe_';
};

/**
 * Extracts the srcset, data-[srcset, src], and src attribute (IFF source tag)
 * from the supplied element
 * @param {Element} elem
 * @param {string} baseURI
 * @param {?Object} acum
 */
AutoFetcherProxyMode.prototype.handleDomElement = function(
  elem,
  baseURI,
  acum
) {
  // we want the original src value in order to resolve URLs in the worker when needed
  var srcv = this.validateSrcV(elem.src);
  var resolve = srcv || baseURI;
  // get the correct mod in order to inform the backing worker where the URL(s) are from
  var mod = this.rwMod(elem);
  if (elem.srcset) {
    if (acum.srcset == null) acum = { srcset: [] };
    acum.srcset.push({ srcset: elem.srcset, resolve: resolve, mod: mod });
  }
  if (elem.dataset && elem.dataset.srcset) {
    if (acum.srcset == null) acum = { srcset: [] };
    acum.srcset.push({
      srcset: elem.dataset.srcset,
      resolve: resolve,
      mod: mod
    });
  }
  if (elem.dataset && elem.dataset.src) {
    if (acum.src == null) acum.src = [];
    acum.src.push({ src: elem.dataset.src, resolve: resolve, mod: mod });
  }
  if (elem.tagName === 'SOURCE' && srcv) {
    if (acum.src == null) acum.src = [];
    acum.src.push({ src: srcv, resolve: baseURI, mod: mod });
  }
};

/**
 * Calls {@link handleDomElement} for each element returned from
 * calling querySelector({@link elemSelector}) on the supplied element.
 *
 * If the acum argument is not supplied the results of the extraction
 * are sent to the backing worker
 * @param {*} fromElem
 * @param {string} baseURI
 * @param {Object} [acum]
 */
AutoFetcherProxyMode.prototype.extractSrcSrcsetFrom = function(
  fromElem,
  baseURI,
  acum
) {
  if (!fromElem.querySelectorAll) return;
  // retrieve the auto-fetched elements from the supplied dom node
  var elems = fromElem.querySelectorAll(this.elemSelector);
  var len = elems.length;
  var msg = acum != null ? acum : { type: 'values', srcset: [], src: [] };
  for (var i = 0; i < len; i++) {
    this.handleDomElement(elems[i], baseURI, msg);
  }
  // send what we have extracted, if anything, to the worker for processing
  if (acum == null && (msg.srcset.length || msg.src.length)) {
    this.postMessage(msg);
  }
};

/**
 * Sends the extracted media values to the backing worker
 * @param {Array<Array<string>>} results
 */
AutoFetcherProxyMode.prototype.handleDeferredSheetResults = function(results) {
  if (results.length === 0) return;
  var len = results.length;
  var media = [];
  for (var i = 0; i < len; ++i) {
    media = media.concat(results[i]);
  }
  if (media.length) {
    this.postMessage({ type: 'values', media: media });
  }
};

/**
 * Extracts CSS media rules from the supplied documents styleSheets list.
 * If a document is not supplied the document used defaults to the current
 * contexts document object
 * @param {?Document} [doc]
 */
AutoFetcherProxyMode.prototype.checkStyleSheets = function(doc) {
  var media = [];
  var deferredMediaExtraction = [];
  var styleSheets = (doc || document).styleSheets;
  var sheetLen = styleSheets.length;
  for (var i = 0; i < sheetLen; i++) {
    var sheet = styleSheets[i];
    // if the sheet belongs to our parser node we must skip it
    if (!this.shouldSkipSheet(sheet)) {
      try {
        // if no error is thrown due to cross origin sheet the urls then just add
        // the resolved URLS if any to the media urls array
        if (sheet.cssRules || sheet.rules) {
          var extracted = this.extractMediaRules(sheet, doc.baseURI);
          if (extracted.length) {
            media = media.concat(extracted);
          }
        } else if (sheet.href != null) {
          // depending on the browser cross origin stylesheets will have their
          // cssRules property null but href non-null
          deferredMediaExtraction.push(this.fetchCSSAndExtract(sheet.href));
        }
      } catch (error) {
        // the stylesheet is cross origin and we must re-fetch via PYWB to get the contents for checking
        if (sheet.href != null) {
          deferredMediaExtraction.push(this.fetchCSSAndExtract(sheet.href));
        }
      }
    }
  }

  if (media.length) {
    // send
    this.postMessage({ type: 'values', media: media });
  }

  if (deferredMediaExtraction.length) {
    // wait for all our deferred fetching and extraction of cross origin
    // stylesheets to complete and then send those values, if any, to the worker
    Promise.all(deferredMediaExtraction).then(this.handleDeferredSheetResults);
  }
};

/**
 * Performs extraction from the current contexts document
 */
AutoFetcherProxyMode.prototype.extractFromLocalDoc = function() {
  // check for data-[src,srcset] and auto-fetched elems with srcset first
  this.extractSrcSrcsetFrom(
    this.wombat.$wbwindow.document,
    this.wombat.$wbwindow.document.baseURI
  );
  // we must use the window reference passed to us to access this origins stylesheets
  this.checkStyleSheets(this.wombat.$wbwindow.document);
};
