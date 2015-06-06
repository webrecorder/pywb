/*
Copyright(c) 2013-2015 Ilya Kreymer. Released under the GNU General Public License.

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
// Wombat JS-Rewriting Library v2.3
//============================================



_WBWombat = (function() {

var wombat_internal = function(window) {


    // Globals
    var wb_replay_prefix;
    var wb_replay_date_prefix;
    var wb_coll_prefix;
    var wb_coll_prefix_check;
    var wb_capture_date_part;
    var wb_orig_scheme;
    var wb_orig_host;

    var wb_setAttribute = window.Element.prototype.setAttribute;
    var wb_getAttribute = window.Element.prototype.getAttribute;

    var wb_info;

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

    var SRC_TAGS = ["IFRAME", "IMG", "SCRIPT", "VIDEO", "AUDIO", "SOURCE", "EMBED", "INPUT"];

    var HREF_TAGS = ["LINK", "A"];

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

        // A special case where the port somehow gets dropped
        // Check for this and add it back in, eg http://localhost/path/ -> http://localhost:8080/path/
        if (window.location.host != window.location.hostname) {
            if (starts_with(url, window.location.protocol + '//' + window.location.hostname + "/")) {
                url = url.replace("/" + window.location.hostname + "/", "/" + window.location.host + "/");
                return url;
            }
        }

        // If server relative url, add prefix and original host
        if (url.charAt(0) == "/" && !starts_with(url, REL_PREFIX)) {

            // Already a relative url, don't make any changes!
            if (wb_capture_date_part && url.indexOf(wb_capture_date_part) >= 0) {
                return url;
            }

            // relative collection 
            if ((url.indexOf(wb_info.coll) == 1) && (url.indexOf("http") > 1)) {
                var scheme_sep = url.indexOf(":/");
                if (scheme_sep > 0 && url[scheme_sep + 2] != '/') {
                    url = url.substring(0, scheme_sep + 2) + "/" + url.substring(scheme_sep + 2);
                }
                return url;
            }

            return wb_replay_date_prefix + wb_orig_host + url;
        }

        // If full url starting with http://, https:// or //
        // add rewrite prefix
        var prefix = starts_with(url, VALID_PREFIXES);

        if (prefix) {
            var prefix_host = prefix + window.location.host + '/';
            // if already rewritten url, must still check scheme
            if (starts_with(url, prefix_host)) {
                if (starts_with(url, wb_replay_prefix)) {
                    return url;
                }

                var curr_scheme = window.location.protocol + '//';
                var host = window.location.host + '/';
                var path = url.substring(prefix_host.length);
                var rebuild = false;

                if (path.indexOf(wb_coll_prefix_check) < 0 && url.indexOf("/static/") < 0) {
                    path = wb_coll_prefix + WB_wombat_location.origin + "/" + path;
                    rebuild = true;
                }
                
                // replace scheme to ensure using the correct server scheme
                //if (starts_with(url, wb_orig_scheme) && (wb_orig_scheme != curr_scheme)) {
                if (prefix != curr_scheme && prefix != REL_PREFIX) {
                    rebuild = true;
                }

                if (rebuild) {
                    url = curr_scheme + host + path;
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
        if (index < 0) {
            index = href.indexOf("///", 1);
        }

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
        //if (ends_with(href, "/")) {
        //    href = href.substring(0, href.length - 1);
        //}

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
            //var info = "Can't redefine prop " + prop;
            //console.log(info);
            //f (obj && obj.tagName) {
            //    info += " on " + obj.tagName;
            //}
            if (value != obj[prop]) {
                obj[prop] = value;
            }
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
            var new_url = rewrite_url(url);
            var orig = extract_orig(new_url);
            if (orig == this.href) {
                return orig;
            }
            return this._orig_loc.replace(new_url);
        }
        this.assign = function(url) {
            var new_url = rewrite_url(url);
            var orig = extract_orig(new_url);
            if (orig == this.href) {
                return orig;
            }
            return this._orig_loc.assign(new_url);
        }
        this.reload = loc.reload;

        // Adapted from:
        // https://gist.github.com/jlong/2428561
        var parser = window.document.createElement('a');
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
        //this.protocol = parser.protocol;
        this.protocol = window.location.protocol;
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
    function override_history_func(func_name) {
        if (!window.history) {
            return;
        }

        var orig_func = window.history[func_name];

        if (!orig_func) {
            return;
        }

        window.history['_orig_' + func_name] = orig_func;

        function rewritten_func(state_obj, title, url) {
            url = rewrite_url(url);
            return orig_func.call(this, state_obj, title, url);
        }

        window.history[func_name] = rewritten_func;
        if (window.History && window.History.prototype) {
            window.History.prototype[func_name] = rewritten_func;
        }

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

            result = orig.call(this, method, url, async, user, password);
            this.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
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
        wb_setAttribute = orig_setAttribute;

        window.Element.prototype._orig_setAttribute = orig_setAttribute;

        window.Element.prototype.setAttribute = function(name, value) {
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
    function init_getAttribute_override()
    {
        if (!window.Element ||
            !window.Element.prototype ||
            !window.Element.prototype.setAttribute) {
            return;
        }

        var orig_getAttribute = window.Element.prototype.getAttribute;
        wb_getAttribute = orig_getAttribute;

        window.Element.prototype.getAttribute = function(name) {
            var result = orig_getAttribute.call(this, name);

            if (equals_any(name.toLowerCase(), REWRITE_ATTRS)) {
                result = extract_orig(result);
            }

            return result;
        }

    }

    //============================================
    function init_createElement_override()
    {
        if (!window.document.createElement ||
            !window.Document.prototype.createElement) {
            return;
        }

        var orig_createElement = window.document.createElement;

        var createElement_override = function(tagName, skip)
        {
            var created = orig_createElement.call(this, tagName);
            if (!created) {
                return created;
            }
            if (!skip) {
                add_attr_overrides(tagName.toUpperCase(), created);
            } else {
                created._no_rewrite = true;
            }

            return created;
        }

        window.Document.prototype.createElement = createElement_override;
        window.document.createElement = createElement_override;
    }

    //============================================
    function init_createElementNS_fix()
    {
        if (!window.document.createElementNS ||
            !window.Document.prototype.createElementNS) {
            return;
        }

        var orig_createElementNS = window.document.createElementNS;

        var createElementNS_fix = function(namespaceURI, qualifiedName)
        {
            namespaceURI = extract_orig(namespaceURI);
            return orig_createElementNS.call(this, namespaceURI, qualifiedName);
        }

        window.Document.prototype.createElementNS = createElementNS_fix;
        window.document.createElementNS = createElementNS_fix;
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
        //var timezone = new Date().getTimezoneOffset() * 60 * 1000;
        // Already UTC!
        var timezone = 0;
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
    function init_mutation_obs(window) {
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

        m.observe(window.document.documentElement, {
            childList: false,
            attributes: true,
            subtree: true,
            //attributeOldValue: true,
            attributeFilter: ["style"]});
    }


    //============================================
    function init_href_src_obs(window)
    {
        if (!window.MutationObserver) {
            return;
        }

        var m = new MutationObserver(function(records, observer)
                                     {
            for (var i = 0; i < records.length; i++) {
                var r = records[i];
                if (r.type == "attributes") {
                    //var curr = wb_getAttribute(r.target, r.attributeName);
                    var curr = r.target.getAttribute(r.attributeName);
                    var new_url = rewrite_url(curr);
                    if (curr != new_url) {
                        wb_setAttribute.call(r.target, r.attributeName, new_url);
                    }
                }
            }
        });

        m.observe(window.document.documentElement, {
            childList: false,
            attributes: true,
            subtree: true,
            //attributeOldValue: true,
            attributeFilter: ["src", "href"]});

    }


    //============================================
    function init_node_insert_obs(window)
    {
        if (!window.MutationObserver) {
            return;
        }

        var m = new MutationObserver(function(records, observer)
                                     {
            for (var i = 0; i < records.length; i++) {
                var r = records[i];
                if (r.type == "childList") {
                    for (var j = 0; j < r.addedNodes.length; j++) {
                        // skip canonical link tag, should have been handled by server-side rewrite
                        // (maybe skip all links?)
                        if (r.addedNodes[j].tagName == "LINK" && r.addedNodes[j].rel == "canonical") {
                            continue;
                        }
                        add_attr_overrides(r.addedNodes[j].tagName, r.addedNodes[j]);
                        //rewrite_attr(r.addedNodes[j], "href", rewrite_url);
                        //rewrite_attr(r.addedNodes[j], "src", rewrite_url);
                        //if (r.addedNodes[j].tagName == "IFRAME") {
                        //    init_iframe_wombat(r.addedNodes[j]);
                        //}
                    }
                }
            }
        });

        m.observe(window.document.documentElement, {
            childList: true,
            subtree: true,
        });
    }

    //============================================
    function rewrite_attr(elem, name, func) {
        if (!elem || !elem.getAttribute) {
            return;
        }

        if (elem._no_rewrite) {
            return;
        }

        // already overwritten
        if (elem["_" + name]) {
            return;
        }

        var value = wb_getAttribute.call(elem, name);

        if (!value || starts_with(value, "javascript:")) {
            return;
        }

        var new_value = value;

        if (func) {
            new_value = func(value);
        }

        if (value != new_value) {
            wb_setAttribute.call(elem, name, new_value);
        }
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
        rewrite_attr(elem, "src", rewrite_url);
        rewrite_attr(elem, "href", rewrite_url);
        rewrite_attr(elem, "style", rewrite_style);

        if (elem && elem.getAttribute && elem.getAttribute("crossorigin")) {
            elem.removeAttribute("crossorigin");
        }
    }

    //============================================
    function rewrite_innerHTML(string) {
        var inner_doc = new DOMParser().parseFromString(string, "text/html");

        if (!inner_doc) {
            return string;
        }

        var new_html = "";

        if (inner_doc.head.innerHTML) {
            var elems = inner_doc.head.children;

            for (var i = 0; i < elems.length; i++) {
                // Call orig write to ensure same execution order and placement
                rewrite_elem(elems[i]);
            }
            new_html += inner_doc.head.innerHTML;
        }

        if (inner_doc.body.innerHTML) {
            var elems = inner_doc.body.children;

            for (var i = 0; i < elems.length; i++) {
                // Call orig write to ensure same execution order and placement
                rewrite_elem(elems[i]);
            }
            new_html += inner_doc.body.innerHTML;
        }

        return new_html;
    }

    //============================================
    function add_attr_overrides(tagName, created)
    {
        if (!created || created._src != undefined || created._href != undefined) {
            return;
        }

        if (equals_any(tagName, SRC_TAGS)) {
            override_attr(created, "src");
        } else if (equals_any(tagName, HREF_TAGS)) {
            override_attr(created, "href");
        }
    }

    //============================================
    function override_attr(obj, attr) {
        var setter = function(orig) {
            var val = rewrite_url(orig);
            wb_setAttribute.call(this, attr, val);
            return val;
        }

        var getter = function(val) {
            var res = this.getAttribute(attr);
            //res = extract_orig(res);
            return res;
        }

        var curr_src = obj.getAttribute(attr);

        def_prop(obj, attr, curr_src, setter, getter);
    }

    //============================================
    function override_proto_prop(obj, prop) {
        if (!window.DOMParser) {
            return;
        }

        var orig_getter;
        var orig_setter;

        if (obj.__lookupGetter__) {
            orig_getter = obj.__lookupGetter__(prop);
        }

        if (obj.__lookupSetter__) {
            orig_setter = obj.__lookupSetter__(prop);
        }

        if ((!orig_getter || !orig_setter) && Object.getOwnPropertyDescriptor) {
            var props = Object.getOwnPropertyDescriptor(obj, prop);
            if (props) {
                orig_getter = props.get;
                orig_setter = props.set;
            }
        }

        if (!orig_getter || !orig_setter) {
            return;
        }

        var setter = function(orig) {
            var res = orig;
            if (!this._no_rewrite) {
                res = rewrite_innerHTML(orig);
            }
            orig_setter.call(this, res);
        }

        var getter = function() {
            return orig_getter.call(this);
        }

        Object.defineProperty(obj, prop, {set: setter, get: getter, configurable: false, enumerable: true});
    }

    //============================================
    function init_wombat_loc(win) {

        if (!win || (win.WB_wombat_location && win.document.WB_wombat_location)) {
            return;
        }

        // Location
        var wombat_location = new WombatLocation(win.location);

        if (wombat_location._autooverride) {

            var setter = function(val) {
                if (typeof(val) == "string") {
                    if (starts_with(val, "about:")) {
                        return null;
                    }
                    this._WB_wombat_location.href = val;
                }
            }

            def_prop(win, "WB_wombat_location", wombat_location, setter);
            def_prop(win.document, "WB_wombat_location", wombat_location, setter);
        } else {
            win.WB_wombat_location = wombat_location;
            win.document.WB_wombat_location = wombat_location;

            // Check quickly after page load
            setTimeout(check_all_locations, 500);

            // Check periodically every few seconds
            setInterval(check_all_locations, 500);
        }
    }

    //============================================
    function rewrite_children(child) {
        var desc;

        if (child.querySelectorAll) {
            desc = child.querySelectorAll("[href], [src]");
        }

        if (desc) {
            for (var i = 0; i < desc.length; i++) {
                rewrite_elem(desc[i]);
            }
        }
    }


    //============================================
    function init_dom_override() {
        if (!window.Node || !window.Node.prototype) {
            return;
        }

        function replace_dom_func(funcname) {
            var orig = window.Node.prototype[funcname];

            window.Node.prototype[funcname] = function() {
                var child = arguments[0];

                if (child) {
                    rewrite_elem(child);

                    // if fragment, rewrite children before adding
                    if (child instanceof DocumentFragment) {
                        rewrite_children(child);
                    }
                }
                /*
                if (child.tagName) {
                    if (child.tagName == "IFRAME") { 
                        //init_iframe_wombat(child);
                    }

                    add_attr_overrides(child.tagName, child);
                }
*/
                var created = orig.apply(this, arguments);

                if (created && created.tagName == "IFRAME") {
                    var src = created.src;
                    if (!src || src == "about:blank" || src.indexOf("javascript:") >= 0) {
                        var win = created.contentWindow;

                        if (!win) {
                            return created;
                        }

                        win.WB_wombat_location = win.location;
                        win.document.WB_wombat_location = win.document.location;
                        win.WB_wombat_top = window.WB_wombat_top;

                        win._WBWombat = wombat_internal(win);
                        win._wb_wombat = new win._WBWombat(wb_info);
                    }
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
                targetOrigin = this.location.origin;
            }

            return orig.call(this, message, targetOrigin, transfer);
        }

        window.postMessage = postmessage_rewritten;

        if (window.Window.prototype.postMessage) {
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

        var addEventListener_rewritten = function(type, listener, useCapture) {
            if (type == "message") {
                var orig_listener = listener;
                var new_listener = function(event) {
                    var ne = event;

                    if (event.data.origin && event.data.message) {
                        ne = new MessageEvent("message",
                                              {"bubbles": event.bubbles,
                                               "cancelable": event.cancelable,
                                               "data": event.data.message,
                                               "origin": event.data.origin,
                                               "lastEventId": event.lastEventId,
                                               "source": event.source,
                                               "ports": event.ports});
                    }

                    return orig_listener(ne);
                }
                listener = new_listener;
            }

            return _orig_addEventListener.call(this, type, listener, useCapture);
        }

        window.addEventListener = addEventListener_rewritten;
        window.Window.prototype.addEventListener = addEventListener_rewritten;
    }

    //============================================
    function init_open_override()
    {
        if (!window.Window.prototype.open) {
            return;
        }

        var orig = window.Window.prototype.open;

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
    function init_cookies_override(window)
    {
        var cookie_path_regex = /\bPath=\'?\"?([^;'"\s]+)/i;

        //var get_cookie = function() {
        //    return window.document.cookie;
        //}

        var set_cookie = function(value) {
            var matched = value.match(cookie_path_regex);

            // if has cookie path, rewrite and replace
            if (matched) {
                var rewritten = rewrite_url(matched[1]);
                value = value.replace(matched[1], rewritten);
            }

            return value;
        }

        def_prop(window.document, "cookie", window.document.cookie, set_cookie);
    }

    //============================================
    function init_write_override()
    {
        if (!window.DOMParser) {
            return;
        }

        var orig_doc_write = window.document.write;

        var new_write = function(string) {
            var write_doc = new DOMParser().parseFromString(string, "text/html");

            if (!write_doc) {
                return;
            }

            if (write_doc.head && this.head) {
                var elems = write_doc.head.children;

                for (var i = 0; i < elems.length; i++) {
                    // Call orig write to ensure same execution order and placement
                    rewrite_elem(elems[i]);
                    orig_doc_write.call(this, elems[i].outerHTML);
                }
            }

            if (write_doc.body && this.body) {
                var elems = write_doc.body.children;

                for (var i = 0; i < elems.length; i++) {
                    // Call orig write to ensure same execution order and placement
                    rewrite_elem(elems[i]);
                    orig_doc_write.call(this, elems[i].outerHTML);
                }
            }
        }

        window.document.write = new_write;
        window.Document.prototype.write = new_write;
    }

    //============================================
    function init_iframe_wombat(iframe) {
        function do_init(the_iframe) {
            var win = the_iframe.contentWindow;

            if (!win || win == window || win._skip_wombat) {
                return;
            }

            if (!win._wb_wombat || !win.WB_wombat_location) {
                win._WBWombat = wombat_internal(win);
                win._wb_wombat = new win._WBWombat(wb_info);
            } else if (!win.document.WB_wombat_location) {
                //init_wombat_loc(win);
                win.document.WB_wombat_location = win.WB_wombat_location;
                init_doc_overrides(win, wb_info.wombat_opts);
            }
        }

        function init_doc() {
            do_init(this);
        }

        //do_init(iframe);

        if (iframe.addEventListener) {
            iframe.addEventListener('load', init_doc, true);
        } else if (iframe.attachEvent) {
            iframe.attachEvent('onload', init_doc);
        }
    }


    //============================================
    function init_doc_overrides(window) {
        if (!Object.defineProperty) {
            return;
        }

        if (window.document._wb_override) {
            return;
        }

        var orig_referrer = extract_orig(window.document.referrer);


        try {

            Object.defineProperty(window.document, "domain", {set: function() {}, configurable: false,
                                                              get: function() { return wbinfo.wombat_host }});

            Object.defineProperty(window.document, "referrer", {set: function() {}, configurable: false,
                                                                get: function() { return orig_referrer; }});
        } catch (e) {

        }


        // Cookies
        init_cookies_override(window);

        // Init mutation observer (for style only)
        init_mutation_obs(window);

        // Attr observers
        if (!wb_opts.skip_attr_observers) {
            init_href_src_obs(window);
        }

        // Node insert observer -- not enabled by default
        if (wb_opts.use_node_observers) {
            init_node_insert_obs(window);
        }

        window.document._wb_override = true;
    }


    //============================================
    function wombat_init(wbinfo) {
        wb_info = wbinfo;

        wb_replay_prefix = wbinfo.prefix;
        if (wb_replay_prefix.indexOf(window.location.origin) == 0) {
            wb_coll_prefix = wb_replay_prefix.substring(window.location.origin.length + 1);
        } else {
            wb_coll_prefix = wb_replay_prefix;
        }
        wb_coll_prefix_check = wb_coll_prefix;

        wbinfo.wombat_opts = wbinfo.wombat_opts || {};
        wb_opts = wbinfo.wombat_opts;

        if (wb_replay_prefix) {
            var ts_mod;

            // if live, don't add the timestamp
            if (wbinfo.is_live) {
                ts_mod = wbinfo.mod;
            } else {
                ts_mod = wbinfo.wombat_ts + wbinfo.mod;
            }

            if (ts_mod != "") {
                ts_mod += "/";
            }

            wb_replay_date_prefix = wb_replay_prefix + ts_mod;
            wb_coll_prefix += ts_mod;

            if (!wbinfo.is_live && wbinfo.wombat_ts.length > 0) {
                wb_capture_date_part = "/" + wbinfo.wombat_ts + "/";
            } else {
                wb_capture_date_part = "";
            }

            wb_orig_scheme = wbinfo.wombat_scheme + '://';

            wb_orig_host = wb_orig_scheme + wbinfo.wombat_host;

            init_bad_prefixes(wb_replay_prefix);
        }

        init_wombat_loc(window);

        var is_framed = (window.top.wbinfo && window.top.wbinfo.is_frame);

        function find_next_top(nextwin) {
            while ((nextwin.parent != nextwin) && (nextwin.parent != nextwin.top)) {
                nextwin = nextwin.parent;
            }
            return nextwin;
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
        //window.document.WB_wombat_domain = wbinfo.wombat_host;
        //window.document.WB_wombat_referrer = extract_orig(window.document.referrer);

        init_doc_overrides(window, wb_opts);

        // History
        override_history_func("pushState");
        override_history_func("replaceState");

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

        if (!wb_opts.skip_disable_worker) {
            //init_worker_override();
        }

        // innerHTML can be overriden on prototype!
        override_proto_prop(window.HTMLElement.prototype, "innerHTML");

        // setAttribute
        if (!wb_opts.skip_setAttribute) {
            init_setAttribute_override();
            //init_getAttribute_override();
        }

        // createElement attr override
        if (!wb_opts.skip_createElement) {
            init_createElement_override();
        }

        // ensure namespace urls are NOT rewritten
        init_createElementNS_fix();

        // Image
        init_image_override();

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
        this.watch_elem = watch_elem;
    }

    // Utility functions used by rewriting rules
    function watch_elem(elem, func)
    {
        if (!window.MutationObserver) {
            return false;
        }

        var m = new MutationObserver(function(records, observer) {
            for (var i = 0; i < records.length; i++) {
                var r = records[i];
                if (r.type == "childList") {
                    for (var j = 0; j < r.addedNodes.length; j++) {
                        func(r.addedNodes[j]);
                    }
                }
            }
        });

        m.observe(elem, {
            childList: true,
            subtree: true,
        });
    };

    return wombat_init;
};

return wombat_internal(window);
})();

window._WBWombat = _WBWombat;
