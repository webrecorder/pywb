/* eslint-disable camelcase */

import { autobind } from './wombatUtils';

/**
 * @param {Wombat} wombat
 */
export default function AutoFetchWorker(wombat) {
  if (!(this instanceof AutoFetchWorker)) {
    return new AutoFetchWorker(wombat);
  }
  // specifically target the elements we desire
  this.elemSelector =
    'img[srcset], img[data-srcset], img[data-src], video[srcset], video[data-srcset], video[data-src], audio[srcset], audio[data-srcset], audio[data-src], ' +
    'picture > source[srcset], picture > source[data-srcset], picture > source[data-src], ' +
    'video > source[srcset], video > source[data-srcset], video > source[data-src], ' +
    'audio > source[srcset], audio > source[data-srcset], audio > source[data-src]';

  this.isTop = wombat.$wbwindow === wombat.$wbwindow.__WB_replay_top;

  /** @type {Wombat} */
  this.wombat = wombat;
  /** @type {Window} */
  this.$wbwindow = wombat.$wbwindow;

  /** @type {?Worker|Object} */
  this.worker = null;
  autobind(this);
  this._initWorker();
}

/**
 * Initializes the backing worker IFF the execution context we are in is
 * the replay tops otherwise creates a dummy worker that simply bounces the
 * message that would have been sent to the backing worker to replay top.
 *
 * If creation of the worker fails, likely due to the execution context we
 * are currently in having an null origin, we fallback to dummy worker creation.
 * @private
 */
AutoFetchWorker.prototype._initWorker = function() {
  var wombat = this.wombat;
  if (this.isTop) {
    // we are top and can will own this worker
    // setup URL for the kewl case
    // Normal replay and preservation mode pworker setup, its all one origin so YAY!
    var workerURL =
      (wombat.wb_info.auto_fetch_worker_prefix ||
        wombat.wb_info.static_prefix) +
      'autoFetchWorker.js?init=' +
      encodeURIComponent(
        JSON.stringify({
          mod: wombat.wb_info.mod,
          prefix: wombat.wb_abs_prefix,
          rwRe: wombat.wb_unrewrite_rx
        })
      );
    try {
      this.worker = new Worker(workerURL);
      return;
    } catch (e) {
      // it is likely we are in some kind of horrid iframe setup
      // and the execution context we are currently in has a null origin
      console.error(
        'Failed to create auto fetch worker\n',
        e,
        '\nFalling back to non top behavior'
      );
    }
  }

  // add only the portions of the worker interface we use since we are not top
  // and if in proxy mode start check polling
  this.worker = {
    postMessage: function(msg) {
      if (!msg.wb_type) {
        msg = { wb_type: 'aaworker', msg: msg };
      }
      wombat.$wbwindow.__WB_replay_top.__orig_postMessage(msg, '*');
    },
    terminate: function() {}
  };
};

/**
 * Extracts the media rules from the supplied CSSStyleSheet object if any
 * are present and returns an array of the media cssText
 * @param {CSSStyleSheet} sheet
 * @return {Array<string>}
 */
AutoFetchWorker.prototype.extractMediaRulesFromSheet = function(sheet) {
  var rules;
  var media = [];
  try {
    rules = sheet.cssRules || sheet.rules;
  } catch (e) {
    return media;
  }

  // loop through each rule of the stylesheet
  for (var i = 0; i < rules.length; ++i) {
    var rule = rules[i];
    if (rule.type === CSSRule.MEDIA_RULE) {
      // we are a media rule so get its text
      media.push(rule.cssText);
    }
  }
  return media;
};

/**
 * Extracts the media rules from the supplied CSSStyleSheet object if any
 * are present after a tick of the event loop sending the results of the
 * extraction to the backing worker
 * @param {CSSStyleSheet|StyleSheet} sheet
 */
AutoFetchWorker.prototype.deferredSheetExtraction = function(sheet) {
  var afw = this;
  // defer things until next time the Promise.resolve Qs are cleared
  Promise.resolve().then(function() {
    // loop through each rule of the stylesheet
    var media = afw.extractMediaRulesFromSheet(sheet);
    if (media.length > 0) {
      // we have some media rules to preserve
      afw.preserveMedia(media);
    }
  });
};

/**
 * Terminates the backing worker. This is a no op when we are not
 * operating in the execution context of replay top
 */
