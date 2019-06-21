/**
 * Mini wombat for performing URL rewriting within the
 * Web/Shared/Service Worker context
 * @param {Object} info
 * @return {WBWombat}
 */
function WBWombat(info) {
  if (!(this instanceof WBWombat)) return new WBWombat(info);
  /** @type {Object} */
  this.info = info;
  this.initImportScriptsRewrite();
  this.initHTTPOverrides();
  this.initClientApisOverride();
  this.initCacheApisOverride();
}

/**
 * Returns T/F indicating if the supplied URL is not to be rewritten
 * @param {string} url
 * @return {boolean}
 */
WBWombat.prototype.noRewrite = function(url) {
  return (
    !url ||
    url.indexOf('blob:') === 0 ||
    url.indexOf('javascript:') === 0 ||
    url.indexOf('data:') === 0 ||
    url.indexOf(this.info.prefix) === 0
  );
};

/**
 * Returns T/F indicating if the supplied URL is an relative URL
 * @param {string} url
 * @return {boolean}
 */
WBWombat.prototype.isRelURL = function(url) {
  return url.indexOf('/') === 0 || url.indexOf('http:') !== 0;
};

/**
 * Attempts to resolve the supplied relative URL against
 * the origin this worker was created on
 * @param {string} maybeRelURL
 * @param {string} against
 * @return {string}
 */
WBWombat.prototype.maybeResolveURL = function(maybeRelURL, against) {
  if (!against) return maybeRelURL;
  try {
    var resolved = new URL(maybeRelURL, against);
    return resolved.href;
  } catch (e) {}
  return maybeRelURL;
};

/**
 * Returns null to indicate that the supplied URL is not to be rewritten.
 * Otherwise returns a URL that can be rewritten
 * @param {*} url
 * @param {string} resolveAgainst
 * @return {?string}
 */
WBWombat.prototype.ensureURL = function(url, resolveAgainst) {
  if (!url) return url;
  var newURL;
  switch (typeof url) {
    case 'string':
      newURL = url;
      break;
    case 'object':
      newURL = url.toString();
      break;
    default:
      return null;
  }
  if (this.noRewrite(newURL)) return null;
  if (this.isRelURL(newURL)) {
    return this.maybeResolveURL(newURL, resolveAgainst);
  }
  return newURL;
};

/**
 * Rewrites the supplied URL
 * @param {string} url
 * @return {string}
 */
WBWombat.prototype.rewriteURL = function(url) {
  var rwURL = this.ensureURL(url, this.info.originalURL);
  if (!rwURL) return url;
  if (this.info.prefixMod) {
    return this.info.prefixMod + rwURL;
  }
  return rwURL;
};

/**
 * Rewrites the supplied URL of an controlled page using the mp\_ modifier
 * @param {string} url
 * @param {WindowClient} [client]
 * @return {string}
 */
WBWombat.prototype.rewriteClientWindowURL = function(url, client) {
  var rwURL = this.ensureURL(url, client ? client.url : this.info.originalURL);
  if (!rwURL) return url;
  if (this.info.prefix) {
    return this.info.prefix + 'mp_/' + rwURL;
  }
  return rwURL;
};

/**
 * Mini url rewriter specifically for rewriting web sockets
 * @param {?string} originalURL
 * @return {string}
 */
WBWombat.prototype.rewriteWSURL = function(originalURL) {
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
  var https = 'https://';

  var wbSecure = this.info.prefix.indexOf(https) === 0;
  var wbPrefix =
    this.info.prefix.replace(
      wbSecure ? https : 'http://',
      wbSecure ? wssScheme : wsScheme
    ) + 'ws_/';
  return wbPrefix + url;
};

/**
 * Rewrites all URLs in the supplied arguments object
 * @param {Object} argsObj
 * @return {Array<string>}
 */
WBWombat.prototype.rewriteArgs = function(argsObj) {
  // recreate the original arguments object just with URLs rewritten
  var newArgObj = new Array(argsObj.length);
  for (var i = 0; i < newArgObj.length; i++) {
    newArgObj[i] = this.rewriteURL(argsObj[i]);
  }
  return newArgObj;
};

/**
 * Rewrites the input to one of the Fetch APIs
 * @param {*|string|Request} input
 * @return {*|string|Request}
 */
