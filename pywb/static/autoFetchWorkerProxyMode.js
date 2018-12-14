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
var FetchDelay = 1000;
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
        case 'fetch-all':
            autofetcher.justFetch(data);
            break;
    }
};

function AutoFetcher() {
    if (!(this instanceof AutoFetcher)) {
        return new AutoFetcher();
    }
    // local cache of URLs fetched, to reduce server load
    this.seen = {};
     // array of URLs to be fetched
    this.queue = [];
    this.avQueue = [];
    // should we queue a URL or not
    this.queuing = false;
    // a URL to resolve relative URLs found in the cssText of CSSMedia rules.
    this.currentResolver = null;
    // should we queue a URL or not
    this.queuing = false;
    this.queuingAV = false;
    this.urlExtractor = this.urlExtractor.bind(this);
    this.imgFetchDone = this.imgFetchDone.bind(this);
    this.avFetchDone = this.avFetchDone.bind(this);
}

AutoFetcher.prototype.delay = function () {
    return new Promise(function (resolve, reject) {
        setTimeout(resolve, FetchDelay);
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
        this.queueNonAVURL(resolvedURL);
    }
    return n1 + n2 + n3;
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
            if (ssSplit[j]) {
                srcsetValue = ssSplit[j].trim();
                if (srcsetValue.length > 0) {
                    // resolve the URL in an exceptionless manner (resolvedURL will be undefined if an error occurred)
                    var resolvedURL = this.safeResolve(srcsetValue.split(' ')[0], extractedSrcSet.resolve);
                    if (resolvedURL) {
                        if (extractedSrcSet.mod === 'im_') {
                            this.queueNonAVURL(resolvedURL);
                        } else {
                            this.queueAVURL(resolvedURL);
                        }
                    }
                }
            }
        }
    }
};

AutoFetcher.prototype.extractSrc = function (srcVals) {
    // preservation worker in proxy mode sends us the value of the srcset attribute of an element
    // and a URL to correctly resolve relative URLS. Thus we must recreate rewrite_srcset logic here
    if (srcVals == null || srcVals.length === 0) return;
    var length = srcVals.length;
    var srcVal;
    for (var i = 0; i < length; i++) {
        srcVal = srcVals[i];
        var resolvedURL = this.safeResolve(srcVal.src, srcVal.resolve);
        if (resolvedURL) {
            if (srcVal.mod === 'im_') {
                this.queueNonAVURL(resolvedURL);
            } else {
                this.queueAVURL(resolvedURL);
            }
        }
    }
};


AutoFetcher.prototype.autofetchMediaSrcset = function (data) {
    // we got a message and now we autofetch!
    // these calls turn into no ops if they have no work
    this.extractMedia(data.media);
    this.extractSrcset(data.srcset);
    this.extractSrc(data.src);
    this.fetchImgs();
    this.fetchAV();
};

AutoFetcher.prototype.justFetch = function (data) {
    // we got a message containing only urls to be fetched
    if (data == null || data.values == null) return;
    for (var i = 0; i < data.values.length; ++i) {
        this.queueNonAVURL(data.values[i]);
    }
    this.fetchImgs();
};

autofetcher = new AutoFetcher();
