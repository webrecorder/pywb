'use strict';
// thanks wombat
var STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/gi;
var IMPORT_REGEX = /(@import\s+[\\"']*)([^)'";]+)([\\"']*\s*;?)/gi;
var srcsetSplit = /\s*(\S*\s+[\d.]+[wx]),|(?:\s*,(?:\s+|(?=https?:)))/;
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
            autofetcher.autofetchMediaSrcset(data);
            break;
    }
};

function AutoFetcher() {
    if (!(this instanceof AutoFetcher)) {
        return new AutoFetcher();
    }
    // local cache of URLs fetched, to reduce server load
    this.seen = {};
    // array of promises returned by fetch(URL)
    this.fetches = [];
    // array of URL to be fetched
    this.queue = [];
    // should we queue a URL or not
    this.queuing = false;
    // a URL to resolve relative URLs found in the cssText of CSSMedia rules.
    this.currentResolver = null;
    this.urlExtractor = this.urlExtractor.bind(this);
    this.fetchDone = this.fetchDone.bind(this);
}

AutoFetcher.prototype.safeFetch = function (url) {
    // ensure we do not request data urls
    if (url.indexOf('data:') === 0) return;
    // check to see if we have seen this url before in order
    // to lessen the load against the server content is autofetchd from
    if (this.seen[url] != null) return;
    this.seen[url] = true;
    if (this.queuing) {
        // we are currently waiting for a batch of fetches to complete
        return this.queue.push(url);
    }
    // fetch this url
    this.fetches.push(fetch(url));
};

AutoFetcher.prototype.safeResolve = function (url, resolver) {
    // Guard against the exception thrown by the URL constructor if the URL or resolver is bad
    // if resolver is undefined/null then this function passes url through
    var resolvedURL = url;
    if (resolver) {
        try {
            resolvedURL = (new URL(url, resolver)).href
        } catch (e) {
            resolvedURL = url;
        }
    }
    return resolvedURL;
};


AutoFetcher.prototype.urlExtractor = function (match, n1, n2, n3, offset, string) {
    // Same function as style_replacer in wombat.rewrite_style, n2 is our URL
    // this.currentResolver is set to the URL which the browser would normally
    // resolve relative urls with (URL of the stylesheet) in an exceptionless manner
    // (resolvedURL will be undefined if an error occurred)
    var resolvedURL = this.safeResolve(n2, this.currentResolver);
    if (resolvedURL) {
        this.safeFetch(resolvedURL);
    }
    return n1 + n2 + n3;
};

AutoFetcher.prototype.fetchDone = function () {
    // indicate we no longer need to Q
    this.queuing = false;
    if (this.queue.length > 0) {
        // we have a Q of some length drain it
        this.drainQ();
    }
};

AutoFetcher.prototype.fetchAll = function () {
    // if we are queuing or have no fetches this is a no op
    if (this.queuing) return;
    if (this.fetches.length === 0) return;
    // we are about to fetch queue anything that comes our way
    this.queuing = true;
    // initiate fetches by turning the initial fetch promises
    // into rejctionless promises and "await" all clearing
    // our fetches array in place
    var runningFetchers = [];
    while (this.fetches.length > 0) {
        runningFetchers.push(this.fetches.shift().catch(noop))
    }
    Promise.all(runningFetchers)
        .then(this.fetchDone)
        .catch(this.fetchDone);
};

AutoFetcher.prototype.drainQ = function () {
    // clear our Q in place and fill our fetches array
    while (this.queue.length > 0) {
        this.fetches.push(fetch(this.queue.shift()));
    }
    // fetch all the things
    this.fetchAll();
};

AutoFetcher.prototype.extractMedia = function (mediaRules) {
    // this is a broken down rewrite_style
    if (mediaRules == null) return;
    for (var i = 0; i < mediaRules.length; i++) {
        // set currentResolver to the value of this stylesheets URL, done to ensure we do not have to
        // create functions on each loop iteration because we potentially create a new `URL` object
        // twice per iteration
        this.currentResolver = mediaRules[i].resolve;
        mediaRules[i].cssText
            .replace(STYLE_REGEX, this.urlExtractor)
            .replace(IMPORT_REGEX, this.urlExtractor);
    }
};

AutoFetcher.prototype.extractSrcset = function (srcsets) {
    // preservation worker in proxy mode sends us the value of the srcset attribute of an element
    // and a URL to correctly resolve relative URLS. Thus we must recreate rewrite_srcset logic here
    if (srcsets == null) return;
    var length = srcsets.length;
    var extractedSrcSet, srcsetValue, ssSplit, j;
    for (var i = 0; i < length; i++) {
        extractedSrcSet = srcsets[i];
        ssSplit = extractedSrcSet.srcset.split(srcsetSplit);
        for (j = 0; j < ssSplit.length; j++) {
            if (Boolean(ssSplit[j])) {
                srcsetValue = ssSplit[j].trim();
                if (srcsetValue.length > 0) {
                    // resolve the URL in an exceptionless manner (resolvedURL will be undefined if an error occurred)
                    var resolvedURL = this.safeResolve(srcsetValue.split(' ')[0], extractedSrcSet.resolve);
                    if (resolvedURL) {
                        this.safeFetch(resolvedURL);
                    }
                }
            }
        }
    }
};

AutoFetcher.prototype.autofetchMediaSrcset = function (data) {
    // we got a message and now we autofetch!
    // these calls turn into no ops if they have no work
    this.extractMedia(data.media);
    this.extractSrcset(data.srcset);
    this.fetchAll();
};

autofetcher = new AutoFetcher();
