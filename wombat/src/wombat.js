/* eslint-disable camelcase */
import FuncMap from './funcMap';
import Storage from './customStorage';
import WombatLocation from './wombatLocation';
import AutoFetcher from './autoFetcher';
import { wrapEventListener, wrapSameOriginEventListener } from './listeners';
import {
  addToStringTagToClass,
  autobind,
  ThrowExceptions
} from './wombatUtils';

/**
 * @param {Window} $wbwindow
 * @param {Object} wbinfo
 */
function Wombat($wbwindow, wbinfo) {
  if (!(this instanceof Wombat)) return new Wombat($wbwindow, wbinfo);

  /** @type {boolean} */
  this.actual = false;

  /** @type {boolean} */
  this.debug_rw = false;

  /** @type {Window} */
  this.$wbwindow = $wbwindow;

  /** @type {string} */
  this.HTTP_PREFIX = 'http://';

  /** @type {string} */
  this.HTTPS_PREFIX = 'https://';

  /** @type {string} */
  this.REL_PREFIX = '//';

  /** @type {Array<string>} */
  this.VALID_PREFIXES = [this.HTTP_PREFIX, this.HTTPS_PREFIX, this.REL_PREFIX];

  /** @type {Array<string>} */
  this.IGNORE_PREFIXES = [
    '#',
    'about:',
    'data:',
    'mailto:',
    'javascript:',
    '{',
    '*'
  ];

  /** @type {function(qualifiedName: string, value: string): void} */
  this.wb_setAttribute = $wbwindow.Element.prototype.setAttribute;

  /** @type {function(qualifiedName: string): ?string} */
  this.wb_getAttribute = $wbwindow.Element.prototype.getAttribute;

  /** @type {function(): string} */
  this.wb_funToString = Function.prototype.toString;

  /** @type {AutoFetcher} */
  this.WBAutoFetchWorker = null;

  /** @type {boolean} */
  this.wbUseAFWorker =
    wbinfo.enable_auto_fetch && $wbwindow.Worker != null && wbinfo.is_live;

  /** @type {string} */
  this.wb_rel_prefix = '';

  /** @type {boolean} */
  this.wb_wombat_updating = false;

  /** @type {FuncMap} */
  this.message_listeners = new FuncMap();

  /** @type {FuncMap} */
  this.storage_listeners = new FuncMap();

  /**
   * rewrite modifiers for <link href="URL" rel="import|preload" as="x">
   * expressed as as-value -> modifier
   * @type {Object}
   */
  this.linkAsTypes = {
    script: 'js_',
    worker: 'js_',
    style: 'cs_',
    image: 'im_',
    document: 'if_',
    fetch: 'mp_',
    font: 'oe_',
    audio: 'oe_',
    video: 'oe_',
    embed: 'oe_',
    object: 'oe_',
    track: 'oe_',
    // the following cover the default case
    '': 'mp_',
    null: 'mp_',
    undefined: 'mp_'
  };

  /**
   * rewrite modifiers for <link href="URL" rel="x"> and or
   * <link href="URL" rel="x" as="y"> expressed as a mapping of
   * rel -> modifier or rel -> as -> modifier
   * @type {Object}
   */
  this.linkTagMods = {
    linkRelToAs: {
      import: this.linkAsTypes,
      preload: this.linkAsTypes
    },
    stylesheet: 'cs_',
    // the following cover the default case
    null: 'mp_',
    undefined: 'mp_',
    '': 'mp_'
  };

  /**
   * pre-computed modifiers for each tag
   * @type {Object}
   */
  this.tagToMod = {
    A: { href: 'mp_' },
    AREA: { href: 'mp_' },
    AUDIO: { src: 'oe_', poster: 'im_' },
    BASE: { href: 'mp_' },
    EMBED: { src: 'oe_' },
    FORM: { action: 'mp_' },
    FRAME: { src: 'fr_' },
    IFRAME: { src: 'if_' },
    IMAGE: { href: 'im_', 'xlink:href': 'im_' },
    IMG: { src: 'im_', srcset: 'im_' },
    INPUT: { src: 'oe_' },
    INS: { cite: 'mp_' },
    META: { content: 'mp_' },
    OBJECT: { data: 'oe_', codebase: 'oe_' },
    Q: { cite: 'mp_' },
    // covers both HTML and SVG script element,
    SCRIPT: { src: 'js_', 'xlink:href': 'js_' },
    SOURCE: { src: 'oe_', srcset: 'oe_' },
    TRACK: { src: 'oe_' },
    VIDEO: { src: 'oe_', poster: 'im_' },
    image: { href: 'im_', 'xlink:href': 'im_' }
  };

  /** @type {Array<string>} */
  this.URL_PROPS = [
    'href',
    'hash',
    'pathname',
    'host',
    'hostname',
    'protocol',
    'origin',
    'search',
    'port'
  ];

  /** @type {Object} */
  this.wb_info = wbinfo;

  /**
   * custom options
   * @type {Object}
   */
  this.wb_opts = wbinfo.wombat_opts;

  /** @type {string} */
  this.wb_replay_prefix = wbinfo.prefix;

  /** @type {boolean} */
  this.wb_is_proxy = this.wb_info.proxy_magic || !this.wb_replay_prefix;

  /** @type {string} */
  this.wb_info.top_host = this.wb_info.top_host || '*';

  /** @type {string} */
  this.wb_curr_host =
    $wbwindow.location.protocol + '//' + $wbwindow.location.host;

  /** @type {Object} */
  this.wb_info.wombat_opts = this.wb_info.wombat_opts || {};

  /** @type {string} */
  this.wb_orig_scheme = this.wb_info.wombat_scheme + '://';
  /** @type {string} */
  this.wb_orig_origin = this.wb_orig_scheme + this.wb_info.wombat_host;

  /** @type {string} */
  this.wb_abs_prefix = this.wb_replay_prefix;

  /** @type {string} */
  this.wb_capture_date_part = '';
  if (!this.wb_info.is_live && this.wb_info.wombat_ts) {
    this.wb_capture_date_part = '/' + this.wb_info.wombat_ts + '/';
  }

  /** @type {Array<string>} */
  this.BAD_PREFIXES = [
    'http:' + this.wb_replay_prefix,
    'https:' + this.wb_replay_prefix,
    'http:/' + this.wb_replay_prefix,
    'https:/' + this.wb_replay_prefix
  ];

  /** @type {RegExp} */
  this.hostnamePortRe = /^[\w-]+(\.[\w-_]+)+(:\d+)(\/|$)/;

  /** @type {RegExp} */
  this.ipPortRe = /^\d+\.\d+\.\d+\.\d+(:\d+)?(\/|$)/;

  /** @type {RegExp} */
  this.workerBlobRe = /__WB_pmw\(.*?\)\.(?=postMessage\()/g;
  /** @type {RegExp} */
  this.rmCheckThisInjectRe = /_____WB\$wombat\$check\$this\$function_____\(.*?\)/g;

  /** @type {RegExp} */
  this.STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/gi;

  /** @type {RegExp} */
  this.IMPORT_REGEX = /(@import\s*[\\"']*)([^)'";]+)([\\"']*\s*;?)/gi;

  /** @type {RegExp} */
  this.no_wombatRe = /WB_wombat_/g;

  /** @type {RegExp} */
  this.srcsetRe = /\s*(\S*\s+[\d.]+[wx]),|(?:\s*,(?:\s+|(?=https?:)))/;

  /** @type {RegExp} */
  this.cookie_path_regex = /\bPath='?"?([^;'"\s]+)/i;

  /** @type {RegExp} */
  this.cookie_domain_regex = /\bDomain=([^;'"\s]+)/i;

  /** @type {RegExp} */
  this.cookie_expires_regex = /\bExpires=([^;'"]+)/gi;

  /** @type {RegExp} */
  this.SetCookieRe = /,(?![|])/;

  /** @type {RegExp} */
  this.IP_RX = /^(\d)+\.(\d)+\.(\d)+\.(\d)+$/;

  /** @type {RegExp} */
  this.FullHTMLRegex = /^\s*<(?:html|head|body|!doctype html)/i;

  /** @type {RegExp} */
  this.DotPostMessageRe = /(.postMessage\s*\()/;

  /** @type {RegExp} */
  this.extractPageUnderModiferRE = /\/(?:[0-9]{14})?([a-z]{2, 3}_)\//;

  /** @type {string} */
  this.write_buff = '';

  var eTargetProto = ($wbwindow.EventTarget || {}).prototype;
  /** @type {Object} */
  this.utilFns = {
    cspViolationListener: function(e) {
      console.group('CSP Violation');
      console.log('Replayed Page URL', window.WB_wombat_location.href);
      console.log('The documentURI', e.documentURI);
      console.log('The blocked URL', e.blockedURI);
      console.log('The directive violated', e.violatedDirective);
      console.log('Our policy', e.originalPolicy);
      if (e.sourceFile) {
        var fileInfo = 'File: ' + e.sourceFile;
        if (e.lineNumber && e.columnNumber) {
          fileInfo += ' @ ' + e.lineNumber + ':' + e.columnNumber;
        } else if (e.lineNumber) {
          fileInfo += ' @ ' + e.lineNumber;
        }
        console.log(fileInfo);
      }
      console.groupEnd();
    },
    addEventListener: eTargetProto.addEventListener,
    removeEventListener: eTargetProto.removeEventListener,
    // some sites do funky things with the toString function
    // (e.g. if used throw error or deny operation) hence we
    // need a surefire and safe way to tell us what an object
    // or function is hence Objects native toString
    objToString: Object.prototype.toString,
    wbSheetMediaQChecker: null,
    XHRopen: null
  };
  /**
   * @type {{yesNo: boolean, added: boolean}}
   */
  this.showCSPViolations = { yesNo: false, added: false };
  autobind(this);
  // this._addRemoveCSPViolationListener(true);
}

/**
 * Performs the initialization of wombat's internals:
 *  - {@link initTopFrame}
 *  - {@link initWombatLoc}
 *  - {@link initWombatTop}
 *  - {@link initAutoFetchWorker}
 *  - initializes the wb_rel_prefix property
 *  - initializes the wb_unrewrite_rx property
 *  - if we are in framed replay mode and the wb_info mod is not bn_
 *    {@link initTopFrameNotify} is called
 * @private
 */
Wombat.prototype._internalInit = function() {
  this.initTopFrame(this.$wbwindow);
  this.initWombatLoc(this.$wbwindow);
  this.initWombatTop(this.$wbwindow);
  // updated wb_unrewrite_rx for imgur.com
  var wb_origin = this.$wbwindow.__WB_replay_top.location.origin;
  var wb_host = this.$wbwindow.__WB_replay_top.location.host;
  var wb_proto = this.$wbwindow.__WB_replay_top.location.protocol;
  if (this.wb_replay_prefix && this.wb_replay_prefix.indexOf(wb_origin) === 0) {
    this.wb_rel_prefix = this.wb_replay_prefix.substring(wb_origin.length);
  } else {
    this.wb_rel_prefix = this.wb_replay_prefix;
  }

  // make the protocol and host optional now
  var rx =
    '((' + wb_proto + ')?//' + wb_host + ')?' + this.wb_rel_prefix + '[^/]+/';
  this.wb_unrewrite_rx = new RegExp(rx, 'g');

  if (this.wb_info.is_framed && this.wb_info.mod !== 'bn_') {
    this.initTopFrameNotify(this.wb_info);
  }
  this.initAutoFetchWorker();
};

/**
 * Internal function that adds a "securitypolicyviolation" event listener
 * to the document that will log any CSP violations in a nicer way than
 * is the default
 *
 * If the yesNo argument is true, the event listener is added, otherwise
 * it is removed
 * @param {boolean} yesNo
 * @private
 */
Wombat.prototype._addRemoveCSPViolationListener = function(yesNo) {
  this.showCSPViolations.yesNo = yesNo;
  if (this.showCSPViolations.yesNo && !this.showCSPViolations.added) {
    this.showCSPViolations.added = true;
    this._addEventListener(
      document,
      'securitypolicyviolation',
      this.utilFns.cspViolationListener
    );
  } else {
    this.showCSPViolations.added = false;
    this._removeEventListener(
      document,
      'securitypolicyviolation',
      this.utilFns.cspViolationListener
    );
  }
};

/**
 * Adds the supplied event listener on the supplied event target
 * @param {Object} obj
 * @param {string} event
 * @param {Function} fun
 * @return {*}
 * @private
 */
Wombat.prototype._addEventListener = function(obj, event, fun) {
  if (this.utilFns.addEventListener) {
    return this.utilFns.addEventListener.call(obj, event, fun);
  }
  obj.addEventListener(event, fun);
};

/**
 * Removes the supplied event listener on the supplied event target
 * @param {Object} obj
 * @param {string} event
 * @param {Function} fun
 * @return {*}
 * @private
 */
Wombat.prototype._removeEventListener = function(obj, event, fun) {
  if (this.utilFns.removeEventListener) {
    return this.utilFns.removeEventListener.call(obj, event, fun);
  }
  obj.removeEventListener(event, fun);
};

/**
 * Extracts the modifier (i.e. mp\_, if\_, ...) the page is under that wombat is
 * operating in. If extracting the modifier fails for some reason mp\_ is returned.
 * Used to ensure the correct modifier is used for rewriting the service workers scope.
 * @return {string}
 */
Wombat.prototype.getPageUnderModifier = function() {
  try {
    var pageUnderModifier = this.extractPageUnderModiferRE.exec(
      location.pathname
    );
    if (pageUnderModifier && pageUnderModifier[1]) {
      var mod = pageUnderModifier[1].trim();
      return mod || 'mp_';
    }
  } catch (e) {}
  return 'mp_';
};

/**
 * Returns T/F indicating if the supplied function is a native function
 * or not. The test checks for the presence of the substring `'[native code]'`
 * in the result of calling `toString` on the function
 * @param {Function} funToTest - The function to be tested
 * @return {boolean}
 */
Wombat.prototype.isNativeFunction = function(funToTest) {
  if (!funToTest || typeof funToTest !== 'function') return false;
  return this.wb_funToString.call(funToTest).indexOf('[native code]') >= 0;
};

/**
 * Returns T/F indicating if the supplied argument is a string or not
 * @param {*} arg
 * @return {boolean}
 */
Wombat.prototype.isString = function(arg) {
  return arg != null && Object.getPrototypeOf(arg) === String.prototype;
};

/**
 * Returns T/F indicating if the supplied element may have attributes that
 * are auto-fetched
 * @param {Element} elem
 * @return {boolean}
 */
Wombat.prototype.isSavedSrcSrcset = function(elem) {
  switch (elem.tagName) {
    case 'IMG':
    case 'VIDEO':
    case 'AUDIO':
      return true;
    case 'SOURCE':
      if (!elem.parentElement) return false;
      switch (elem.parentElement.tagName) {
        case 'PICTURE':
        case 'VIDEO':
        case 'AUDIO':
          return true;
        default:
          return false;
      }
    default:
      return false;
  }
};

/**
 * Returns T/F indicating if the supplied element is an Image element that
 * may have srcset values to be sent to the backing auto-fetch worker
 * @param {Element} elem
 * @return {boolean}
 */
Wombat.prototype.isSavedDataSrcSrcset = function(elem) {
  if (elem.dataset && elem.dataset.srcset != null) {
    return this.isSavedSrcSrcset(elem);
  }
  return false;
};

/**
 * Determines if the supplied string is an host URL
 * @param {string} str
 * @return {boolean}
 */
Wombat.prototype.isHostUrl = function(str) {
  // Good guess that's its a hostname
  if (str.indexOf('www.') === 0) {
    return true;
  }

  // hostname:port (port required)
  var matches = str.match(this.hostnamePortRe);
  if (matches && matches[0].length < 64) {
    return true;
  }

  // ip:port
  matches = str.match(this.ipPortRe);
  if (matches) {
    return matches[0].length < 64;
  }
  return false;
};

/**
 * Returns T/F indicating if the supplied object is the arguments object
 * @param {*} maybeArgumentsObj
 * @return {boolean}
 */
Wombat.prototype.isArgumentsObj = function(maybeArgumentsObj) {
  if (
    !maybeArgumentsObj ||
    !(typeof maybeArgumentsObj.toString === 'function')
  ) {
    return false;
  }
  try {
    return (
      this.utilFns.objToString.call(maybeArgumentsObj) === '[object Arguments]'
    );
  } catch (e) {
    return false;
  }
};

/**
 * Ensures that each element in the supplied arguments object or
 * array is deproxied handling cases where we can not modify the
 * supplied object returning a new or modified object with the
 * exect elements/properties
 * @param {*} maybeArgumentsObj
 * @return {*}
 */
Wombat.prototype.deproxyArrayHandlingArgumentsObj = function(
  maybeArgumentsObj
) {
  if (
    !maybeArgumentsObj ||
    maybeArgumentsObj instanceof NodeList ||
    !maybeArgumentsObj.length
  ) {
    return maybeArgumentsObj;
  }
  var args = this.isArgumentsObj(maybeArgumentsObj)
    ? new Array(maybeArgumentsObj.length)
    : maybeArgumentsObj;
  for (var i = 0; i < maybeArgumentsObj.length; ++i) {
    args[i] = this.proxyToObj(maybeArgumentsObj[i]);
  }
  return args;
};

/**
 * Determines if a string starts with the supplied prefix.
 * If it does the matching prefix is returned otherwise undefined.
 * @param {?string} string
 * @param {string} prefix
 * @return {?string}
 */
Wombat.prototype.startsWith = function(string, prefix) {
  if (!string) return undefined;
  return string.indexOf(prefix) === 0 ? prefix : undefined;
};

/**
 * Determines if a string starts with the supplied array of prefixes.
 * If it does the matching prefix is returned otherwise undefined.
 * @param {?string} string
 * @param {Array<string>} prefixes
 * @return {?string}
 */
Wombat.prototype.startsWithOneOf = function(string, prefixes) {
  if (!string) return undefined;
  for (var i = 0; i < prefixes.length; i++) {
    if (string.indexOf(prefixes[i]) === 0) {
      return prefixes[i];
    }
  }
  return undefined;
};

/**
 * Determines if a string ends with the supplied suffix.
 * If it does the suffix is returned otherwise undefined.
 * @param {?string} str
 * @param {string} suffix
 * @return {?string}
 */
Wombat.prototype.endsWith = function(str, suffix) {
  if (!str) return undefined;
  if (str.indexOf(suffix, str.length - suffix.length) !== -1) {
    return suffix;
  }
  return undefined;
};

/**
 * Returns T/F indicating if the supplied tag name and attribute name
 * combination are to be rewritten
 * @param {string} tagName
 * @param {string} attr
 * @return {boolean}
 */
Wombat.prototype.shouldRewriteAttr = function(tagName, attr) {
  switch (attr) {
    case 'href':
    case 'src':
    case 'xlink:href':
      return true;
  }
  if (
    tagName &&
    this.tagToMod[tagName] &&
    this.tagToMod[tagName][attr] !== undefined
  ) {
    return true;
  }
  return (
    (tagName === 'VIDEO' && attr === 'poster') ||
    (tagName === 'META' && attr === 'content')
  );
};

/**
 * Returns T/F indicating if the script tag being rewritten should not
 * have its text contents wrapped based on the supplied script type.
 * @param {?string} scriptType
 * @return {boolean}
 */
Wombat.prototype.skipWrapScriptBasedOnType = function(scriptType) {
  if (!scriptType) return false;
  if (scriptType.indexOf('json') >= 0) return true;
  return scriptType.indexOf('text/template') >= 0;
};

/**
 * Returns T/F indicating if the script tag being rewritten should not
 * have its text contents wrapped based on heuristic analysis of its
 * text contents.
 * @param {?string} text
 * @return {boolean}
 */
Wombat.prototype.skipWrapScriptTextBasedOnText = function(text) {
  if (
    !text ||
    text.indexOf('_____WB$wombat$assign$function_____') >= 0 ||
    text.indexOf('<') === 0
  ) {
    return true;
  }
  var override_props = [
    'window',
    'self',
    'document',
    'location',
    'top',
    'parent',
    'frames',
    'opener'
  ];

  for (var i = 0; i < override_props.length; i++) {
    if (text.indexOf(override_props[i]) >= 0) {
      return false;
    }
  }

  return true;
};

/**
 * Returns T/F indicating if the supplied DOM Node has child Elements/Nodes.
 * Note this function should be used when the Node(s) being considered can
 * be null/undefined.
 * @param {Node} node
 * @return {boolean}
 */
Wombat.prototype.nodeHasChildren = function(node) {
  if (!node) return false;
  if (typeof node.hasChildNodes === 'function') return node.hasChildNodes();
  var kids = node.children || node.childNodes;
  if (kids) return kids.length > 0;
  return false;
};

/**
 * Returns the correct rewrite modifier for the supplied element and
 * attribute combination if one exists otherwise mp_.
 * Used by
 *  - {@link performAttributeRewrite}
 *  - {@link rewriteFrameSrc}
 *  - {@link initElementGetSetAttributeOverride}
 *  - {@link overrideHrefAttr}
 *
 * @param {*} elem
 * @param {string} attrName
 * @return {?string}
 */
Wombat.prototype.rwModForElement = function(elem, attrName) {
  if (!elem) return undefined;
  // the default modifier, if none is supplied to rewrite_url, is mp_
  var mod = 'mp_';
  if (elem.tagName === 'LINK' && attrName === 'href') {
    // link types are always ASCII case-insensitive, and must be compared as such.
    // https://html.spec.whatwg.org/multipage/links.html#linkTypes
    if (elem.rel) {
      var relV = elem.rel.trim().toLowerCase();
      var asV = this.wb_getAttribute.call(elem, 'as');
      if (asV && this.linkTagMods.linkRelToAs[relV] != null) {
        var asMods = this.linkTagMods.linkRelToAs[relV];
        mod = asMods[asV.toLowerCase()];
      } else if (this.linkTagMods[relV] != null) {
        mod = this.linkTagMods[relV];
      }
    }
  } else {
    // check if this element has an rewrite modifiers and set mod to it if it does
    var maybeMod = this.tagToMod[elem.tagName];
    if (maybeMod != null) {
      mod = maybeMod[attrName];
    }
  }
  return mod;
};

/**
 * If the supplied element is a script tag and has the server-side rewrite added
 * property "__wb_orig_src" it is removed and the "__$removedWBOSRC$__" property
 * is added to element as an internal flag indicating no further checks are to be
 * made.
 *
 * See also {@link retrieveWBOSRC}
 * @param {Element} elem
 */
Wombat.prototype.removeWBOSRC = function(elem) {
  if (elem.tagName === 'SCRIPT' && !elem.__$removedWBOSRC$__) {
    if (elem.hasAttribute('__wb_orig_src')) {
      elem.removeAttribute('__wb_orig_src');
    }
    elem.__$removedWBOSRC$__ = true;
  }
};

/**
 * If the supplied element is a script tag and has the server-side rewrite added
 * property "__wb_orig_src" its value is returned otherwise undefined is returned.
 * If the element did not have the "__wb_orig_src" property the
 * "__$removedWBOSRC$__" property is added to element as an internal flag
 * indicating no further checks are to be made.
 *
 * See also {@link removeWBOSRC}
 * @param {Element} elem
 * @return {?string}
 */
Wombat.prototype.retrieveWBOSRC = function(elem) {
  if (elem.tagName === 'SCRIPT' && !elem.__$removedWBOSRC$__) {
    var maybeWBOSRC;
    if (this.wb_getAttribute) {
      maybeWBOSRC = this.wb_getAttribute.call(elem, '__wb_orig_src');
    } else {
      maybeWBOSRC = elem.getAttribute('__wb_orig_src');
    }
    if (maybeWBOSRC == null) elem.__$removedWBOSRC$__ = true;
    return maybeWBOSRC;
  }
  return undefined;
};

/**
 * Wraps the supplied text contents of a script tag with the required Wombat setup
 * @param {?string} scriptText
 * @return {string}
 */
Wombat.prototype.wrapScriptTextJsProxy = function(scriptText) {
  return (
    'var _____WB$wombat$assign$function_____ = function(name) {return (self._wb_wombat && ' +
    'self._wb_wombat.local_init &&self._wb_wombat.local_init(name)) || self[name]; };\n' +
    'var _____WB$wombat$check$this$function_____ = function(thisObj) {' +
    'if (thisObj && thisObj._WB_wombat_obj_proxy) return thisObj._WB_wombat_obj_proxy;' +
    'return thisObj; }\nif (!self.__WB_pmw) { self.__WB_pmw = function(obj) { ' +
    'this.__WB_source = obj; return this; } }\n{\n' +
    'let window = _____WB$wombat$assign$function_____("window");\n' +
    'let self = _____WB$wombat$assign$function_____("self");\n' +
    'let document = _____WB$wombat$assign$function_____("document");\n' +
    'let location = _____WB$wombat$assign$function_____("location");\n' +
    'let top = _____WB$wombat$assign$function_____("top");\n' +
    'let parent = _____WB$wombat$assign$function_____("parent");\n' +
    'let frames = _____WB$wombat$assign$function_____("frames");\n' +
    'let opener = _____WB$wombat$assign$function_____("opener");\n' +
    scriptText.replace(this.DotPostMessageRe, '.__WB_pmw(self.window)$1') +
    '\n\n}'
  );
};

/**
 * Calls the supplied function when the supplied element undergoes mutations
 * @param elem
 * @param func
 * @return {boolean}
 */
Wombat.prototype.watchElem = function(elem, func) {
  if (!this.$wbwindow.MutationObserver) {
    return false;
  }
  var m = new this.$wbwindow.MutationObserver(function(records, observer) {
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      if (r.type === 'childList') {
        for (var j = 0; j < r.addedNodes.length; j++) {
          func(r.addedNodes[j]);
        }
      }
    }
  });

  m.observe(elem, {
    childList: true,
    subtree: true
  });
};

/**
 * Reconstructs the doctype string if the supplied doctype object
 * is non null/undefined. This function is used by {@link rewriteHtmlFull}
 * in order to ensure correctness of rewriting full string of HTML that
 * started with <!doctype ...> since the innerHTML and outerHTML properties
 * do not include that.
 * @param {DocumentType} doctype
 * @return {string}
 */
Wombat.prototype.reconstructDocType = function(doctype) {
  if (doctype == null) return '';
  return (
    '<!doctype ' +
    doctype.name +
    (doctype.publicId ? ' PUBLIC "' + doctype.publicId + '"' : '') +
    (!doctype.publicId && doctype.systemId ? ' SYSTEM' : '') +
    (doctype.systemId ? ' "' + doctype.systemId + '"' : '') +
    '>'
  );
};

/**
 * Constructs the final URL for the URL rewriting process
 * @param {boolean} useRel
 * @param {string} mod
 * @param {string} url
 * @return {string}
 */
Wombat.prototype.getFinalUrl = function(useRel, mod, url) {
  var prefix = useRel ? this.wb_rel_prefix : this.wb_abs_prefix;

  if (mod == null) {
    mod = this.wb_info.mod;
  }

  // if live, don't add the timestamp
  if (!this.wb_info.is_live) {
    prefix += this.wb_info.wombat_ts;
  }

  prefix += mod;

  if (prefix[prefix.length - 1] !== '/') {
    prefix += '/';
  }

  return prefix + url;
};

/**
 * Converts the supplied relative URL to an absolute URL using an A tag
 * @param {string} url
 * @param {?Document} doc
 * @return {string}
 */
Wombat.prototype.resolveRelUrl = function(url, doc) {
  var docObj = doc || this.$wbwindow.document;
  var parser = this.makeParser(docObj.baseURI, docObj);
  var hash = parser.href.lastIndexOf('#');
  var href = hash >= 0 ? parser.href.substring(0, hash) : parser.href;
  var lastslash = href.lastIndexOf('/');

  if (lastslash >= 0 && lastslash !== href.length - 1) {
    parser.href = href.substring(0, lastslash + 1) + url;
  } else {
    parser.href = href + url;
  }
  return parser.href;
};

/**
 * Extracts the original URL from the supplied rewritten URL
 * @param {?string} rewrittenUrl
 * @return {string}
 */
Wombat.prototype.extractOriginalURL = function(rewrittenUrl) {
  if (!rewrittenUrl) {
    return '';
  } else if (this.wb_is_proxy) {
    // proxy mode: no extraction needed
    return rewrittenUrl;
  }

  var rwURLString = rewrittenUrl.toString();

  var url = rwURLString;

  // ignore certain urls
  if (this.startsWithOneOf(url, this.IGNORE_PREFIXES)) {
    return url;
  }

  var start;

  if (this.startsWith(url, this.wb_abs_prefix)) {
    start = this.wb_abs_prefix.length;
  } else if (this.wb_rel_prefix && this.startsWith(url, this.wb_rel_prefix)) {
    start = this.wb_rel_prefix.length;
  } else {
    // if no coll, start from beginning, otherwise could be part of coll..
    start = this.wb_rel_prefix ? 1 : 0;
  }

  var index = url.indexOf('/http', start);
  if (index < 0) {
    index = url.indexOf('///', start);
  }

  // extract original url from wburl
  if (index >= 0) {
    url = url.substr(index + 1);
  } else {
    index = url.indexOf(this.wb_replay_prefix);
    if (index >= 0) {
      url = url.substr(index + this.wb_replay_prefix.length);
    }
    if (url.length > 4 && url.charAt(2) === '_' && url.charAt(3) === '/') {
      url = url.substr(4);
    }

    if (
      url !== rwURLString &&
      !this.startsWithOneOf(url, this.VALID_PREFIXES)
    ) {
      url = this.wb_orig_scheme + url;
    }
  }

  if (
    rwURLString.charAt(0) === '/' &&
    rwURLString.charAt(1) !== '/' &&
    this.startsWith(url, this.wb_orig_origin)
  ) {
    url = url.substr(this.wb_orig_origin.length);
  }

  if (this.startsWith(url, this.REL_PREFIX)) {
    return this.wb_info.wombat_scheme + ':' + url;
  }

  return url;
};

/**
 * Creates and returns an A tag ready for parsing the original URL
 * part of the supplied URL.
 * @param {string} maybeRewrittenURL
 * @param {?Document} doc
 * @return {HTMLAnchorElement}
 */
Wombat.prototype.makeParser = function(maybeRewrittenURL, doc) {
  var originalURL = this.extractOriginalURL(maybeRewrittenURL);
  var docElem = doc;
  if (!doc) {
    // special case: for newly opened blank windows, use the opener
    // to create parser to have the proper baseURI
    if (
      this.$wbwindow.location.href === 'about:blank' &&
      this.$wbwindow.opener
    ) {
      docElem = this.$wbwindow.opener.document;
    } else {
      docElem = this.$wbwindow.document;
    }
  }

  var p = docElem.createElement('a');
  p._no_rewrite = true;
  p.href = originalURL;
  return p;
};

/**
 * Defines a new getter and optional setter for the property on the supplied
 * object returning T/F to indicate if the new property was successfully defined
 * @param {Object} obj
 * @param {string} prop
 * @param {?function(value: *): *} setFunc
 * @param {function(): *} getFunc
 * @param {?boolean} [enumerable]
 * @return {boolean}
 */
Wombat.prototype.defProp = function(obj, prop, setFunc, getFunc, enumerable) {
  // if the property is marked as non-configurable in the current
  // browser, skip the override
  var existingDescriptor = Object.getOwnPropertyDescriptor(obj, prop);
  if (existingDescriptor && !existingDescriptor.configurable) {
    return false;
  }

  // if no getter function was supplied, skip the override.
  // See https://github.com/webrecorder/pywb/issues/147 for context
  if (!getFunc) {
    return false;
  }

  var descriptor = {
    configurable: true,
    enumerable: enumerable || false,
    get: getFunc
  };

  if (setFunc) {
    descriptor.set = setFunc;
  }

  try {
    Object.defineProperty(obj, prop, descriptor);
    return true;
  } catch (e) {
    console.warn('Failed to redefine property %s', prop, e.message);
    return false;
  }
};

/**
 * Defines a new getter for the property on the supplied object returning
 * T/F to indicate if the new property was successfully defined
 * @param {Object} obj
 * @param {string} prop
 * @param {function(): *} getFunc
 * @param {?boolean} [enumerable]
 * @return {boolean}
 */
Wombat.prototype.defGetterProp = function(obj, prop, getFunc, enumerable) {
  var existingDescriptor = Object.getOwnPropertyDescriptor(obj, prop);
  if (existingDescriptor && !existingDescriptor.configurable) {
    return false;
  }
  // if no getter function was supplied, skip the override.
  // See https://github.com/webrecorder/pywb/issues/147 for context
  if (!getFunc) return false;

  try {
    Object.defineProperty(obj, prop, {
      configurable: true,
      enumerable: enumerable || false,
      get: getFunc
    });
    return true;
  } catch (e) {
    console.warn('Failed to redefine property %s', prop, e.message);
    return false;
  }
};

/**
 * Returns the original getter function for the supplied object's property
 * @param {Object} obj
 * @param {string} prop
 * @return {function(): *}
 */
Wombat.prototype.getOrigGetter = function(obj, prop) {
  var orig_getter;

  if (obj.__lookupGetter__) {
    orig_getter = obj.__lookupGetter__(prop);
  }

  if (!orig_getter && Object.getOwnPropertyDescriptor) {
    var props = Object.getOwnPropertyDescriptor(obj, prop);
    if (props) {
      orig_getter = props.get;
    }
  }

  return orig_getter;
};

/**
 * Returns the original setter function for the supplied object's property
 * @param {Object} obj
 * @param {string} prop
 * @return {function(): *}
 */
Wombat.prototype.getOrigSetter = function(obj, prop) {
  var orig_setter;

  if (obj.__lookupSetter__) {
    orig_setter = obj.__lookupSetter__(prop);
  }

  if (!orig_setter && Object.getOwnPropertyDescriptor) {
    var props = Object.getOwnPropertyDescriptor(obj, prop);
    if (props) {
      orig_setter = props.set;
    }
  }

  return orig_setter;
};

/**
 * Returns an array containing the names of all the properties
 * that exist on the supplied object
 * @param {Object} obj
 * @return {Array<string>}
 */
Wombat.prototype.getAllOwnProps = function(obj) {
  /** @type {Array<string>} */
  var ownProps = [];

  var props = Object.getOwnPropertyNames(obj);
  var i = 0;
  for (; i < props.length; i++) {
    var prop = props[i];

    try {
      if (obj[prop] && !obj[prop].prototype) {
        ownProps.push(prop);
      }
    } catch (e) {}
  }

  var traverseObj = Object.getPrototypeOf(obj);

  while (traverseObj) {
    props = Object.getOwnPropertyNames(traverseObj);
    for (i = 0; i < props.length; i++) {
      ownProps.push(props[i]);
    }
    traverseObj = Object.getPrototypeOf(traverseObj);
  }

  return ownProps;
};

/**
 * Sends the supplied message to __WB_top_frame
 * @param {*} message
 * @param {boolean} [skipTopCheck]
 */
Wombat.prototype.sendTopMessage = function(message, skipTopCheck) {
  if (!this.$wbwindow.__WB_top_frame) return;
  if (!skipTopCheck && this.$wbwindow != this.$wbwindow.__WB_replay_top) {
    return;
  }
  this.$wbwindow.__WB_top_frame.postMessage(message, this.wb_info.top_host);
};

/**
 * Notifies __WB_top_frame of an history update
 * @param {?string} url
 * @param {?string} title
 */
Wombat.prototype.sendHistoryUpdate = function(url, title) {
  this.sendTopMessage({
    url: url,
    ts: this.wb_info.timestamp,
    request_ts: this.wb_info.request_ts,
    is_live: this.wb_info.is_live,
    title: title,
    wb_type: 'replace-url'
  });
};

/**
 * Updates the real location object with the results of rewriting the supplied URL
 * @param {?string} reqHref
 * @param {string} origHref
 * @param {Location} actualLocation
 */
Wombat.prototype.updateLocation = function(reqHref, origHref, actualLocation) {
  if (!reqHref || reqHref === origHref) return;

  var ext_orig = this.extractOriginalURL(origHref);
  var ext_req = this.extractOriginalURL(reqHref);

  if (!ext_orig || ext_orig === ext_req) return;

  var final_href = this.rewriteUrl(reqHref);

  console.log(actualLocation.href + ' -> ' + final_href);

  actualLocation.href = final_href;
};

/**
 * Updates the real location with a change
 * @param {*} wombatLoc
 * @param {boolean} isTop
 */
Wombat.prototype.checkLocationChange = function(wombatLoc, isTop) {
  var locType = typeof wombatLoc;

  var actual_location = isTop
    ? this.$wbwindow.__WB_replay_top.location
    : this.$wbwindow.location;

  // String has been assigned to location, so assign it
  if (locType === 'string') {
    this.updateLocation(wombatLoc, actual_location.href, actual_location);
  } else if (locType === 'object') {
    this.updateLocation(wombatLoc.href, wombatLoc._orig_href, actual_location);
  }
};

/**
 * Checks for a location change, either this browser context or top and updates
 * accordingly
 * @return {boolean}
 */
Wombat.prototype.checkAllLocations = function() {
  if (this.wb_wombat_updating) {
    return false;
  }

  this.wb_wombat_updating = true;

  this.checkLocationChange(this.$wbwindow.WB_wombat_location, false);

  // Only check top if its a different $wbwindow
  if (
    this.$wbwindow.WB_wombat_location !=
    this.$wbwindow.__WB_replay_top.WB_wombat_location
  ) {
    this.checkLocationChange(
      this.$wbwindow.__WB_replay_top.WB_wombat_location,
      true
    );
  }

  this.wb_wombat_updating = false;
};

/**
 * Returns the Object the Proxy was proxying if it exists otherwise
 * the original object
 * @param {*} source
 * @return {?Object}
 */
Wombat.prototype.proxyToObj = function(source) {
  if (source) {
    try {
      var proxyRealObj = source.__WBProxyRealObj__;
      if (proxyRealObj) return proxyRealObj;
    } catch (e) {}
  }
  return source;
};

/**
 * Returns the Proxy object for the supplied Object if it exists otherwise
 * the original object
 * @param {?Object} obj
 * @return {Proxy|?Object}
 */
Wombat.prototype.objToProxy = function(obj) {
  if (obj) {
    try {
      var maybeWbProxy = obj._WB_wombat_obj_proxy;
      if (maybeWbProxy) return maybeWbProxy;
    } catch (e) {}
  }
  return obj;
};

/**
 * Returns the value of supplied object that is being Proxied
 * @param {*} obj
 * @param {*} prop
 * @param {Array<string>} ownProps
 * @param {Object} fnCache
 * @return {*}
 */
Wombat.prototype.defaultProxyGet = function(obj, prop, ownProps, fnCache) {
  switch (prop) {
    case '__WBProxyRealObj__':
      return obj;
    case 'location':
    case 'WB_wombat_location':
      return obj.WB_wombat_location;
    case '_WB_wombat_obj_proxy':
      return obj._WB_wombat_obj_proxy;
    case '__WB_pmw':
      return obj[prop];
    case 'constructor':
      // allow tests such as self.constructor === Window to work
      // you can't create a new instance of window using its constructor
      if (obj.constructor === Window) return obj.constructor;
      break;
  }
  var retVal = obj[prop];

  var type = typeof retVal;

  if (type === 'function' && ownProps.indexOf(prop) !== -1) {
    // certain sites (e.g. facebook) are applying polyfills to native functions
    // treating the polyfill as a native function [fn.bind(obj)] causes incorrect execution of the polyfill
    // also depending on the site, the site can detect we "tampered" with the polyfill by binding it to obj
    // to avoid these situations, we do not bind the returned fn if we detect they were polyfilled
    switch (prop) {
      case 'requestAnimationFrame':
      case 'cancelAnimationFrame': {
        if (!this.isNativeFunction(retVal)) {
          return retVal;
        }
        break;
      }
    }
    // due to specific use cases involving native functions
    // we must return the
    var cachedFN = fnCache[prop];
    if (!cachedFN || cachedFN.original !== retVal) {
      cachedFN = {
        original: retVal,
        boundFn: retVal.bind(obj)
      };
      fnCache[prop] = cachedFN;
    }
    return cachedFN.boundFn;
  } else if (type === 'object' && retVal && retVal._WB_wombat_obj_proxy) {
    if (retVal instanceof Window) {
      this.initNewWindowWombat(retVal);
    }
    return retVal._WB_wombat_obj_proxy;
  }

  return retVal;
};

/**
 * Set the location properties for either an instance of WombatLocation
 * or an anchor tag
 * @param {HTMLAnchorElement|WombatLocation} loc
 * @param {string} originalURL
 */
Wombat.prototype.setLoc = function(loc, originalURL) {
  var parser = this.makeParser(originalURL, loc.ownerDocument);

  loc._orig_href = originalURL;
  loc._parser = parser;

  var href = parser.href;
  loc._hash = parser.hash;

  loc._href = href;

  loc._host = parser.host;
  loc._hostname = parser.hostname;

  if (parser.origin) {
    loc._origin = parser.origin;
  } else {
    loc._origin =
      parser.protocol +
      '//' +
      parser.hostname +
      (parser.port ? ':' + parser.port : '');
  }

  loc._pathname = parser.pathname;
  loc._port = parser.port;
  // this.protocol = parser.protocol;
  loc._protocol = parser.protocol;
  loc._search = parser.search;

  if (!Object.defineProperty) {
    loc.href = href;
    loc.hash = parser.hash;

    loc.host = loc._host;
    loc.hostname = loc._hostname;
    loc.origin = loc._origin;
    loc.pathname = loc._pathname;
    loc.port = loc._port;
    loc.protocol = loc._protocol;
    loc.search = loc._search;
  }
};

/**
 * Returns a function for retrieving some property on an instance of either
 * WombatLocation or an anchor tag
 * @param {string} prop
 * @param {function(): string} origGetter
 * @return {function(): string}
 */
Wombat.prototype.makeGetLocProp = function(prop, origGetter) {
  var wombat = this;
  return function newGetLocProp() {
    if (this._no_rewrite) return origGetter.call(this, prop);

    var curr_orig_href = origGetter.call(this, 'href');

    if (prop === 'href') {
      return wombat.extractOriginalURL(curr_orig_href);
    }

    if (this._orig_href !== curr_orig_href) {
      wombat.setLoc(this, curr_orig_href);
    }
    return this['_' + prop];
  };
};

/**
 * Returns a function for setting some property on an instance of either
 * WombatLocation or an anchor tag
 * @param {string} prop
 * @param {function (value: *): *} origSetter
 * @param {function(): *} origGetter
 * @return {function (value: *): *}
 */
Wombat.prototype.makeSetLocProp = function(prop, origSetter, origGetter) {
  var wombat = this;
  return function newSetLocProp(value) {
    if (this._no_rewrite) {
      return origSetter.call(this, prop, value);
    }
    if (this['_' + prop] === value) return;

    this['_' + prop] = value;

    if (!this._parser) {
      var href = origGetter.call(this);
      this._parser = wombat.makeParser(href, this.ownerDocument);
    }

    var rel = false;

    // Special case for href="." assignment
    if (prop === 'href' && typeof value === 'string') {
      if (value) {
        if (value[0] === '.') {
          value = wombat.resolveRelUrl(value, this.ownerDocument);
        } else if (
          value[0] === '/' &&
          (value.length <= 1 || value[1] !== '/')
        ) {
          rel = true;
          value = WB_wombat_location.origin + value;
        }
      }
    }

    try {
      this._parser[prop] = value;
    } catch (e) {
      console.log('Error setting ' + prop + ' = ' + value);
    }

    if (prop === 'hash') {
      value = this._parser[prop];
      origSetter.call(this, 'hash', value);
    } else {
      rel = rel || value === this._parser.pathname;
      value = wombat.rewriteUrl(this._parser.href, rel);
      origSetter.call(this, 'href', value);
    }
  };
};

/**
 * Function used for rewriting URL's contained in CSS style definitions
 * @param {Object} match
 * @param {string} n1
 * @param {string} n2
 * @param {string} n3
 * @param {number} offset
 * @param {string} string
 * @return {string}
 */
Wombat.prototype.styleReplacer = function(match, n1, n2, n3, offset, string) {
  return n1 + this.rewriteUrl(n2) + n3;
};

/**
 * Simple helper function for ensuring that the server side rewriting
 * injected functions are present in the supplied window.
 *
 * They could be absent due to how certain pages use iframes
 * @param {?Window} win
 */
Wombat.prototype.ensureServerSideInjectsExistOnWindow = function(win) {
  if (!win) return;
  if (typeof win._____WB$wombat$check$this$function_____ !== 'function') {
    win._____WB$wombat$check$this$function_____ = function(thisObj) {
      if (thisObj && thisObj._WB_wombat_obj_proxy)
        return thisObj._WB_wombat_obj_proxy;
      return thisObj;
    };
  }
  if (typeof win._____WB$wombat$assign$function_____ !== 'function') {
    win._____WB$wombat$assign$function_____ = function(name) {
      return (
        (self._wb_wombat &&
          self._wb_wombat.local_init &&
          self._wb_wombat.local_init(name)) ||
        self[name]
      );
    };
  }
};

/**
 * Due to the fact that we override specific DOM constructors, e.g. Worker,
 * the normal TypeErrors are not thrown if the pre-conditions for those
 * constructors are not met.
 *
 * Code that performs polyfills or browser feature detection based
 * on those TypeErrors will not work as expected if we do not perform
 * those checks ourselves (Note we use Chrome's error messages)
 *
 * This function checks for those pre-conditions and throws an TypeError
 * with the appropriate message if a pre-condition is not met
 *  - `this` instanceof Window is false (requires new)
 *  - supplied required arguments
 *
 * @param {Object} thisObj
 * @param {string} what
 * @param {Object} [args]
 * @param {number} [numRequiredArgs]
 */
Wombat.prototype.domConstructorErrorChecker = function(
  thisObj,
  what,
  args,
  numRequiredArgs
) {
  var needArgs = typeof numRequiredArgs === 'number' ? numRequiredArgs : 1;
  var erorMsg;
  if (thisObj instanceof Window) {
    erorMsg =
      "Failed to construct '" +
      what +
      "': Please use the 'new' operator, this DOM object constructor cannot be called as a function.";
  } else if (args && args.length < needArgs) {
    erorMsg =
      "Failed to construct '" +
      what +
      "': " +
      needArgs +
      ' argument required, but only 0 present.';
  }
  if (erorMsg) {
    throw new TypeError(erorMsg);
  }
};

/**
 * Rewrites the arguments supplied to an function of the Node interface
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {Node} newNode
 * @param {Node} [oldNode]
 */
Wombat.prototype.rewriteNodeFuncArgs = function(
  fnThis,
  originalFn,
  newNode,
  oldNode
) {
  if (newNode) {
    switch (newNode.nodeType) {
      case Node.ELEMENT_NODE:
        this.rewriteElemComplete(newNode);
        break;
      case Node.TEXT_NODE:
        // newNode is the new child of fnThis (the parent node)
        if (
          fnThis.tagName === 'STYLE' ||
          (newNode.parentNode && newNode.parentNode.tagName === 'STYLE')
        ) {
          newNode.textContent = this.rewriteStyle(newNode.textContent);
        }
        break;
      case Node.DOCUMENT_FRAGMENT_NODE:
        this.recurseRewriteElem(newNode);
        break;
    }
  }
  var created = originalFn.call(fnThis, newNode, oldNode);
  if (created && created.tagName === 'IFRAME') {
    this.initIframeWombat(created);
  }
  return created;
};

/**
 * Mini url rewriter specifically for rewriting web sockets
 * @param {?string} originalURL
 * @return {string}
 */
Wombat.prototype.rewriteWSURL = function(originalURL) {
  // If undefined, just return it
  if (!originalURL) return originalURL;

  var urltype_ = typeof originalURL;
  var url = originalURL;

  // If object, use toString
  if (urltype_ === 'object') {
    url = originalURL.toString();
  } else if (urltype_ !== 'string') {
    return originalURL;
  }

  // empty string check
  if (!url) return url;

  var wsScheme = 'ws://';
  var wssScheme = 'wss://';

  // proxy mode: If no wb_replay_prefix, only rewrite scheme
  // proxy mode: If no wb_replay_prefix, only rewrite scheme
  if (this.wb_is_proxy) {
    if (
      this.wb_orig_scheme === this.HTTP_PREFIX &&
      this.startsWith(url, wssScheme)
    ) {
      return wsScheme + url.substr(wssScheme.length);
    } else if (
      this.wb_orig_scheme === this.HTTPS_PREFIX &&
      this.startsWith(url, wsScheme)
    ) {
      return wssScheme + url.substr(wsScheme.length);
    } else {
      return url;
    }
  }

  var wbSecure = this.wb_abs_prefix.indexOf(this.HTTPS_PREFIX) === 0;
  var wbPrefix = this.wb_abs_prefix.replace(
    wbSecure ? this.HTTPS_PREFIX : this.HTTP_PREFIX,
    wbSecure ? wssScheme : wsScheme
  );
  wbPrefix += this.wb_info.wombat_ts + 'ws_';
  if (url[url.length - 1] !== '/') {
    wbPrefix += '/';
  }
  return wbPrefix + url.replace('WB_wombat_', '');
};

/**
 * Rewrites the supplied URL returning the rewritten URL
 * @param {?string} originalURL
 * @param {?boolean} [useRel]
 * @param {?string} [mod]
 * @param {?Document} [doc]
 * @return {?string}
 * @private
 */
Wombat.prototype.rewriteUrl_ = function(originalURL, useRel, mod, doc) {
  // If undefined, just return it
  if (!originalURL) return originalURL;

  var urltype_ = typeof originalURL;
  var url;

  // If object, use toString
  if (urltype_ === 'object') {
    url = originalURL.toString();
  } else if (urltype_ !== 'string') {
    return originalURL;
  } else {
    url = originalURL;
  }

  // empty string check
  if (!url) return url;

  // proxy mode: If no wb_replay_prefix, only rewrite scheme
  if (this.wb_is_proxy) {
    if (
      this.wb_orig_scheme === this.HTTP_PREFIX &&
      this.startsWith(url, this.HTTPS_PREFIX)
    ) {
      return this.HTTP_PREFIX + url.substr(this.HTTPS_PREFIX.length);
    } else if (
      this.wb_orig_scheme === this.HTTPS_PREFIX &&
      this.startsWith(url, this.HTTP_PREFIX)
    ) {
      return this.HTTPS_PREFIX + url.substr(this.HTTP_PREFIX.length);
    } else {
      return url;
    }
  }

  // just in case _wombat reference made it into url!
  url = url.replace('WB_wombat_', '');

  // ignore anchors, about, data
  if (this.startsWithOneOf(url.toLowerCase(), this.IGNORE_PREFIXES)) {
    return url;
  }

  // OPTS: additional ignore prefixes
  if (
    this.wb_opts.no_rewrite_prefixes &&
    this.startsWithOneOf(url, this.wb_opts.no_rewrite_prefixes)
  ) {
    return url;
  }

  // If starts with prefix, no rewriting needed
  // Only check replay prefix (no date) as date may be different for each
  // capture

  // if scheme relative, prepend current scheme
  var check_url;

  if (url.indexOf('//') === 0) {
    check_url = window.location.protocol + url;
  } else {
    check_url = url;
  }

  var originalLoc = this.$wbwindow.location;
  if (
    this.startsWith(check_url, this.wb_replay_prefix) ||
    this.startsWith(check_url, originalLoc.origin + this.wb_replay_prefix)
  ) {
    return url;
  }

  // A special case where the port somehow gets dropped
  // Check for this and add it back in, eg http://localhost/path/ -> http://localhost:8080/path/
  if (
    originalLoc.host !== originalLoc.hostname &&
    this.startsWith(
      url,
      originalLoc.protocol + '//' + originalLoc.hostname + '/'
    )
  ) {
    return url.replace(
      '/' + originalLoc.hostname + '/',
      '/' + originalLoc.host + '/'
    );
  }

  // If server relative url, add prefix and original host
  if (url.charAt(0) === '/' && !this.startsWith(url, this.REL_PREFIX)) {
    // Already a relative url, don't make any changes!
    if (
      this.wb_capture_date_part &&
      url.indexOf(this.wb_capture_date_part) >= 0
    ) {
      return url;
    }

    // relative collection
    if (url.indexOf(this.wb_rel_prefix) === 0 && url.indexOf('http') > 1) {
      var scheme_sep = url.indexOf(':/');
      if (scheme_sep > 0 && url[scheme_sep + 2] !== '/') {
        return (
          url.substring(0, scheme_sep + 2) + '/' + url.substring(scheme_sep + 2)
        );
      }
      return url;
    }

    return this.getFinalUrl(true, mod, this.wb_orig_origin + url);
  }

  // Use a parser
  if (url.charAt(0) === '.') {
    url = this.resolveRelUrl(url, doc);
  }

  // If full url starting with http://, https:// or //
  // add rewrite prefix, we convert to lower case for this check
  // due to the fact that the URL's scheme could be HTTP(S) LUL
  var prefix = this.startsWithOneOf(url.toLowerCase(), this.VALID_PREFIXES);

  if (prefix) {
    var orig_host = this.$wbwindow.__WB_replay_top.location.host;
    var orig_protocol = this.$wbwindow.__WB_replay_top.location.protocol;

    var prefix_host = prefix + orig_host + '/';

    // if already rewritten url, must still check scheme
    if (this.startsWith(url, prefix_host)) {
      if (this.startsWith(url, this.wb_replay_prefix)) {
        return url;
      }

      var curr_scheme = orig_protocol + '//';
      var path = url.substring(prefix_host.length);
      var rebuild = false;

      if (path.indexOf(this.wb_rel_prefix) < 0 && url.indexOf('/static/') < 0) {
        path = this.getFinalUrl(
          true,
          mod,
          WB_wombat_location.origin + '/' + path
        );
        rebuild = true;
      }

      // replace scheme to ensure using the correct server scheme
      // if (starts_with(url, wb_orig_scheme) && (wb_orig_scheme != curr_scheme)) {
      if (prefix !== curr_scheme && prefix !== this.REL_PREFIX) {
        rebuild = true;
      }

      if (rebuild) {
        if (!useRel) {
          url = curr_scheme + orig_host;
        } else {
          url = '';
        }
        if (path && path[0] !== '/') {
          url += '/';
        }
        url += path;
      }

      return url;
    }
    return this.getFinalUrl(useRel, mod, url);
  }
  // Check for common bad prefixes and remove them
  prefix = this.startsWithOneOf(url, this.BAD_PREFIXES);

  if (prefix) {
    return this.getFinalUrl(useRel, mod, this.extractOriginalURL(url));
  }

  // May or may not be a hostname, call function to determine
  // If it is, add the prefix and make sure port is removed
  if (this.isHostUrl(url) && !this.startsWith(url, originalLoc.host + '/')) {
    return this.getFinalUrl(useRel, mod, this.wb_orig_scheme + url);
  }

  return url;
};

/**
 * Rewrites the supplied URL returning the rewritten URL.
 * If wombat is in debug mode the rewrite is logged to the console
 * @param {*} url
 * @param {?boolean} [useRel]
 * @param {?string} [mod]
 * @param {?Document} [doc]
 * @return {?string}
 */
Wombat.prototype.rewriteUrl = function(url, useRel, mod, doc) {
  var rewritten = this.rewriteUrl_(url, useRel, mod, doc);
  if (this.debug_rw) {
    if (url !== rewritten) {
      console.log('REWRITE: ' + url + ' -> ' + rewritten);
    } else {
      console.log('NOT REWRITTEN ' + url);
    }
  }
  return rewritten;
};

/**
 * Rewrites the value of the supplied elements attribute returning its rewritten value.
 * Used by {@link newAttrObjGetSet} and {@link rewriteAttr}
 *
 * @param {Element} elem
 * @param {string} name
 * @param {*} value
 * @param {boolean} [absUrlOnly]
 * @return {*}
 */
Wombat.prototype.performAttributeRewrite = function(
  elem,
  name,
  value,
  absUrlOnly
) {
  switch (name) {
    // inner and outer HTML are for the overrides applied by newAttrObjGetSet
    case 'innerHTML':
    case 'outerHTML':
      return this.rewriteHtml(value);
    case 'filter': // for svg filter attribute which is url(...)
      return this.rewriteInlineStyle(value);
    case 'style':
      return this.rewriteStyle(value);
    case 'srcset':
      return this.rewriteSrcset(value, elem);
  }
  // Only rewrite if absolute url
  if (absUrlOnly && !this.startsWithOneOf(value, this.VALID_PREFIXES)) {
    return value;
  }
  var mod = this.rwModForElement(elem, name);
  if (
    this.wbUseAFWorker &&
    this.WBAutoFetchWorker &&
    this.isSavedDataSrcSrcset(elem)
  ) {
    this.WBAutoFetchWorker.preserveDataSrcset(elem);
  }
  return this.rewriteUrl(value, false, mod, elem.ownerDocument);
};

/**
 * Rewrites an element attribute's value
 * @param {Element} elem
 * @param {string} name
 * @param {boolean} [absUrlOnly]
 * @return {boolean}
 */
Wombat.prototype.rewriteAttr = function(elem, name, absUrlOnly) {
  var changed = false;
  if (!elem || !elem.getAttribute || elem._no_rewrite || elem['_' + name]) {
    return changed;
  }

  var value = this.wb_getAttribute.call(elem, name);

  if (!value || this.startsWith(value, 'javascript:')) return changed;

  var new_value = this.performAttributeRewrite(elem, name, value, absUrlOnly);

  if (new_value !== value) {
    this.removeWBOSRC(elem);
    this.wb_setAttribute.call(elem, name, new_value);
    changed = true;
  }

  return changed;
};

/**
 * {@link rewriteStyle} wrapped in a try catch
 * @param {string|Object} style
 * @return {string|Object|null}
 */
Wombat.prototype.noExceptRewriteStyle = function(style) {
  try {
    return this.rewriteStyle(style);
  } catch (e) {
    return style;
  }
};

/**
 * Rewrites the supplied CSS style definitions
 * @param {string|Object} style
 * @return {string|Object|null}
 */
Wombat.prototype.rewriteStyle = function(style) {
  if (!style) return style;

  var value = style;
  if (typeof style === 'object') {
    value = style.toString();
  }

  if (typeof value === 'string') {
    return value
      .replace(this.STYLE_REGEX, this.styleReplacer)
      .replace(this.IMPORT_REGEX, this.styleReplacer)
      .replace(this.no_wombatRe, '');
  }

  return value;
};

/**
 * Rewrites the supplied srcset string returning the rewritten results.
 * If the element is one the srcset values are auto-fetched they are sent
 * to the backing auto-fetch worker
 * @param {string} value
 * @param {Element} elem
 * @return {string}
 */
Wombat.prototype.rewriteSrcset = function(value, elem) {
  if (!value) return '';

  var split = value.split(this.srcsetRe);
  var values = [];
  var mod = this.rwModForElement(elem, 'srcset');
  for (var i = 0; i < split.length; i++) {
    // Filter removes non-truthy values like null, undefined, and ""
    if (split[i]) {
      var trimmed = split[i].trim();
      if (trimmed) values.push(this.rewriteUrl(trimmed, true, mod));
    }
  }

  if (
    this.wbUseAFWorker &&
    this.WBAutoFetchWorker &&
    this.isSavedSrcSrcset(elem)
  ) {
    // send post split values to preservation worker
    this.WBAutoFetchWorker.preserveSrcset(
      values,
      this.WBAutoFetchWorker.rwMod(elem)
    );
  }

  return values.join(', ');
};

/**
 * Rewrites the URL supplied to the setter of an (i)frame's src attribute
 * @param {Element} elem
 * @param {string} attrName
 * @return {boolean}
 */
Wombat.prototype.rewriteFrameSrc = function(elem, attrName) {
  var value = this.wb_getAttribute.call(elem, attrName);
  var new_value;

  // special case for rewriting javascript: urls that contain WB_wombat_
  // must insert _wombat init first!
  if (this.startsWith(value, 'javascript:')) {
    if (value.indexOf('WB_wombat_') >= 0) {
      var JS = 'javascript:';
      new_value =
        JS +
        'window.parent._wb_wombat.initNewWindowWombat(window);' +
        value.substr(JS.length);
    }
  }

  if (!new_value) {
    new_value = this.rewriteUrl(
      value,
      false,
      this.rwModForElement(elem, attrName)
    );
  }

  if (new_value !== value) {
    this.wb_setAttribute.call(elem, attrName, new_value);
    return true;
  }

  return false;
};

/**
 * Rewrites either the URL contained in the src attribute or the text contents
 * of the supplied script element. Returns T/F indicating if a rewrite occurred
 * @param elem
 * @return {boolean}
 */
Wombat.prototype.rewriteScript = function(elem) {
  if (elem.hasAttribute('src') || !elem.textContent || !this.$wbwindow.Proxy) {
    return this.rewriteAttr(elem, 'src');
  }
  if (this.skipWrapScriptBasedOnType(elem.type)) return false;
  var text = elem.textContent.trim();
  if (this.skipWrapScriptTextBasedOnText(text)) return false;
  elem.textContent = this.wrapScriptTextJsProxy(text);
  return true;
};

/**
 * Rewrites the supplied SVG element returning T/F indicating if a rewrite occurred
 * @param {SVGElement} elem
 * @return {boolean}
 */
Wombat.prototype.rewriteSVGElem = function(elem) {
  var changed = this.rewriteAttr(elem, 'filter');
  changed = this.rewriteAttr(elem, 'style') || changed;
  // xlink:href is deprecated since SVG 2 in favor of href
  // https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/xlink:href
  changed = this.rewriteAttr(elem, 'xlink:href') || changed;
  changed = this.rewriteAttr(elem, 'href') || changed;
  changed = this.rewriteAttr(elem, 'src') || changed;
  return changed;
};

/**
 * Rewrites the supplied element returning T/F indicating if a rewrite occured
 * @param {Element|Node} elem - The element to be rewritten
 * @return {boolean}
 */
Wombat.prototype.rewriteElem = function(elem) {
  var changed = false;
  if (!elem) return changed;
  if (elem instanceof SVGElement) {
    changed = this.rewriteSVGElem(elem);
  } else {
    switch (elem.tagName) {
      case 'META':
        var maybeCSP = this.wb_getAttribute.call(elem, 'http-equiv');
        if (maybeCSP && maybeCSP.toLowerCase() === 'content-security-policy') {
          this.wb_setAttribute.call(elem, 'http-equiv', '_' + maybeCSP);
          changed = true;
        }
        break;
      case 'STYLE':
        var new_content = this.rewriteStyle(elem.textContent);
        if (elem.textContent !== new_content) {
          elem.textContent = new_content;
          changed = true;
          if (
            this.wbUseAFWorker &&
            this.WBAutoFetchWorker &&
            elem.sheet != null
          ) {
            // we have a stylesheet so lets be nice to UI thread
            // and defer extraction
            this.WBAutoFetchWorker.deferredSheetExtraction(elem.sheet);
          }
        }
        break;
      case 'LINK':
        changed = this.rewriteAttr(elem, 'href');
        if (this.wbUseAFWorker && elem.rel === 'stylesheet') {
          // we can only check link[rel='stylesheet'] when it loads
          this._addEventListener(
            elem,
            'load',
            this.utilFns.wbSheetMediaQChecker
          );
        }
        break;
      case 'IMG':
        changed = this.rewriteAttr(elem, 'src');
        changed = this.rewriteAttr(elem, 'srcset') || changed;
        changed = this.rewriteAttr(elem, 'style') || changed;
        if (
          this.wbUseAFWorker &&
          this.WBAutoFetchWorker &&
          elem.dataset.srcset
        ) {
          this.WBAutoFetchWorker.preserveDataSrcset(elem);
        }
        break;
      case 'OBJECT':
        changed = this.rewriteAttr(elem, 'data', true);
        changed = this.rewriteAttr(elem, 'style') || changed;
        break;
      case 'FORM':
        changed = this.rewriteAttr(elem, 'poster');
        changed = this.rewriteAttr(elem, 'action') || changed;
        changed = this.rewriteAttr(elem, 'style') || changed;
        break;
      case 'IFRAME':
      case 'FRAME':
        changed = this.rewriteFrameSrc(elem, 'src');
        changed = this.rewriteAttr(elem, 'style') || changed;
        break;
      case 'SCRIPT':
        changed = this.rewriteScript(elem);
        break;
      default: {
        changed = this.rewriteAttr(elem, 'src');
        changed = this.rewriteAttr(elem, 'srcset') || changed;
        changed = this.rewriteAttr(elem, 'href') || changed;
        changed = this.rewriteAttr(elem, 'style') || changed;
        changed = this.rewriteAttr(elem, 'poster') || changed;
        break;
      }
    }
  }

  if (elem.hasAttribute && elem.removeAttribute) {
    if (elem.hasAttribute('crossorigin')) {
      elem.removeAttribute('crossorigin');
      changed = true;
    }

    if (elem.hasAttribute('integrity')) {
      elem.removeAttribute('integrity');
      changed = true;
    }
  }
  return changed;
};

/**
 * Rewrites all the children and there descendants of the supplied Node
 * returning T/F if a rewrite occurred
 * @param {Node} curr
 * @return {boolean}
 */
Wombat.prototype.recurseRewriteElem = function(curr) {
  if (!this.nodeHasChildren(curr)) return false;
  var changed = false;
  var rewriteQ = [curr.children || curr.childNodes];

  while (rewriteQ.length > 0) {
    var children = rewriteQ.shift();
    for (var i = 0; i < children.length; i++) {
      var child = children[i];
      if (child.nodeType === Node.ELEMENT_NODE) {
        changed = this.rewriteElem(child) || changed;
        if (this.nodeHasChildren(child)) {
          rewriteQ.push(child.children || child.childNodes);
        }
      }
    }
  }

  return changed;
};

/**
 * Rewrites the supplied element and all its children if any.
 * See {@link rewriteElem} and {@link recurseRewriteElem} for more details
 * @param {Node} elem
 * @return {boolean}
 */
Wombat.prototype.rewriteElemComplete = function(elem) {
  if (!elem) return false;
  var changed = this.rewriteElem(elem);
  var changedRecursively = this.recurseRewriteElem(elem);
  return changed || changedRecursively;
};

/**
 * Rewrites any elements found in the supplied arguments object returning
 * a new array containing the original contents of the supplied arguments
 * object after rewriting.
 * @param {Object} originalArguments
 * @return {Array<*>}
 */
Wombat.prototype.rewriteElementsInArguments = function(originalArguments) {
  var argArr = new Array(originalArguments.length);
  for (var i = 0; i < originalArguments.length; i++) {
    var argElem = originalArguments[i];
    if (argElem instanceof Node) {
      this.rewriteElemComplete(argElem);
      argArr[i] = argElem;
    } else if (typeof argElem === 'string') {
      argArr[i] = this.rewriteHtml(argElem);
    } else {
      argArr[i] = argElem;
    }
  }
  return argArr;
};

/**
 * Rewrites the supplied string containing HTML, if the supplied string
 * is full HTML (starts with <HTML, <DOCUMENT...) the string is rewritten
 * using {@link Wombat#rewriteHtmlFull}
 * @param {string} string
 * @param {boolean} [checkEndTag]
 * @return {?string}
 */
Wombat.prototype.rewriteHtml = function(string, checkEndTag) {
  if (!string) {
    return string;
  }
  var rwString = string;
  if (typeof string !== 'string') {
    rwString = string.toString();
  }

  if (this.write_buff) {
    rwString = this.write_buff + rwString;
    this.write_buff = '';
  }

  if (rwString.indexOf('<script') <= 0) {
    // string = string.replace(/WB_wombat_/g, "");
    rwString = rwString.replace(/((id|class)=".*)WB_wombat_([^"]+)/, '$1$3');
  }

  if (
    !this.$wbwindow.HTMLTemplateElement ||
    this.FullHTMLRegex.test(rwString)
  ) {
    return this.rewriteHtmlFull(rwString, checkEndTag);
  }

  var inner_doc = new DOMParser().parseFromString(
    '<template>' + rwString + '</template>',
    'text/html'
  );

  if (
    !inner_doc ||
    !this.nodeHasChildren(inner_doc.head) ||
    !inner_doc.head.children[0].content
  ) {
    return rwString;
  }

  var template = inner_doc.head.children[0];
  template._no_rewrite = true;
  if (this.recurseRewriteElem(template.content)) {
    var new_html = template.innerHTML;
    if (checkEndTag) {
      var first_elem =
        template.content.children && template.content.children[0];
      if (first_elem) {
        var end_tag = '</' + first_elem.tagName.toLowerCase() + '>';
        if (
          this.endsWith(new_html, end_tag) &&
          !this.endsWith(rwString, end_tag)
        ) {
          new_html = new_html.substring(0, new_html.length - end_tag.length);
        }
      } else if (rwString[0] !== '<' || rwString[rwString.length - 1] !== '>') {
        this.write_buff += rwString;
        return undefined;
      }
    }
    return new_html;
  }

  return rwString;
};

/**
 * Rewrites the supplied string containing full HTML
 * @param {string} string
 * @param {boolean} [checkEndTag]
 * @return {?string}
 */
Wombat.prototype.rewriteHtmlFull = function(string, checkEndTag) {
  var inner_doc = new DOMParser().parseFromString(string, 'text/html');
  if (!inner_doc) return string;

  var changed = false;

  for (var i = 0; i < inner_doc.all.length; i++) {
    changed = this.rewriteElem(inner_doc.all[i]) || changed;
  }

  if (changed) {
    var new_html;
    // if original had <html> tag, add full document HTML
    if (string && string.indexOf('<html') >= 0) {
      inner_doc.documentElement._no_rewrite = true;
      new_html =
        this.reconstructDocType(inner_doc.doctype) +
        inner_doc.documentElement.outerHTML;
    } else {
      //
      inner_doc.head._no_rewrite = true;
      inner_doc.body._no_rewrite = true;
      // hasChildNodes includes text nodes
      var headHasKids = this.nodeHasChildren(inner_doc.head);
      var bodyHasKids = this.nodeHasChildren(inner_doc.body);
      new_html =
        (headHasKids ? inner_doc.head.outerHTML : '') +
        (bodyHasKids ? inner_doc.body.outerHTML : '');
      if (checkEndTag) {
        if (inner_doc.all.length > 3) {
          var end_tag = '</' + inner_doc.all[3].tagName.toLowerCase() + '>';
          if (
            this.endsWith(new_html, end_tag) &&
            !this.endsWith(string, end_tag)
          ) {
            new_html = new_html.substring(0, new_html.length - end_tag.length);
          }
        } else if (string[0] !== '<' || string[string.length - 1] !== '>') {
          this.write_buff += string;
          return;
        }
      }
      new_html = this.reconstructDocType(inner_doc.doctype) + new_html;
    }

    return new_html;
  }

  return string;
};

/**
 * Rewrites a CSS style string found in the style property of an element or
 * FontFace
 * @param {string} orig
 * @return {string}
 */
Wombat.prototype.rewriteInlineStyle = function(orig) {
  var decoded;

  try {
    decoded = decodeURIComponent(orig);
  } catch (e) {
    decoded = orig;
  }

  if (decoded !== orig) {
    var parts = this.rewriteStyle(decoded).split(',', 2);
    return parts[0] + ',' + encodeURIComponent(parts[1]);
  }

  return this.rewriteStyle(orig);
};

/**
 * Rewrites the supplied cookie
 * @param {string} cookie
 * @return {string}
 */
Wombat.prototype.rewriteCookie = function(cookie) {
  var wombat = this;
  var rwCookie = cookie
    .replace(this.wb_abs_prefix, '')
    .replace(this.wb_rel_prefix, '');
  rwCookie = rwCookie
    .replace(this.cookie_domain_regex, function(m, m1) {
      // rewrite domain
      var message = {
        domain: m1,
        cookie: rwCookie,
        wb_type: 'cookie'
      };

      // norify of cookie setting to allow server-side tracking
      wombat.sendTopMessage(message, true);

      // if no subdomain, eg. "localhost", just remove domain altogether
      if (
        wombat.$wbwindow.location.hostname.indexOf('.') >= 0 &&
        !wombat.IP_RX.test(wombat.$wbwindow.location.hostname)
      ) {
        return 'Domain=.' + wombat.$wbwindow.location.hostname;
      }
      return '';
    })
    .replace(this.cookie_path_regex, function(m, m1) {
      // rewrite path
      var rewritten = wombat.rewriteUrl(m1);

      if (rewritten.indexOf(wombat.wb_curr_host) === 0) {
        rewritten = rewritten.substring(wombat.wb_curr_host.length);
      }

      return 'Path=' + rewritten;
    });

  // rewrite secure, if needed
  if (wombat.$wbwindow.location.protocol !== 'https:') {
    rwCookie = rwCookie.replace('secure', '');
  }

  return rwCookie.replace(',|', ',');
};

/**
 * Rewrites the supplied web worker URL
 * @param {string} workerUrl
 * @return {string}
 */
Wombat.prototype.rewriteWorker = function(workerUrl) {
  if (!workerUrl) return workerUrl;
  var isBlob = workerUrl.indexOf('blob:') === 0;
  var isJS = workerUrl.indexOf('javascript:') === 0;
  if (!isBlob && !isJS) {
    if (
      !this.startsWithOneOf(workerUrl, this.VALID_PREFIXES) &&
      !this.startsWith(workerUrl, '/') &&
      !this.startsWithOneOf(workerUrl, this.BAD_PREFIXES)
    ) {
      // super relative url assets/js/xyz.js
      var rurl = this.resolveRelUrl(workerUrl, this.$wbwindow.document);
      return this.rewriteUrl(rurl, false, 'wkr_', this.$wbwindow.document);
    }
    return this.rewriteUrl(workerUrl, false, 'wkr_', this.$wbwindow.document);
  }

  var workerCode = isJS ? workerUrl.replace('javascript:', '') : null;
  if (isBlob) {
    // fetching only skipped if it was JS url
    var x = new XMLHttpRequest();
    // use sync ajax request to get the contents, remove postMessage() rewriting
    this.utilFns.XHRopen.call(x, 'GET', workerUrl, false);
    x.send();
    workerCode = x.responseText
      .replace(this.workerBlobRe, '')
      // resolving blobs hit our sever side rewriting so we gotta
      // ensure we good
      .replace(this.rmCheckThisInjectRe, 'this');
  }

  if (this.wb_info.static_prefix || this.wb_info.ww_rw_script) {
    var originalURL = this.$wbwindow.document.baseURI;
    // if we are here we can must return blob so set makeBlob to true
    var ww_rw =
      this.wb_info.ww_rw_script ||
      this.wb_info.static_prefix + 'wombatWorkers.js';
    var rw =
      "(function() { self.importScripts('" +
      ww_rw +
      "'); new WBWombat({'prefix': '" +
      this.wb_abs_prefix +
      "', 'prefixMod': '" +
      this.wb_abs_prefix +
      "wkrf_/', 'originalURL': '" +
      originalURL +
      "'}); })();";

    workerCode = rw + workerCode;
  }
  var blob = new Blob([workerCode], { type: 'application/javascript' });
  return URL.createObjectURL(blob);
};

/**
 * Rewrite the arguments supplied to a function of the Text interface in order
 * to ensure CSS is rewritten when a text node is the child of the style tag
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {Object} argsObj
 */
Wombat.prototype.rewriteTextNodeFn = function(fnThis, originalFn, argsObj) {
  var deproxiedThis = this.proxyToObj(fnThis);
  var args;
  if (
    argsObj.length > 0 &&
    deproxiedThis.parentElement &&
    deproxiedThis.parentElement.tagName === 'STYLE'
  ) {
    // appendData(DOMString data); dataIndex = 0
    // insertData(unsigned long offset, DOMString data); dataIndex = 1
    // replaceData(unsigned long offset, unsigned long count, DOMString data); dataIndex = 2
    args = new Array(argsObj.length);
    var dataIndex = argsObj.length - 1;
    if (dataIndex === 2) {
      args[0] = argsObj[0];
      args[1] = argsObj[1];
    } else if (dataIndex === 1) {
      args[0] = argsObj[0];
    }
    args[dataIndex] = this.rewriteStyle(argsObj[dataIndex]);
  } else {
    args = argsObj;
  }
  if (originalFn.__WB_orig_apply) {
    return originalFn.__WB_orig_apply(deproxiedThis, args);
  }
  return originalFn.apply(deproxiedThis, args);
};

/**
 * Rewrite the arguments supplied to document.[write, writeln] in order
 * to ensure that the string of HTML is rewritten
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {Object} argsObj
 */
Wombat.prototype.rewriteDocWriteWriteln = function(
  fnThis,
  originalFn,
  argsObj
) {
  var thisObj = this.proxyToObj(fnThis);
  var argLen = argsObj.length;
  var string;
  if (argLen === 0) {
    return originalFn.call(thisObj);
  }
  if (argLen === 1) {
    string = argsObj[0];
  } else {
    // use Array.join rather than Array.apply because join works with array like objects
    string = Array.prototype.join.call(argsObj, '');
  }
  var new_buff = this.rewriteHtml(string, true);
  var res = originalFn.call(thisObj, new_buff);
  this.initNewWindowWombat(thisObj.defaultView);
  return res;
};

/**
 * Rewrite the arguments supplied to a function of the ChildNode interface
 * in order to ensure that elements are rewritten
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {Object} argsObj
 */
Wombat.prototype.rewriteChildNodeFn = function(fnThis, originalFn, argsObj) {
  var thisObj = this.proxyToObj(fnThis);
  if (argsObj.length === 0) return originalFn.call(thisObj);
  var newArgs = this.rewriteElementsInArguments(argsObj);
  if (originalFn.__WB_orig_apply) {
    return originalFn.__WB_orig_apply(thisObj, newArgs);
  }
  return originalFn.apply(thisObj, newArgs);
};

/**
 * Rewrites the arguments supplied to Element.[insertAdjacentElement, insertAdjacentHTML].
 * If rwHTML is true the rewrite performed is done by {@link rewriteHtml} other wise
 * {@link rewriteElemComplete}
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {number} position
 * @param {string|Node} textOrElem
 * @param {boolean} rwHTML
 * @return {*}
 */
Wombat.prototype.rewriteInsertAdjHTMLOrElemArgs = function(
  fnThis,
  originalFn,
  position,
  textOrElem,
  rwHTML
) {
  var fnThisObj = this.proxyToObj(fnThis);
  if (fnThisObj._no_rewrite) {
    return originalFn.call(fnThisObj, position, textOrElem);
  }
  if (rwHTML) {
    return originalFn.call(fnThisObj, position, this.rewriteHtml(textOrElem));
  }
  this.rewriteElemComplete(textOrElem);
  return originalFn.call(fnThisObj, position, textOrElem);
};

/**
 * Rewrites the arguments of either setTimeout or setInterval because
 * [setTimeout|setInterval]('document.location.href = "xyz.com"', time)
 * is legal and used
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {Object} argsObj
 * @return {*}
 */
Wombat.prototype.rewriteSetTimeoutInterval = function(
  fnThis,
  originalFn,
  argsObj
) {
  // strings are primitives with a prototype or __proto__ of String depending on the browser
  var rw = this.isString(argsObj[0]);
  // do not mess with the arguments object unless you want instant de-optimization
  var args = rw ? new Array(argsObj.length) : argsObj;
  if (rw) {
    if (this.$wbwindow.Proxy) {
      args[0] = this.wrapScriptTextJsProxy(argsObj[0]);
    } else {
      args[0] = argsObj[0].replace(/\blocation\b/g, 'WB_wombat_$&');
    }
    for (var i = 1; i < argsObj.length; ++i) {
      args[i] = this.proxyToObj(argsObj[i]);
    }
  }
  // setTimeout|setInterval does not require its this arg to be window so just in case
  // someone got funky with it
  var thisObj = this.proxyToObj(fnThis);
  if (originalFn.__WB_orig_apply) {
    return originalFn.__WB_orig_apply(thisObj, args);
  }
  return originalFn.apply(thisObj, args);
};

/**
 * Rewrites the value of used in to set SomeElement.[innerHTML|outerHTML]
 * iframe.srcdoc, or style.textContent handling edge cases e.g. script tags.
 *
 * If the element is a style tag and it has a sheet after the new value is set
 * it, the sheet, is checked for media rules.
 *
 * @param {Object} thisObj
 * @param {Function} oSetter
 * @param {?string} newValue
 */
Wombat.prototype.rewriteHTMLAssign = function(thisObj, oSetter, newValue) {
  var res = newValue;
  var tagName = thisObj.tagName;
  if (!thisObj._no_rewrite) {
    if (tagName === 'STYLE') {
      res = this.rewriteStyle(newValue);
    } else {
      res = this.rewriteHtml(newValue);
      if (tagName === 'SCRIPT' && res === newValue) {
        // script tags are used to hold HTML for later use
        // so we let the rewriteHtml function go first
        // however in this case inner or outer html was
        // used to populate a script tag with some JS
        if (
          !this.skipWrapScriptBasedOnType(thisObj.type) &&
          !this.skipWrapScriptTextBasedOnText(newValue)
        ) {
          res = this.wrapScriptTextJsProxy(res);
        }
      }
    }
  }
  oSetter.call(thisObj, res);
  if (
    this.wbUseAFWorker &&
    this.WBAutoFetchWorker &&
    tagName === 'STYLE' &&
    thisObj.sheet != null
  ) {
    // got to preserve all the things
    this.WBAutoFetchWorker.deferredSheetExtraction(thisObj.sheet);
  }
};

/**
 * Rewrites the value to be supplied to eval or our injected wrapper
 * @param {Function} rawEvalOrWrapper
 * @param {*} evalArg
 * @return {*}
 */
Wombat.prototype.rewriteEvalArg = function(rawEvalOrWrapper, evalArg) {
  var toBeEvald =
    this.isString(evalArg) &&
    evalArg.indexOf('_____WB$wombat$assign$function_____') === -1
      ? this.wrapScriptTextJsProxy(evalArg)
      : evalArg;
  return rawEvalOrWrapper(toBeEvald);
};

/**
 * Applies an Event property getter override for the supplied property
 * @param {string} attr
 * @param {Object} [eventProto]
 */
Wombat.prototype.addEventOverride = function(attr, eventProto) {
  var theProto = eventProto;
  if (!eventProto) {
    theProto = this.$wbwindow.MessageEvent.prototype;
  }
  var origGetter = this.getOrigGetter(theProto, attr);
  if (!origGetter) return;
  this.defGetterProp(theProto, attr, function() {
    if (this['_' + attr] != null) {
      return this['_' + attr];
    }
    return origGetter.call(this);
  });
};

/**
 * Returns T/F indicating if the supplied attribute node is to be rewritten
 * @param {Object} attr
 * @return {boolean}
 */
Wombat.prototype.isAttrObjRewrite = function(attr) {
  if (!attr) return false;
  var tagName = attr.ownerElement && attr.ownerElement.tagName;
  return this.shouldRewriteAttr(tagName, attr.nodeName);
};

/**
 * Defines a new getter and setter function for the supplied
 * property of the Attr interface
 * @param {Object} attrProto
 * @param {string} prop
 */
Wombat.prototype.newAttrObjGetSet = function(attrProto, prop) {
  var wombat = this;
  var oGetter = this.getOrigGetter(attrProto, prop);
  var oSetter = this.getOrigSetter(attrProto, prop);
  this.defProp(
    attrProto,
    prop,
    function newAttrObjSetter(newValue) {
      var obj = wombat.proxyToObj(this);
      var res = newValue;
      if (wombat.isAttrObjRewrite(obj)) {
        res = wombat.performAttributeRewrite(
          obj.ownerElement,
          obj.name,
          newValue,
          false
        );
      }
      return oSetter.call(obj, res);
    },
    function newAttrObjGetter() {
      var obj = wombat.proxyToObj(this);
      var res = oGetter.call(obj);
      if (wombat.isAttrObjRewrite(obj)) {
        return wombat.extractOriginalURL(res);
      }
      return res;
    }
  );
};

/**
 * Overrides the nodeValue property of the Attr interface
 */
Wombat.prototype.overrideAttrProps = function() {
  var attrProto = this.$wbwindow.Attr.prototype;
  this.newAttrObjGetSet(attrProto, 'value');
  this.newAttrObjGetSet(attrProto, 'nodeValue');
  this.newAttrObjGetSet(attrProto, 'textContent');
};

/**
 * Applies an override the attribute get/set override
 * @param {Object} obj
 * @param {string} attr
 * @param {string} mod
 */
Wombat.prototype.overrideAttr = function(obj, attr, mod) {
  var orig_getter = this.getOrigGetter(obj, attr);
  var orig_setter = this.getOrigSetter(obj, attr);
  var wombat = this;

  var setter = function newAttrPropSetter(orig) {
    if (mod === 'js_' && !this.__$removedWBOSRC$__) {
      wombat.removeWBOSRC(this);
    }
    var val = wombat.rewriteUrl(orig, false, mod);
    if (orig_setter) {
      return orig_setter.call(this, val);
    } else if (wombat.wb_setAttribute) {
      return wombat.wb_setAttribute.call(this, attr, val);
    }
  };

  var getter = function newAttrPropGetter() {
    var res;
    if (orig_getter) {
      res = orig_getter.call(this);
    } else if (wombat.wb_getAttribute) {
      res = wombat.wb_getAttribute.call(this, attr);
    }
    return wombat.extractOriginalURL(res);
  };

  this.defProp(obj, attr, setter, getter);
};

/**
 * Applies an attribute getter override IFF an original getter exists
 * @param {Object} proto
 * @param {string} prop
 * @param {*} [cond]
 */
Wombat.prototype.overridePropExtract = function(proto, prop, cond) {
  var orig_getter = this.getOrigGetter(proto, prop);
  var wombat = this;
  if (orig_getter) {
    var new_getter = function overridePropExtractNewGetter() {
      var obj = wombat.proxyToObj(this);
      var res = orig_getter.call(obj);
      if (!cond || cond(obj)) {
        return wombat.extractOriginalURL(res);
      }
      return res;
    };
    this.defGetterProp(proto, prop, new_getter);
  }
};

/**
 * Applies an attribute getter override IFF an original getter exists that
 * ensures that the results of retrieving the attributes value is not a
 * wombat Proxy
 * @param {Object} proto
 * @param {string} prop
 */
Wombat.prototype.overridePropToProxy = function(proto, prop) {
  var orig_getter = this.getOrigGetter(proto, prop);
  if (orig_getter) {
    var wombat = this;
    var new_getter = function overridePropToProxyNewGetter() {
      return wombat.objToProxy(orig_getter.call(this));
    };
    this.defGetterProp(proto, prop, new_getter);
  }
};

/**
 * Applies an override to supplied history function name IFF it exists
 * @param {string} funcName
 * @return {?function}
 */
Wombat.prototype.overrideHistoryFunc = function(funcName) {
  if (!this.$wbwindow.history) return undefined;
  var orig_func = this.$wbwindow.history[funcName];
  if (!orig_func) return undefined;

  this.$wbwindow.history['_orig_' + funcName] = orig_func;
  var wombat = this;

  var rewrittenFunc = function histNewFunc(stateObj, title, url) {
    var wombatLocation = wombat.$wbwindow.WB_wombat_location;
    var rewritten_url;
    var resolvedURL;

    if (url) {
      var parser = wombat.$wbwindow.document.createElement('a');
      parser.href = url;
      resolvedURL = parser.href;

      rewritten_url = wombat.rewriteUrl(resolvedURL);

      if (
        resolvedURL !== wombatLocation.origin &&
        wombatLocation.href !== 'about:blank' &&
        !wombat.startsWith(resolvedURL, wombatLocation.origin + '/')
      ) {
        throw new DOMException('Invalid history change: ' + resolvedURL);
      }
    } else {
      resolvedURL = wombatLocation.href;
    }

    orig_func.call(this, stateObj, title, rewritten_url);

    wombat.sendHistoryUpdate(resolvedURL, title);
  };

  this.$wbwindow.history[funcName] = rewrittenFunc;
  if (this.$wbwindow.History && this.$wbwindow.History.prototype) {
    this.$wbwindow.History.prototype[funcName] = rewrittenFunc;
  }

  return rewrittenFunc;
};

/**
 * Applies an getter/setter override to the supplied style interface's attribute
 * and prop name combination
 * @param {Object} obj
 * @param {string} attr
 * @param {string} [propName]
 */
Wombat.prototype.overrideStyleAttr = function(obj, attr, propName) {
  var orig_getter = this.getOrigGetter(obj, attr);
  var orig_setter = this.getOrigSetter(obj, attr);

  var wombat = this;

  var setter = function overrideStyleAttrSetter(orig) {
    var val = wombat.rewriteStyle(orig);
    if (orig_setter) {
      orig_setter.call(this, val);
    } else {
      this.setProperty(propName, val);
    }
    return val;
  };

  var getter = orig_getter;

  if (!orig_getter) {
    getter = function overrideStyleAttrGetter() {
      return this.getPropertyValue(propName);
    };
  }

  if ((orig_setter && orig_getter) || propName) {
    this.defProp(obj, attr, setter, getter);
  }
};

/**
 * Applies an override to the setProperty function
 * @param style_proto
 */
Wombat.prototype.overrideStyleSetProp = function(style_proto) {
  var orig_setProp = style_proto.setProperty;
  var wombat = this;
  style_proto.setProperty = function rwSetProperty(name, value, priority) {
    var rwvalue = wombat.rewriteStyle(value);
    return orig_setProp.call(this, name, rwvalue, priority);
  };
};

/**
 * Overrides the getter and setter functions for the properties listed in
 * {@link Wombat#URL_PROPS} for the `a` and `area` tags
 * @param {Object} whichObj
 */
Wombat.prototype.overrideAnchorAreaElem = function(whichObj) {
  if (!whichObj || !whichObj.prototype) return;
  var originalGetSets = {};
  var originalProto = whichObj.prototype;

  var anchorAreaSetter = function anchorAreaSetter(prop, value) {
    var func = originalGetSets['set_' + prop];
    if (func) return func.call(this, value);
    return '';
  };

  var anchorAreaGetter = function anchorAreaGetter(prop) {
    var func = originalGetSets['get_' + prop];
    if (func) return func.call(this);
    return '';
  };

  for (var i = 0; i < this.URL_PROPS.length; i++) {
    var prop = this.URL_PROPS[i];
    originalGetSets['get_' + prop] = this.getOrigGetter(originalProto, prop);
    originalGetSets['set_' + prop] = this.getOrigSetter(originalProto, prop);
    if (Object.defineProperty) {
      this.defProp(
        originalProto,
        prop,
        this.makeSetLocProp(prop, anchorAreaSetter, anchorAreaGetter),
        this.makeGetLocProp(prop, anchorAreaGetter),
        true
      );
    }
  }

  originalProto.toString = function toString() {
    return this.href;
  };
};

/**
 * Overrides the getter and setter functions for the `innerHTML` and `outerHTML`
 * properties of the supplied element
 * @param {Object} elem
 * @param {string} prop
 * @param {boolean} [rewriteGetter]
 */
Wombat.prototype.overrideHtmlAssign = function(elem, prop, rewriteGetter) {
  if (!this.$wbwindow.DOMParser || !elem || !elem.prototype) {
    return;
  }

  var obj = elem.prototype;

  var orig_getter = this.getOrigGetter(obj, prop);
  var orig_setter = this.getOrigSetter(obj, prop);

  if (!orig_setter) return;

  var rewriteFn = this.rewriteHTMLAssign;

  var setter = function overrideHTMLAssignSetter(orig) {
    return rewriteFn(this, orig_setter, orig);
  };

  var wb_unrewrite_rx = this.wb_unrewrite_rx;

  var getter = function overrideHTMLAssignGetter() {
    var res = orig_getter.call(this);
    if (!this._no_rewrite) {
      return res.replace(wb_unrewrite_rx, '');
    }
    return res;
  };

  this.defProp(obj, prop, setter, rewriteGetter ? getter : orig_getter);
};

/**
 * Overrides the getter and setter functions for the supplied property
 * on the HTMLIFrameElement
 * @param {string} prop
 */
Wombat.prototype.overrideIframeContentAccess = function(prop) {
  if (
    !this.$wbwindow.HTMLIFrameElement ||
    !this.$wbwindow.HTMLIFrameElement.prototype
  ) {
    return;
  }

  var obj = this.$wbwindow.HTMLIFrameElement.prototype;
  var orig_getter = this.getOrigGetter(obj, prop);

  if (!orig_getter) return;

  var orig_setter = this.getOrigSetter(obj, prop);
  var wombat = this;
  var getter = function overrideIframeContentAccessGetter() {
    wombat.initIframeWombat(this);
    return wombat.objToProxy(orig_getter.call(this));
  };

  this.defProp(obj, prop, orig_setter, getter);
  obj['_get_' + prop] = orig_getter;
};

/**
 * Applies an override to the gettter function for the frames property of
 * the supplied window in order to ensure that wombat is initialized in
 * all frames.
 * * @param {Window} $wbwindow
 */
Wombat.prototype.overrideFramesAccess = function($wbwindow) {
  // If $wbwindow.frames is the window itself, nothing to override
  // This can be handled in the Obj Proxy
  if ($wbwindow.Proxy && $wbwindow === $wbwindow.frames) {
    return;
  }
  $wbwindow.__wb_frames = $wbwindow.frames;
  var wombat = this;
  var getter = function overrideFramesAccessGetter() {
    for (var i = 0; i < this.__wb_frames.length; i++) {
      try {
        wombat.initNewWindowWombat(this.__wb_frames[i]);
      } catch (e) {}
    }
    return this.__wb_frames;
  };

  this.defGetterProp($wbwindow, 'frames', getter);
  this.defGetterProp($wbwindow.Window.prototype, 'frames', getter);
};

/**
 * Overrides the supplied method in order to ensure that the `this` argument
 * of the function is not one of the JS Proxy objects used by wombat.
 * @param {object} cls
 * @param {string} method
 * @param {Object} [obj]
 */
Wombat.prototype.overrideFuncThisProxyToObj = function(cls, method, obj) {
  if (!cls) return;

  var ovrObj = obj;
  if (!obj && cls.prototype && cls.prototype[method]) {
    ovrObj = cls.prototype;
  } else if (!obj && cls[method]) {
    ovrObj = cls;
  }

  if (!ovrObj) return;

  var wombat = this;
  var orig = ovrObj[method];
  ovrObj[method] = function deproxyThis() {
    return orig.apply(wombat.proxyToObj(this), arguments);
  };
};

/**
 * Applies an function override that ensures that the argument the supplied index
 * is not one of the JS Proxy objects used by wombat.
 * @param {Object} cls
 * @param {string} method
 * @param {number} [argumentIdx]
 */
Wombat.prototype.overrideFuncArgProxyToObj = function(
  cls,
  method,
  argumentIdx
) {
  if (!cls || !cls.prototype) return;
  var argIndex = argumentIdx || 0;
  var orig = cls.prototype[method];
  if (!orig) return;
  var wombat = this;
  cls.prototype[method] = function deproxyFnArg() {
    var args = new Array(arguments.length);
    for (var i = 0; i < args.length; i++) {
      if (i === argIndex) {
        args[i] = wombat.proxyToObj(arguments[i]);
      } else {
        args[i] = arguments[i];
      }
    }
    var thisObj = wombat.proxyToObj(this);
    if (orig.__WB_orig_apply) {
      return orig.__WB_orig_apply(thisObj, args);
    }
    return orig.apply(thisObj, args);
  };
};

/**
 * Overrides Function.prototype.apply in order to ensure that none of the
 * arguments of `native` functions are one of the JS Proxy objects used by wombat.
 * @param {Window} $wbwindow
 */
Wombat.prototype.overrideFunctionApply = function($wbwindow) {
  if ($wbwindow.Function.prototype.__WB_orig_apply) {
    return;
  }
  var orig_apply = $wbwindow.Function.prototype.apply;
  $wbwindow.Function.prototype.__WB_orig_apply = orig_apply;
  var wombat = this;
  $wbwindow.Function.prototype.apply = function apply(obj, args) {
    var deproxiedObj = wombat.proxyToObj(obj);
    var newArgs = args;
    if (wombat.isNativeFunction(this)) {
      newArgs = wombat.deproxyArrayHandlingArgumentsObj(args);
    }
    return this.__WB_orig_apply(deproxiedObj, newArgs);
  };
  this.wb_funToString.apply = orig_apply;
};

/**
 * Overrides the getter and setter functions for the `srcset` property
 * of the supplied Object in order to rewrite accesses and retrievals
 * @param {Object} obj
 * @param {string} [mod]
 */
Wombat.prototype.overrideSrcsetAttr = function(obj, mod) {
  var prop = 'srcset';
  var orig_getter = this.getOrigGetter(obj, prop);
  var orig_setter = this.getOrigSetter(obj, prop);
  var wombat = this;

  var setter = function srcset(orig) {
    var val = wombat.rewriteSrcset(orig, this);
    if (orig_setter) {
      return orig_setter.call(this, val);
    } else if (wombat.wb_setAttribute) {
      return wombat.wb_setAttribute.call(this, prop, val);
    }
  };

  var getter = function srcset() {
    var res;
    if (orig_getter) {
      res = orig_getter.call(this);
    } else if (wombat.wb_getAttribute) {
      res = wombat.wb_getAttribute.call(this, prop);
    }
    res = wombat.extractOriginalURL(res);
    return res;
  };

  this.defProp(obj, prop, setter, getter);
};

/**
 * Overrides the getter and setter functions for the `href` property
 * of the supplied Object in order to rewrite accesses and retrievals
 * @param {Object} obj
 * @param {string} mod
 */
Wombat.prototype.overrideHrefAttr = function(obj, mod) {
  var orig_getter = this.getOrigGetter(obj, 'href');
  var orig_setter = this.getOrigSetter(obj, 'href');

  var wombat = this;

  var setter = function href(orig) {
    var val;
    if (mod === 'cs_' && orig.indexOf('data:text/css') === 0) {
      val = wombat.rewriteInlineStyle(orig);
    } else if (this.tagName === 'LINK') {
      val = wombat.rewriteUrl(
        orig,
        false,
        wombat.rwModForElement(this, 'href')
      );
    } else {
      val = wombat.rewriteUrl(orig, false, mod, this.ownerDocument);
    }
    if (orig_setter) {
      return orig_setter.call(this, val);
    } else if (wombat.wb_setAttribute) {
      return wombat.wb_setAttribute.call(this, 'href', val);
    }
  };

  var getter = function href() {
    var res;
    if (orig_getter) {
      res = orig_getter.call(this);
    } else if (wombat.wb_getAttribute) {
      res = wombat.wb_getAttribute.call(this, 'href');
    }
    if (!this._no_rewrite) return wombat.extractOriginalURL(res);
    return res;
  };

  this.defProp(obj, 'href', setter, getter);
};

/**
 * Overrides the getter and setter functions for a property of the Text
 * interface in order to rewrite accesses and retrievals when a text node
 * is the child of the style tag
 * @param {Object} textProto
 * @param {string} whichProp
 */
Wombat.prototype.overrideTextProtoGetSet = function(textProto, whichProp) {
  var orig_getter = this.getOrigGetter(textProto, whichProp);
  var wombat = this;
  var setter;
  // data, from CharacterData, is both readable and writable whereas wholeText, from Text, is not
  if (whichProp === 'data') {
    var orig_setter = this.getOrigSetter(textProto, whichProp);
    setter = function rwTextProtoSetter(orig) {
      var res = orig;
      if (
        !this._no_rewrite &&
        this.parentElement &&
        this.parentElement.tagName === 'STYLE'
      ) {
        res = wombat.rewriteStyle(orig);
      }
      return orig_setter.call(this, res);
    };
  }
  var getter = function rwTextProtoGetter() {
    var res = orig_getter.call(this);
    if (
      !this._no_rewrite &&
      this.parentElement &&
      this.parentElement.tagName === 'STYLE'
    ) {
      return res.replace(wombat.wb_unrewrite_rx, '');
    }
    return res;
  };
  this.defProp(textProto, whichProp, setter, getter);
};

/**
 * Overrides the constructor of an UIEvent object in order to ensure
 * that the `view`, `relatedTarget`, and `target` arguments of the
 * constructor are not a JS Proxy used by wombat.
 * @param {string} which
 */
Wombat.prototype.overrideAnUIEvent = function(which) {
  var didOverrideKey = '__wb_' + which + '_overridden';
  var ConstructorFN = this.$wbwindow[which];
  if (
    !ConstructorFN ||
    !ConstructorFN.prototype ||
    ConstructorFN.prototype[didOverrideKey]
  )
    return;
  // ensure if and when view is accessed it is proxied
  var wombat = this;
  this.overridePropToProxy(ConstructorFN.prototype, 'view');
  var initFNKey = 'init' + which;
  if (ConstructorFN.prototype[initFNKey]) {
    var originalInitFn = ConstructorFN.prototype[initFNKey];
    ConstructorFN.prototype[initFNKey] = function() {
      var thisObj = wombat.proxyToObj(this);
      if (arguments.length === 0 || arguments.length < 3) {
        if (originalInitFn.__WB_orig_apply) {
          return originalInitFn.__WB_orig_apply(thisObj, arguments);
        }
        return originalInitFn.apply(thisObj, arguments);
      }
      var newArgs = new Array(arguments.length);
      for (var i = 0; i < arguments.length; i++) {
        if (i === 3) {
          newArgs[i] = wombat.proxyToObj(arguments[i]);
        } else {
          newArgs[i] = arguments[i];
        }
      }
      if (originalInitFn.__WB_orig_apply) {
        return originalInitFn.__WB_orig_apply(thisObj, newArgs);
      }
      return originalInitFn.apply(thisObj, newArgs);
    };
  }
  this.$wbwindow[which] = (function(EventConstructor) {
    return function NewEventConstructor(type, init) {
      wombat.domConstructorErrorChecker(this, which, arguments);
      if (init) {
        if (init.view != null) {
          init.view = wombat.proxyToObj(init.view);
        }
        if (init.relatedTarget != null) {
          init.relatedTarget = wombat.proxyToObj(init.relatedTarget);
        }
        if (init.target != null) {
          init.target = wombat.proxyToObj(init.target);
        }
      }
      return new EventConstructor(type, init);
    };
  })(ConstructorFN);
  this.$wbwindow[which].prototype = ConstructorFN.prototype;
  Object.defineProperty(this.$wbwindow[which].prototype, 'constructor', {
    value: this.$wbwindow[which]
  });
  this.$wbwindow[which].prototype[didOverrideKey] = true;
};

/**
 * Rewrites the arguments supplied to the functions of the ParentNode interface
 * @param {Object} fnThis
 * @param {function} originalFn
 * @param {Object} argsObj
 * @return {*}
 */
Wombat.prototype.rewriteParentNodeFn = function(fnThis, originalFn, argsObj) {
  var argArr = this._no_rewrite
    ? argsObj
    : this.rewriteElementsInArguments(argsObj);
  var thisObj = this.proxyToObj(fnThis);
  if (originalFn.__WB_orig_apply) {
    return originalFn.__WB_orig_apply(thisObj, argArr);
  }
  return originalFn.apply(thisObj, argArr);
};

/**
 * Overrides the append and prepend functions on the supplied object in order
 * to ensure that the elements or string of HTML supplied as arguments to these
 * functions are rewritten
 * @param {Object} obj
 * @see https://developer.mozilla.org/en-US/docs/Web/API/ParentNode/append
 * @see https://developer.mozilla.org/en-US/docs/Web/API/ParentNode/prepend
 */
Wombat.prototype.overrideParentNodeAppendPrepend = function(obj) {
  var rewriteParentNodeFn = this.rewriteParentNodeFn;
  if (obj.prototype.append) {
    var originalAppend = obj.prototype.append;
    obj.prototype.append = function append() {
      return rewriteParentNodeFn(this, originalAppend, arguments);
    };
  }
  if (obj.prototype.prepend) {
    var originalPrepend = obj.prototype.prepend;
    obj.prototype.prepend = function prepend() {
      return rewriteParentNodeFn(this, originalPrepend, arguments);
    };
  }
};

/**
 * Overrides the `innerHTML` property and `append`, `prepend` functions
 * on the ShadowRoot interface in order to ensure any HTML elements
 * added via these methods are rewritten
 * @see https://developer.mozilla.org/en-US/docs/Web/API/ShadowRoot
 */
Wombat.prototype.overrideShadowDom = function() {
  if (!this.$wbwindow.ShadowRoot || !this.$wbwindow.ShadowRoot.prototype) {
    return;
  }
  // shadow root inherits from DocumentFragment, Node, and ParentNode not Element
  this.overrideHtmlAssign(this.$wbwindow.ShadowRoot, 'innerHTML', true);
  this.overrideParentNodeAppendPrepend(this.$wbwindow.ShadowRoot);
};

/**
 * Applies an override to the ChildNode interface that is inherited by
 * the supplied Object. If the textIface argument is truthy the rewrite function
 * used is {@link rewriteChildNodeFn} otherwise {@link rewriteTextNodeFn}
 * @param {*} ifaceWithChildNode
 * @param {boolean} [textIface]
 */
Wombat.prototype.overrideChildNodeInterface = function(
  ifaceWithChildNode,
  textIface
) {
  if (!ifaceWithChildNode || !ifaceWithChildNode.prototype) return;
  var rewriteFn = textIface ? this.rewriteTextNodeFn : this.rewriteChildNodeFn;
  if (ifaceWithChildNode.prototype.before) {
    var originalBefore = ifaceWithChildNode.prototype.before;
    ifaceWithChildNode.prototype.before = function before() {
      return rewriteFn(this, originalBefore, arguments);
    };
  }
  if (ifaceWithChildNode.prototype.after) {
    var originalAfter = ifaceWithChildNode.prototype.after;
    ifaceWithChildNode.prototype.after = function after() {
      return rewriteFn(this, originalAfter, arguments);
    };
  }
  if (ifaceWithChildNode.prototype.replaceWith) {
    var originalReplaceWith = ifaceWithChildNode.prototype.replaceWith;
    ifaceWithChildNode.prototype.replaceWith = function replaceWith() {
      return rewriteFn(this, originalReplaceWith, arguments);
    };
  }
};

/**
 * Applies overrides to the `appendData`, `insertData`, and `replaceData` functions
 * and `data` and `wholeText` properties on the Text interface in order to ensure
 * CSS strings are rewritten when Text nodes are children of the style tag
 */
Wombat.prototype.initTextNodeOverrides = function() {
  var Text = this.$wbwindow.Text;
  if (!Text || !Text.prototype) return;
  // https://dom.spec.whatwg.org/#characterdata and https://dom.spec.whatwg.org/#interface-text
  // depending on the JS frameworks used some pages include JS that will append a single text node child
  // to a style tag and then progressively modify that text nodes data for changing the css values that
  // style tag contains
  var textProto = Text.prototype;
  // override inherited CharacterData functions
  var rewriteTextProtoFunction = this.rewriteTextNodeFn;
  if (textProto.appendData) {
    var originalAppendData = textProto.appendData;
    textProto.appendData = function appendData() {
      return rewriteTextProtoFunction(this, originalAppendData, arguments);
    };
  }
  if (textProto.insertData) {
    var originalInsertData = textProto.insertData;
    textProto.insertData = function insertData() {
      return rewriteTextProtoFunction(this, originalInsertData, arguments);
    };
  }
  if (textProto.replaceData) {
    var originalReplaceData = textProto.replaceData;
    textProto.replaceData = function replaceData() {
      return rewriteTextProtoFunction(this, originalReplaceData, arguments);
    };
  }
  this.overrideChildNodeInterface(Text, true);
  // override property getters and setters
  this.overrideTextProtoGetSet(textProto, 'data');
  this.overrideTextProtoGetSet(textProto, 'wholeText');
};

/**
 * Applies attribute getter and setter function overrides to the HTML elements
 * and CSS properties that are URLs are rewritten
 */
Wombat.prototype.initAttrOverrides = function() {
  // href attr overrides
  this.overrideHrefAttr(this.$wbwindow.HTMLLinkElement.prototype, 'cs_');
  this.overrideHrefAttr(this.$wbwindow.CSSStyleSheet.prototype, 'cs_');
  this.overrideHrefAttr(this.$wbwindow.HTMLBaseElement.prototype, 'mp_');
  // srcset attr overrides
  this.overrideSrcsetAttr(this.$wbwindow.HTMLImageElement.prototype, 'im_');
  this.overrideSrcsetAttr(this.$wbwindow.HTMLSourceElement.prototype, 'oe_');
  // poster attr overrides
  this.overrideAttr(this.$wbwindow.HTMLVideoElement.prototype, 'poster', 'im_');
  this.overrideAttr(this.$wbwindow.HTMLAudioElement.prototype, 'poster', 'im_');
  // src attr overrides
  this.overrideAttr(this.$wbwindow.HTMLImageElement.prototype, 'src', 'im_');
  this.overrideAttr(this.$wbwindow.HTMLInputElement.prototype, 'src', 'oe_');
  this.overrideAttr(this.$wbwindow.HTMLEmbedElement.prototype, 'src', 'oe_');
  this.overrideAttr(this.$wbwindow.HTMLVideoElement.prototype, 'src', 'oe_');
  this.overrideAttr(this.$wbwindow.HTMLAudioElement.prototype, 'src', 'oe_');
  this.overrideAttr(this.$wbwindow.HTMLSourceElement.prototype, 'src', 'oe_');
  if (window.HTMLTrackElement && window.HTMLTrackElement.prototype) {
    this.overrideAttr(this.$wbwindow.HTMLTrackElement.prototype, 'src', 'oe_');
  }
  this.overrideAttr(this.$wbwindow.HTMLIFrameElement.prototype, 'src', 'if_');
  if (
    this.$wbwindow.HTMLFrameElement &&
    this.$wbwindow.HTMLFrameElement.prototype
  ) {
    this.overrideAttr(this.$wbwindow.HTMLFrameElement.prototype, 'src', 'fr_');
  }
  this.overrideAttr(this.$wbwindow.HTMLScriptElement.prototype, 'src', 'js_');
  // other attr overrides
  this.overrideAttr(this.$wbwindow.HTMLObjectElement.prototype, 'data', 'oe_');
  this.overrideAttr(
    this.$wbwindow.HTMLObjectElement.prototype,
    'codebase',
    'oe_'
  );
  this.overrideAttr(this.$wbwindow.HTMLMetaElement.prototype, 'content', 'mp_');
  this.overrideAttr(this.$wbwindow.HTMLFormElement.prototype, 'action', 'mp_');
  this.overrideAttr(this.$wbwindow.HTMLQuoteElement.prototype, 'cite', 'mp_');
  this.overrideAttr(this.$wbwindow.HTMLModElement.prototype, 'cite', 'mp_');
  // a, area tag overrides
  this.overrideAnchorAreaElem(this.$wbwindow.HTMLAnchorElement);
  this.overrideAnchorAreaElem(this.$wbwindow.HTMLAreaElement);

  var style_proto = this.$wbwindow.CSSStyleDeclaration.prototype;

  // For FF
  if (this.$wbwindow.CSS2Properties) {
    style_proto = this.$wbwindow.CSS2Properties.prototype;
  }

  this.overrideStyleAttr(style_proto, 'cssText');
  this.overrideStyleAttr(style_proto, 'background', 'background');
  this.overrideStyleAttr(style_proto, 'backgroundImage', 'background-image');
  this.overrideStyleAttr(style_proto, 'cursor', 'cursor');
  this.overrideStyleAttr(style_proto, 'listStyle', 'list-style');
  this.overrideStyleAttr(style_proto, 'listStyleImage', 'list-style-image');
  this.overrideStyleAttr(style_proto, 'border', 'border');
  this.overrideStyleAttr(style_proto, 'borderImage', 'border-image');
  this.overrideStyleAttr(
    style_proto,
    'borderImageSource',
    'border-image-source'
  );
  this.overrideStyleAttr(style_proto, 'maskImage', 'mask-image');

  this.overrideStyleSetProp(style_proto);

  if (this.$wbwindow.CSSStyleSheet && this.$wbwindow.CSSStyleSheet.prototype) {
    // https://developer.mozilla.org/en-US/docs/Web/API/CSSStyleSheet/insertRule
    // ruleText is a string of raw css....
    var wombat = this;
    var oInsertRule = this.$wbwindow.CSSStyleSheet.prototype.insertRule;
    this.$wbwindow.CSSStyleSheet.prototype.insertRule = function insertRule(
      ruleText,
      index
    ) {
      return oInsertRule.call(this, wombat.rewriteStyle(ruleText), index);
    };
  }

  if (this.$wbwindow.CSSRule && this.$wbwindow.CSSRule.prototype) {
    this.overrideStyleAttr(this.$wbwindow.CSSRule.prototype, 'cssText');
  }
};

/**
 * Applies overrides to CSSStyleValue.[parse,parseAll], CSSKeywordValue, and
 * StylePropertyMap in order to ensure the URLs these interfaces operate on
 * are rewritten. Gotta love Chrome.
 * @see https://drafts.css-houdini.org/css-typed-om-1/
 */
Wombat.prototype.initCSSOMOverrides = function() {
  var wombat = this;
  if (this.$wbwindow.CSSStyleValue) {
    var cssStyleValueOverride = function(CSSSV, which) {
      var oFN = CSSSV[which];
      CSSSV[which] = function parseOrParseAllOverride(property, cssText) {
        if (cssText == null) return oFN.call(this, property, cssText);
        var rwCSSText = wombat.noExceptRewriteStyle(cssText);
        return oFN.call(this, property, rwCSSText);
      };
    };

    if (
      this.$wbwindow.CSSStyleValue.parse &&
      this.$wbwindow.CSSStyleValue.parse.toString().indexOf('[native code]') > 0
    ) {
      cssStyleValueOverride(this.$wbwindow.CSSStyleValue, 'parse');
    }

    if (
      this.$wbwindow.CSSStyleValue.parseAll &&
      this.$wbwindow.CSSStyleValue.parseAll
        .toString()
        .indexOf('[native code]') > 0
    ) {
      cssStyleValueOverride(this.$wbwindow.CSSStyleValue, 'parseAll');
    }
  }

  if (
    this.$wbwindow.CSSKeywordValue &&
    this.$wbwindow.CSSKeywordValue.prototype
  ) {
    var oCSSKV = this.$wbwindow.CSSKeywordValue;
    this.$wbwindow.CSSKeywordValue = (function(CSSKeywordValue_) {
      return function CSSKeywordValue(cssValue) {
        wombat.domConstructorErrorChecker(this, 'CSSKeywordValue', arguments);
        return new CSSKeywordValue_(wombat.rewriteStyle(cssValue));
      };
    })(this.$wbwindow.CSSKeywordValue);
    this.$wbwindow.CSSKeywordValue.prototype = oCSSKV.prototype;
    Object.defineProperty(
      this.$wbwindow.CSSKeywordValue.prototype,
      'constructor',
      {
        value: this.$wbwindow.CSSKeywordValue
      }
    );
    addToStringTagToClass(this.$wbwindow.CSSKeywordValue, 'CSSKeywordValue');
  }

  if (
    this.$wbwindow.StylePropertyMap &&
    this.$wbwindow.StylePropertyMap.prototype
  ) {
    var originalSet = this.$wbwindow.StylePropertyMap.prototype.set;
    this.$wbwindow.StylePropertyMap.prototype.set = function set() {
      if (arguments.length <= 1) {
        if (originalSet.__WB_orig_apply) {
          return originalSet.__WB_orig_apply(this, arguments);
        }
        return originalSet.apply(this, arguments);
      }
      var newArgs = new Array(arguments.length);
      newArgs[0] = arguments[0];
      for (var i = 1; i < arguments.length; i++) {
        newArgs[i] = wombat.noExceptRewriteStyle(arguments[i]);
      }
      if (originalSet.__WB_orig_apply) {
        return originalSet.__WB_orig_apply(this, newArgs);
      }
      return originalSet.apply(this, newArgs);
    };

    var originalAppend = this.$wbwindow.StylePropertyMap.prototype.append;
    this.$wbwindow.StylePropertyMap.prototype.append = function append() {
      if (arguments.length <= 1) {
        if (originalSet.__WB_orig_apply) {
          return originalAppend.__WB_orig_apply(this, arguments);
        }
        return originalAppend.apply(this, arguments);
      }
      var newArgs = new Array(arguments.length);
      newArgs[0] = arguments[0];
      for (var i = 1; i < arguments.length; i++) {
        newArgs[i] = wombat.noExceptRewriteStyle(arguments[i]);
      }
      if (originalAppend.__WB_orig_apply) {
        return originalAppend.__WB_orig_apply(this, newArgs);
      }
      return originalAppend.apply(this, newArgs);
    };
  }
};

/**
 * Applies an overrides to the Audio constructor in order to ensure its URL
 * argument is rewritten
 */
Wombat.prototype.initAudioOverride = function() {
  if (!this.$wbwindow.Audio) return;
  var orig_audio = this.$wbwindow.Audio;
  var wombat = this;
  this.$wbwindow.Audio = (function(Audio_) {
    return function Audio(url) {
      wombat.domConstructorErrorChecker(this, 'Audio');
      return new Audio_(wombat.rewriteUrl(url, true, 'oe_'));
    };
  })(this.$wbwindow.Audio);

  this.$wbwindow.Audio.prototype = orig_audio.prototype;
  Object.defineProperty(this.$wbwindow.Audio.prototype, 'constructor', {
    value: this.$wbwindow.Audio
  });
  addToStringTagToClass(this.$wbwindow.Audio, 'HTMLAudioElement');
};

/**
 * Initializes the BAD_PREFIXES array using the supplied prefix
 * @param {string} prefix
 */
Wombat.prototype.initBadPrefixes = function(prefix) {
  this.BAD_PREFIXES = [
    'http:' + prefix,
    'https:' + prefix,
    'http:/' + prefix,
    'https:/' + prefix
  ];
};

/**
 * Applies an override to crypto.getRandomValues in order to make
 * the values it returns are deterministic during replay
 */
Wombat.prototype.initCryptoRandom = function() {
  if (!this.$wbwindow.crypto || !this.$wbwindow.Crypto) return;
  var wombat = this;
  var new_getrandom = function getRandomValues(array) {
    for (var i = 0; i < array.length; i++) {
      array[i] = parseInt(wombat.$wbwindow.Math.random() * 4294967296);
    }
    return array;
  };
  this.$wbwindow.Crypto.prototype.getRandomValues = new_getrandom;
  this.$wbwindow.crypto.getRandomValues = new_getrandom;
};

/**
 * Applies an override to the Date object in order to ensure that
 * all Dates used during replay are in the datetime of replay
 * @param {string} timestamp
 */
Wombat.prototype.initDateOverride = function(timestamp) {
  if (this.$wbwindow.__wb_Date_now) return;
  var newTimestamp = parseInt(timestamp) * 1000;
  // var timezone = new Date().getTimezoneOffset() * 60 * 1000;
  // Already UTC!
  var timezone = 0;
  var start_now = this.$wbwindow.Date.now();
  var timediff = start_now - (newTimestamp - timezone);

  var orig_date = this.$wbwindow.Date;

  var orig_utc = this.$wbwindow.Date.UTC;
  var orig_parse = this.$wbwindow.Date.parse;
  var orig_now = this.$wbwindow.Date.now;

  this.$wbwindow.__wb_Date_now = orig_now;

  this.$wbwindow.Date = (function(Date_) {
    return function Date(A, B, C, D, E, F, G) {
      // [native code]
      // Apply doesn't work for constructors and Date doesn't
      // seem to like undefined args, so must explicitly
      // call constructor for each possible args 0..7
      if (A === undefined) {
        return new Date_(orig_now() - timediff);
      } else if (B === undefined) {
        return new Date_(A);
      } else if (C === undefined) {
        return new Date_(A, B);
      } else if (D === undefined) {
        return new Date_(A, B, C);
      } else if (E === undefined) {
        return new Date_(A, B, C, D);
      } else if (F === undefined) {
        return new Date_(A, B, C, D, E);
      } else if (G === undefined) {
        return new Date_(A, B, C, D, E, F);
      } else {
        return new Date_(A, B, C, D, E, F, G);
      }
    };
  })(this.$wbwindow.Date);

  this.$wbwindow.Date.prototype = orig_date.prototype;

  this.$wbwindow.Date.now = function now() {
    return orig_now() - timediff;
  };

  this.$wbwindow.Date.UTC = orig_utc;
  this.$wbwindow.Date.parse = orig_parse;

  this.$wbwindow.Date.__WB_timediff = timediff;

  Object.defineProperty(this.$wbwindow.Date.prototype, 'constructor', {
    value: this.$wbwindow.Date
  });
};

/**
 * Applies an override to the document.title property in order to ensure
 * that actual top (archive top frame containing the replay iframe) receives
 * document.title updates
 */
Wombat.prototype.initDocTitleOverride = function() {
  var orig_get_title = this.getOrigGetter(this.$wbwindow.document, 'title');
  var orig_set_title = this.getOrigSetter(this.$wbwindow.document, 'title');
  var wombat = this;
  var set_title = function title(value) {
    var res = orig_set_title.call(this, value);
    var message = { wb_type: 'title', title: value };
    wombat.sendTopMessage(message);
    return res;
  };
  this.defProp(this.$wbwindow.document, 'title', set_title, orig_get_title);
};

/**
 * Applies an override to the FontFace constructor in order to ensure font URLs
 * are rewritten
 * @see https://drafts.csswg.org/css-font-loading/#FontFace-interface
 */
Wombat.prototype.initFontFaceOverride = function() {
  if (!this.$wbwindow.FontFace || this.$wbwindow.FontFace.__wboverriden__) {
    return;
  }
  var wombat = this;
  var origFontFace = this.$wbwindow.FontFace;
  this.$wbwindow.FontFace = (function(FontFace_) {
    return function FontFace(family, source, descriptors) {
      wombat.domConstructorErrorChecker(this, 'FontFace', arguments, 2);
      var rwSource = source;
      if (source != null) {
        if (typeof source !== 'string') {
          // is CSSOMString or ArrayBuffer or ArrayBufferView
          rwSource = wombat.rewriteInlineStyle(source.toString());
        } else {
          rwSource = wombat.rewriteInlineStyle(source);
        }
      }
      return new FontFace_(family, rwSource, descriptors);
    };
  })(this.$wbwindow.FontFace);
  this.$wbwindow.FontFace.prototype = origFontFace.prototype;
  Object.defineProperty(this.$wbwindow.FontFace.prototype, 'constructor', {
    value: this.$wbwindow.FontFace
  });
  this.$wbwindow.FontFace.__wboverriden__ = true;
  addToStringTagToClass(this.$wbwindow.FontFace, 'FontFace');
};

/**
 * Forces, when possible, the devicePixelRatio property of window to 1
 * in order to ensure deterministic replay
 */
Wombat.prototype.initFixedRatio = function() {
  try {
    // otherwise, just set it
    this.$wbwindow.devicePixelRatio = 1;
  } catch (e) {}

  // prevent changing, if possible
  if (Object.defineProperty) {
    try {
      // fixed pix ratio
      Object.defineProperty(this.$wbwindow, 'devicePixelRatio', {
        value: 1,
        writable: false
      });
    } catch (e) {}
  }
};

/**
 * Initializes wombats path information from the supplied wbinfo object
 * @param {Object} wbinfo
 */
Wombat.prototype.initPaths = function(wbinfo) {
  wbinfo.wombat_opts = wbinfo.wombat_opts || {};
  this.wb_info = wbinfo;
  this.wb_opts = wbinfo.wombat_opts;
  this.wb_replay_prefix = wbinfo.prefix;
  this.wb_is_proxy = wbinfo.proxy_magic || !this.wb_replay_prefix;
  this.wb_info.top_host = this.wb_info.top_host || '*';
  this.wb_curr_host =
    this.$wbwindow.location.protocol + '//' + this.$wbwindow.location.host;
  this.wb_orig_scheme = wbinfo.wombat_scheme + '://';
  this.wb_orig_origin = this.wb_orig_scheme + wbinfo.wombat_host;
  this.wb_abs_prefix = this.wb_replay_prefix;
  if (!wbinfo.is_live && wbinfo.wombat_ts) {
    this.wb_capture_date_part = '/' + wbinfo.wombat_ts + '/';
  } else {
    this.wb_capture_date_part = '';
  }
  this.initBadPrefixes(this.wb_replay_prefix);
};

/**
 * Applies an override to Math.seed and Math.random using the supplied
 * seed in order to ensure that random numbers are deterministic during
 * replay
 * @param {string} seed
 */
Wombat.prototype.initSeededRandom = function(seed) {
  // Adapted from:
  // http://indiegamr.com/generate-repeatable-random-numbers-in-js/
  this.$wbwindow.Math.seed = parseInt(seed);
  var wombat = this;
  this.$wbwindow.Math.random = function random() {
    wombat.$wbwindow.Math.seed =
      (wombat.$wbwindow.Math.seed * 9301 + 49297) % 233280;
    return wombat.$wbwindow.Math.seed / 233280;
  };
};

/**
 * Applies overrides to history.pushState and history.replaceState in order
 * to ensure that URLs used for browser history manipulation are rewritten.
 * Also adds a `popstate` listener to window of the browser context wombat is in
 * in order to ensure that actual top (archive top frame containing the replay iframe)
 * browser history is updated IFF the history manipulation happens in the replay top
 */
Wombat.prototype.initHistoryOverrides = function() {
  this.overrideHistoryFunc('pushState');
  this.overrideHistoryFunc('replaceState');
  var wombat = this;
  this.$wbwindow.addEventListener('popstate', function(event) {
    wombat.sendHistoryUpdate(
      wombat.$wbwindow.WB_wombat_location.href,
      wombat.$wbwindow.document.title
    );
  });
};

/**
 * Applies overrides to the XMLHttpRequest.open and XMLHttpRequest.responseURL
 * in order to ensure URLs are rewritten.
 *
 * Applies an override to window.fetch in order to rewrite URLs and URLs of
 * the supplied Request objects used as arguments to fetch.
 *
 * Applies overrides to window.Request, window.Response, window.EventSource,
 * and window.WebSocket in order to ensure URLs they operate on are rewritten.
 *
 * @see https://xhr.spec.whatwg.org/
 * @see https://fetch.spec.whatwg.org/
 * @see https://html.spec.whatwg.org/multipage/web-sockets.html#websocket
 * @see https://html.spec.whatwg.org/multipage/server-sent-events.html#the-eventsource-interface
 */
Wombat.prototype.initHTTPOverrides = function() {
  var wombat = this;
  if (
    this.$wbwindow.XMLHttpRequest &&
    this.$wbwindow.XMLHttpRequest.prototype
  ) {
    if (this.$wbwindow.XMLHttpRequest.prototype.open) {
      var origXMLHttpOpen = this.$wbwindow.XMLHttpRequest.prototype.open;
      this.utilFns.XHRopen = origXMLHttpOpen;
      this.$wbwindow.XMLHttpRequest.prototype.open = function open(
        method,
        url,
        async,
        user,
        password
      ) {
        var rwURL = !this._no_rewrite ? wombat.rewriteUrl(url) : url;
        var openAsync = true;
        if (async != null && !async) openAsync = false;
        origXMLHttpOpen.call(this, method, rwURL, openAsync, user, password);
        if (!wombat.startsWith(rwURL, 'data:')) {
          this.setRequestHeader('X-Pywb-Requested-With', 'XMLHttpRequest');
        }
      };
    }
    // responseURL override
    this.overridePropExtract(
      this.$wbwindow.XMLHttpRequest.prototype,
      'responseURL'
    );
  }

  if (this.$wbwindow.fetch) {
    var orig_fetch = this.$wbwindow.fetch;
    this.$wbwindow.fetch = function fetch(input, init_opts) {
      var rwInput = input;
      var inputType = typeof input;
      if (inputType === 'string') {
        rwInput = wombat.rewriteUrl(input);
      } else if (inputType === 'object' && input.url) {
        var new_url = wombat.rewriteUrl(input.url);
        if (new_url !== input.url) {
          rwInput = new Request(new_url, input);
        }
      } else if (inputType === 'object' && input.href) {
        // it is likely that input is either window.location or window.URL
        rwInput = wombat.rewriteUrl(input.href);
      }

      init_opts = init_opts || {};
      init_opts['credentials'] = 'include';

      return orig_fetch.call(wombat.proxyToObj(this), rwInput, init_opts);
    };
  }

  if (this.$wbwindow.Request && this.$wbwindow.Request.prototype) {
    var orig_request = this.$wbwindow.Request;
    this.$wbwindow.Request = (function(Request_) {
      return function Request(input, init_opts) {
        wombat.domConstructorErrorChecker(this, 'Request', arguments);
        var newInitOpts = init_opts || {};
        var newInput = input;
        var inputType = typeof input;
        switch (inputType) {
          case 'string':
            newInput = wombat.rewriteUrl(input);
            break;
          case 'object':
            newInput = input;
            if (input.url) {
              var new_url = wombat.rewriteUrl(input.url);
              if (new_url !== input.url) {
                // not much we can do here Request.url is read only
                // https://developer.mozilla.org/en-US/docs/Web/API/Request/url
                newInput = new Request_(new_url, input);
              }
            } else if (input.href) {
              // it is likely that input is either window.location or window.URL
              newInput = wombat.rewriteUrl(input.toString(), true);
            }
            break;
        }
        newInitOpts['credentials'] = 'include';
        return new Request_(newInput, newInitOpts);
      };
    })(this.$wbwindow.Request);

    this.$wbwindow.Request.prototype = orig_request.prototype;
    Object.defineProperty(this.$wbwindow.Request.prototype, 'constructor', {
      value: this.$wbwindow.Request
    });
  }

  if (this.$wbwindow.Response && this.$wbwindow.Response.prototype) {
    // https://developer.mozilla.org/en-US/docs/Web/API/Response/redirect
    var originalRedirect = this.$wbwindow.Response.prototype.redirect;
    this.$wbwindow.Response.prototype.redirect = function redirect(
      url,
      status
    ) {
      var rwURL = wombat.rewriteUrl(url, true, null, wombat.$wbwindow.document);
      return originalRedirect.call(this, rwURL, status);
    };
  }

  if (this.$wbwindow.EventSource && this.$wbwindow.EventSource.prototype) {
    var origEventSource = this.$wbwindow.EventSource;
    this.$wbwindow.EventSource = (function(EventSource_) {
      return function EventSource(url, configuration) {
        wombat.domConstructorErrorChecker(this, 'EventSource', arguments);
        var rwURL = url;
        if (url != null) {
          rwURL = wombat.rewriteUrl(url);
        }
        return new EventSource_(rwURL, configuration);
      };
    })(this.$wbwindow.EventSource);
    this.$wbwindow.EventSource.prototype = origEventSource.prototype;
    Object.defineProperty(this.$wbwindow.EventSource.prototype, 'constructor', {
      value: this.$wbwindow.EventSource
    });
    addToStringTagToClass(this.$wbwindow.EventSource, 'EventSource');
  }

  if (this.$wbwindow.WebSocket && this.$wbwindow.WebSocket.prototype) {
    var origWebSocket = this.$wbwindow.WebSocket;
    this.$wbwindow.WebSocket = (function(WebSocket_) {
      return function WebSocket(url, configuration) {
        wombat.domConstructorErrorChecker(this, 'WebSocket', arguments);
        var rwURL = url;
        if (url != null) {
          rwURL = wombat.rewriteWSURL(url);
        }
        return new WebSocket_(rwURL, configuration);
      };
    })(this.$wbwindow.WebSocket);
    this.$wbwindow.WebSocket.prototype = origWebSocket.prototype;
    Object.defineProperty(this.$wbwindow.WebSocket.prototype, 'constructor', {
      value: this.$wbwindow.WebSocket
    });
    addToStringTagToClass(this.$wbwindow.WebSocket, 'WebSocket');
  }
};

/**
 * Applies an override to Element.[getAttribute, setAttribute] in order to
 * ensure that operations on properties that contain URLs are rewritten
 * @see https://www.w3.org/TR/dom/#interface-element
 */
Wombat.prototype.initElementGetSetAttributeOverride = function() {
  if (
    this.wb_opts.skip_setAttribute ||
    (!this.$wbwindow.Element || !this.$wbwindow.Element.prototype)
  ) {
    return;
  }

  var wombat = this;
  var ElementProto = this.$wbwindow.Element.prototype;

  if (ElementProto.setAttribute) {
    var orig_setAttribute = ElementProto.setAttribute;
    ElementProto._orig_setAttribute = orig_setAttribute;
    ElementProto.setAttribute = function setAttribute(name, value) {
      var rwValue = value;
      if (name && typeof rwValue === 'string') {
        var lowername = name.toLowerCase();
        if (
          this.tagName === 'LINK' &&
          lowername === 'href' &&
          rwValue.indexOf('data:text/css') === 0
        ) {
          rwValue = wombat.rewriteInlineStyle(value);
        } else if (lowername === 'style') {
          rwValue = wombat.rewriteStyle(value);
        } else if (lowername === 'srcset') {
          rwValue = wombat.rewriteSrcset(value, this);
        } else {
          var shouldRW = wombat.shouldRewriteAttr(this.tagName, lowername);
          if (shouldRW) {
            wombat.removeWBOSRC(this);
            if (!this._no_rewrite) {
              rwValue = wombat.rewriteUrl(
                value,
                false,
                wombat.rwModForElement(this, lowername)
              );
            }
          }
        }
      }
      return orig_setAttribute.call(this, name, rwValue);
    };
  }

  if (ElementProto.getAttribute) {
    var orig_getAttribute = ElementProto.getAttribute;
    this.wb_getAttribute = orig_getAttribute;
    ElementProto.getAttribute = function getAttribute(name) {
      var result = orig_getAttribute.call(this, name);
      var lowerName = name;
      if (name) {
        lowerName = name.toLowerCase();
      }
      if (wombat.shouldRewriteAttr(this.tagName, lowerName)) {
        var maybeWBOSRC = wombat.retrieveWBOSRC(this);
        if (maybeWBOSRC) return maybeWBOSRC;
        return wombat.extractOriginalURL(result);
      } else if (
        wombat.startsWith(lowerName, 'data-') &&
        wombat.startsWithOneOf(result, wombat.VALID_PREFIXES)
      ) {
        return wombat.extractOriginalURL(result);
      }

      return result;
    };
  }
};

/**
 * Applies an override to the getAttribute[NS] and setAttribute[NS] functions
 * of the SVGImageElement interface in order to ensure that the URLs of the
 * href and xlink:href properties are rewritten
 */
Wombat.prototype.initSvgImageOverrides = function() {
  if (!this.$wbwindow.SVGImageElement) {
    return;
  }
  var svgImgProto = this.$wbwindow.SVGImageElement.prototype;

  var orig_getAttr = svgImgProto.getAttribute;
  var orig_getAttrNS = svgImgProto.getAttributeNS;
  var orig_setAttr = svgImgProto.setAttribute;
  var orig_setAttrNS = svgImgProto.setAttributeNS;
  var wombat = this;

  svgImgProto.getAttribute = function getAttribute(name) {
    var value = orig_getAttr.call(this, name);
    if (name.indexOf('xlink:href') >= 0 || name === 'href') {
      return wombat.extractOriginalURL(value);
    }
    return value;
  };

  svgImgProto.getAttributeNS = function getAttributeNS(ns, name) {
    var value = orig_getAttrNS.call(this, ns, name);
    if (name.indexOf('xlink:href') >= 0 || name === 'href') {
      return wombat.extractOriginalURL(value);
    }
    return value;
  };

  svgImgProto.setAttribute = function setAttribute(name, value) {
    var rwValue = value;
    if (name.indexOf('xlink:href') >= 0 || name === 'href') {
      rwValue = wombat.rewriteUrl(value);
    }
    return orig_setAttr.call(this, name, rwValue);
  };

  svgImgProto.setAttributeNS = function setAttributeNS(ns, name, value) {
    var rwValue = value;
    if (name.indexOf('xlink:href') >= 0 || name === 'href') {
      rwValue = wombat.rewriteUrl(value);
    }
    return orig_setAttrNS.call(this, ns, name, rwValue);
  };
};

/**
 * Applies an override to document.createElementNS in order to ensure that the
 * nameSpaceURI argument is un-rewritten
 */
Wombat.prototype.initCreateElementNSFix = function() {
  if (
    !this.$wbwindow.document.createElementNS ||
    !this.$wbwindow.Document.prototype.createElementNS
  ) {
    return;
  }
  var orig_createElementNS = this.$wbwindow.document.createElementNS;
  var wombat = this;

  var createElementNS = function createElementNS(namespaceURI, qualifiedName) {
    return orig_createElementNS.call(
      wombat.proxyToObj(this),
      wombat.extractOriginalURL(namespaceURI),
      qualifiedName
    );
  };

  this.$wbwindow.Document.prototype.createElementNS = createElementNS;
  this.$wbwindow.document.createElementNS = createElementNS;
};

/**
 * Applies an override to Element.insertAdjacentHTML in order to ensure
 * that the strings of HTML to be inserted are rewritten and to
 * Element.insertAdjacentElement in order to ensure that the Elements to
 * be inserted are rewritten
 */
Wombat.prototype.initInsertAdjacentElementHTMLOverrides = function() {
  var Element = this.$wbwindow.Element;
  if (!Element || !Element.prototype) return;
  var elementProto = Element.prototype;
  var rewriteFn = this.rewriteInsertAdjHTMLOrElemArgs;
  if (elementProto.insertAdjacentHTML) {
    var origInsertAdjacentHTML = elementProto.insertAdjacentHTML;
    elementProto.insertAdjacentHTML = function insertAdjacentHTML(
      position,
      text
    ) {
      return rewriteFn(this, origInsertAdjacentHTML, position, text, true);
    };
  }
  if (elementProto.insertAdjacentElement) {
    var origIAdjElem = elementProto.insertAdjacentElement;
    elementProto.insertAdjacentElement = function insertAdjacentElement(
      position,
      element
    ) {
      return rewriteFn(this, origIAdjElem, position, element, false);
    };
  }
};

/**
 * Applies overrides to Node.[appendChild, insertBefore, replaceChild] and
 * [Element, DocumentFragment].[append, prepend) in order to ensure the that
 * the elements added by these functions are rewritten.
 * Also applies an override to the Node.ownerDocument, HTMLHtmlElement.parentNode,
 * and Event.target getter functions do not return a JS Proxy object used by wombat
 * @see https://www.w3.org/TR/dom/#node
 */
Wombat.prototype.initDomOverride = function() {
  var Node = this.$wbwindow.Node;
  if (Node && Node.prototype) {
    var rewriteFn = this.rewriteNodeFuncArgs;
    if (Node.prototype.appendChild) {
      var originalAppendChild = Node.prototype.appendChild;
      Node.prototype.appendChild = function appendChild(newNode, oldNode) {
        return rewriteFn(this, originalAppendChild, newNode, oldNode);
      };
    }
    if (Node.prototype.insertBefore) {
      var originalInsertBefore = Node.prototype.insertBefore;
      Node.prototype.insertBefore = function insertBefore(newNode, oldNode) {
        return rewriteFn(this, originalInsertBefore, newNode, oldNode);
      };
    }
    if (Node.prototype.replaceChild) {
      var originalReplaceChild = Node.prototype.replaceChild;
      Node.prototype.replaceChild = function replaceChild(newNode, oldNode) {
        return rewriteFn(this, originalReplaceChild, newNode, oldNode);
      };
    }
    this.overridePropToProxy(Node.prototype, 'ownerDocument');
    this.overridePropToProxy(
      this.$wbwindow.HTMLHtmlElement.prototype,
      'parentNode'
    );
    this.overridePropToProxy(this.$wbwindow.Event.prototype, 'target');
  }

  if (this.$wbwindow.Element && this.$wbwindow.Element.prototype) {
    this.overrideParentNodeAppendPrepend(this.$wbwindow.Element);
    this.overrideChildNodeInterface(this.$wbwindow.Element, false);
  }

  if (
    this.$wbwindow.DocumentFragment &&
    this.$wbwindow.DocumentFragment.prototype
  ) {
    this.overrideParentNodeAppendPrepend(this.$wbwindow.DocumentFragment);
  }
};

/**
 * Applies overrides to document.referrer, document.origin, document.domain, and
 * window.origin in order to ensure their getters and setters behave as expected
 * on the live web
 * @param {Document} $document
 */
Wombat.prototype.initDocOverrides = function($document) {
  if (!Object.defineProperty) return;

  // referrer
  this.overridePropExtract($document, 'referrer');

  // origin
  this.defGetterProp($document, 'origin', function origin() {
    return this.WB_wombat_location.origin;
  });
  // https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/origin, chrome 59+ and ff 54+
  this.defGetterProp(this.$wbwindow, 'origin', function origin() {
    return this.WB_wombat_location.origin;
  });

  var wombat = this;
  // domain
  var domain_setter = function domain(val) {
    var loc = this.WB_wombat_location;
    if (loc && wombat.endsWith(loc.hostname, val)) {
      this.__wb_domain = val;
    }
  };

  var domain_getter = function domain() {
    return this.__wb_domain || this.WB_wombat_location.hostname;
  };

  this.defProp($document, 'domain', domain_setter, domain_getter);
};

/**
 * Apples overrides to document.[write, writeln, open, close] in order
 * to ensure that the values they operate on or create are rewritten and
 * wombat is initialized in the new documents/windows.
 * @see https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html
 * @see https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html#dom-document-open-window
 * @see https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html#dom-document-close
 * @see https://html.spec.whatwg.org/multipage/dom.html#dom-document-body
 */
Wombat.prototype.initDocWriteOpenCloseOverride = function() {
  if (!this.$wbwindow.DOMParser) {
    return;
  }

  // for both document.write and document.writeln, all arguments are treated as a string and concatenated together
  // https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html

  var DocumentProto = this.$wbwindow.Document.prototype;
  var $wbDocument = this.$wbwindow.document;
  var docWriteWritelnRWFn = this.rewriteDocWriteWriteln;

  // Write
  var orig_doc_write = $wbDocument.write;
  var new_write = function write() {
    return docWriteWritelnRWFn(this, orig_doc_write, arguments);
  };
  $wbDocument.write = new_write;
  DocumentProto.write = new_write;

  // Writeln
  var orig_doc_writeln = $wbDocument.writeln;
  var new_writeln = function writeln() {
    return docWriteWritelnRWFn(this, orig_doc_writeln, arguments);
  };
  $wbDocument.writeln = new_writeln;
  DocumentProto.writeln = new_writeln;

  var wombat = this;

  // Open
  var orig_doc_open = $wbDocument.open;
  var new_open = function open() {
    var thisObj = wombat.proxyToObj(this);
    var res;
    if (arguments.length === 3) {
      // we have the case where a new window will be opened
      // https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html#dom-document-open-window
      var rwUrl = wombat.rewriteUrl(arguments[0], false, 'mp_');
      res = orig_doc_open.call(thisObj, rwUrl, arguments[1], arguments[2]);
      wombat.initNewWindowWombat(res, rwUrl);
    } else {
      res = orig_doc_open.call(thisObj);
      wombat.initNewWindowWombat(thisObj.defaultView);
    }
    return res;
  };

  $wbDocument.open = new_open;
  DocumentProto.open = new_open;

  // we override close in order to ensure wombat is init'd
  // https://html.spec.whatwg.org/multipage/dynamic-markup-insertion.html#dom-document-close
  var originalClose = $wbDocument.close;
  var newClose = function close() {
    var thisObj = wombat.proxyToObj(this);
    wombat.initNewWindowWombat(thisObj.defaultView);
    if (originalClose.__WB_orig_apply) {
      return originalClose.__WB_orig_apply(thisObj, arguments);
    }
    return originalClose.apply(thisObj, arguments);
  };

  $wbDocument.close = newClose;
  DocumentProto.close = newClose;

  // we override the setter for document.body because it is settable
  // to either an instance of HTMLBodyElement or HTMLFrameSetElement and
  // there are ways to get un-rewritten elements into replay we must allow
  // https://html.spec.whatwg.org/multipage/dom.html#dom-document-body
  var oBodyGetter = this.getOrigGetter(DocumentProto, 'body');
  var oBodySetter = this.getOrigSetter(DocumentProto, 'body');
  if (oBodyGetter && oBodySetter) {
    this.defProp(
      DocumentProto,
      'body',
      function body(newBody) {
        if (
          newBody &&
          (newBody instanceof HTMLBodyElement ||
            newBody instanceof HTMLFrameSetElement)
        ) {
          wombat.rewriteElemComplete(newBody);
        }
        return oBodySetter.call(wombat.proxyToObj(this), newBody);
      },
      oBodyGetter
    );
  }
};

/**
 * Inits wombat in the supplied iframe
 * @param {HTMLIFrameElement} iframe
 */
Wombat.prototype.initIframeWombat = function(iframe) {
  var win;

  if (iframe._get_contentWindow) {
    win = iframe._get_contentWindow.call(iframe); // eslint-disable-line no-useless-call
  } else {
    win = iframe.contentWindow;
  }

  try {
    if (!win || win === this.$wbwindow || win._skip_wombat || win._wb_wombat) {
      return;
    }
  } catch (e) {
    return;
  }

  // var src = iframe.src;
  var src = this.wb_getAttribute.call(iframe, 'src');

  this.initNewWindowWombat(win, src);
};

/**
 * Initializes wombat in the supplied window IFF the src URL of the window is
 * not the empty string, about:blank, or a "javascript:" URL
 * @param {Window} win
 * @param {string} [src]
 */
Wombat.prototype.initNewWindowWombat = function(win, src) {
  this.ensureServerSideInjectsExistOnWindow(win);
  if (!win || win._wb_wombat) return;
  if (
    !src ||
    src === '' ||
    this.startsWith(src, 'about:') ||
    src.indexOf('javascript:') >= 0
  ) {
    // win._WBWombat = wombat_internal(win);
    // win._wb_wombat = new win._WBWombat(wb_info);
    var wombat = new Wombat(win, this.wb_info);
    win._wb_wombat = wombat.wombatInit();
  } else {
    // These should get overriden when content is loaded, but just in case...
    // win._WB_wombat_location = win.location;
    // win.document.WB_wombat_location = win.document.location;
    // win._WB_wombat_top = $wbwindow.WB_wombat_top;

    this.initProtoPmOrigin(win);
    this.initPostMessageOverride(win);
    this.initMessageEventOverride(win);
  }
};

/**
 * Applies an override to either window.[setTimeout, setInterval] functions
 * in order to ensure that usage such as [setTimeout|setInterval]('document.location.href = "xyz.com"', time)
 * behaves as expected during replay.
 *
 * In this case the supplied string is eval'd in the current context skipping
 * the surrounding scope
 */
Wombat.prototype.initTimeoutIntervalOverrides = function() {
  var rewriteFn = this.rewriteSetTimeoutInterval;
  if (this.$wbwindow.setTimeout && !this.$wbwindow.setTimeout.__$wbpatched$__) {
    var originalSetTimeout = this.$wbwindow.setTimeout;
    this.$wbwindow.setTimeout = function setTimeout() {
      return rewriteFn(this, originalSetTimeout, arguments);
    };
    this.$wbwindow.setTimeout.__$wbpatched$__ = true;
  }

  if (
    this.$wbwindow.setInterval &&
    !this.$wbwindow.setInterval.__$wbpatched$__
  ) {
    var originalSetInterval = this.$wbwindow.setInterval;
    this.$wbwindow.setInterval = function setInterval() {
      return rewriteFn(this, originalSetInterval, arguments);
    };
    this.$wbwindow.setInterval.__$wbpatched$__ = true;
  }
};

/**
 * Applies an overrides to the constructor of window.[Worker, SharedWorker] in
 * order to ensure that the URL argument is rewritten.
 *
 * Applies an override to ServiceWorkerContainer.register in order to ensure
 * that the URLs used in ServiceWorker registration are rewritten.
 *
 * Applies an override to Worklet.addModule in order to ensure that URL
 * to the worklet module is rewritten
 * @see https://html.spec.whatwg.org/multipage/workers.html
 * @see https://w3c.github.io/ServiceWorker/
 * @see https://drafts.css-houdini.org/worklets/#worklet
 */
Wombat.prototype.initWorkerOverrides = function() {
  var wombat = this;

  if (this.$wbwindow.Worker && !this.$wbwindow.Worker._wb_worker_overriden) {
    // Worker unrewrite postMessage
    var orig_worker = this.$wbwindow.Worker;
    this.$wbwindow.Worker = (function(Worker_) {
      return function Worker(url, options) {
        wombat.domConstructorErrorChecker(this, 'Worker', arguments);
        return new Worker_(wombat.rewriteWorker(url), options);
      };
    })(orig_worker);

    this.$wbwindow.Worker.prototype = orig_worker.prototype;
    Object.defineProperty(this.$wbwindow.Worker.prototype, 'constructor', {
      value: this.$wbwindow.Worker
    });
    this.$wbwindow.Worker._wb_worker_overriden = true;
  }

  if (
    this.$wbwindow.SharedWorker &&
    !this.$wbwindow.SharedWorker.__wb_sharedWorker_overriden
  ) {
    // per https://html.spec.whatwg.org/multipage/workers.html#sharedworker
    var oSharedWorker = this.$wbwindow.SharedWorker;
    this.$wbwindow.SharedWorker = (function(SharedWorker_) {
      return function SharedWorker(url, options) {
        wombat.domConstructorErrorChecker(this, 'SharedWorker', arguments);
        return new SharedWorker_(wombat.rewriteWorker(url), options);
      };
    })(oSharedWorker);

    this.$wbwindow.SharedWorker.prototype = oSharedWorker.prototype;
    Object.defineProperty(
      this.$wbwindow.SharedWorker.prototype,
      'constructor',
      {
        value: this.$wbwindow.SharedWorker
      }
    );
    this.$wbwindow.SharedWorker.__wb_sharedWorker_overriden = true;
  }

  if (
    this.$wbwindow.ServiceWorkerContainer &&
    this.$wbwindow.ServiceWorkerContainer.prototype &&
    this.$wbwindow.ServiceWorkerContainer.prototype.register
  ) {
    // https://w3c.github.io/ServiceWorker/
    var orig_register = this.$wbwindow.ServiceWorkerContainer.prototype
      .register;
    this.$wbwindow.ServiceWorkerContainer.prototype.register = function register(
      scriptURL,
      options
    ) {
      var newScriptURL = new URL(scriptURL, wombat.$wbwindow.document.baseURI)
        .href;
      var mod = wombat.getPageUnderModifier();
      if (options && options.scope) {
        options.scope = wombat.rewriteUrl(options.scope, false, mod);
      } else {
        options = { scope: wombat.rewriteUrl('/', false, mod) };
      }
      return orig_register.call(
        this,
        wombat.rewriteUrl(newScriptURL, false, 'sw_'),
        options
      );
    };
  }

  if (
    this.$wbwindow.Worklet &&
    this.$wbwindow.Worklet.prototype &&
    this.$wbwindow.Worklet.prototype.addModule &&
    !this.$wbwindow.Worklet.__wb_workerlet_overriden
  ) {
    // https://developer.mozilla.org/en-US/docs/Web/API/Worklet/addModule
    var oAddModule = this.$wbwindow.Worklet.prototype.addModule;
    this.$wbwindow.Worklet.prototype.addModule = function addModule(
      moduleURL,
      options
    ) {
      var rwModuleURL = wombat.rewriteUrl(moduleURL, false, 'js_');
      return oAddModule.call(this, rwModuleURL, options);
    };
    this.$wbwindow.Worklet.__wb_workerlet_overriden = true;
  }
};

/**
 * Applies overrides to the getter setter functions of the supplied object
 * for the properties defined in {@link Wombat#URL_PROPS} IFF
 * Object.defineProperty is defined
 * @param {Object} loc
 * @param {function} oSetter
 * @param {function} oGetter
 */
Wombat.prototype.initLocOverride = function(loc, oSetter, oGetter) {
  if (Object.defineProperty) {
    for (var i = 0; i < this.URL_PROPS.length; i++) {
      var prop = this.URL_PROPS[i];
      this.defProp(
        loc,
        prop,
        this.makeSetLocProp(prop, oSetter, oGetter),
        this.makeGetLocProp(prop, oGetter),
        true
      );
    }
  }
};

/**
 * Initialized WombatLocation on the supplied window object and adds the
 * __WB_pmw function on the window, as well as, defines WB_wombat_location
 * as property on the prototype of Object and adds the _WB_wombat_location
 * and __WB_check_loc properties to the supplied window
 * @param {Window} win
 */
Wombat.prototype.initWombatLoc = function(win) {
  if (!win || (win.WB_wombat_location && win.document.WB_wombat_location)) {
    return;
  }

  // Location
  var wombat_location = new WombatLocation(win.location, this);

  if (Object.defineProperty) {
    var setter = function location(value) {
      var loc =
        this._WB_wombat_location ||
        (this.defaultView && this.defaultView._WB_wombat_location) ||
        this.location;

      if (loc) {
        loc.href = value;
      }
    };

    var getter = function location() {
      return (
        this._WB_wombat_location ||
        (this.defaultView && this.defaultView._WB_wombat_location) ||
        this.location
      );
    };

    this.defProp(win.Object.prototype, 'WB_wombat_location', setter, getter);

    this.initProtoPmOrigin(win);

    win._WB_wombat_location = wombat_location;
  } else {
    win.WB_wombat_location = wombat_location;

    // Check quickly after page load
    setTimeout(this.checkAllLocations, 500);

    // Check periodically every few seconds
    setInterval(this.checkAllLocations, 500);
  }
};

/**
 * Adds the __WB_pmw property to prototype of Object and adds the
 * __WB_check_loc property to window
 * @param {Window} win
 */
Wombat.prototype.initProtoPmOrigin = function(win) {
  if (win.Object.prototype.__WB_pmw) return;

  var pm_origin = function pm_origin(origin_window) {
    this.__WB_source = origin_window;
    return this;
  };

  try {
    win.Object.defineProperty(win.Object.prototype, '__WB_pmw', {
      get: function() {
        return pm_origin;
      },
      set: function() {},
      configurable: true,
      enumerable: false
    });
  } catch (e) {}

  win.__WB_check_loc = function(loc) {
    if (loc instanceof Location || loc instanceof WombatLocation) {
      return this.WB_wombat_location;
    } else {
      return {};
    }
  };
};

/**
 * Adds listeners for `message` and `hashchange` to window of the browser context wombat is in
 * in order to ensure that actual top (archive top frame containing the replay iframe)
 * browser history is updated IFF the history manipulation happens in the replay top
 */
Wombat.prototype.initHashChange = function() {
  if (!this.$wbwindow.__WB_top_frame) return;

  var wombat = this;

  var receive_hash_change = function receive_hash_change(event) {
    if (!event.data || !event.data.from_top) {
      return;
    }

    var message = event.data.message;

    if (!message.wb_type) return;

    if (message.wb_type === 'outer_hashchange') {
      if (wombat.$wbwindow.location.hash != message.hash) {
        wombat.$wbwindow.location.hash = message.hash;
      }
    }
  };

  var send_hash_change = function send_hash_change() {
    var message = {
      wb_type: 'hashchange',
      hash: wombat.$wbwindow.location.hash
    };

    wombat.sendTopMessage(message);
  };

  this.$wbwindow.addEventListener('message', receive_hash_change);

  this.$wbwindow.addEventListener('hashchange', send_hash_change);
};

/**
 * Overrides window.postMessage in order to ensure that messages sent
 * via this function are routed to the correct window, especially that
 * messages sent to the "top frame" do not go to archive top but replay top.
 *
 * This function also applies an override to EventTarget.[addEventListener, removeEventListener]
 * to ensure that listening to events behaves correctly during replay.
 *
 * This function is the place where the `onmessage` and `onstorage` setter functions
 * are overriden.
 * @param {Window} $wbwindow
 */
Wombat.prototype.initPostMessageOverride = function($wbwindow) {
  if (!$wbwindow.postMessage || $wbwindow.__orig_postMessage) {
    return;
  }

  var orig = $wbwindow.postMessage;
  var wombat = this;

  $wbwindow.__orig_postMessage = orig;

  // use this_obj.__WB_source not window to fix google calendar embeds, pm_origin sets this.__WB_source
  var postmessage_rewritten = function postMessage(
    message,
    targetOrigin,
    transfer,
    from_top
  ) {
    var from;
    var src_id;
    var this_obj = wombat.proxyToObj(this);
    if (this_obj.__WB_source && this_obj.__WB_source.WB_wombat_location) {
      var source = this_obj.__WB_source;

      from = source.WB_wombat_location.origin;
      if (!this_obj.__WB_win_id) {
        this_obj.__WB_win_id = {};
        this_obj.__WB_counter = 0;
      }

      if (!source.__WB_id) {
        var id = this_obj.__WB_counter;
        source.__WB_id = id + source.WB_wombat_location.href;
        this_obj.__WB_counter += 1;
      }
      this_obj.__WB_win_id[source.__WB_id] = source;

      src_id = source.__WB_id;

      this_obj.__WB_source = undefined;
    } else {
      from = window.WB_wombat_location.origin;
    }

    var to_origin = targetOrigin;

    // if passed in origin is the replay (rewriting missed somewhere?)
    // set origin to current 'from' origin
    if (to_origin === this_obj.location.origin) {
      to_origin = from;
    }

    var new_message = {
      from: from,
      to_origin: to_origin,
      src_id: src_id,
      message: message,
      from_top: from_top
    };

    // set to 'real' origin if not '*'
    if (targetOrigin !== '*') {
      // if target origin is null (about:blank) or empty, don't pass event at all
      // as it would never succeed
      if (
        this_obj.location.origin === 'null' ||
        this_obj.location.origin === ''
      ) {
        return;
      }
      // set to actual (rewritten) origin
      targetOrigin = this_obj.location.origin;
    }

    // console.log(`Sending ${from} -> ${to_origin} (${targetOrigin}) ${message}`);

    return orig.call(this_obj, new_message, targetOrigin, transfer);
  };

  $wbwindow.postMessage = postmessage_rewritten;
  $wbwindow.Window.prototype.postMessage = postmessage_rewritten;

  var eventTarget = null;
  if ($wbwindow.EventTarget && $wbwindow.EventTarget.prototype) {
    eventTarget = $wbwindow.EventTarget.prototype;
  } else {
    eventTarget = $wbwindow;
  }

  // ADD
  var _oAddEventListener = eventTarget.addEventListener;
  eventTarget.addEventListener = function addEventListener(
    type,
    listener,
    useCapture
  ) {
    var obj = wombat.proxyToObj(this);
    var rwListener;
    if (type === 'message') {
      rwListener = wombat.message_listeners.add_or_get(listener, function() {
        return wrapEventListener(listener, obj, wombat);
      });
    } else if (type === 'storage') {
      wombat.storage_listeners.add_or_get(listener, function() {
        return wrapSameOriginEventListener(listener, obj);
      });
    } else {
      rwListener = listener;
    }
    if (rwListener) {
      return _oAddEventListener.call(obj, type, rwListener, useCapture);
    }
  };

  // REMOVE
  var _oRemoveEventListener = eventTarget.removeEventListener;
  eventTarget.removeEventListener = function removeEventListener(
    type,
    listener,
    useCapture
  ) {
    var obj = wombat.proxyToObj(this);
    var rwListener;

    if (type === 'message') {
      rwListener = wombat.message_listeners.remove(listener);
    } else if (type === 'storage') {
      wombat.storage_listeners.remove(listener);
    } else {
      rwListener = listener;
    }

    if (rwListener) {
      return _oRemoveEventListener.call(obj, type, rwListener, useCapture);
    }
  };

  // ONMESSAGE & ONSTORAGE
  var override_on_prop = function(onevent, wrapperFN) {
    // var orig_getter = _wombat.getOrigGetter($wbwindow, onevent)
    var orig_setter = wombat.getOrigSetter($wbwindow, onevent);

    var setter = function(value) {
      this['__orig_' + onevent] = value;
      var obj = wombat.proxyToObj(this);
      var listener = value ? wrapperFN(value, obj, wombat) : value;
      return orig_setter.call(obj, listener);
    };

    var getter = function() {
      return this['__orig_' + onevent];
    };

    wombat.defProp($wbwindow, onevent, setter, getter);
  };
  override_on_prop('onmessage', wrapEventListener);
  override_on_prop('onstorage', wrapSameOriginEventListener);
};

/**
 * Applies overrides to the MessageEvent.[target, srcElement, currentTarget, eventPhase, path, source]
 * in order to ensure they are not a JS Proxy used by wombat
 * @param {Window} $wbwindow
 */
Wombat.prototype.initMessageEventOverride = function($wbwindow) {
  if (!$wbwindow.MessageEvent || $wbwindow.MessageEvent.prototype.__extended) {
    return;
  }
  this.addEventOverride('target');
  this.addEventOverride('srcElement');
  this.addEventOverride('currentTarget');
  this.addEventOverride('eventPhase');
  this.addEventOverride('path');
  this.overridePropToProxy($wbwindow.MessageEvent.prototype, 'source');
  $wbwindow.MessageEvent.prototype.__extended = true;
};

/**
 * Applies overrides to the constructors
 *  - UIEvent
 *  - MouseEvent
 *  - TouchEvent
 *  - KeyboardEvent
 *  - WheelEvent
 *  - InputEvent
 *  - CompositionEvent
 *
 * in order to ensure the proper behavior of the events when wombat is using
 * an JS Proxy
 */
Wombat.prototype.initUIEventsOverrides = function() {
  this.overrideAnUIEvent('UIEvent');
  this.overrideAnUIEvent('MouseEvent');
  this.overrideAnUIEvent('TouchEvent');
  this.overrideAnUIEvent('FocusEvent');
  this.overrideAnUIEvent('KeyboardEvent');
  this.overrideAnUIEvent('WheelEvent');
  this.overrideAnUIEvent('InputEvent');
  this.overrideAnUIEvent('CompositionEvent');
};

/**
 * Applies an override to window.open in order to ensure the URL argument is rewritten.
 * Also applies the same override to the open function of all frames returned by
 * window.frames
 */
Wombat.prototype.initOpenOverride = function() {
  var orig = this.$wbwindow.open;

  if (this.$wbwindow.Window.prototype.open) {
    orig = this.$wbwindow.Window.prototype.open;
  }

  var wombat = this;

  var open_rewritten = function open(strUrl, strWindowName, strWindowFeatures) {
    var rwStrUrl = wombat.rewriteUrl(strUrl, false, '');
    var res = orig.call(
      wombat.proxyToObj(this),
      rwStrUrl,
      strWindowName,
      strWindowFeatures
    );
    wombat.initNewWindowWombat(res, rwStrUrl);
    return res;
  };

  this.$wbwindow.open = open_rewritten;

  if (this.$wbwindow.Window.prototype.open) {
    this.$wbwindow.Window.prototype.open = open_rewritten;
  }

  for (var i = 0; i < this.$wbwindow.frames.length; i++) {
    try {
      this.$wbwindow.frames[i].open = open_rewritten;
    } catch (e) {
      console.log(e);
    }
  }
};

/**
 * Applies an override to the getter and setter functions of document.cookie
 * in order to ensure that cookies are rewritten
 */
Wombat.prototype.initCookiesOverride = function() {
  var orig_get_cookie = this.getOrigGetter(this.$wbwindow.document, 'cookie');
  var orig_set_cookie = this.getOrigSetter(this.$wbwindow.document, 'cookie');

  if (!orig_get_cookie) {
    orig_get_cookie = this.getOrigGetter(
      this.$wbwindow.Document.prototype,
      'cookie'
    );
  }
  if (!orig_set_cookie) {
    orig_set_cookie = this.getOrigSetter(
      this.$wbwindow.Document.prototype,
      'cookie'
    );
  }

  var rwCookieReplacer = function(m, d1) {
    var date = new Date(d1);
    if (isNaN(date.getTime())) {
      return 'Expires=Thu,| 01 Jan 1970 00:00:00 GMT';
    }
    var finalDate = new Date(date.getTime() + Date.__WB_timediff);
    return 'Expires=' + finalDate.toUTCString().replace(',', ',|');
  };

  var wombat = this;
  var set_cookie = function cookie(value) {
    if (!value) return;
    var newValue = value.replace(wombat.cookie_expires_regex, rwCookieReplacer);
    var cookies = newValue.split(wombat.SetCookieRe);
    for (var i = 0; i < cookies.length; i++) {
      cookies[i] = wombat.rewriteCookie(cookies[i]);
    }
    return orig_set_cookie.call(wombat.proxyToObj(this), cookies.join(','));
  };

  var get_cookie = function cookie() {
    return orig_get_cookie.call(wombat.proxyToObj(this));
  };

  this.defProp(this.$wbwindow.document, 'cookie', set_cookie, get_cookie);
};

/**
 * Applies an override to navigator.[registerProtocolHandler, unregisterProtocolHandler] in order to
 * ensure that the URI argument is rewritten
 */
Wombat.prototype.initRegisterUnRegPHOverride = function() {
  var wombat = this;
  var winNavigator = this.$wbwindow.navigator;
  if (winNavigator.registerProtocolHandler) {
    var orig_registerPH = winNavigator.registerProtocolHandler;
    winNavigator.registerProtocolHandler = function registerProtocolHandler(
      protocol,
      uri,
      title
    ) {
      return orig_registerPH.call(
        this,
        protocol,
        wombat.rewriteUrl(uri),
        title
      );
    };
  }

  if (winNavigator.unregisterProtocolHandler) {
    var origUnregPH = winNavigator.unregisterProtocolHandler;
    winNavigator.unregisterProtocolHandler = function unregisterProtocolHandler(
      scheme,
      url
    ) {
      return origUnregPH.call(this, scheme, wombat.rewriteUrl(url));
    };
  }
};

/**
 * Applies an override to navigator.sendBeacon in order to ensure that
 * the URL argument is rewritten. This ensures that when a page is rewritten
 * no information about who is viewing is leaked to the outside world
 */
Wombat.prototype.initBeaconOverride = function() {
  if (!this.$wbwindow.navigator.sendBeacon) return;
  var orig_sendBeacon = this.$wbwindow.navigator.sendBeacon;
  var wombat = this;
  this.$wbwindow.navigator.sendBeacon = function sendBeacon(url, data) {
    return orig_sendBeacon.call(this, wombat.rewriteUrl(url), data);
  };
};

/**
 * Applies an override to the constructor of the PresentationRequest interface object
 * in order to rewrite its URL(s) arguments
 * @see https://w3c.github.io/presentation-api/#constructing-a-presentationrequest
 */
Wombat.prototype.initPresentationRequestOverride = function() {
  if (
    this.$wbwindow.PresentationRequest &&
    this.$wbwindow.PresentationRequest.prototype
  ) {
    var wombat = this;
    var origPresentationRequest = this.$wbwindow.PresentationRequest;
    this.$wbwindow.PresentationRequest = (function(PresentationRequest_) {
      return function PresentationRequest(url) {
        wombat.domConstructorErrorChecker(
          this,
          'PresentationRequest',
          arguments
        );
        var rwURL = url;
        if (url != null) {
          if (Array.isArray(rwURL)) {
            for (var i = 0; i < rwURL.length; i++) {
              rwURL[i] = wombat.rewriteUrl(rwURL[i], true, 'mp_');
            }
          } else {
            rwURL = wombat.rewriteUrl(url, true, 'mp_');
          }
        }
        return new PresentationRequest_(rwURL);
      };
    })(this.$wbwindow.PresentationRequest);
    this.$wbwindow.PresentationRequest.prototype =
      origPresentationRequest.prototype;
    Object.defineProperty(
      this.$wbwindow.PresentationRequest.prototype,
      'constructor',
      {
        value: this.$wbwindow.PresentationRequest
      }
    );
  }
};

/**
 * Applies an override that disables the pages ability to send OS native
 * notifications. Also disables the ability of the replayed page to retrieve the geolocation
 * of the view.
 *
 * This is done in order to ensure that no malicious abuse of these functions
 * can happen during replay.
 */
Wombat.prototype.initDisableNotificationsGeoLocation = function() {
  if (window.Notification) {
    window.Notification.requestPermission = function requestPermission(
      callback
    ) {
      if (callback) {
        callback('denied');
      }

      return Promise.resolve('denied');
    };
  }

  var applyOverride = function(on) {
    if (!on) return;
    if (on.getCurrentPosition) {
      on.getCurrentPosition = function getCurrentPosition(
        success,
        error,
        options
      ) {
        if (error) {
          error({ code: 2, message: 'not available' });
        }
      };
    }
    if (on.watchPosition) {
      on.watchPosition = function watchPosition(success, error, options) {
        if (error) {
          error({ code: 2, message: 'not available' });
        }
      };
    }
  };
  if (window.geolocation) {
    applyOverride(window.geolocation);
  }
  if (window.navigator.geolocation) {
    applyOverride(window.navigator.geolocation);
  }
};

/**
 * Applies an override to window.[localStorage, sessionStorage] storage in order to ensure
 * that the replayed page can use both interfaces as expected during replay.
 */
Wombat.prototype.initStorageOverride = function() {
  this.addEventOverride('storageArea', this.$wbwindow.StorageEvent.prototype);

  var local;
  var session;
  var pLocal = 'localStorage';
  var pSession = 'sessionStorage';
  ThrowExceptions.yes = false;
  if (this.$wbwindow.Proxy) {
    var storageProxyHandler = function() {
      return {
        get: function(target, prop) {
          if (prop in target) return target[prop];
          return target.getItem(prop);
        },
        set: function(target, prop, value) {
          if (target.hasOwnProperty(prop)) return false;
          target.setItem(prop, value);
          return true;
        },
        getOwnPropertyDescriptor: function(target, prop) {
          return Object.getOwnPropertyDescriptor(target, prop);
        }
      };
    };
    local = new this.$wbwindow.Proxy(
      new Storage(this, pLocal),
      storageProxyHandler()
    );
    session = new this.$wbwindow.Proxy(
      new Storage(this, pSession),
      storageProxyHandler()
    );
  } else {
    local = new Storage(this, pLocal);
    session = new Storage(this, pSession);
  }

  this.defGetterProp(this.$wbwindow, pLocal, function localStorage() {
    return local;
  });

  this.defGetterProp(this.$wbwindow, pSession, function sessionStorage() {
    return session;
  });
  // ensure localStorage instanceof Storage works
  this.$wbwindow.Storage = Storage;
  ThrowExceptions.yes = true;
};

/**
 * Initializes the wombat window JS Proxy object IFF JS Proxies are available.
 * @param {Window} $wbwindow
 * @return {Proxy<Window>}
 */
Wombat.prototype.initWindowObjProxy = function($wbwindow) {
  if (!$wbwindow.Proxy) return undefined;

  var ownProps = this.getAllOwnProps($wbwindow);
  var funCache = {};
  var wombat = this;
  var windowProxy = new $wbwindow.Proxy(
    {},
    {
      get: function(target, prop) {
        switch (prop) {
          case 'top':
            return wombat.$wbwindow.WB_wombat_top._WB_wombat_obj_proxy;
          case 'parent':
            var realParent = $wbwindow.parent;
            if (realParent === $wbwindow.WB_wombat_top) {
              return $wbwindow.WB_wombat_top._WB_wombat_obj_proxy;
            }
            return realParent._WB_wombat_obj_proxy;
        }
        return wombat.defaultProxyGet($wbwindow, prop, ownProps, funCache);
      },
      set: function(target, prop, value) {
        switch (prop) {
          case 'location':
            $wbwindow.WB_wombat_location = value;
            return true;
          case 'postMessage':
          case 'document':
            return true;
        }
        try {
          if (!Reflect.set(target, prop, value)) {
            return false;
          }
        } catch (e) {}
        return Reflect.set($wbwindow, prop, value);
      },
      has: function(target, prop) {
        return prop in $wbwindow;
      },
      ownKeys: function(target) {
        return Object.getOwnPropertyNames($wbwindow).concat(
          Object.getOwnPropertySymbols($wbwindow)
        );
      },
      getOwnPropertyDescriptor: function(target, key) {
        // first try the underlying object's descriptor
        // (to match defineProperty() behavior)
        var descriptor = Object.getOwnPropertyDescriptor(target, key);
        if (!descriptor) {
          descriptor = Object.getOwnPropertyDescriptor($wbwindow, key);
          // if using window's descriptor, must ensure it's configurable
          if (descriptor) {
            descriptor.configurable = true;
          }
        }
        return descriptor;
      },
      getPrototypeOf: function(target) {
        return Object.getPrototypeOf($wbwindow);
      },
      setPrototypeOf: function(target, newProto) {
        return false;
      },
      isExtensible: function(target) {
        return Object.isExtensible($wbwindow);
      },
      preventExtensions: function(target) {
        Object.preventExtensions($wbwindow);
        return true;
      },
      deleteProperty: function(target, prop) {
        var propDescriptor = Object.getOwnPropertyDescriptor($wbwindow, prop);
        if (propDescriptor === undefined) {
          return true;
        }
        if (propDescriptor.configurable === false) {
          return false;
        }
        delete target[prop];
        delete $wbwindow[prop];
        return true;
      },
      defineProperty: function(target, prop, desc) {
        var ndesc = desc || {};
        if (!ndesc.value && !ndesc.get) {
          ndesc.value = $wbwindow[prop];
        }
        Reflect.defineProperty($wbwindow, prop, ndesc);
        return Reflect.defineProperty(target, prop, ndesc);
      }
    }
  );
  $wbwindow._WB_wombat_obj_proxy = windowProxy;
  return windowProxy;
};

/**
 * Initializes the wombat document JS Proxy object IFF JS Proxies are available.
 * This function also applies the {@link initDocOverrides} overrides regardless
 * if JS Proxies are available.
 * @param {Document} $document
 * @return {Proxy<Document>}
 */
Wombat.prototype.initDocumentObjProxy = function($document) {
  this.initDocOverrides($document);
  if (!this.$wbwindow.Proxy) return undefined;
  var funCache = {};
  var ownProps = this.getAllOwnProps($document);
  var wombat = this;
  var documentProxy = new this.$wbwindow.Proxy($document, {
    get: function(target, prop) {
      return wombat.defaultProxyGet($document, prop, ownProps, funCache);
    },
    set: function(target, prop, value) {
      if (prop === 'location') {
        $document.WB_wombat_location = value;
      } else {
        target[prop] = value;
      }
      return true;
    }
  });
  $document._WB_wombat_obj_proxy = documentProxy;
  return documentProxy;
};

/**
 * Initializes and starts the auto-fetch worker IFF wbUseAFWorker is true
 */
Wombat.prototype.initAutoFetchWorker = function() {
  if (!this.wbUseAFWorker) return;
  var af = new AutoFetcher(this, {
    isTop: this.$wbwindow === this.$wbwindow.__WB_replay_top,
    workerURL:
      (this.wb_info.auto_fetch_worker_prefix || this.wb_info.static_prefix) +
      'autoFetchWorker.js?init=' +
      encodeURIComponent(
        JSON.stringify({
          mod: this.wb_info.mod,
          prefix: this.wb_abs_prefix,
          rwRe: this.wb_unrewrite_rx.source
        })
      )
  });
  this.WBAutoFetchWorker = af;
  this.$wbwindow.$WBAutoFetchWorker$ = af;
  var wombat = this;
  this.utilFns.wbSheetMediaQChecker = function checkStyle() {
    // used only for link[rel='stylesheet'] so we remove our listener
    wombat._removeEventListener(
      this,
      'load',
      wombat.utilFns.wbSheetMediaQChecker
    );
    // check no op condition
    if (this.sheet == null) return;
    // defer extraction to be nice :)
    if (wombat.WBAutoFetchWorker) {
      wombat.WBAutoFetchWorker.deferredSheetExtraction(this.sheet);
    }
  };
};

/**
 * Initializes the listener for when the document.readyState is "complete" in
 * order to send archive top the information about the title of the page and
 * have it add any favicons of the replayed page to its own markup.
 *
 * The wb_type="load" message is sent to archive top IFF the page it originates
 * is replay top
 * @param {Object} wbinfo
 */
Wombat.prototype.initTopFrameNotify = function(wbinfo) {
  var wombat = this;

  var notify_top = function notify_top(event) {
    if (!wombat.$wbwindow.__WB_top_frame) {
      var hash = wombat.$wbwindow.location.hash;
      wombat.$wbwindow.location.replace(wbinfo.top_url + hash);
      return;
    }

    if (!wombat.$wbwindow.WB_wombat_location) return;

    var url = wombat.$wbwindow.WB_wombat_location.href;

    if (
      typeof url !== 'string' ||
      url === 'about:blank' ||
      url.indexOf('javascript:') === 0
    ) {
      return;
    }

    if (
      wombat.$wbwindow.document.readyState === 'complete' &&
      wombat.wbUseAFWorker &&
      wombat.WBAutoFetchWorker
    ) {
      wombat.WBAutoFetchWorker.extractFromLocalDoc();
    }

    if (wombat.$wbwindow !== wombat.$wbwindow.__WB_replay_top) {
      return;
    }

    var icons = [];
    var hicons = wombat.$wbwindow.document.querySelectorAll(
      "link[rel*='icon']"
    );

    for (var i = 0; i < hicons.length; i++) {
      var hicon = hicons[i];
      icons.push({
        rel: hicon.rel,
        href: wombat.wb_getAttribute.call(hicon, 'href')
      });
    }

    var message = {
      icons: icons,
      url: wombat.$wbwindow.WB_wombat_location.href,
      ts: wombat.wb_info.timestamp,
      request_ts: wombat.wb_info.request_ts,
      is_live: wombat.wb_info.is_live,
      title: wombat.$wbwindow.document ? wombat.$wbwindow.document.title : '',
      readyState: wombat.$wbwindow.document.readyState,
      wb_type: 'load'
    };

    wombat.sendTopMessage(message);
  };

  if (this.$wbwindow.document.readyState === 'complete') {
    notify_top();
  } else if (this.$wbwindow.addEventListener) {
    this.$wbwindow.document.addEventListener('readystatechange', notify_top);
  } else if (this.$wbwindow.attachEvent) {
    this.$wbwindow.document.attachEvent('onreadystatechange', notify_top);
  }
};

/**
 * Initialises the _WB_replay_top and _WB_top_frame properties on window
 * @param {Window} $wbwindow
 */
Wombat.prototype.initTopFrame = function($wbwindow) {
  // proxy mode
  if (this.wb_is_proxy) {
    $wbwindow.__WB_replay_top = $wbwindow.top;
    $wbwindow.__WB_top_frame = undefined;
    return;
  }

  var next_parent = function(win) {
    try {
      if (!win) return false;
      // if no wbinfo, see if _wb_wombat was set (eg. if about:blank page)
      if (!win.wbinfo) {
        return win._wb_wombat != null;
      } else {
        // otherwise, ensure that it is not a top container frame
        return win.wbinfo.is_framed;
      }
    } catch (e) {
      return false;
    }
  };

  var replay_top = $wbwindow;
  while (replay_top.parent != replay_top && next_parent(replay_top.parent)) {
    replay_top = replay_top.parent;
  }

  $wbwindow.__WB_replay_top = replay_top;

  var real_parent = replay_top.__WB_orig_parent || replay_top.parent;
  // Check to ensure top frame is different window and directly accessible (later refactor to support postMessage)
  if (real_parent == $wbwindow || !this.wb_info.is_framed) {
    real_parent = undefined;
  }

  if (real_parent) {
    $wbwindow.__WB_top_frame = real_parent;
    this.initFrameElementOverride($wbwindow);
  } else {
    $wbwindow.__WB_top_frame = undefined;
  }

  // Fix .parent only if not embeddable, otherwise leave for accessing embedding window
  if (!this.wb_opts.embedded && replay_top == $wbwindow) {
    if (this.wbUseAFWorker) {
      var wombat = this;
      this.$wbwindow.addEventListener(
        'message',
        function(event) {
          if (
            event.data &&
            event.data.wb_type === 'aaworker' &&
            wombat.WBAutoFetchWorker
          ) {
            wombat.WBAutoFetchWorker.postMessage(event.data.msg);
          }
        },
        false
      );
    }
    $wbwindow.__WB_orig_parent = $wbwindow.parent;
    $wbwindow.parent = replay_top;
  }
};

/**
 * Applies an override to window.frameElement IFF the supplied windows
 * __WB_replay_top property is equal to the window object of the browser context
 * wombat is currently operating in
 * @param {Window} $wbwindow
 */
Wombat.prototype.initFrameElementOverride = function($wbwindow) {
  if (!Object.defineProperty) return;
  // Also try disabling frameElement directly, though may no longer be supported in all browsers
  if (
    this.proxyToObj($wbwindow.__WB_replay_top) == this.proxyToObj($wbwindow)
  ) {
    try {
      Object.defineProperty($wbwindow, 'frameElement', {
        value: null,
        configurable: false
      });
    } catch (e) {}
  }
};

/**
 * Adds the WB_wombat_top property to the prototype of Object
 * @param {Window} $wbwindow
 */
Wombat.prototype.initWombatTop = function($wbwindow) {
  if (!Object.defineProperty) return;

  // from http://stackoverflow.com/a/6229603
  var isWindow = function isWindow(obj) {
    if (typeof window.constructor === 'undefined') {
      return obj instanceof window.constructor;
    }
    return obj.window == obj;
  };

  var getter = function top() {
    if (this.__WB_replay_top) {
      return this.__WB_replay_top;
    } else if (isWindow(this)) {
      return this;
    }
    return this.top;
  };

  var setter = function top(val) {
    this.top = val;
  };

  this.defProp($wbwindow.Object.prototype, 'WB_wombat_top', setter, getter);
};

/**
 * There is evil in this world because this is it.
 * To quote the MDN / every sane person 'Do not ever use eval'.
 * Why cause we gotta otherwise infinite loops.
 */
Wombat.prototype.initEvalOverride = function() {
  var rewriteEvalArg = this.rewriteEvalArg;
  var setNoop = function() {};
  var wrappedEval = function wrappedEval(arg) {
    return rewriteEvalArg(eval, arg);
  };
  this.defProp(
    this.$wbwindow.Object.prototype,
    'WB_wombat_eval',
    setNoop,
    function() {
      return wrappedEval;
    }
  );
  var runEval = function runEval(func) {
    return {
      eval: function(arg) {
        return rewriteEvalArg(func, arg);
      }
    };
  };
  this.defProp(
    this.$wbwindow.Object.prototype,
    'WB_wombat_runEval',
    setNoop,
    function() {
      return runEval;
    }
  );
};

/**
 * Initialize wombat's internal state and apply all overrides
 * @return {Object}
 */
Wombat.prototype.wombatInit = function() {
  // wombat init
  this._internalInit();

  // History
  this.initHistoryOverrides();

  this.overrideFunctionApply(this.$wbwindow);

  // Doc Title
  this.initDocTitleOverride();
  this.initHashChange();

  // postMessage
  // OPT skip
  if (!this.wb_opts.skip_postmessage) {
    this.initPostMessageOverride(this.$wbwindow);
    this.initMessageEventOverride(this.$wbwindow);
  }

  this.initUIEventsOverrides();

  // write
  this.initDocWriteOpenCloseOverride();

  // eval
  this.initEvalOverride();

  // Ajax, Fetch, Request, Response, EventSource, WebSocket
  this.initHTTPOverrides();

  // Audio
  this.initAudioOverride();

  // FontFace
  this.initFontFaceOverride(this.$wbwindow);

  // Worker override (experimental)
  this.initWorkerOverrides();

  // text node overrides for js frameworks doing funky things with CSS
  this.initTextNodeOverrides();
  this.initCSSOMOverrides();

  // innerHTML & outerHTML can be overriden on prototype!
  // we must override innerHTML & outerHTML on Element otherwise un-rewritten HTML
  // can get into replay
  this.overrideHtmlAssign(this.$wbwindow.Element, 'innerHTML', true);
  this.overrideHtmlAssign(this.$wbwindow.Element, 'outerHTML', true);
  this.overrideHtmlAssign(this.$wbwindow.HTMLIFrameElement, 'srcdoc', true);
  this.overrideHtmlAssign(this.$wbwindow.HTMLStyleElement, 'textContent');
  this.overrideShadowDom();

  // Document.URL override
  this.overridePropExtract(this.$wbwindow.Document.prototype, 'URL');
  this.overridePropExtract(this.$wbwindow.Document.prototype, 'documentURI');

  // Node.baseURI override
  this.overridePropExtract(this.$wbwindow.Node.prototype, 'baseURI');

  // Attr nodeValue and value
  this.overrideAttrProps();

  // init insertAdjacent[Element, HTML] override
  this.initInsertAdjacentElementHTMLOverrides();

  // iframe.contentWindow and iframe.contentDocument overrides to
  // ensure _wombat is inited on the iframe $wbwindow!
  this.overrideIframeContentAccess('contentWindow');
  this.overrideIframeContentAccess('contentDocument');

  // override funcs to convert first arg proxy->obj
  this.overrideFuncArgProxyToObj(this.$wbwindow.MutationObserver, 'observe');
  this.overrideFuncArgProxyToObj(
    this.$wbwindow.Node,
    'compareDocumentPosition'
  );
  this.overrideFuncArgProxyToObj(this.$wbwindow.Node, 'contains');
  this.overrideFuncArgProxyToObj(this.$wbwindow.Document, 'createTreeWalker');
  this.overrideFuncArgProxyToObj(this.$wbwindow.Document, 'evaluate', 1);
  this.overrideFuncArgProxyToObj(this.$wbwindow.Document, 'createTouch', 1);
  this.overrideFuncArgProxyToObj(
    this.$wbwindow.XSLTProcessor,
    'transformToFragment',
    1
  );

  this.overrideFuncThisProxyToObj(
    this.$wbwindow,
    'getComputedStyle',
    this.$wbwindow
  );

  this.initTimeoutIntervalOverrides();

  this.overrideFramesAccess(this.$wbwindow);

  // setAttribute
  this.initElementGetSetAttributeOverride();

  this.initSvgImageOverrides();

  // override href and src attrs
  this.initAttrOverrides();

  // Cookies
  this.initCookiesOverride();

  // ensure namespace urls are NOT rewritten
  this.initCreateElementNSFix();

  // DOM
  // OPT skip
  if (!this.wb_opts.skip_dom) {
    this.initDomOverride();
  }

  // registerProtocolHandler override
  this.initRegisterUnRegPHOverride();
  this.initPresentationRequestOverride();

  // sendBeacon override
  this.initBeaconOverride();

  // other overrides
  // proxy mode: only using these overrides

  // Random
  this.initSeededRandom(this.wb_info.wombat_sec);

  // Crypto Random
  this.initCryptoRandom();

  // set fixed pixel ratio
  this.initFixedRatio();

  // Date
  this.initDateOverride(this.wb_info.wombat_sec);

  // open
  this.initOpenOverride();

  // disable notifications
  this.initDisableNotificationsGeoLocation();

  // custom storage
  this.initStorageOverride();

  // add window and document obj proxies, if available
  this.initWindowObjProxy(this.$wbwindow);
  this.initDocumentObjProxy(this.$wbwindow.document);

  var wombat = this;
  return {
    actual: false,
    extract_orig: this.extractOriginalURL,
    rewrite_url: this.rewriteUrl,
    watch_elem: this.watchElem,
    init_new_window_wombat: this.initNewWindowWombat,
    init_paths: this.initPaths,
    local_init: function(name) {
      var res = wombat.$wbwindow._WB_wombat_obj_proxy[name];
      if (name === 'document' && res && !res._WB_wombat_obj_proxy) {
        return wombat.initDocumentObjProxy(res) || res;
      }
      return res;
    },
    showCSPViolations: function(yesNo) {
      wombat._addRemoveCSPViolationListener(yesNo);
    }
  };
};

export default Wombat;