AutoFetchWorker.prototype.terminate = function() {
  // terminate the worker, a no op when not replay top
  this.worker.terminate();
};

/**
 * Sends a message to backing worker. If deferred is true
 * the message is sent after one tick of the event loop
 * @param {Object} msg
 * @param {boolean} [deferred]
 */
AutoFetchWorker.prototype.postMessage = function(msg, deferred) {
  if (deferred) {
    var afWorker = this;
    Promise.resolve().then(function() {
      afWorker.worker.postMessage(msg);
    });
    return;
  }
  this.worker.postMessage(msg);
};

/**
 * Sends the supplied srcset value to the backing worker for preservation
 * @param {string|Array<string>} srcset
 * @param {string} [mod]
 */
AutoFetchWorker.prototype.preserveSrcset = function(srcset, mod) {
  // send values from rewriteSrcset to the worker
  this.postMessage(
    {
      type: 'values',
      srcset: { values: srcset, mod: mod, presplit: true }
    },
    true
  );
};

/**
 * Send the value of the supplied elements data-srcset attribute to the
 * backing worker for preservation
 * @param {Node} elem
 */
AutoFetchWorker.prototype.preserveDataSrcset = function(elem) {
  // send values from rewriteAttr srcset to the worker deferred
  // to ensure the page viewer sees the images first
  this.postMessage(
    {
      type: 'values',
      srcset: {
        value: elem.dataset.srcset,
        mod: this.rwMod(elem),
        presplit: false
      }
    },
    true
  );
};

/**
 * Sends the supplied array of cssText from media rules to the backing worker
 * @param {Array<string>} media
 */
AutoFetchWorker.prototype.preserveMedia = function(media) {
  // send CSSMediaRule values to the worker
  this.postMessage({ type: 'values', media: media }, true);
};

/**
 * Extracts the value of the srcset property if it exists from the supplied
 * element
 * @param {Element} elem
 * @return {?string}
 */
AutoFetchWorker.prototype.getSrcset = function(elem) {
  if (this.wombat.wb_getAttribute) {
    return this.wombat.wb_getAttribute.call(elem, 'srcset');
  }
  return elem.getAttribute('srcset');
};

/**
 * Returns the correct rewrite modifier for the supplied element
 * @param {Element} elem
 * @return {string}
 */
AutoFetchWorker.prototype.rwMod = function(elem) {
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
 * Extracts the media rules from stylesheets and the (data-)srcset URLs from
 * image elements the current context's document contains
 */
AutoFetchWorker.prototype.extractFromLocalDoc = function() {
  // get the values to be preserved from the documents stylesheets
  // and all img, video, audio elements with (data-)?srcset or data-src
  var afw = this;
  Promise.resolve().then(function() {
    var msg = {
      type: 'values',
      context: { docBaseURI: document.baseURI }
    };
    var media = [];
    var i = 0;
    var sheets = document.styleSheets;
    for (; i < sheets.length; ++i) {
      media = media.concat(afw.extractMediaRulesFromSheet(sheets[i]));
    }
    var elems = document.querySelectorAll(afw.elemSelector);
    var srcset = { values: [], presplit: false };
    var src = { values: [] };
    var elem, srcv, mod;
    for (i = 0; i < elems.length; ++i) {
      elem = elems[i];
      // we want the original src value in order to resolve URLs in the worker when needed
      srcv = elem.src ? elem.src : null;
      // a from value of 1 indicates images and a 2 indicates audio/video
      mod = afw.rwMod(elem);
      if (elem.srcset) {
        srcset.values.push({
          srcset: afw.getSrcset(elem),
          mod: mod,
          tagSrc: srcv
        });
      }
      if (elem.dataset.srcset) {
        srcset.values.push({
          srcset: elem.dataset.srcset,
          mod: mod,
          tagSrc: srcv
        });
      }
      if (elem.dataset.src) {
        src.values.push({ src: elem.dataset.src, mod: mod });
      }
      if (elem.tagName === 'SOURCE' && srcv) {
        src.values.push({ src: srcv, mod: mod });
      }
    }
    if (media.length) {
      msg.media = media;
    }
    if (srcset.values.length) {
      msg.srcset = srcset;
    }
    if (src.values.length) {
      msg.src = src;
    }
    if (msg.media || msg.srcset || msg.src) {
      afw.postMessage(msg);
    }
  });
};
