/*
Copyright(c) 2013-2014 Ilya Kreymer. Released under the GNU General Public License.

This file is part of pywb, https://github.com/ikreymer/pywb

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
// Wombat JS-Rewriting Library v2.2
//============================================
_WBWombat = (function() {

    // Globals
    var wb_replay_prefix;
    var wb_replay_date_prefix;
    var wb_capture_date_part;
    var wb_orig_scheme;
    var wb_orig_host;

    var wb_wombat_updating = false;

    // custom options
    var wb_opts;

    //============================================
    function is_host_url(str) {
        // Good guess that's its a hostname
        if (str.indexOf("www.") == 0) {
            return true;
        }

        // hostname:port (port required)
        var matches = str.match(/^[\w-]+(\.[\w-_]+)+(:\d+)(\/|$)/);
        if (matches && (matches[0].length < 64)) {
            return true;
        }

        // ip:port
        matches = str.match(/^\d+\.\d+\.\d+\.\d+(:\d+)?(\/|$)/);
        if (matches && (matches[0].length < 64)) {
            return true;
        }

        return false;
    }

    //============================================
    function starts_with(string, arr_or_prefix) {
        if (arr_or_prefix instanceof Array) {
            for (var i = 0; i < arr_or_prefix.length; i++) {
                if (string.indexOf(arr_or_prefix[i]) == 0) {
                    return arr_or_prefix[i];
                }
            }
        } else if (string.indexOf(arr_or_prefix) == 0) {
            return arr_or_prefix;
        }

        return undefined;
    }

    //============================================
    function equals_any(string, arr) {
        for (var i = 0; i < arr.length; i++) {
            if (string === arr[i]) {
                return arr[i];
            }
        }
        return undefined;
    }

    //============================================
    function ends_with(str, suffix) {
        if (str.indexOf(suffix, str.length - suffix.length) !== -1) {
            return suffix;
        } else {
            return undefined;
        }
    }

    //============================================
    var rewrite_url = rewrite_url_;

    function rewrite_url_debug(url) {
        var rewritten = rewrite_url_(url);
        if (url != rewritten) {
            console.log('REWRITE: ' + url + ' -> ' + rewritten);
        } else {
            console.log('NOT REWRITTEN ' + url);
        }
        return rewritten;
    }

    //============================================
    var HTTP_PREFIX = "http://";
    var HTTPS_PREFIX = "https://";
    var REL_PREFIX = "//";

    var VALID_PREFIXES = [HTTP_PREFIX, HTTPS_PREFIX, REL_PREFIX];
    var IGNORE_PREFIXES = ["#", "about:", "data:", "mailto:", "javascript:"];

    var BAD_PREFIXES;

    function init_bad_prefixes(prefix) {
        BAD_PREFIXES = ["http:" + prefix, "https:" + prefix,
                        "http:/" + prefix, "https:/" + prefix];
    }

    var SRC_TAGS = ["IMG", "SCRIPT", "VIDEO", "AUDIO", "SOURCE", "EMBED", "INPUT"];

    var REWRITE_ATTRS = ["src", "href", "poster"];

    //============================================
    function rewrite_url_(url) {
        // If undefined, just return it
        if (!url) {
            return url;
        }

        var urltype_ = (typeof url);

        // If object, use toString
        if (urltype_ == "object") {
            url = url.toString();
        } else if (urltype_ != "string") {
            return url;
        }

        // proxy mode: If no wb_replay_prefix, only rewrite https:// -> http://
        if (!wb_replay_prefix) {
            if (starts_with(url, HTTPS_PREFIX)) {
                return HTTP_PREFIX + url.substr(HTTPS_PREFIX.length);
            } else {
                return url;
            }
        }

        // just in case wombat reference made it into url!
        url = url.replace("WB_wombat_", "");

        // ignore anchors, about, data
        if (starts_with(url, IGNORE_PREFIXES)) {
            return url;
        }

        // OPTS: additional ignore prefixes
        if (wb_opts.no_rewrite_prefixes) {
            if (starts_with(url, wb_opts.no_rewrite_prefixes)) {
                return url;
            }
        }

        // If starts with prefix, no rewriting needed
        // Only check replay prefix (no date) as date may be different for each
        // capture
        if (starts_with(url, wb_replay_prefix) || starts_with(url, window.location.origin + wb_replay_prefix)) {
            return url;
        }

        // If server relative url, add prefix and original host
        if (url.charAt(0) == "/" && !starts_with(url, REL_PREFIX)) {

            // Already a relative url, don't make any changes!
            if (wb_capture_date_part && url.indexOf(wb_capture_date_part) >= 0) {
                return url;
            }

            return wb_replay_date_prefix + wb_orig_host + url;
        }

        // If full url starting with http://, https:// or //
        // add rewrite prefix
        var prefix = starts_with(url, VALID_PREFIXES);

        if (prefix) {
            // if already rewriting url, must still check scheme
            if (starts_with(url, prefix + window.location.host + '/')) {
                var curr_scheme = window.location.protocol + '//';

                // replace scheme to ensure using the correct server scheme
                if (starts_with(url, wb_orig_scheme) && (wb_orig_scheme != curr_scheme)) {
                    url = curr_scheme + url.substring(wb_orig_scheme.length);
                }
                return url;
            }
            return wb_replay_date_prefix + url;
        }

        // Check for common bad prefixes and remove them
        prefix = starts_with(url, BAD_PREFIXES);

        if (prefix) {
            url = extract_orig(url);
            return wb_replay_date_prefix + url;
        }

        // May or may not be a hostname, call function to determine
        // If it is, add the prefix and make sure port is removed
        if (is_host_url(url) && !starts_with(url, window.location.host + '/')) {
            return wb_replay_date_prefix + wb_orig_scheme + url;
        }

        return url;
    }

    //============================================
    function extract_orig(href) {
        if (!href) {
            return "";
        }

        // proxy mode: no extraction needed
        if (!wb_replay_prefix) {
            return href;
        }

        href = href.toString();

        var index = href.indexOf("/http", 1);

        // extract original url from wburl
        if (index > 0) {
            href = href.substr(index + 1);
        } else {
            index = href.indexOf(wb_replay_prefix);
            if (index >= 0) {
                href = href.substr(index + wb_replay_prefix.length);
            }
            if ((href.length > 4) &&
                (href.charAt(2) == "_") &&
                (href.charAt(3) == "/")) {
                href = href.substr(4);
            }

            if (!starts_with(href, "http")) {
                href = HTTP_PREFIX + href;
            }
        }

        // remove trailing slash
        if (ends_with(href, "/")) {
            href = href.substring(0, href.length - 1);
        }

        return href;
    }

    //============================================
    // Define custom property
    function def_prop(obj, prop, value, set_func, get_func) {
        var key = "_" + prop;
        obj[key] = value;

        try {
            Object.defineProperty(obj, prop, {
                configurable: false,
                enumerable: true,
                set: function(newval) {
                    var result = set_func.call(obj, newval);
                    if (result != undefined) {
                        obj[key] = result;
                    }
                },
                get: function() {
                    if (get_func) {
                        return get_func.call(obj, obj[key]);
                    } else {
                        return obj[key];
                    }
                }
            });
            return true;
        } catch (e) {
            var info = "Can't redefine prop " + prop;
            if (obj && obj.tagName) {
                info += " on " + obj.tagName;
            }
            console.log(info);
            obj[prop] = value;
            return false;
        }
    }

    //============================================
    //Define WombatLocation

    function WombatLocation(loc) {
        this._orig_loc = loc;
        this._orig_href = loc.href;

        // Rewrite replace and assign functions
        this.replace = function(url) {
            return this._orig_loc.replace(rewrite_url(url));
        }
        this.assign = function(url) {
            var new_url = rewrite_url(url);
            if (new_url != this._orig_href) {
                return this._orig_loc.assign(new_url);
            }
        }
        this.reload = loc.reload;

        // Adapted from:
        // https://gist.github.com/jlong/2428561
        var parser = document.createElement('a');
        var href = extract_orig(this._orig_href);
        parser.href = href;

        this._autooverride = false;

        var _set_hash = function(hash) {
            this._orig_loc.hash = hash;
            return this._orig_loc.hash;
        }

        var _get_hash = function() {
            return this._orig_loc.hash;
        }

        var _get_url_with_hash = function(url) {
            return url + this._orig_loc.hash;
        }

        href = parser.getAttribute("href");
        var hash = parser.hash;

        if (hash) {
            var hidx = href.lastIndexOf("#");
            if (hidx > 0) {
                href = href.substring(0, hidx);
            }
        }

        if (Object.defineProperty) {
            var res1 = def_prop(this, "href", href,
                               this.assign,
                               _get_url_with_hash);

            var res2 = def_prop(this, "hash", parser.hash,
                               _set_hash,
                               _get_hash);

            this._autooverride = res1 && res2;
        } else {
            this.href = href;
            this.hash = parser.hash;
        }

        this.host = parser.host;
        this.hostname = parser.hostname;

        if (parser.origin) {
            this.origin = parser.origin;
        }

        this.pathname = parser.pathname;
        this.port = parser.port
        this.protocol = parser.protocol;
        this.search = parser.search;

        this.toString = function() {
            return this.href;
        }

        // Copy any remaining properties
        for (prop in loc) {
            if (this.hasOwnProperty(prop)) {
                continue;
            }

            if ((typeof loc[prop]) != "function") {
                this[prop] = loc[prop];
            }
        }
    }

    //============================================
    function update_location(req_href, orig_href, actual_location, wombat_loc) {
        if (!req_href) {
            return;
        }

        if (req_href == orig_href) {
            // Reset wombat loc to the unrewritten version
            //if (wombat_loc) {
            //    wombat_loc.href = extract_orig(orig_href);
            //}
            return;
        }


        var ext_orig = extract_orig(orig_href);
        var ext_req = extract_orig(req_href);

        if (!ext_orig || ext_orig == ext_req) {
            return;
        }

        var final_href = rewrite_url(req_href);

        console.log(actual_location.href + ' -> ' + final_href);

        actual_location.href = final_href;
    }

    //============================================
    function check_location_change(wombat_loc, is_top) {
        var locType = (typeof wombat_loc);

        var actual_location = (is_top ? window.top.location : window.location);

        // String has been assigned to location, so assign it
        if (locType == "string") {
            update_location(wombat_loc, actual_location.href, actual_location);

        } else if (locType == "object") {
            update_location(wombat_loc.href,
                            wombat_loc._orig_href,
                            actual_location);
        }
    }

    //============================================
    function check_all_locations() {
        if (wb_wombat_updating) {
            return false;
        }

        wb_wombat_updating = true;

        check_location_change(window.WB_wombat_location, false);

        // Only check top if its a different window
        if (window.WB_wombat_location != window.top.WB_wombat_location) {
            check_location_change(window.top.WB_wombat_location, true);
        }

//        lochash = window.WB_wombat_location.hash;
//
//        if (lochash) {
//            window.location.hash = lochash;
//
//            //if (window.top.update_wb_url) {
//            //    window.top.location.hash = lochash;
//            //}
//        }

        wb_wombat_updating = false;
    }

    //============================================
    function init_seeded_random(seed) {
        // Adapted from:
        // http://indiegamr.com/generate-repeatable-random-numbers-in-js/

        Math.seed = parseInt(seed);
        function seeded_random() {
            Math.seed = (Math.seed * 9301 + 49297) % 233280;
            var rnd = Math.seed / 233280;

            return rnd;
        }

        Math.random = seeded_random;
    }

    //============================================
    function copy_history_func(history, func_name) {
        var orig_func = history[func_name];

        if (!orig_func) {
            return;
        }

        history['_orig_' + func_name] = orig_func;

        function rewritten_func(state_obj, title, url) {
            url = rewrite_url(url);
            return orig_func.call(history, state_obj, title, url);
        }

        history[func_name] = rewritten_func;

        return rewritten_func;
    }

    //============================================
    function init_ajax_rewrite() {
        if (!window.XMLHttpRequest ||
            !window.XMLHttpRequest.prototype ||
            !window.XMLHttpRequest.prototype.open) {
            return;
        }

        var orig = window.XMLHttpRequest.prototype.open;

        function open_rewritten(method, url, async, user, password) {
            if (!this._no_rewrite) {
                url = rewrite_url(url);
            }

            // defaults to true
            if (async != false) {
                async = true;
            }

            return orig.call(this, method, url, async, user, password);
        }

        window.XMLHttpRequest.prototype.open = open_rewritten;
    }

    //============================================
    function init_setAttribute_override()
    {
        if (!window.Element ||
            !window.Element.prototype ||
            !window.Element.prototype.setAttribute) {
            return;
        }

        var orig_setAttribute = window.Element.prototype.setAttribute;

        Element.prototype.setAttribute = function(name, value) {
            if (name) {
                var lowername = name.toLowerCase();
                if (equals_any(lowername, REWRITE_ATTRS) && typeof(value) == "string") {
                    if (!this._no_rewrite) {
                        var old_value = value;
                        var new_value = rewrite_url(value);
                        if (new_value != old_value) {
                            this._no_rewrite = true;
                        }
                        value = new_value;
                    }
                }
            }
            orig_setAttribute.call(this, name, value);
        };
    }

    //============================================
    function init_createElementNS_fix()
    {
        if (!document.createElementNS ||
            !Document.prototype.createElementNS) {
            return;
        }

        document._orig_createElementNS = document.createElementNS;
        var createElementNS_fix = function(namespaceURI, qualifiedName)
        {
            namespaceURI = extract_orig(namespaceURI);
            return document._orig_createElementNS(namespaceURI, qualifiedName);
        }

        Document.prototype.createElementNS = createElementNS_fix;
        document.createElementNS = createElementNS_fix;
    }

    //============================================
    function init_image_override() {
        window.__Image = window.Image;
        window.Image = function (Image) {
            return function (width, height) {
                var image = new Image(width, height);
                override_attr(image, "src");
                return image;
            }
        }(window.Image);
    }

    //============================================
    function init_date_override(timestamp) {
        timestamp = parseInt(timestamp) * 1000;
        var timezone = new Date().getTimezoneOffset() * 60 * 1000;
        var timediff = Date.now() - (timestamp - timezone);

        window.__Date = window.Date;
        window.__Date_now = window.Date.now;
        var utc = window.Date.UTC;
        var parse = window.Date.parse;

        window.Date = function (Date) {
            return function (A, B, C, D, E, F, G) {
                // Apply doesn't work for constructors and Date doesn't
                // seem to like undefined args, so must explicitly
                // call constructor for each possible args 0..7
                if (A === undefined) {
                    return new Date(window.Date.now());
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
        }(window.Date);

        window.Date.prototype = window.__Date.prototype;

        window.Date.now = function() {
            return __Date_now() - timediff;
        }

        window.Date.UTC = utc;
        window.Date.parse = parse;
    }

    //============================================
    function init_worker_override() {
        if (!window.Worker) {
            return;
        }

        // for now, disabling workers until override of worker content can be supported
        // hopefully, pages depending on workers will have a fallback
        window.Worker = undefined;
    }


    //============================================
    function init_mutation_obs() {
        if (!window.MutationObserver) {
            return;
        }

        var m = new MutationObserver(function(records, observer)
        {
            for (var i = 0; i < records.length; i++) {
                var r = records[i];
                if (r.type == "attributes" && r.attributeName == "style") {
                    var style = r.target.style.cssText;
                    if (style.indexOf("url(") > 0) {
                        var new_style = rewrite_style(style);
                        if (new_style != style) {
                            r.target.style.cssText = new_style;
                        }
                    }
                }
            }
        });

        m.observe(document.documentElement, {childList: false,
                                  attributes: true,
                                  subtree: true,
                                  //attributeOldValue: true,
                                  attributeFilter: ["style"]});
    }

    //============================================
    function rewrite_attr(elem, name, func) {
        if (!elem || !elem.getAttribute) {
            return;
        }

        var value = elem.getAttribute(name);

        if (!value) {
            return;
        }

        if (starts_with(value, "javascript:")) {
            return;
        }

        if (func) {
            value = func(value);
        }

        // this now handles the actual rewrite
        elem.setAttribute(name, value);
    }

    //============================================
    function rewrite_style(value)
    {
        STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/g;

        function style_replacer(match, n1, n2, n3, offset, string) {
            return n1 + rewrite_url(n2) + n3;
        }

        return value.replace(STYLE_REGEX, style_replacer);
    }

    //============================================
    function rewrite_elem(elem)
    {
        rewrite_attr(elem, "src");
        rewrite_attr(elem, "href");
        rewrite_attr(elem, "style", rewrite_style);

        if (elem && elem.getAttribute && elem.getAttribute("crossorigin")) {
            elem.removeAttribute("crossorigin");
        }
    }

    //============================================
    function override_attr(obj, attr) {
        var setter = function(orig) {
            //var val = rewrite_url(orig);
            var val = orig;
            this.setAttribute(attr, val);
            return val;
        }

        var getter = function(val) {
            var res = this.getAttribute(attr);
            return res;
        }

        var curr_src = obj.getAttribute(attr);

        def_prop(obj, attr, curr_src, setter, getter);
    }

    //============================================
    function init_dom_override() {
        if (!Node || !Node.prototype) {
            return;
        }

        function replace_dom_func(funcname) {
            var orig = Node.prototype[funcname];

            Node.prototype[funcname] = function() {
                var child = arguments[0];

                rewrite_elem(child);

                var desc;

                if (child instanceof DocumentFragment) {
                    desc = child.querySelectorAll("a[href], iframe[src]");
                } else if (child.getElementsByTagName) {
                    desc = child.getElementsByTagName("*");
                }

                if (desc) {
                    for (var i = 0; i < desc.length; i++) {
                        rewrite_elem(desc[i]);
                    }
                }

                var created = orig.apply(this, arguments);

                if (!created) {
                    return;
                }

                if (created.tagName == "IFRAME") {
                    if (created.contentWindow) {
                        created.contentWindow.window.WB_wombat_location = created.contentWindow.window.location;
                    }

                    override_attr(created, "src");
                } else if (created.tagName && equals_any(created.tagName, SRC_TAGS)) {
                    override_attr(created, "src");
                }

                return created;
            }
        }

        replace_dom_func("appendChild");
        replace_dom_func("insertBefore");
        replace_dom_func("replaceChild");
    }

    //============================================
    function init_postmessage_override()
    {
        if (!window.postMessage) {
            return;
        }

        var orig = window.postMessage;

        var postmessage_rewritten = function(message, targetOrigin, transfer) {
            message = {"origin": targetOrigin, "message": message};

            if (targetOrigin && targetOrigin != "*") {
                targetOrigin = window.location.origin;
            }

            return orig.call(this, message, targetOrigin, transfer);
        }

        window.postMessage = postmessage_rewritten;

        if (Window.prototype.postMessage) {
            window.Window.prototype.postMessage = postmessage_rewritten;
        }

        for (var i = 0; i < window.frames.length; i++) {
            try {
                window.frames[i].postMessage = postmessage_rewritten;
            } catch (e) {
                console.log(e);
            }
        }


        window._orig_addEventListener = window.addEventListener;

        window.addEventListener = function(type, listener, useCapture) {
            if (type == "message") {
                var orig_listener = listener;
                listener = function(event) {

                    var ne = new MessageEvent("message",
                                    {"bubbles": event.bubbles,
                                     "cancelable": event.cancelable,
                                     "data": event.data.message,
                                     "origin": event.data.origin,
                                     "lastEventId": event.lastEventId,
                                     "source": event.source,
                                     "ports": event.ports});

                    return orig_listener(ne);
                }
            }

            return window._orig_addEventListener(type, listener, useCapture);
        }
    }

    //============================================
    function init_open_override()
    {
        if (!Window.prototype.open) {
            return;
        }

        var orig = Window.prototype.open;

        var open_rewritten = function(strUrl, strWindowName, strWindowFeatures) {
            strUrl = rewrite_url(strUrl);
            return orig.call(this, strUrl, strWindowName, strWindowFeatures);
        }

        window.open = open_rewritten;
        window.Window.prototype.open = open_rewritten;

        for (var i = 0; i < window.frames.length; i++) {
            try {
                window.frames[i].open = open_rewritten;
            } catch (e) {
                console.log(e);
            }
        }
    }

    //============================================
    function init_cookies_override()
    {
        var cookie_path_regex = /\bPath=\'?\"?([^;'"\s]+)/i;

        var get_cookie = function() {
            return document.cookie;
        }

        var set_cookie = function(value) {
            var matched = value.match(cookie_path_regex);

            // if has cookie path, rewrite and replace
            if (matched) {
                var rewritten = rewrite_url(matched[1]);
                value = value.replace(matched[1], rewritten);
            }

            document.cookie = value;
        }

        def_prop(document, "WB_wombat_cookie", document.cookie,
                set_cookie,
                get_cookie);
    }

    //============================================
    function init_write_override()
    {
        var orig_doc_write = document.write;

        document.write = function(string) {
            var write_doc = new DOMParser().parseFromString(string, "text/html");

            if (!write_doc) {
                return;
            }

            if (write_doc.head && document.head) {
                var elems = write_doc.head.children;

                for (var i = 0; i < elems.length; i++) {
                    // Call orig write to ensure same execution order and placement
                    rewrite_elem(elems[i]);
                    orig_doc_write.call(this, elems[i].outerHTML);
                }
            }

            if (write_doc.body && document.body) {
                var elems = write_doc.body.children;

                for (var i = 0; i < elems.length; i++) {
                    // Call orig write to ensure same execution order and placement
                    rewrite_elem(elems[i]);
                    orig_doc_write.call(this, elems[i].outerHTML);
                }
            }
        }
    }

    //============================================
    function wombat_init(wbinfo) {
        wb_replay_prefix = wbinfo.prefix;

        wb_opts = wbinfo.wombat_opts || {};

        if (wb_replay_prefix) {
            wb_replay_date_prefix = wb_replay_prefix + wbinfo.wombat_ts + wbinfo.mod + "/";

            if (wbinfo.wombat_ts.length > 0) {
                wb_capture_date_part = "/" + wbinfo.wombat_ts + "/";
            } else {
                wb_capture_date_part = "";
            }

            wb_orig_scheme = wbinfo.wombat_scheme + '://';

            wb_orig_host = wb_orig_scheme + wbinfo.wombat_host;

            init_bad_prefixes(wb_replay_prefix);
        }

        // Location
        var wombat_location = new WombatLocation(window.location);

        if (wombat_location._autooverride) {

            var setter = function(val) {
                if (typeof(val) == "string") {
                    if (starts_with(val, "about:")) {
                        return undefined;
                    }
                    this._WB_wombat_location.href = val;
                }
            }

            def_prop(window, "WB_wombat_location", wombat_location, setter);
            def_prop(document, "WB_wombat_location", wombat_location, setter);
        } else {
            window.WB_wombat_location = wombat_location;
            document.WB_wombat_location = wombat_location;

            // Check quickly after page load
            setTimeout(check_all_locations, 500);

            // Check periodically every few seconds
            setInterval(check_all_locations, 500);
        }

        var is_framed = (window.top.wbinfo && window.top.wbinfo.is_frame);

        function find_next_top(win) {
            while ((win.parent != win) && (win.parent != win.top)) {
                win = win.parent;
            }
            return win;
        }

        if (window.location != window.top.location) {
            window.__orig_parent = window.parent;
            if (is_framed) {
                window.top.WB_wombat_location = window.WB_wombat_location;

                window.WB_wombat_top = find_next_top(window);

                if (window.parent == window.top) {
                    window.parent = window;

                    // Disable frameElement also as this should be top frame
                    if (Object.defineProperty) {
                        Object.defineProperty(window, "frameElement", {value: undefined, configurable: false});
                    }
                }
            } else {
                window.top.WB_wombat_location = new WombatLocation(window.top.location);
                window.WB_wombat_top = window.top;
            }
        } else {
            window.WB_wombat_top = window.top;
        }

        //if (window.opener) {
        //    window.opener.WB_wombat_location = copy_location_obj(window.opener.location);
        //}

        // Domain
        document.WB_wombat_domain = wbinfo.wombat_host;
        document.WB_wombat_referrer = extract_orig(document.referrer);


        // History
        copy_history_func(window.history, 'pushState');
        copy_history_func(window.history, 'replaceState');

        // open
        init_open_override();

        // postMessage
        // OPT skip
        if (!wb_opts.skip_postmessage) {
            init_postmessage_override();
        }

        // write
        init_write_override();

        // Ajax
        init_ajax_rewrite();
        init_worker_override();

        // Init mutation observer (for style only)
        init_mutation_obs();

        // setAttribute
        if (!wb_opts.skip_setAttribute) {
            init_setAttribute_override();
        }
        // ensure namespace urls are NOT rewritten
        init_createElementNS_fix();

        // Image
        init_image_override();

        // Cookies
        init_cookies_override();

        // DOM
        // OPT skip
        if (!wb_opts.skip_dom) {
            init_dom_override();
        }

        // Random
        init_seeded_random(wbinfo.wombat_sec);

        // Date
        init_date_override(wbinfo.wombat_sec);

        // expose functions
        this.extract_orig = extract_orig;
    }

    return wombat_init;

})();

window._WBWombat = _WBWombat;
