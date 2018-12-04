/*
Copyright(c) 2013-2018 Rhizome and Ilya Kreymer. Released under the GNU General Public License.

This file is part of pywb, https://github.com/webrecorder/pywb

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
// Wombat JS-Rewriting Library v2.53
//============================================

// Wombat lite for proxy-mode
var _WBWombat = function ($wbwindow, wbinfo) {
    // Globals
    var wb_info = wbinfo;
    wb_info.top_host = wb_info.top_host || "*";
    wbinfo.wombat_opts = wbinfo.wombat_opts || {};
    var wbAutoFetchWorkerPrefix = (wb_info.auto_fetch_worker_prefix || wb_info.static_prefix) + 'autoFetchWorkerProxyMode.js';
    var WBAutoFetchWorker;

    function init_seeded_random(seed) {
        // Adapted from:
        // http://indiegamr.com/generate-repeatable-random-numbers-in-js/

        $wbwindow.Math.seed = parseInt(seed);

        function seeded_random() {
            $wbwindow.Math.seed = ($wbwindow.Math.seed * 9301 + 49297) % 233280;
            var rnd = $wbwindow.Math.seed / 233280;

            return rnd;
        }

        $wbwindow.Math.random = seeded_random;
    }

    function init_crypto_random() {
        if (!$wbwindow.crypto || !$wbwindow.Crypto) {
            return;
        }

        var orig_getrandom = $wbwindow.Crypto.prototype.getRandomValues;

        var new_getrandom = function (array) {
            for (var i = 0; i < array.length; i++) {
                array[i] = parseInt($wbwindow.Math.random() * 4294967296);
            }
            return array;
        };

        $wbwindow.Crypto.prototype.getRandomValues = new_getrandom;
        $wbwindow.crypto.getRandomValues = new_getrandom;
    }

    //============================================
    function init_fixed_ratio() {
        // otherwise, just set it
        $wbwindow.devicePixelRatio = 1;

        // prevent changing, if possible
        if (Object.defineProperty) {
            try {
                // fixed pix ratio
                Object.defineProperty($wbwindow, "devicePixelRatio", {value: 1, writable: false});
            } catch (e) {
            }
        }
    }

    //========================================
    function init_date_override(timestamp) {
        timestamp = parseInt(timestamp) * 1000;
        //var timezone = new Date().getTimezoneOffset() * 60 * 1000;
        // Already UTC!
        var timezone = 0;
        var start_now = $wbwindow.Date.now();
        var timediff = start_now - (timestamp - timezone);

        if ($wbwindow.__wb_Date_now) {
            return;
        }

        var orig_date = $wbwindow.Date;

        var orig_utc = $wbwindow.Date.UTC;
        var orig_parse = $wbwindow.Date.parse;
        var orig_now = $wbwindow.Date.now;

        $wbwindow.__wb_Date_now = orig_now;

        $wbwindow.Date = function (Date) {
            return function (A, B, C, D, E, F, G) {
                // Apply doesn't work for constructors and Date doesn't
                // seem to like undefined args, so must explicitly
                // call constructor for each possible args 0..7
                if (A === undefined) {
                    return new Date(orig_now() - timediff);
                } else if (B === undefined) {
                    return new Date(A);
                } else if (C === undefined) {
                    return new Date(A, B);
                } else if (D === undefined) {
                    return new Date(A, B, C);
                } else if (E === undefined) {
                    return new Date(A, B, C, D);
                } else if (F === undefined) {
                    return new Date(A, B, C, D, E);
                } else if (G === undefined) {
                    return new Date(A, B, C, D, E, F);
                } else {
                    return new Date(A, B, C, D, E, F, G);
                }
            }
        }($wbwindow.Date);

        $wbwindow.Date.prototype = orig_date.prototype;

        $wbwindow.Date.now = function () {
            return orig_now() - timediff;
        };

        $wbwindow.Date.UTC = orig_utc;
        $wbwindow.Date.parse = orig_parse;

        $wbwindow.Date.__WB_timediff = timediff;

        Object.defineProperty($wbwindow.Date.prototype, "constructor", {value: $wbwindow.Date});
    }

    //============================================
    function init_disable_notifications() {
        if (window.Notification) {
            window.Notification.requestPermission = function (callback) {
                if (callback) {
                    callback("denied");
                }

                return Promise.resolve("denied");
            };
        }

        if (window.geolocation) {
            var disabled = function (success, error, options) {
                if (error) {
                    error({"code": 2, "message": "not available"});
                }
            };

            window.geolocation.getCurrentPosition = disabled;
            window.geolocation.watchPosition = disabled;
        }
    }

    function initAutoFetchWorker() {
        if (!$wbwindow.Worker) {
            return;
        }

        var isTop = $wbwindow.self === $wbwindow.top;

        function AutoFetchWorkerProxyMode() {
            if (!(this instanceof AutoFetchWorkerProxyMode)) {
                return new AutoFetchWorkerProxyMode();
            }
            this.checkIntervalTime = 15000;
            this.checkIntervalCB = this.checkIntervalCB.bind(this);
            this.elemSelector = ['img', 'source', 'video', 'audio'].map(function (which) {
                if (which === 'source') {
                    return ['picture > ', 'video > ', 'audio >'].map(function (parent) {
                        return parent + which + '[srcset], ' + parent + which + '[data-srcset], ' + parent + which + '[data-src]'
                    }).join(', ');
                } else {
                    return which + '[srcset], ' + which + '[data-srcset], ' + which + '[data-src]';
                }
            }).join(', ');

            if (isTop) {
                // Cannot directly load our worker from the proxy origin into the current origin
                // however we fetch it from proxy origin and can blob it into the current origin :)
                var self = this;
                fetch(wbAutoFetchWorkerPrefix)
                    .then(function (res) {
                        return res.text().then(function (text) {
                            var blob = new Blob([text], {"type": "text/javascript"});
                            self.worker = new $wbwindow.Worker(URL.createObjectURL(blob));
                            // use our origins reference to the document in order for us to parse stylesheets :/
                            self.styleTag = document.createElement('style');
                            self.styleTag.id = '$wrStyleParser$';
                            document.documentElement.appendChild(self.styleTag);
                            self.startCheckingInterval();
                        });
                    });
            } else {
                // add only the portions of the worker interface we use since we are not top and if in proxy mode start check polling
                this.worker = {
                    "postMessage": function (msg) {
                        if (!msg.wb_type) {
                            msg = {'wb_type': 'aaworker', 'msg': msg};
                        }
                        $wbwindow.top.postMessage(msg, '*');
                    },
                    "terminate": function () {
                    }
                };
                this.startCheckingInterval();
            }
        }

        AutoFetchWorkerProxyMode.prototype.startCheckingInterval = function () {
            // if document ready state is complete do first extraction and start check polling
            // otherwise wait for document ready state to complete to extract and start check polling
            var self = this;
            if ($wbwindow.document.readyState === "complete") {
                this.extractFromLocalDoc();
                setInterval(this.checkIntervalCB, this.checkIntervalTime);
            } else {
                var i = setInterval(function () {
                    if ($wbwindow.document.readyState === "complete") {
                        self.extractFromLocalDoc();
                        clearInterval(i);
                        setInterval(self.checkIntervalCB, self.checkIntervalTime);
                    }
                }, 1000);
            }
        };

        AutoFetchWorkerProxyMode.prototype.checkIntervalCB = function () {
            this.extractFromLocalDoc();
        };

        AutoFetchWorkerProxyMode.prototype.terminate = function () {
            // terminate the worker, a no op when not replay top
            this.worker.terminate();
        };

        AutoFetchWorkerProxyMode.prototype.postMessage = function (msg, deferred) {
            if (deferred) {
                var self = this;
                return Promise.resolve().then(function () {
                    self.worker.postMessage(msg);
                });
            }
            this.worker.postMessage(msg);
        };

        AutoFetchWorkerProxyMode.prototype.extractMediaRules = function (rules, href) {
            // We are in proxy mode and must include a URL to resolve relative URLs in media rules
            if (!rules) return [];
            var rvlen = rules.length;
            var text = [];
            var rule;
            for (var i = 0; i < rvlen; ++i) {
                rule = rules[i];
                if (rule.type === CSSRule.MEDIA_RULE) {
                    text.push({"cssText": rule.cssText, "resolve": href});
                }
            }
            return text;
        };

        AutoFetchWorkerProxyMode.prototype.corsCSSFetch = function (href) {
            // because this JS in proxy mode operates as it would on the live web
            // the rules of CORS apply and we cannot rely on URLs being rewritten correctly
            // fetch the cross origin css file and then parse it using a style tag to get the rules
            var url = location.protocol + '//' + wb_info.proxy_magic + '/proxy-fetch/' + href;
            var aaw = this;
            return fetch(url).then(function (res) {
                return res.text().then(function (text) {
                    aaw.styleTag.textContent = text;
                    var sheet = aaw.styleTag.sheet || {};
                    return aaw.extractMediaRules(sheet.cssRules || sheet.rules, href);
                });
            }).catch(function (error) {
                return [];
            });
        };

        AutoFetchWorkerProxyMode.prototype.shouldSkipSheet = function (sheet) {
            // we skip extracting rules from sheets if they are from our parsing style or come from pywb
            if (sheet.id === '$wrStyleParser$') return true;
            return !!(sheet.href && sheet.href.indexOf(wb_info.proxy_magic) !== -1);
        };

        AutoFetchWorkerProxyMode.prototype.getImgAVElems = function () {
            var elem, srcv, mod;
            var results = { 'srcset': [], 'src': []} ;
            var baseURI = $wbwindow.document.baseURI;
            var elems = $wbwindow.document.querySelectorAll(this.elemSelector);
            for (var i = 0; i < elems.length; i++) {
                elem = elems[i];
                // we want the original src value in order to resolve URLs in the worker when needed
                srcv = elem.src ? elem.src : null;
                // get the correct mod in order to inform the backing worker where the URL(s) are from
                mod = elem.tagName === "SOURCE" ?
                    elem.parentElement.tagName === "PICTURE" ? 'im_' : 'oe_'
                    : elem.tagName === "IMG" ? 'im_' : 'oe_';
                if (elem.srcset) {
                    results.srcset.push({ 'srcset': elem.srcset, 'resolve': srcv || baseURI, 'mod': mod });
                }
                if (elem.dataset.srcset) {
                    results.srcset.push({ 'srcset': elem.dataset.srcset, 'resolve': srcv || baseURI, 'mod': mod });
                }
                if (elem.dataset.src) {
                    results.src.push({'src': elem.dataset.src, 'resolve': srcv || baseURI, 'mod': mod});
                }
                if (elem.tagName === "SOURCE" && srcv) {
                    results.src.push({'src': srcv, 'resolve': baseURI, 'mod': mod});
                }
            }
            return results;
        };

        AutoFetchWorkerProxyMode.prototype.extractFromLocalDoc = function () {
            var media = [];
            var deferredMediaURLS = [];
            var sheet;
            var resolve;
            // We must use the window reference passed to us to access this origins stylesheets
            var styleSheets = $wbwindow.document.styleSheets;
            for (var i = 0; i < styleSheets.length; i++) {
                sheet = styleSheets[i];
                // if the sheet belongs to our parser node we must skip it
                if (!this.shouldSkipSheet(sheet)) {
                    try {
                        // if no error is thrown due to cross origin sheet the urls then just add
                        // the resolved URLS if any to the media urls array
                        if (sheet.cssRules != null) {
                            resolve = sheet.href || $wbwindow.document.baseURI;
                            media = media.concat(this.extractMediaRules(sheet.cssRules, resolve));
                        } else if (sheet.href != null) {
                            // depending on the browser cross origin stylesheets will have their
                            // cssRules property null but href non-null
                            deferredMediaURLS.push(this.corsCSSFetch(sheet.href));
                        }
                    } catch (error) {
                        // the stylesheet is cross origin and we must re-fetch via PYWB to get the contents for checking
                        deferredMediaURLS.push(this.corsCSSFetch(sheet.href));
                    }
                }
            }
            // We must use the window reference passed to us to access this origins elements with srcset attr
            // like cssRule handling we must include a URL to resolve relative URLs by
            var results = this.getImgAVElems();
            var msg = { 'type': 'values' };
            // send what we have extracted, if anything, to the worker for processing
            if (media.length > 0) {
                msg.media = media;
            }
            if (results.srcset) {
                msg.srcset = results.srcset;
            }
            if (results.src) {
                msg.src = results.src;
            }
            if (msg.media || msg.srcset || msg.src) {
                this.postMessage(msg);
            }

            if (deferredMediaURLS.length > 0) {
                // wait for all our deferred fetching and extraction of cross origin
                // stylesheets to complete and then send those values, if any, to the worker
                var aaw = this;
                Promise.all(deferredMediaURLS).then(function (values) {
                    var results = [];
                    while (values.length > 0) {
                        results = results.concat(values.shift());
                    }
                    if (results.length > 0) {
                        aaw.postMessage({'type': 'values', 'media': results});
                    }
                });
            }
        };

        WBAutoFetchWorker = new AutoFetchWorkerProxyMode();

        if (isTop) {
            $wbwindow.addEventListener("message", function (event) {
                if (event.data && event.data.wb_type === 'aaworker') {
                    WBAutoFetchWorker.postMessage(event.data.msg);
                }
            }, false);
        }
    }

    if (wbinfo.enable_auto_fetch && wbinfo.is_live) {
        initAutoFetchWorker();
    }

    // proxy mode overrides
    // Random
    init_seeded_random(wbinfo.wombat_sec);

    // Crypto Random
    init_crypto_random();

    // set fixed pixel ratio
    init_fixed_ratio();

    // Date
    init_date_override(wbinfo.wombat_sec);

    // disable notifications
    init_disable_notifications();

    return {};
};

window._WBWombat = _WBWombat;

window._WBWombatInit = function (wbinfo) {
    if (!this._wb_wombat || !this._wb_wombat.actual) {
        this._wb_wombat = new _WBWombat(this, wbinfo);
        this._wb_wombat.actual = true;
    } else if (!this._wb_wombat) {
        console.warn("_wb_wombat missing!");
    }
};