WBWombat.prototype.rewriteFetchApi = function(input) {
  var rwInput = input;
  switch (typeof input) {
    case 'string':
      rwInput = this.rewriteURL(input);
      break;
    case 'object':
      if (input.url) {
        var new_url = this.rewriteURL(input.url);
        if (new_url !== input.url) {
          // not much we can do here Request.url is read only
          // https://developer.mozilla.org/en-US/docs/Web/API/Request/url
          rwInput = new Request(new_url, input);
        }
      } else if (input.href) {
        // it is likely that input is either self.location or self.URL
        // we cant do anything here so just let it go
        rwInput = input.href;
      }
      break;
  }
  return rwInput;
};

/**
 * Rewrites the input to one of the Cache APIs
 * @param {*|string|Request} request
 * @return {*|string|Request}
 */
WBWombat.prototype.rewriteCacheApi = function(request) {
  var rwRequest = request;
  if (typeof request === 'string') {
    rwRequest = this.rewriteURL(request);
  }
  return rwRequest;
};

/**
 * Applies an override to the importScripts function
 * @see https://html.spec.whatwg.org/multipage/workers.html#dom-workerglobalscope-importscripts
 */
WBWombat.prototype.initImportScriptsRewrite = function() {
  if (!self.importScripts) return;
  var wombat = this;
  var origImportScripts = self.importScripts;
  self.importScripts = function importScripts() {
    // rewrite the arguments object and call original function via fn.apply
    var rwArgs = wombat.rewriteArgs(arguments);
    return origImportScripts.apply(this, rwArgs);
  };
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
WBWombat.prototype.initHTTPOverrides = function() {
  var wombat = this;
  if (
    self.XMLHttpRequest &&
    self.XMLHttpRequest.prototype &&
    self.XMLHttpRequest.prototype.open
  ) {
    var oXHROpen = self.XMLHttpRequest.prototype.open;
    self.XMLHttpRequest.prototype.open = function open(
      method,
      url,
      async,
      user,
      password
    ) {
      var rwURL = wombat.rewriteURL(url);
      var openAsync = true;
      if (async != null && !async) openAsync = false;
      oXHROpen.call(this, method, rwURL, openAsync, user, password);
      if (rwURL.indexOf('data:') === -1) {
        this.setRequestHeader('X-Pywb-Requested-With', 'XMLHttpRequest');
      }
    };
  }

  if (self.fetch != null) {
    // this fetch is Worker.fetch
    var orig_fetch = self.fetch;
    self.fetch = function fetch(input, init_opts) {
      var rwInput = wombat.rewriteFetchApi(input);
      var newInitOpts = init_opts || {};
      newInitOpts['credentials'] = 'include';
      return orig_fetch.call(this, rwInput, newInitOpts);
    };
  }

  if (self.Request && self.Request.prototype) {
    var orig_request = self.Request;
    self.Request = (function(Request_) {
      return function Request(input, init_opts) {
        var newInitOpts = init_opts || {};
        var newInput = wombat.rewriteFetchApi(input);
        newInitOpts['credentials'] = 'include';
        return new Request_(newInput, newInitOpts);
      };
    })(self.Request);
    self.Request.prototype = orig_request.prototype;
  }

  if (self.Response && self.Response.prototype) {
    var originalRedirect = self.Response.prototype.redirect;
    self.Response.prototype.redirect = function redirect(url, status) {
      var rwURL = wombat.rewriteUrl(url);
      return originalRedirect.call(this, rwURL, status);
    };
  }

  if (self.EventSource && self.EventSource.prototype) {
    var origEventSource = self.EventSource;
    self.EventSource = (function(EventSource_) {
      return function EventSource(url, configuration) {
        var rwURL = url;
        if (url != null) {
          rwURL = wombat.rewriteUrl(url);
        }
        return new EventSource_(rwURL, configuration);
      };
    })(self.EventSource);
    self.EventSource.prototype = origEventSource.prototype;
    Object.defineProperty(self.EventSource.prototype, 'constructor', {
      value: self.EventSource
    });
  }

  if (self.WebSocket && self.WebSocket.prototype) {
    var origWebSocket = self.WebSocket;
    self.WebSocket = (function(WebSocket_) {
      return function WebSocket(url, configuration) {
        var rwURL = url;
        if (url != null) {
          rwURL = wombat.rewriteWSURL(url);
        }
        return new WebSocket_(rwURL, configuration);
      };
    })(self.WebSocket);
    self.WebSocket.prototype = origWebSocket.prototype;
    Object.defineProperty(self.WebSocket.prototype, 'constructor', {
      value: self.WebSocket
    });
  }
};

/**
 * Applies an override to Clients.openWindow and WindowClient.navigate that rewrites
 * the supplied URL that represents a controlled window
 * @see https://w3c.github.io/ServiceWorker/#window-client-interface
 * @see https://w3c.github.io/ServiceWorker/#clients-interface
 */
WBWombat.prototype.initClientApisOverride = function() {
  var wombat = this;
  if (
    self.Clients &&
    self.Clients.prototype &&
    self.Clients.prototype.openWindow
  ) {
    var oClientsOpenWindow = self.Clients.prototype.openWindow;
    self.Clients.prototype.openWindow = function openWindow(url) {
      var rwURL = wombat.rewriteClientWindowURL(url);
      return oClientsOpenWindow.call(this, rwURL);
    };
  }

  if (
    self.WindowClient &&
    self.WindowClient.prototype &&
    self.WindowClient.prototype.navigate
  ) {
    var oWinClientNavigate = self.WindowClient.prototype.navigate;
    self.WindowClient.prototype.navigate = function navigate(url) {
      var rwURL = wombat.rewriteClientWindowURL(url, this);
      return oWinClientNavigate.call(this, rwURL);
    };
  }
};

/**
 * Applies overrides to the CachStorage and Cache interfaces in order
 * to rewrite the URLs they operate on
 * @see https://w3c.github.io/ServiceWorker/#cachestorage
 * @see https://w3c.github.io/ServiceWorker/#cache-interface
 */
WBWombat.prototype.initCacheApisOverride = function() {
  var wombat = this;
  if (
    self.CacheStorage &&
    self.CacheStorage.prototype &&
    self.CacheStorage.prototype.match
  ) {
    var oCacheStorageMatch = self.CacheStorage.prototype.match;
    self.CacheStorage.prototype.match = function match(request, options) {
      var rwRequest = wombat.rewriteCacheApi(request);
      return oCacheStorageMatch.call(this, rwRequest, options);
    };
  }

  if (self.Cache && self.Cache.prototype) {
    if (self.Cache.prototype.match) {
      var oCacheMatch = self.Cache.prototype.match;
      self.Cache.prototype.match = function match(request, options) {
        var rwRequest = wombat.rewriteCacheApi(request);
        return oCacheMatch.call(this, rwRequest, options);
      };
    }

    if (self.Cache.prototype.matchAll) {
      var oCacheMatchAll = self.Cache.prototype.matchAll;
      self.Cache.prototype.matchAll = function matchAll(request, options) {
        var rwRequest = wombat.rewriteCacheApi(request);
        return oCacheMatchAll.call(this, rwRequest, options);
      };
    }

    if (self.Cache.prototype.add) {
      var oCacheAdd = self.Cache.prototype.add;
      self.Cache.prototype.add = function add(request, options) {
        var rwRequest = wombat.rewriteCacheApi(request);
        return oCacheAdd.call(this, rwRequest, options);
      };
    }

    if (self.Cache.prototype.addAll) {
      var oCacheAddAll = self.Cache.prototype.addAll;
      self.Cache.prototype.addAll = function addAll(requests) {
        var rwRequests = requests;
        if (Array.isArray(requests)) {
          rwRequests = new Array(requests.length);
          for (var i = 0; i < requests.length; i++) {
            rwRequests[i] = wombat.rewriteCacheApi(requests[i]);
          }
        }
        return oCacheAddAll.call(this, rwRequests);
      };
    }

    if (self.Cache.prototype.put) {
      var oCachePut = self.Cache.prototype.put;
      self.Cache.prototype.put = function put(request, response) {
        var rwRequest = wombat.rewriteCacheApi(request);
        return oCachePut.call(this, rwRequest, response);
      };
    }

    if (self.Cache.prototype.delete) {
      var oCacheDelete = self.Cache.prototype.delete;
      self.Cache.prototype.delete = function newCacheDelete(request, options) {
        var rwRequest = wombat.rewriteCacheApi(request);
        return oCacheDelete.call(this, rwRequest, options);
      };
    }

    if (self.Cache.prototype.keys) {
      var oCacheKeys = self.Cache.prototype.keys;
      self.Cache.prototype.keys = function keys(request, options) {
        var rwRequest = wombat.rewriteCacheApi(request);
        return oCacheKeys.call(this, rwRequest, options);
      };
    }
  }
};

self.WBWombat = WBWombat;
