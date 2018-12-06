'use strict';
// thanks wombat
var STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/gi;
var IMPORT_REGEX = /(@import\s+[\\"']*)([^)'";]+)([\\"']*\s*;?)/gi;
var srcsetSplit = /\s*(\S*\s+[\d.]+[wx]),|(?:\s*,(?:\s+|(?=https?:)))/;
var DefaultNumImFetches = 30;
var FullImgQDrainLen = 10;
var DefaultNumAvFetches = 5;
var FullAVQDrainLen = 5;
var DataURLPrefix = 'data:';

// the autofetcher instance for this worker
var autofetcher = null;

function noop() {}

if (typeof self.Promise === 'undefined') {
    // not kewl we must polyfill Promise
    self.Promise = function (executor) {
        executor(noop, noop);
    };
    self.Promise.prototype.then = function (cb) {
        if (cb) cb();
        return this;
    };
    self.Promise.prototype.catch = function () {
        return this;
    };
    self.Promise.all = function (values) {
        return new Promise(noop);
    };
}

if (typeof self.fetch === 'undefined') {
    // not kewl we must polyfill fetch.
    self.fetch = function (url) {
        return new Promise(function (resolve) {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', url);
            xhr.send();
            resolve();
        });
    };
}

self.onmessage = function (event) {
    var data = event.data;
    switch (data.type) {
        case 'values':
            autofetcher.autoFetch(data);
            break;
    }
};

function AutoFetcher(init) {
    if (!(this instanceof AutoFetcher)) {
        return new AutoFetcher(init);
    }
    this.prefix = init.prefix;
    this.mod = init.mod;
    this.prefixMod = init.prefix + init.mod;
    this.rwRe = new RegExp(init.rwRe);
    // relative url, WorkerLocation is set by owning document
    this.relative = init.prefix.split(location.origin)[1];
    // schemeless url
    this.schemeless = '/' + this.relative;
    // local cache of URLs fetched, to reduce server load
    this.seen = {};
    // array of URLs to be fetched
    this.queue = [];
    this.avQueue = [];
    // should we queue a URL or not
    this.queuing = false;
    this.queuingAV = false;
    this.urlExtractor = this.urlExtractor.bind(this);
    this.imgFetchDone = this.imgFetchDone.bind(this);
    this.avFetchDone = this.avFetchDone.bind(this);
}

AutoFetcher.prototype.delay = function () {
    // 2 second delay seem reasonable
    return new Promise(function (resolve, reject) {
        setTimeout(resolve, 2000);
    });
};

AutoFetcher.prototype.imgFetchDone = function () {
    if (this.queue.length > 0) {
        // we have a Q of some length drain it
        var autofetcher = this;
        this.delay().then(function () {
            autofetcher.queuing = false;
            autofetcher.fetchImgs();
        });
    } else {
        this.queuing = false;
    }
};

AutoFetcher.prototype.avFetchDone = function () {
    if (this.avQueue.length > 0) {
        // we have a Q of some length drain it
        var autofetcher = this;
        this.delay().then(function () {
            autofetcher.queuingAV = false;
            autofetcher.fetchAV();
        });
    } else {
        this.queuingAV = false;
    }
};

AutoFetcher.prototype.fetchAV = function () {
    if (this.queuingAV || this.avQueue.length === 0) {
        return;
    }
    // the number of fetches is limited to a maximum of DefaultNumAvFetches + FullAVQDrainLen outstanding fetches
    // the baseline maximum number of fetches is DefaultNumAvFetches but if the size(avQueue) <= FullAVQDrainLen
    // we add them to the current batch. Because audio video resources might be big
    // we limit how many we fetch at a time drastically
    this.queuingAV = true;
    var runningFetchers = [];
    while (this.avQueue.length > 0 && runningFetchers.length <= DefaultNumAvFetches) {
        runningFetchers.push(fetch(this.avQueue.shift()).catch(noop))
    }
    if (this.avQueue.length <= FullAVQDrainLen) {
        while (this.avQueue.length > 0) {
            runningFetchers.push(fetch(this.avQueue.shift()).catch(noop))
        }
    }
    Promise.all(runningFetchers)
        .then(this.avFetchDone)
        .catch(this.avFetchDone);
};

AutoFetcher.prototype.fetchImgs = function () {
    if (this.queuing || this.queue.length === 0) {
        return;
    }
    // the number of fetches is limited to a maximum of DefaultNumImFetches + FullImgQDrainLen outstanding fetches
    // the baseline maximum number of fetches is DefaultNumImFetches but if the size(queue) <= FullImgQDrainLen
    // we add them to the current batch
    this.queuing = true;
    var runningFetchers = [];
    while (this.queue.length > 0 && runningFetchers.length <= DefaultNumImFetches) {
        runningFetchers.push(fetch(this.queue.shift()).catch(noop))
    }
    if (this.queue.length <= FullImgQDrainLen) {
        while (this.queue.length > 0) {
            runningFetchers.push(fetch(this.queue.shift()).catch(noop))
        }
    }
    Promise.all(runningFetchers)
        .then(this.imgFetchDone)
        .catch(this.imgFetchDone);
};

AutoFetcher.prototype.queueNonAVURL = function (url) {
    // ensure we do not request data urls
    if (url.indexOf(DataURLPrefix) === 0) return;
    // check to see if we have seen this url before in order
    // to lessen the load against the server content is fetched from
    if (this.seen[url] != null) return;
    this.seen[url] = true;
    this.queue.push(url);
};

AutoFetcher.prototype.queueAVURL = function (url) {
    // ensure we do not request data urls
    if (url.indexOf(DataURLPrefix) === 0) return;
    // check to see if we have seen this url before in order
    // to lessen the load against the server content is fetched from
    if (this.seen[url] != null) return;
    this.seen[url] = true;
    this.avQueue.push(url);
};

AutoFetcher.prototype.maybeResolveURL = function (url, base) {
    // given a url and base url returns a resolved full URL or
    // null if resolution was unsuccessful
    try {
        var _url = new URL(url, base);
        return _url.href;
    } catch (e) {
        return null;
    }
};

AutoFetcher.prototype.maybeFixUpRelSchemelessPrefix = function (url) {
    // attempt to ensure rewritten relative or schemeless URLs become full URLS!
    // otherwise returns null if this did not happen
    if (url.indexOf(this.relative) === 0) {
        return url.replace(this.relative, this.prefix);
    }
    if (url.indexOf(this.schemeless) === 0) {
        return url.replace(this.schemeless, this.prefix);
    }
    return null;
};

AutoFetcher.prototype.maybeFixUpURL = function (url, resolveOpts) {
    // attempt to fix up the url and do our best to ensure we can get dat 200 OK!
    if (this.rwRe.test(url)) {
        return url;
    }
    var mod = resolveOpts.mod || 'mp_';
    // first check for / (relative) or // (schemeless) rewritten urls
    var maybeFixed = this.maybeFixUpRelSchemelessPrefix(url);
    if (maybeFixed != null) {
        return maybeFixed;
    }
    // resolve URL against tag src
    if (resolveOpts.tagSrc != null) {
        maybeFixed = this.maybeResolveURL(url, resolveOpts.tagSrc);
        if (maybeFixed != null) {
            return this.prefix + mod + '/' + maybeFixed;
        }
    }
    // finally last attempt resolve the originating documents base URI
    if (resolveOpts.docBaseURI) {
        maybeFixed = this.maybeResolveURL(url, resolveOpts.docBaseURI);
        if (maybeFixed != null) {
            return this.prefix + mod + '/' + maybeFixed;
        }
    }
    // not much to do now.....
    return this.prefixMod + '/' + url;
};

AutoFetcher.prototype.urlExtractor = function (match, n1, n2, n3, offset, string) {
    // Same function as style_replacer in wombat.rewrite_style, n2 is our URL
    this.queueNonAVURL(n2);
    return n1 + n2 + n3;
};

AutoFetcher.prototype.handleMedia = function (mediaRules) {
    // this is a broken down rewrite_style
    if (mediaRules == null || mediaRules.length === 0) return;
    // var rules = mediaRules.values;
    for (var i = 0; i < mediaRules.length; i++) {
        mediaRules[i]
            .replace(STYLE_REGEX, this.urlExtractor)
            .replace(IMPORT_REGEX, this.urlExtractor);
    }
};

AutoFetcher.prototype.handleSrc = function (srcValues, context) {
    var resolveOpts = { 'docBaseURI': context.docBaseURI };
    if (srcValues.value) {
        resolveOpts.mod = srcValues.mod;
        if (resolveOpts.mod === 1) {
            return this.queueNonAVURL(this.maybeFixUpURL(srcValues.value.trim(), resolveOpts));
        }
        return this.queueAVURL(this.maybeFixUpURL(srcValues.value.trim(), resolveOpts));
    }
    var len = srcValues.values.length;
    for (var i = 0; i < len; i++) {
        var value = srcValues.values[i];
        resolveOpts.mod = value.mod;
        if (resolveOpts.mod  === 'im_') {
            this.queueNonAVURL(this.maybeFixUpURL(value.src, resolveOpts));
        } else {
            this.queueAVURL(this.maybeFixUpURL(value.src, resolveOpts));
        }
    }
};

AutoFetcher.prototype.extractSrcSetNotPreSplit = function (ssV, resolveOpts) {
    // was from extract from local doc so we need to duplicate  work
    var srcsetValues = ssV.split(srcsetSplit);
    for (var i = 0; i < srcsetValues.length; i++) {
        // grab the URL not width/height key
        if (srcsetValues[i]) {
            var value = srcsetValues[i].trim().split(' ')[0];
            var maybeResolvedURL = this.maybeFixUpURL(value.trim(), resolveOpts);
            if (resolveOpts.mod === 'im_') {
                this.queueNonAVURL(maybeResolvedURL);
            } else {
                this.queueAVURL(maybeResolvedURL);
            }
        }
    }
};

AutoFetcher.prototype.extractSrcset = function (srcsets, context) {
    // was rewrite_srcset and only need to q
    for (var i = 0; i < srcsets.length; i++) {
        // grab the URL not width/height key
        var url = srcsets[i].split(' ')[0];
        if (context.mod === 'im_') {
            this.queueNonAVURL(url);
        } else {
            this.queueAVURL(url);
        }
    }
};

AutoFetcher.prototype.handleSrcset = function (srcset, context) {
    var resolveOpts = { 'docBaseURI': context.docBaseURI };
    if (srcset.value) {
        // we have a single value, this srcset came from either
        // preserveDataSrcset (not presplit) preserveSrcset (presplit)
        resolveOpts.mod = srcset.mod;
        if (!srcset.presplit) {
            // extract URLs from the srcset string
            return this.extractSrcSetNotPreSplit(srcset.value, resolveOpts);
        }
        // we have an array of srcset URL strings
        return this.extractSrcset(srcset.value, resolveOpts);
    }
    // we have an array of values, these srcsets came from extractFromLocalDoc
    var len = srcset.values.length;
    for (var i = 0; i < len; i++) {
        var ssv = srcset.values[i];
        resolveOpts.mod = ssv.mod;
        resolveOpts.tagSrc = ssv.tagSrc;
        this.extractSrcSetNotPreSplit(ssv.srcset, resolveOpts);
    }
};


AutoFetcher.prototype.autoFetch = function (data) {
    // we got a message and now we autofetch!
    // these calls turn into no ops if they have no work
    if (data.media) {
        this.handleMedia(data.media);
    }

    if (data.src) {
        this.handleSrc(data.src, data.context || {});
    }

    if (data.srcset) {
        this.handleSrcset(data.srcset, data.context || {});
    }

    this.fetchImgs();
    this.fetchAV();
};

// initialize ourselves from the query params :)
try {
    var loc = new self.URL(location.href);
    autofetcher = new AutoFetcher(JSON.parse(loc.searchParams.get('init')));
} catch (e) {
    // likely we are in an older version of safari
    var search = decodeURIComponent(location.search.split('?')[1]).split('&');
    var init = JSON.parse(search[0].substr(search[0].indexOf('=') + 1));
    init.prefix = decodeURIComponent(init.prefix);
    init.baseURI = decodeURIComponent(init.baseURI);
    autofetcher = new AutoFetcher(init);
}
