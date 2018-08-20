'use strict';
// thanks wombat
var STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/gi;
var IMPORT_REGEX = /(@import\s+[\\"']*)([^)'";]+)([\\"']*\s*;?)/gi;
var srcsetSplit = /\s*(\S*\s+[\d.]+[wx]),|(?:\s*,(?:\s+|(?=https?:)))/;
// the preserver instance for this worker
var preserver = null;

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
            preserver.preserveMediaSrcset(data);
            break;
    }
};

function pMap(p) {
    // mapping function to ensure each fetch promises catch has a no op cb
    return p.catch(noop);
}

function Preserver(prefix, mod) {
    if (!(this instanceof Preserver)) {
        return new Preserver(prefix, mod);
    }
    this.prefix = prefix;
    this.mod = mod;
    this.prefixMod = prefix + mod;
    // relative url, WorkerLocation is set by owning document
    this.relative = prefix.split(location.origin)[1];
    // schemeless url
    this.schemeless = '/' + this.relative;
    // local cache of URLs fetched, to reduce server load
    this.seen = {};
    // counter used to know when to clear seen (count > 2500)
    this.seenCount = 0;
    // array of promises returned by fetch(URL)
    this.fetches = [];
    // array of URL to be fetched
    this.queue = [];
    // should we queue a URL or not
    this.queuing = false;
    this.urlExtractor = this.urlExtractor.bind(this);
    this.fetchDone = this.fetchDone.bind(this);
}

Preserver.prototype.fixupURL = function (url) {
    // attempt to fix up the url and do our best to ensure we can get dat 200 OK!
    if (url.indexOf(this.prefixMod) === 0) {
        return url;
    }
    if (url.indexOf(this.relative) === 0) {
        return url.replace(this.relative, this.prefix);
    }
    if (url.indexOf(this.schemeless) === 0) {
        return url.replace(this.schemeless, this.prefix);
    }
    if (url.indexOf(this.prefix) !== 0) {
        return this.prefix + url;
    }
    return url;
};

Preserver.prototype.safeFetch = function (url) {
    var fixedURL = this.fixupURL(url);
    // check to see if we have seen this url before in order
    // to lessen the load against the server content is preserved from
    if (this.seen[url] != null) return;
    this.seen[url] = true;
    if (this.queuing) {
        // we are currently waiting for a batch of fetches to complete
        return this.queue.push(fixedURL);
    }
    // queue this urls fetch
    this.fetches.push(fetch(fixedURL));
};

Preserver.prototype.urlExtractor = function (match, n1, n2, n3, offset, string) {
    // Same function as style_replacer in wombat.rewrite_style, n2 is our URL
    this.safeFetch(n2);
    return n1 + n2 + n3;
};

Preserver.prototype.fetchDone = function () {
    // clear our fetches array in place
    // https://www.ecma-international.org/ecma-262/9.0/index.html#sec-properties-of-array-instances-length
    this.fetches.length = 0;
    // indicate we no longer need to Q
    this.queuing = false;
    if (this.queue.length > 0) {
        // we have a Q of some length drain it
        this.drainQ();
    } else if (this.seenCount > 2500) {
        // we seen 2500 URLs so lets free some memory as at this point
        // we will probably see some more. GC it!
        this.seen = {};
        this.seenCount = 0;
    }
};

Preserver.prototype.fetchAll = function () {
    // if we are queuing or have no fetches this is a no op
    if (this.queuing) return;
    if (this.fetches.length === 0) return;
    // we are about to fetch queue anything that comes our way
    this.queuing = true;
    // initiate fetches by turning the initial fetch promises
    // into rejctionless promises and "await" all
    Promise.all(this.fetches.map(pMap))
        .then(this.fetchDone)
        .catch(this.fetchDone);
};

Preserver.prototype.drainQ = function () {
    // clear our Q in place and fill our fetches array
    while (this.queue.length > 0) {
        this.fetches.push(fetch(this.queue.shift()));
    }
    // fetch all the things
    this.fetchAll();
};

Preserver.prototype.extractMedia = function (mediaRules) {
    // this is a broken down rewrite_style
    if (mediaRules == null) return;
    for (var i = 0; i < mediaRules.length; i++) {
        var rule = mediaRules[i];
        rule.replace(STYLE_REGEX, this.urlExtractor);
        rule.replace(IMPORT_REGEX, this.urlExtractor);
    }
};

Preserver.prototype.extractSrcset = function (srcsets) {
    if (srcsets == null || srcsets.values == null) return;
    var srcsetValues = srcsets.values;
    // was srcsets from rewrite_srcset and if so no need to split
    var presplit = srcsets.presplit;
    for (var i = 0; i < srcsetValues.length; i++) {
        var srcset = srcsetValues[i];
        if (presplit) {
            // was rewrite_srcset so just ensure we just
            // grab the URL not width/height key
            this.safeFetch(srcset.split(' ')[0]);
        } else {
            // was from extract from local doc so we need to duplicate  work
            var values = srcset.split(srcsetSplit).filter(Boolean);
            for (var j = 0; j < values.length; j++) {
                var value = values[j].trim();
                if (value.length > 0) {
                    this.safeFetch(value.split(' ')[0]);
                }
            }
        }
    }
};

Preserver.prototype.preserveMediaSrcset = function (data) {
    // we got a message and now we preserve!
    // these calls turn into no ops if they have no work
    this.extractMedia(data.media);
    this.extractSrcset(data.srcset);
    this.fetchAll();
};

// initialize ourselves from the query params :)
try {
    var loc = new self.URL(location);
    preserver = new Preserver(loc.searchParams.get('prefix'), loc.searchParams.get('mod'));
} catch (e) {
    // likely we are in an older version of safari
    var search = decodeURIComponent(location.search.split('?')[1]).split('&');
    preserver = new Preserver(search[0].substr(search[0].indexOf('=') + 1), search[1].substr(search[1].indexOf('=') + 1));
}
