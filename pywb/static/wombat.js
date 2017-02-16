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
// Wombat JS-Rewriting Library v2.18
//============================================



_WBWombat = (function() {


var wombat_internal = function($wbwindow) {

    // Globals
    var wb_replay_prefix;

    var wb_abs_prefix;
    var wb_rel_prefix;
    var wb_rel_prefix_check;

    var wb_capture_date_part;
    var wb_orig_scheme;
    var wb_orig_origin;
    var wb_curr_host;

    var wb_setAttribute = $wbwindow.Element.prototype.setAttribute;
    var wb_getAttribute = $wbwindow.Element.prototype.getAttribute;

    var wb_info;

    var wb_wombat_updating = false;

    // custom options
    var wb_opts;

    var wb_is_proxy = false;

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
        if (!string) { return undefined; }

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

    function rewrite_url_debug(url, use_rel, mod) {
        var rewritten = rewrite_url_(url, use_rel, mod);
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
    var IGNORE_PREFIXES = ["#", "about:", "data:", "mailto:", "javascript:", "{", "*"];

    var BAD_PREFIXES;

    function init_bad_prefixes(prefix) {
        BAD_PREFIXES = ["http:" + prefix, "https:" + prefix,
                        "http:/" + prefix, "https:/" + prefix];
    }

    var SRC_TAGS = ["IFRAME", "IMG", "SCRIPT", "VIDEO", "AUDIO", "SOURCE", "EMBED", "INPUT"];

    var HREF_TAGS = ["LINK", "A"];

    var REWRITE_ATTRS = ["src", "href", "poster"];

    var URL_PROPS = ["href", "hash", "pathname", "host", "hostname", "protocol", "origin", "search", "port"];

    //============================================
    function rewrite_url_(url, use_rel, mod) {
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

        // proxy mode: If no wb_replay_prefix, only rewrite scheme
        if (wb_is_proxy) {
            if (wb_orig_scheme == HTTP_PREFIX && starts_with(url, HTTPS_PREFIX)) {
                return HTTP_PREFIX + url.substr(HTTPS_PREFIX.length);
            } else if (wb_orig_scheme == HTTPS_PREFIX && starts_with(url, HTTP_PREFIX)) {
                return HTTPS_PREFIX + url.substr(HTTP_PREFIX.length);
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
        if (starts_with(url, wb_replay_prefix) || starts_with(url, $wbwindow.location.origin + wb_replay_prefix)) {
            return url;
        }

        // A special case where the port somehow gets dropped
        // Check for this and add it back in, eg http://localhost/path/ -> http://localhost:8080/path/
        if ($wbwindow.location.host != $wbwindow.location.hostname) {
            if (starts_with(url, $wbwindow.location.protocol + '//' + $wbwindow.location.hostname + "/")) {
                url = url.replace("/" + $wbwindow.location.hostname + "/", "/" + $wbwindow.location.host + "/");
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
            if ((url.indexOf(wb_rel_prefix) == 1) && (url.indexOf("http") > 1)) {
                var scheme_sep = url.indexOf(":/");
                if (scheme_sep > 0 && url[scheme_sep + 2] != '/') {
                    url = url.substring(0, scheme_sep + 2) + "/" + url.substring(scheme_sep + 2);
                }
                return url;
            }

            return get_final_url(use_rel ? wb_rel_prefix : wb_abs_prefix, mod, wb_orig_origin + url);
        }

        // Use a parser
        if (url.charAt(0) == ".") {
            url = resolve_rel_url(url);
        }

        // If full url starting with http://, https:// or //
        // add rewrite prefix
        var prefix = starts_with(url, VALID_PREFIXES);

        if (prefix) {
            var orig_host = $wbwindow.__WB_replay_top.location.host;
            var orig_protocol = $wbwindow.__WB_replay_top.location.protocol;

            var prefix_host = prefix + orig_host + '/';

            // if already rewritten url, must still check scheme
            if (starts_with(url, prefix_host)) {
                if (starts_with(url, wb_replay_prefix)) {
                    return url;
                }

                var curr_scheme = orig_protocol + '//';
                var path = url.substring(prefix_host.length);
                var rebuild = false;

                if (path.indexOf(wb_rel_prefix_check) < 0 && url.indexOf("/static/") < 0) {
                    path = get_final_url(wb_rel_prefix, mod, WB_wombat_location.origin + "/" + path);
                    rebuild = true;
                }

                // replace scheme to ensure using the correct server scheme
                //if (starts_with(url, wb_orig_scheme) && (wb_orig_scheme != curr_scheme)) {
                if (prefix != curr_scheme && prefix != REL_PREFIX) {
                    rebuild = true;
                }

                if (rebuild) {
                    if (!use_rel) {
                        url = curr_scheme + orig_host;
                    } else {
                        url = "";
                    }
                    url += "/" + path;
                }

                return url;
            }
            return get_final_url(wb_abs_prefix, mod, url);
        }

        // Check for common bad prefixes and remove them
        prefix = starts_with(url, BAD_PREFIXES);

        if (prefix) {
            url = extract_orig(url);
            return get_final_url(wb_abs_prefix, mod, url);
        }

        // May or may not be a hostname, call function to determine
        // If it is, add the prefix and make sure port is removed
        if (is_host_url(url) && !starts_with(url, $wbwindow.location.host + '/')) {
            return get_final_url(wb_abs_prefix, mod, wb_orig_scheme + url);
        }

        return url;
    }

    //============================================
    function resolve_rel_url(url) {
        var parser = make_parser(extract_orig($wbwindow.document.baseURI));
        var href = parser.href;
        var hash = href.lastIndexOf("#");

        if (hash >= 0) {
            href = href.substring(0, hash);
        }

        var lastslash = href.lastIndexOf("/");

        if (lastslash >= 0 && lastslash != (href.length - 1)) {
            href = href.substring(0, lastslash + 1);
        }

        parser.href = href + url;
        url = parser.href;
        return url;
    }

    //============================================
    function extract_orig(href) {
        if (!href) {
            return "";
        }

        var orig_href = href;

        // proxy mode: no extraction needed
        if (wb_is_proxy) {
            return href;
        }

        href = href.toString();

        // ignore certain urls
        if (starts_with(href, IGNORE_PREFIXES)) {
            return href;
        }

        // if no coll, start from beginning, otherwise could be part of coll..
        var start = wb_rel_prefix ? 1 : 0;

        var index = href.indexOf("/http", start);
        if (index < 0) {
            index = href.indexOf("///", start);
        }

        // extract original url from wburl
        if (index >= 0) {
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

            if (href != orig_href && !starts_with(href, VALID_PREFIXES)) {
                href = HTTP_PREFIX + href;
            }
        }

        if (orig_href.charAt(0) == "/" && orig_href.charAt(1) != "/" && starts_with(href, wb_orig_origin)) {
            href = href.substr(wb_orig_origin.length);
        }

        return href;
    }

    //============================================
    // Override a DOM property
    function def_prop(obj, prop, set_func, get_func, enumerable) {
        // if the property is marked as non-configurable in the current
        // browser, skip the override
        var existingDescriptor = Object.getOwnPropertyDescriptor(obj, prop);
        if (existingDescriptor && !existingDescriptor.configurable) {
            return;
        }

        // if no getter function was supplied, skip the override.
        // See https://github.com/ikreymer/pywb/issues/147 for context
        if (!get_func) {
            return;
        }

        try {
            var descriptor = {
                configurable: true,
                enumerable: enumerable || false,
                get: get_func,
            };

            if (set_func) {
                descriptor.set = set_func;
            }

            Object.defineProperty(obj, prop, descriptor);

            return true;
        } catch (e) {
            console.warn('Failed to redefine property %s', prop, e.message);
            return false;
        }
    }


    //============================================
    function make_parser(href) {
        href = extract_orig(href);

        var baseWin;

        // special case: for newly opened blank windows, use the opener
        // to create parser to have the proper baseURI
        if ($wbwindow.location.href == "about:blank" && $wbwindow.opener) {
            baseWin = $wbwindow.opener;
        } else {
            baseWin = $wbwindow;
        }

        var p = baseWin.document.createElement("a", true);
        p.href = href;
        return p;
    }


    //============================================
    function set_loc(loc, orig_href) {
        var parser = make_parser(orig_href);

        loc._orig_href = orig_href;
        loc._parser = parser;

        var href = parser.href;
        loc._hash = parser.hash;

        loc._href = href;

        loc._host = parser.host;
        loc._hostname = parser.hostname;

        if (parser.origin) {
            loc._origin = parser.origin;
        }

        loc._pathname = parser.pathname;
        loc._port = parser.port;
        //this.protocol = parser.protocol;
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
    }


    function init_loc_override(loc_obj, orig_setter, orig_getter) {
        var make_get_loc_prop = function(prop) {
            function getter() {
                if (this._no_rewrite) {
                    return orig_getter.call(this, prop);
                }

                var curr_orig_href = orig_getter.call(this, "href");

                if (prop == "href") {
                    return extract_orig(curr_orig_href);
                }

                if (this._orig_href != curr_orig_href) {
                    set_loc(this, curr_orig_href);
                }

                var value = this["_" + prop];

                return value;
            }

            return getter;
        }

        var make_set_loc_prop = function(prop) {
            function setter(value) {
                if (this._no_rewrite) {
                    orig_setter.call(this, prop, value);
                    return;
                }

                this["_" + prop] = value;

                if (!this._parser) {
                    var href = orig_getter.call(this);
                    this._parser = make_parser(href);
                }

                //Special case for href="." assignment
                if (prop == "href" && typeof(value) == "string") {
                    if (value) {
                        if (value[0] == ".") {
                            value = resolve_rel_url(value);
                        } else if (value[0] == "/" && (value.length <= 1 || value[1] != "/")) {
                            value = WB_wombat_location.origin + value;
                        }
                    }
                }

                try {
                    this._parser[prop] = value;
                } catch (e) {
                    console.log('Error setting ' + prop + ' = ' + value);
                }

                if (prop == "hash") {
                    value = this._parser[prop];
                } else {
                    prop = "href";
                    var rel = (value == this._parser.pathname);
                    value = rewrite_url(this._parser.href, rel);
                }

                orig_setter.call(this, prop, value);
            }

            return setter;
        }

        function add_loc_prop(loc, prop) {
            def_prop(loc, prop, make_set_loc_prop(prop), make_get_loc_prop(prop), true);
        }

        if (Object.defineProperty) {
            for (var i = 0; i < URL_PROPS.length; i++) {
               add_loc_prop(loc_obj, URL_PROPS[i]);
            }
        }
    }


    //============================================
    //Define WombatLocation

    function WombatLocation(orig_loc) {
        this._orig_loc = orig_loc;

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

        this.reload = function() {
            return this._orig_loc.reload();
        }
       
        this.orig_getter = function(prop) {
            return this._orig_loc[prop];
        }

        this.orig_setter = function(prop, value) {
            this._orig_loc[prop] = value;
        }

        init_loc_override(this, this.orig_setter, this.orig_getter);
        
        set_loc(this, orig_loc.href);

        this.toString = function() {
            return this.href;
        }

        // Copy any remaining properties
        for (prop in orig_loc) {
            if (this.hasOwnProperty(prop)) {
                continue;
            }

            if ((typeof orig_loc[prop]) != "function") {
                this[prop] = orig_loc[prop];
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

        var actual_location = (is_top ? $wbwindow.__WB_replay_top.location : $wbwindow.location);

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

        check_location_change($wbwindow.WB_wombat_location, false);

        // Only check top if its a different $wbwindow
        if ($wbwindow.WB_wombat_location != $wbwindow.__WB_replay_top.WB_wombat_location) {
            check_location_change($wbwindow.__WB_replay_top.WB_wombat_location, true);
        }

        //        lochash = $wbwindow.WB_wombat_location.hash;
        //
        //        if (lochash) {
        //            $wbwindow.location.hash = lochash;
        //
        //            //if ($wbwindow.top.update_wb_url) {
        //            //    $wbwindow.top.location.hash = lochash;
        //            //}
        //        }

        wb_wombat_updating = false;
    }

    //============================================
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

        var new_getrandom = function(array) {
            for (i = 0; i < array.length; i++) {
                array[i] = parseInt($wbwindow.Math.random() * 4294967296);
            }
            return array;
        }

        $wbwindow.Crypto.prototype.getRandomValues = new_getrandom;
        $wbwindow.crypto.getRandomValues = new_getrandom;
    } 

    //============================================
    function override_history_func(func_name) {
        if (!$wbwindow.history) {
            return;
        }

        var orig_func = $wbwindow.history[func_name];

        if (!orig_func) {
            return;
        }

        $wbwindow.history['_orig_' + func_name] = orig_func;

        function rewritten_func(state_obj, title, url) {
            url = rewrite_url(url);

            var abs_url = extract_orig(url);

            if (!abs_url) {
                abs_url = $wbwindow.WB_wombat_location.href;
            }

            if (abs_url &&
                (abs_url != $wbwindow.WB_wombat_location.origin) &&
                !starts_with(abs_url, $wbwindow.WB_wombat_location.origin + "/")) {
                throw new DOMException("Invalid history change: " + abs_url);
            }

            if (url == $wbwindow.location.href) {
                return;
            }

            orig_func.call(this, state_obj, title, url);

            if ($wbwindow.__WB_top_frame) {
                var message = {
                           "url": abs_url,
                           "ts": wb_info.timestamp,
                           "request_ts": wb_info.request_ts,
                           "is_live": wb_info.is_live,
                           "title": title,
                           "wb_type": func_name,
                          }

                $wbwindow.__WB_top_frame.postMessage(message, wb_info.top_host);
            }
        }

        $wbwindow.history[func_name] = rewritten_func;
        if ($wbwindow.History && $wbwindow.History.prototype) {
            $wbwindow.History.prototype[func_name] = rewritten_func;
        }

        return rewritten_func;
    }

    //============================================
    function override_history_nav(func_name) {
        if (!$wbwindow.history) {
            return;
        }

        // Only useful for framed replay
        if (!$wbwindow.__WB_top_frame) {
            return;
        }

        var orig_func = $wbwindow.history[func_name];

        if (!orig_func) {
            return;
        }

        function rewritten_func() {
            orig_func.apply(this, arguments);

            var message = {
                       "wb_type": func_name,
                      }

            if (func_name == "go") {
                message["param"] = arguments[0];
            }

            if ($wbwindow.__WB_top_frame) {
                $wbwindow.__WB_top_frame.postMessage(message, wb_info.top_host);
            }
        }

        $wbwindow.history[func_name] = rewritten_func;
        if ($wbwindow.History && $wbwindow.History.prototype) {
            $wbwindow.History.prototype[func_name] = rewritten_func;
        }

        return rewritten_func;
    }

    //============================================
    function init_ajax_rewrite() {
        if (!$wbwindow.XMLHttpRequest ||
            !$wbwindow.XMLHttpRequest.prototype ||
            !$wbwindow.XMLHttpRequest.prototype.open) {
            return;
        }

        var orig = $wbwindow.XMLHttpRequest.prototype.open;

        function open_rewritten(method, url, async, user, password) {
            if (!this._no_rewrite) {
                url = rewrite_url(url);
            }

            // defaults to true
            if (async != false) {
                async = true;
            }

            result = orig.call(this, method, url, async, user, password);
            if (!starts_with(url, "data:")) {
                this.setRequestHeader('X-Pywb-Requested-With', 'XMLHttpRequest');
            }
        }

        $wbwindow.XMLHttpRequest.prototype.open = open_rewritten;
    }

    //============================================
    function init_fetch_rewrite()
    {
        if (!$wbwindow.fetch) {
            return;
        }

        var orig_fetch = $wbwindow.fetch;

        $wbwindow.fetch = function(input, init) {
            if (typeof(input) === "string") {
                input = rewrite_url(input);
            } else if (typeof(input) === "object" && input.url) {
                var new_url = rewrite_url(input.url);
                if (new_url != input.url) {
                    input = new Request(new_url, input);
                }
            }

            return orig_fetch.call(this, input, init);
        }
    }

    //============================================
    function init_base_override()
    {
        if (!Object.defineProperty) {
            return;
        }

        // <base> element .getAttribute()
        orig_getAttribute = $wbwindow.HTMLBaseElement.prototype.getAttribute;

        $wbwindow.HTMLBaseElement.prototype.getAttribute = function(name) {
            var result = orig_getAttribute.call(this, name);
            if (name == "href") {
                result = extract_orig(result);
            }
            return result;
        }

        // <base> element .href
        var base_href_get = function() {
            return this.getAttribute("href");
        };

        def_prop($wbwindow.HTMLBaseElement.prototype, "href", undefined, base_href_get);

        // Shared baseURI
        var orig_getter = get_orig_getter($wbwindow.Node.prototype, "baseURI");
        if (orig_getter) {
            var get_baseURI = function() {
                var res = orig_getter.call(this);
                return extract_orig(res);
            }

            def_prop($wbwindow.Node.prototype, "baseURI", undefined, get_baseURI);
        }
    }

    //============================================
    function init_setAttribute_override()
    {
        if (!$wbwindow.Element ||
            !$wbwindow.Element.prototype ||
            !$wbwindow.Element.prototype.setAttribute) {
            return;
        }

        var orig_setAttribute = $wbwindow.Element.prototype.setAttribute;
        wb_setAttribute = orig_setAttribute;

        $wbwindow.Element.prototype._orig_setAttribute = orig_setAttribute;

        $wbwindow.Element.prototype.setAttribute = function(name, value) {
            if (name) {
                var lowername = name.toLowerCase();
                if (equals_any(lowername, REWRITE_ATTRS) && typeof(value) == "string") {
                    if (!this._no_rewrite) {
                        var old_value = value;

                        var mod = undefined;
                        if (this.tagName == "SCRIPT") {
                            mod = "js_";
                        }
                        value = rewrite_url(value, false, mod);
                    }
                } else if (lowername == "style" && typeof(value) == "string") {
                    value = rewrite_style(value);
                }
            }
            orig_setAttribute.call(this, name, value);
        };
    }

    //============================================
    function init_getAttribute_override()
    {
        if (!$wbwindow.Element ||
            !$wbwindow.Element.prototype ||
            !$wbwindow.Element.prototype.setAttribute) {
            return;
        }

        var orig_getAttribute = $wbwindow.Element.prototype.getAttribute;
        wb_getAttribute = orig_getAttribute;

        $wbwindow.Element.prototype.getAttribute = function(name) {
            var result = orig_getAttribute.call(this, name);

            if (equals_any(name.toLowerCase(), REWRITE_ATTRS)) {
                result = extract_orig(result);
            } else if (starts_with(name, "data-") && starts_with(result, VALID_PREFIXES)) {
                result = extract_orig(result);
            }

            return result;
        }

    }

    //============================================
    function init_createElement_override()
    {
        if (!$wbwindow.document.createElement ||
            !$wbwindow.Document.prototype.createElement) {
            return;
        }

        var orig_createElement = $wbwindow.document.createElement;

        var createElement_override = function(tagName, skip)
        {
            var created = orig_createElement.call(this, tagName);
            if (!created) {
                return created;
            }
            if (skip) {
                created._no_rewrite = true;
            }
            else {
                // form override
                if (created.tagName == "FORM") {
                    override_attr(created, "action", "", true);
                }
            }

            return created;
        }

        $wbwindow.Document.prototype.createElement = createElement_override;
        $wbwindow.document.createElement = createElement_override;
    }

    //============================================
    function init_createElementNS_fix()
    {
        if (!$wbwindow.document.createElementNS ||
            !$wbwindow.Document.prototype.createElementNS) {
            return;
        }

        var orig_createElementNS = $wbwindow.document.createElementNS;

        var createElementNS_fix = function(namespaceURI, qualifiedName)
        {
            namespaceURI = extract_orig(namespaceURI);
            return orig_createElementNS.call(this, namespaceURI, qualifiedName);
        }

        $wbwindow.Document.prototype.createElementNS = createElementNS_fix;
        $wbwindow.document.createElementNS = createElementNS_fix;
    }

    //============================================
    //function init_image_override() {
    //    $wbwindow.__Image = $wbwindow.Image;
    //    $wbwindow.Image = function (Image) {
    //        return function (width, height) {
    //            var image = new Image(width, height);
    //            override_attr(image, "src");
    //            return image;
    //        }
    //    }($wbwindow.Image);
    //}

    //============================================
    function init_date_override(timestamp) {
        timestamp = parseInt(timestamp) * 1000;
        //var timezone = new Date().getTimezoneOffset() * 60 * 1000;
        // Already UTC!
        var timezone = 0;
        var start_now = $wbwindow.Date.now()
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

        $wbwindow.Date.now = function() {
            return orig_now() - timediff;
        }

        $wbwindow.Date.UTC = orig_utc;
        $wbwindow.Date.parse = orig_parse;

        $wbwindow.Date.__WB_timediff = timediff;
    }

    //============================================
    function init_worker_override() {
        if (!$wbwindow.Worker) {
            return;
        }

        // for now, disabling workers until override of worker content can be supported
        // hopefully, pages depending on workers will have a fallback
        $wbwindow.Worker = undefined;
    }


    //============================================
/*    function init_mutation_obs($wbwindow) {
        if (!$wbwindow.MutationObserver) {
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

        m.observe($wbwindow.document.documentElement, {
            childList: false,
            attributes: true,
            subtree: true,
            //attributeOldValue: true,
            attributeFilter: ["style"]});
    }
*/
    //============================================
/*    function init_href_src_obs($wbwindow)
    {
        if (!$wbwindow.MutationObserver) {
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

        m.observe($wbwindow.document.documentElement, {
            childList: false,
            attributes: true,
            subtree: true,
            //attributeOldValue: true,
            attributeFilter: ["src", "href"]});

    }


    //============================================
    function init_iframe_insert_obs(root)
    {
        if (!$wbwindow.MutationObserver) {
            return;
        }

        var m = new MutationObserver(function(records, observer)
        {
            for (var i = 0; i < records.length; i++) {
                var r = records[i];
                if (r.type == "childList") {
                    for (var j = 0; j < r.addedNodes.length; j++) {
                        if (r.addedNodes[j].tagName == "IFRAME") {
                            init_iframe_wombat(r.addedNodes[j]);
                        }
                    }
                }
            }
        });

        m.observe(root, {
            childList: true,
            subtree: true,
        });
    }
*/
    //============================================
    function rewrite_attr(elem, name, abs_url_only) {
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

        var new_value;

        if (name == "style") {
            new_value = rewrite_style(value);
        } else {
            // Only rewrite if absolute url
            if (abs_url_only && !starts_with(value, VALID_PREFIXES)) {
                return;
            }

            var mod = undefined;

            if (elem.tagName == "SCRIPT") {
                mod = "js_";
            }
            new_value = rewrite_url(value, false, mod);
        }

        if (new_value != value) {
            wb_setAttribute.call(elem, name, new_value);
            return true;
        }
    }

    //============================================
    function rewrite_style(value)
    {
        STYLE_REGEX = /(url\s*\(\s*[\\"']*)([^)'"]+)([\\"']*\s*\))/gi;

        function style_replacer(match, n1, n2, n3, offset, string) {
            return n1 + rewrite_url(n2) + n3;
        }

        if (typeof(value) === "string") {
            value = value.replace(STYLE_REGEX, style_replacer);
            value = value.replace('WB_wombat_', '');
        }

        return value;
    }

    //============================================
    function rewrite_frame_src(elem, name)
    {
        var value = wb_getAttribute.call(elem, name);
        var new_value = undefined;

        // special case for rewriting javascript: urls that contain WB_wombat_
        // must insert wombat init first!
        if (starts_with(value, "javascript:")) {
            if (value.indexOf("WB_wombat_") >= 0) {
                var JS = "javascript:";
                new_value = JS;
                new_value += "window.parent._wb_wombat.init_new_window_wombat(window);"
                new_value += value.substr(JS.length);
            }
        }

        if (!new_value) {
            new_value = rewrite_url(value, false);
        }

        if (new_value != value) {
            wb_setAttribute.call(elem, name, new_value);
            return true;
        }

        return false;
    }

    //============================================
    function rewrite_elem(elem)
    {
        if (!elem) {
            return;
        }

        var changed;

        if (elem.tagName == "STYLE") {
            var new_content = rewrite_style(elem.textContent);
            if (elem.textContent != new_content) {
                elem.textContent = new_content;
                changed = true;
            }
        } else if (elem.tagName == "OBJECT") {
            changed = rewrite_attr(elem, "data", true);
        } else if (elem.tagName == "FORM") {
            changed = rewrite_attr(elem, "action", true);
        } else if (elem.tagName == "INPUT") {
            changed = rewrite_attr(elem, "value", true);
        } else if (elem.tagName == "IFRAME" || elem.tagName == "FRAME") {
            changed = rewrite_frame_src(elem, "src");
        } else {
            changed = rewrite_attr(elem, "src");
            changed = rewrite_attr(elem, "srcset") || changed;
            changed = rewrite_attr(elem, "href") || changed;
            changed = rewrite_attr(elem, "style") || changed;
            changed = rewrite_attr(elem, "poster") || changed;
        }

        if (elem.getAttribute) {
            if (elem.getAttribute("crossorigin")) {
                elem.removeAttribute("crossorigin");
                changed = true;
            }

            if (elem.getAttribute("integrity")) {
                elem.removeAttribute("integrity");
                changed = true;
            }
        }

        return changed;
    }

    var write_buff = "";

    //============================================
    function rewrite_html(string, check_end_tag) {
        if (!string) {
            return string;
        }

        if (write_buff) {
            string = write_buff + string;
            write_buff = "";
        }
         var inner_doc = new DOMParser().parseFromString(string, "text/html");

        if (!inner_doc) {
            return string;
        }

        string = string.toString();

        var changed = false;

        for (var i = 0; i < inner_doc.all.length; i++) {
            changed = rewrite_elem(inner_doc.all[i]) || changed;
        }

        if (!changed) {
            return string;
        }

        var new_html = "";

        // if original had <html> tag, add full document HTML
        if (string && string.indexOf("<html") >= 0) {
            new_html = inner_doc.documentElement.outerHTML;
        } else {
        // otherwise, just add contents of head and body
            new_html = inner_doc.head.innerHTML;
            new_html += inner_doc.body.innerHTML;

            if (check_end_tag) {
                if (inner_doc.all.length > 3) {
                    var end_tag = "</" + inner_doc.all[3].tagName.toLowerCase() + ">";
                    if (ends_with(new_html, end_tag) && !ends_with(string, end_tag)) {
                        new_html = new_html.substring(0, new_html.length - end_tag.length);
                    }
                } else if (string[0] != "<" || string[string.length - 1] != ">") {
                    write_buff += string;
                    return;
                }
            }
        }

        return new_html;
    }

    //============================================
/*    function add_attr_overrides(tagName, created)
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
*/
    //============================================
    function get_orig_getter(obj, prop) {
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
    }

    //============================================
    function get_orig_setter(obj, prop) {
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
    }

    //============================================
    function override_attr(obj, attr, mod, default_to_setget) {
        var orig_getter = get_orig_getter(obj, attr);
        var orig_setter = get_orig_setter(obj, attr);

        var setter = function(orig) {
            var val = rewrite_url(orig, false, mod);
            if (orig_setter) {
                return orig_setter.call(this, val);
            } else if (default_to_setget) {
                return wb_setAttribute.call(this, attr, val);
            }
        }

        var getter = function() {
            var res = undefined;

            if (orig_getter) {
                res = orig_getter.call(this);
            } else if (default_to_setget) {
                res = wb_getAttribute.call(this, attr);
            }
            res = extract_orig(res);

            return res;
        }

        def_prop(obj, attr, setter, getter);
    }


    //============================================
    function override_style_attr(obj, attr, prop_name) {
        var orig_getter = get_orig_getter(obj, attr);
        var orig_setter = get_orig_setter(obj, attr);

        var setter = function(orig) {
            var val = rewrite_style(orig);
            if (orig_setter) {
                orig_setter.call(this, val);
            } else {
                this.setProperty(prop_name, val);
            }

            return val;
        }

        var getter = function() {
            if (orig_getter) {
                return orig_getter.call(this);
            } else {
                return this.getPropertyValue(prop_name);
            }
        }

        if ((orig_setter && orig_getter) || prop_name) {
            def_prop(obj, attr, setter, getter);
        }
    }


    //============================================
    function init_attr_overrides($wbwindow) {
        override_attr($wbwindow.HTMLLinkElement.prototype, "href", "cs_");
        override_attr($wbwindow.CSSStyleSheet.prototype, "href", "cs_");
        override_attr($wbwindow.HTMLImageElement.prototype, "src", "im_");
        override_attr($wbwindow.HTMLIFrameElement.prototype, "src", "if_");
        override_attr($wbwindow.HTMLScriptElement.prototype, "src", "js_");
        override_attr($wbwindow.HTMLVideoElement.prototype, "src", "oe_");
        override_attr($wbwindow.HTMLVideoElement.prototype, "poster", "im_");
        override_attr($wbwindow.HTMLAudioElement.prototype, "src", "oe_");
        override_attr($wbwindow.HTMLAudioElement.prototype, "poster", "im_");
        override_attr($wbwindow.HTMLSourceElement.prototype, "src", "oe_");
        override_attr($wbwindow.HTMLSourceElement.prototype, "srcset", "oe_");
        override_attr($wbwindow.HTMLInputElement.prototype, "src", "oe_");
        override_attr($wbwindow.HTMLEmbedElement.prototype, "src", "oe_");
        override_attr($wbwindow.HTMLObjectElement.prototype, "data", "oe_");
     
        override_anchor_elem();

        var style_proto = $wbwindow.CSSStyleDeclaration.prototype;

        // For FF
        if ($wbwindow.CSS2Properties) {
            style_proto = $wbwindow.CSS2Properties.prototype;
        }

        override_style_attr(style_proto, "cssText");

        override_style_attr(style_proto, "background", "background");
        override_style_attr(style_proto, "backgroundImage", "background-image");

        override_style_attr(style_proto, "listStyle", "list-style");
        override_style_attr(style_proto, "listStyleImage", "list-style-image");

        override_style_attr(style_proto, "border", "border");
        override_style_attr(style_proto, "borderImage", "border-image");
        override_style_attr(style_proto, "borderImageSource", "border-image-source");
    }

    //============================================
    function override_anchor_elem() {
        var anchor_orig = {}

        function save_prop(prop) {
            anchor_orig["get_" + prop] = get_orig_getter($wbwindow.HTMLAnchorElement.prototype, prop);
            anchor_orig["set_" + prop] = get_orig_setter($wbwindow.HTMLAnchorElement.prototype, prop);
        }

        for (var i = 0; i < URL_PROPS.length; i++) {
            save_prop(URL_PROPS[i]);
        } 

        var anchor_setter = function(prop, value) {
            var func = anchor_orig["set_" + prop];
            if (func) {
                return func.call(this, value);
            } else {
                return "";
            }
        }

        var anchor_getter = function(prop) {
            var func = anchor_orig["get_" + prop];
            if (func) {
                return func.call(this);
            } else {
                return "";
            }
        }

        init_loc_override($wbwindow.HTMLAnchorElement.prototype, anchor_setter, anchor_getter);
        $wbwindow.HTMLAnchorElement.prototype.toString = function () {
            return this.href;
        };
    }


    //============================================
    function override_html_assign(elemtype, prop) {
        if (!$wbwindow.DOMParser ||
            !elemtype ||
            !elemtype.prototype) {
            return;
        }

        var obj = elemtype.prototype;

        var orig_getter = get_orig_getter(obj, prop);
        var orig_setter = get_orig_setter(obj, prop);

        if (!orig_setter) {
            return;
        }

        var setter = function(orig) {
            var res = orig;
            if (!this._no_rewrite) {
                //init_iframe_insert_obs(this);
                if (this.tagName == "STYLE") {
                    res = rewrite_style(orig);
                } else {
                    res = rewrite_html(orig);
                }
            }
            orig_setter.call(this, res);
        }

        def_prop(obj, prop, setter, orig_getter);
    }


    //============================================
    function override_iframe_content_access(prop)
    {
        if (!$wbwindow.HTMLIFrameElement ||
            !$wbwindow.HTMLIFrameElement.prototype) {
            return;
        }

        var obj = $wbwindow.HTMLIFrameElement.prototype;

        var orig_getter = get_orig_getter(obj, prop);
        var orig_setter = get_orig_setter(obj, prop);

        if (!orig_getter) {
            return;
        }

        var getter = function() {
            init_iframe_wombat(this);
            return orig_getter.call(this);
        };
        
        def_prop(obj, prop, orig_setter, getter);
        obj["_get_" + prop] = orig_getter;
    }

    //============================================
    function init_insertAdjacentHTML_override()
    {
        if (!$wbwindow.Element ||
            !$wbwindow.Element.prototype ||
            !$wbwindow.Element.prototype.insertAdjacentHTML) {
            return;
        }

        var orig_insertAdjacentHTML = $wbwindow.Element.prototype.insertAdjacentHTML;

        var insertAdjacent_override = function(position, text)
        {
            if (!this._no_rewrite) {
                // inserting adjacent, so must observe parent
                //if (this.parentElement) {
                //    init_iframe_insert_obs(this.parentElement);
                //}
                text = rewrite_html(text);
            }
 
            return orig_insertAdjacentHTML.call(this, position, text);
        }

        $wbwindow.Element.prototype.insertAdjacentHTML = insertAdjacent_override;
    }



    //============================================
    function init_wombat_loc(win) {

        if (!win || (win.WB_wombat_location && win.document.WB_wombat_location)) {
            return;
        }

        // Location
        var wombat_location = new WombatLocation(win.location);

        if (Object.defineProperty) {

            var setter = function(value) {
                if (this._WB_wombat_location) {
                    this._WB_wombat_location.href = value;
                } else {
                    this.location = value;
                }
            }

            var getter = function() {
                if (this._WB_wombat_location) {
                    return this._WB_wombat_location;
                } else {
                    return this.location;
                }
            }

            def_prop(win.Object.prototype, "WB_wombat_location", setter, getter);

            init_proto_pm_origin(win);

            win._WB_wombat_location = wombat_location;
            win.document._WB_wombat_location = wombat_location;
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
/*    function rewrite_children(child) {
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
*/

    //============================================
    function init_dom_override() {
        if (!$wbwindow.Node || !$wbwindow.Node.prototype) {
            return;
        }

        function replace_dom_func(funcname) {
            var orig = $wbwindow.Node.prototype[funcname];

            $wbwindow.Node.prototype[funcname] = function() {
                var child = arguments[0];

                if (child) {

                    if (child instanceof $wbwindow.Element) {
                        rewrite_elem(child);
                    } else if (child instanceof $wbwindow.Text) {
                        if (this.tagName == "STYLE") {
                            child.textContent = rewrite_style(child.textContent);
                        }
                    }

                    // if fragment, rewrite children before adding
                    //if (child instanceof DocumentFragment) {
                    //   rewrite_children(child);
                    //}
                }

                var created = orig.apply(this, arguments);

                if (created && created.tagName == "IFRAME") {
                    init_iframe_wombat(created);
                }

                return created;
            }
        }

        replace_dom_func("appendChild");
        replace_dom_func("insertBefore");
        replace_dom_func("replaceChild");
    }


    function init_proto_pm_origin(win) {
        function pm_origin(origin_window) {
            this.__WB_source = origin_window;
            return this;
        }

        try {
            win.Object.defineProperty(win.Object.prototype, "__WB_pmw", {value: pm_origin, configurable: false, enumerable: false});
        } catch(e) {
        }
    }

    //============================================
    function init_hash_change()
    {
        if (!$wbwindow.__WB_top_frame) {
            return;
        }

        function receive_hash_change(event)
        {
            if (!event.data || event.source != $wbwindow.__WB_top_frame) {
                return;
            }

            var message = event.data;

            if (!message.wb_type) {
                return;
            }

            if (message.wb_type == "outer_hashchange") {
                if ($wbwindow.location.hash != message.hash) {
                    $wbwindow.location.hash = message.hash;
                }
            }
        }

        function send_hash_change() {
            var message = {"wb_type": "hashchange",
                           "hash": $wbwindow.location.hash
                          }

            if ($wbwindow.__WB_top_frame) {
                $wbwindow.__WB_top_frame.postMessage(message, wb_info.top_host);
            }
        }

        $wbwindow.addEventListener("message", receive_hash_change);

        $wbwindow.addEventListener("hashchange", send_hash_change);
    }

    //============================================
    function init_postmessage_override($wbwindow)
    {
        if (!$wbwindow.postMessage || $wbwindow.__orig_postMessage) {
            return;
        }

        var orig = $wbwindow.postMessage;
        
        $wbwindow.__orig_postMessage = orig;

        var postmessage_rewritten = function(message, targetOrigin, transfer, from_top) {
            var from = undefined;
            var src_id = undefined;

            if (window.__WB_source && window.__WB_source.WB_wombat_location) {
                var source = window.__WB_source;

                var from = source.WB_wombat_location.origin;

                if (!this.__WB_win_id) {
                    this.__WB_win_id = {};
                    this.__WB_counter = 0;
                }

                if (!source.__WB_id) {
                    source.__WB_id = (this.__WB_counter++) + source.WB_wombat_location.href;
                }
                this.__WB_win_id[source.__WB_id] = source;

                src_id = source.__WB_id;
                
                window.__WB_source = undefined;
            } else {
                from = window.WB_wombat_location.origin;
            }

            var to = targetOrigin;
            
            if (to == this.location.origin) {
                to = "*";
            } else {
                var to_host = to.split("//", 2);
                if (to_host.length == 2) {
                    to = to_host[1];
                }
            }

            var new_message = {"from": from,
                               "to_host": to,
                               "src_id":  src_id,
                               "message": message,
                               "from_top": from_top,
                              }

            if (targetOrigin != "*") {
                targetOrigin = this.location.origin;
                //targetOrigin = "*";
            }

            //console.log("Sending " + from + " -> " + to + " (" + targetOrigin + ") " + message);
            
            return orig.call(this, new_message, targetOrigin, transfer);
        }

        $wbwindow.postMessage = postmessage_rewritten;

        $wbwindow.Window.prototype.postMessage = postmessage_rewritten;

/*
        for (var i = 0; i < $wbwindow.frames.length; i++) {
            try {
                //init_postmessage_override($wbwindow.frames[i]);
                $wbwindow.frames[i].postMessage = postmessage_rewritten;
            } catch (e) {
                console.log(e);
            }
        }
*/
        function WrappedListener(event, orig_listener, win) {
            var ne = event;

            if (event.data.from && event.data.message) {

                if (event.data.to_host != "*" && win.WB_wombat_location && event.data.to_host != win.WB_wombat_location.host) {
                    console.log("Skipping " + win.WB_wombat_location.host + " not " + event.data.to_host);
                    return;
                }

                var source = event.source;

                if (event.data.from_top) {
                    source = win.__WB_top_frame;
                } else if (event.data.src_id && win.__WB_win_id && win.__WB_win_id[event.data.src_id]) {
                    source = win.__WB_win_id[event.data.src_id];
                }

                ne = new MessageEvent("message",
                                      {"bubbles": event.bubbles,
                                       "cancelable": event.cancelable,
                                       "data": event.data.message,
                                       "origin": event.data.from,
                                       "lastEventId": event.lastEventId,
                                       "source": source,
                                       "ports": event.ports});

            }

            return orig_listener(ne);
        }

        var listen_map = {};

        // ADD
        var _orig_addEventListener = $wbwindow.addEventListener;
        
        var addEventListener_rewritten = function(type, listener, useCapture) {
            if (type == "message") {
                var win = this;
                var wrapped_listener = function(event) { return WrappedListener(event, listener, win); }

                listen_map[listener] = wrapped_listener;

                return _orig_addEventListener.call(this, type, wrapped_listener, useCapture);
            } else {
                return _orig_addEventListener.call(this, type, listener, useCapture);
            }
        }
 
        $wbwindow.addEventListener = addEventListener_rewritten;

        // REMOVE
        var _orig_removeEventListener = $wbwindow.removeEventListener;
        
        var removeEventListener_rewritten = function(type, listener, useCapture) {
            if (type == "message") {
                var mapped = listen_map[listener];
                if (mapped) {
                    delete listen_map[listener];
                    return _orig_removeEventListener.call(this, type, mapped, useCapture);
                }
            } else {
                return _orig_removeEventListener.call(this, type, listener, useCapture);
            }
        }

        $wbwindow.removeEventListener = removeEventListener_rewritten;
    }

    //============================================
    function init_open_override()
    {
        var orig = $wbwindow.open;

        if ($wbwindow.Window.prototype.open) {
            orig = $wbwindow.Window.prototype.open;
        }

        var open_rewritten = function(strUrl, strWindowName, strWindowFeatures) {
            strUrl = rewrite_url(strUrl, false, "");
            var res = orig.call(this, strUrl, strWindowName, strWindowFeatures);
            init_new_window_wombat(res, strUrl);
            return res;
        }

        $wbwindow.open = open_rewritten;

        if ($wbwindow.Window.prototype.open) {
            $wbwindow.Window.prototype.open = open_rewritten;
        }

        for (var i = 0; i < $wbwindow.frames.length; i++) {
            try {
                $wbwindow.frames[i].open = open_rewritten;
            } catch (e) {
                console.log(e);
            }
        }
    }

    //============================================
    function init_cookies_override($wbwindow)
    {
        var cookie_path_regex = /\bPath=\'?\"?([^;'"\s]+)/i;
        var cookie_domain_regex = /\bDomain=([^;'"\s]+)/i;
        var cookie_expires_regex = /\bExpires=([^;'"]+)/ig;

        var orig_get_cookie = get_orig_getter($wbwindow.document, "cookie");
        var orig_set_cookie = get_orig_setter($wbwindow.document, "cookie");

        if (!orig_get_cookie) {
            orig_get_cookie = get_orig_getter($wbwindow.Document.prototype, "cookie");
        }
        if (!orig_set_cookie) {
            orig_set_cookie = get_orig_setter($wbwindow.Document.prototype, "cookie");
        }

        function rewrite_cookie(cookie) {
            var IP_RX = /^(\d)+\.(\d)+\.(\d)+\.(\d)+$/;

            cookie = cookie.replace(wb_abs_prefix, '');
            cookie = cookie.replace(wb_rel_prefix, '');

            // rewrite domain
            cookie = cookie.replace(cookie_domain_regex, function(m, m1) {
                var message = {"domain": m1,
                               "cookie": cookie,
                               "wb_type": "cookie",
                              }

                // norify of cookie setting to allow server-side tracking
                if ($wbwindow.__WB_top_frame) {
                    $wbwindow.__WB_top_frame.postMessage(message, wb_info.top_host);
                }

                // if no subdomain, eg. "localhost", just remove domain altogether
                if ($wbwindow.location.hostname.indexOf(".") >= 0 && !IP_RX.test($wbwindow.location.hostname)) {
                    return "Domain=." + $wbwindow.location.hostname;
                } else {
                    return "";
                }
            });

            // rewrite path
            cookie = cookie.replace(cookie_path_regex, function(m, m1) {
                var rewritten = rewrite_url(m1);

                if (rewritten.indexOf(wb_curr_host) == 0) {
                    rewritten = rewritten.substring(wb_curr_host.length);
                }

                return "Path=" + rewritten;
            });

            // rewrite secure, if needed
            if ($wbwindow.location.protocol != "https:") {
                cookie = cookie.replace("secure", "");
            }

            cookie = cookie.replace(",|", ",");

            return cookie;
        }


        var set_cookie = function(value) {
            if (!value) {
                return;
            }

            var orig_value = value;

            value = value.replace(cookie_expires_regex, function(m, d1) {
                var date = new Date(d1);

                if (isNaN(date.getTime())) {
                    return "Expires=Thu,| 01 Jan 1970 00:00:00 GMT";
                }

                date = new Date(date.getTime() + Date.__WB_timediff);
                return "Expires=" + date.toUTCString().replace(",", ",|");
            });

            var cookies = value.split(/,(?![|])/);

            for (var i = 0; i < cookies.length; i++) {
                cookies[i] = rewrite_cookie(cookies[i]);
            }

            value = cookies.join(",")

            return orig_set_cookie.call(this, value);
        }

        def_prop($wbwindow.document, "cookie", set_cookie, orig_get_cookie);
    }

    //============================================
    function init_write_override()
    {
        if (!$wbwindow.DOMParser) {
            return;
        }

        var check_wombat = function(win) {
            if (win && !win._wb_wombat) {
                win._WBWombat = wombat_internal(win);
                win._wb_wombat = new win._WBWombat(wb_info);
            }
        }

        // Write
        var orig_doc_write = $wbwindow.document.write;

        var new_write = function(string) {
            new_buff = rewrite_html(string, true);
            if (!new_buff) {
                return;
            }
            var res = orig_doc_write.call(this, new_buff);
            check_wombat(this.defaultView);
            return res;
        }

        $wbwindow.document.write = new_write;
        $wbwindow.Document.prototype.write = new_write;

        // Writeln
        var orig_doc_writeln = $wbwindow.document.writeln;

        var new_writeln = function(string) {
            new_buff = rewrite_html(string, true);
            if (!new_buff) {
                return;
            }
            var res = orig_doc_writeln.call(this, new_buff);
            check_wombat(this.defaultView);
            return res;
        }

        $wbwindow.document.writeln = new_writeln;
        $wbwindow.Document.prototype.writeln = new_writeln;

        // Open
        var orig_doc_open = $wbwindow.document.open;

        var new_open = function() {
            var res = orig_doc_open.call(this);
            check_wombat(this.defaultView);
            return res;
        }

        $wbwindow.document.open = new_open;
        $wbwindow.Document.prototype.open = new_open;
    }

    //============================================
    function init_eval_override() {
        var orig_eval = $wbwindow.eval;

        $wbwindow.eval = function(string) {
            if (string) {
                string = string.replace(/\blocation\b/g, "WB_wombat_$&");
            }
            orig_eval.call(this, string);
        }
    }

    //============================================
    function init_iframe_wombat(iframe) {
        var win;

        if (iframe._get_contentWindow) {
            win = iframe._get_contentWindow.call(iframe);
        } else {
            win = iframe.contentWindow;
        }

        try {
            if (!win || win == $wbwindow || win._skip_wombat || win._wb_wombat) {
                return;
            }
        } catch (e) {
            return;
        }

        //var src = iframe.src;
        var src = wb_getAttribute.call(iframe, "src");

        init_new_window_wombat(win, src);
    }

    function init_new_window_wombat(win, src) {
        if (!src || src == "" || src == "about:blank" || src.indexOf("javascript:") >= 0) {
            win._WBWombat = wombat_internal(win);
            win._wb_wombat = new win._WBWombat(wb_info);
        } else {
            // These should get overriden when content is loaded, but just in case...
            //win._WB_wombat_location = win.location;
            //win.document.WB_wombat_location = win.document.location;
            //win._WB_wombat_top = $wbwindow.WB_wombat_top;

            init_proto_pm_origin(win);
            //init_postmessage_override(win);
        }
    }


    //============================================
    function init_doc_overrides($wbwindow) {
        if (!Object.defineProperty) {
            return;
        }

        if ($wbwindow.document._wb_override) {
            return;
        }

        var orig_referrer = extract_orig($wbwindow.document.referrer);

        var domain_info;

        if ($wbwindow.wbinfo) {
            domain_info = $wbwindow.wbinfo;
        } else {
            domain_info = wbinfo;
        }

        domain_info.domain = domain_info.wombat_host;

        var domain_setter = function(val) {
            if (ends_with(domain_info.wombat_host, val)) {
                domain_info.domain = val;
            }
        }

        var domain_getter = function() {
            return domain_info.domain;
        }

        // changing domain disallowed, but set as no-op to avoid errors
        def_prop($wbwindow.document, "domain", domain_setter, domain_getter);

        def_prop($wbwindow.document, "referrer", undefined, function() { return orig_referrer; });


        // Cookies
        init_cookies_override($wbwindow);

        // Init mutation observer (for style only)
        //init_mutation_obs($wbwindow);

        // override href and src attrs
        init_attr_overrides($wbwindow);


        init_form_overrides($wbwindow);


        // Attr observers
        //if (!wb_opts.skip_attr_observers) {
           // init_href_src_obs($wbwindow);
        //}

        $wbwindow.document._wb_override = true;
    }


    //============================================
    // Necessary since HTMLFormElement.prototype.action is not consistently
    // overridable
    function init_form_overrides($wbwindow) {
        var do_init_forms = function() {
            for (var i = 0; i < $wbwindow.document.forms.length; i++) {
                var new_action = rewrite_url($wbwindow.document.forms[i].action);
                if (new_action != $wbwindow.document.forms[i].action) {
                    $wbwindow.document.forms[i].action = new_action;
                }
                override_attr($wbwindow.document.forms[i], "action", "", true);
            }
        }

        if (document.readyState == "loading") {
            document.addEventListener("DOMContentLoaded", do_init_forms);
        } else {
            do_init_forms();
        }
    }


    //============================================
    function init_registerPH_override()
    {
        if (!$wbwindow.navigator.registerProtocolHandler) {
            return;
        }

        var orig_registerPH = $wbwindow.navigator.registerProtocolHandler;

        $wbwindow.navigator.registerProtocolHandler = function(protocol, uri, title) {
            return orig_registerPH.call(this, protocol, rewrite_url(uri), title);
        }
    }

    //============================================
    function init_beacon_override()
    {
        if (!$wbwindow.navigator.sendBeacon) {
            return;
        }

        var orig_sendBeacon = $wbwindow.navigator.sendBeacon;

        $wbwindow.navigator.sendBeacon = function(url, data) {
            return orig_sendBeacon.call(this, rewrite_url(url), data);
        }
    }

    //============================================
    function init_disable_notifications() {
        if (window.Notification) {
            window.Notification.requestPermission = function(callback) {
                if (callback) {
                    callback("denied");
                }

                return Promise.resolve("denied");
            }
        }

        if (window.geolocation) {
            var disabled = function(success, error, options) {
                if (error) {
                    error({"code": 2, "message": "not available"});
                }
            }

            window.geolocation.getCurrentPosition = disabled;
            window.geolocation.watchPosition = disabled;
        }
    }

    //============================================
    function get_final_url(prefix, mod, url) {
        if (mod == undefined) {
            mod = wb_info.mod;
        }

        // if live, don't add the timestamp
        if (!wb_info.is_live) {
            prefix += wb_info.wombat_ts;
        }

        prefix += mod;

        if (prefix[prefix.length - 1] != "/") {
            prefix += "/";
        }

        return prefix + url
    }

    //============================================
    function wombat_init(wbinfo) {
        wb_info = wbinfo;
        wb_opts = wbinfo.wombat_opts;
        wb_replay_prefix = wbinfo.prefix;
        wb_is_proxy = (!wb_replay_prefix);

        wb_info.top_host = wb_info.top_host || "*";

        init_top_frame($wbwindow);

        init_wombat_loc($wbwindow);

        wbinfo.wombat_opts = wbinfo.wombat_opts || {};

        wb_orig_scheme = wbinfo.wombat_scheme + '://';

        // archival mode: init url-rewriting intercepts
        if (!wb_is_proxy) {
            init_wombat_top($wbwindow);

            wb_curr_host = $wbwindow.location.protocol + "//" + $wbwindow.location.host;

            if (wb_replay_prefix && wb_replay_prefix.indexOf($wbwindow.__WB_replay_top.location.origin) == 0) {
                wb_rel_prefix = wb_replay_prefix.substring($wbwindow.__WB_replay_top.location.origin.length + 1);
            } else {
                wb_rel_prefix = wb_replay_prefix;
            }
            wb_rel_prefix_check = wb_rel_prefix;

            wb_abs_prefix = wb_replay_prefix;
            //wb_replay_date_prefix = wb_replay_prefix + ts_mod;
            //wb_coll_prefix += ts_mod;

            if (!wbinfo.is_live && wbinfo.wombat_ts.length > 0) {
                wb_capture_date_part = "/" + wbinfo.wombat_ts + "/";
            } else {
                wb_capture_date_part = "";
            }

            wb_orig_origin = wb_orig_scheme + wbinfo.wombat_host;

            init_bad_prefixes(wb_replay_prefix);

            //if ($wbwindow.opener) {
            //    $wbwindow.opener.WB_wombat_location = copy_location_obj($wbwindow.opener.location);
            //}

            // Domain
            //$wbwindow.document.WB_wombat_domain = wbinfo.wombat_host;
            //$wbwindow.document.WB_wombat_referrer = extract_orig($wbwindow.document.referrer);

            init_doc_overrides($wbwindow, wb_opts);

            // History
            override_history_func("pushState");
            override_history_func("replaceState");

            override_history_nav("go");
            override_history_nav("back");
            override_history_nav("forward");

            // postMessage
            // OPT skip
            if (!wb_opts.skip_postmessage) {
                init_postmessage_override($wbwindow);
            }

            init_hash_change();

            // write
            init_write_override();

            // eval
            //init_eval_override();

            // Ajax
            init_ajax_rewrite();

            // Fetch
            init_fetch_rewrite();

            if (!wb_opts.skip_disable_worker) {
                //init_worker_override();
            }

            // innerHTML can be overriden on prototype!
            override_html_assign($wbwindow.HTMLElement, "innerHTML");
            override_html_assign($wbwindow.HTMLIFrameElement, "srcdoc");
            override_html_assign($wbwindow.HTMLStyleElement, "textContent");


            // init insertAdjacentHTML() override
            init_insertAdjacentHTML_override();

            // iframe.contentWindow and iframe.contentDocument overrides to 
            // ensure wombat is inited on the iframe $wbwindow!
            override_iframe_content_access("contentWindow");
            override_iframe_content_access("contentDocument");

            // base override
            init_base_override();

            // setAttribute
            if (!wb_opts.skip_setAttribute) {
                init_setAttribute_override();
                init_getAttribute_override();
            }

            // createElement attr override
            if (!wb_opts.skip_createElement) {
                init_createElement_override();
            }

            // ensure namespace urls are NOT rewritten
            init_createElementNS_fix();

            // Image
            //init_image_override();

            // DOM
            // OPT skip
            if (!wb_opts.skip_dom) {
                init_dom_override();
            }

            // registerProtocolHandler override
            init_registerPH_override();

            //sendBeacon override
            init_beacon_override();
        }

        // other overrides
        // proxy mode: only using these overrides

        // Random
        init_seeded_random(wbinfo.wombat_sec);

        // Crypto Random
        init_crypto_random();

        // Date
        init_date_override(wbinfo.wombat_sec);

        // open
        init_open_override();

        // disable notifications
        init_disable_notifications();

        // expose functions
        this.extract_orig = extract_orig;
        this.rewrite_url = rewrite_url;
        this.watch_elem = watch_elem;
        this.init_new_window_wombat = init_new_window_wombat;
    }

    function init_top_frame($wbwindow) {
        // proxy mode
        if (wb_is_proxy) {
            $wbwindow.__WB_replay_top = $wbwindow.top;
            $wbwindow.__WB_top_frame = undefined;
            return;
        }

        function next_parent(win) {
            try {
                if (!win) {
                    return false;
                }

                // if no wbinfo, see if _wb_wombat was set (eg. if about:blank page)
                if (!win.wbinfo) {
                    return (win._wb_wombat != undefined);
                } else {
                // otherwise, ensure that it is not a top container frame
                    return !win.wbinfo.is_frame;
                }

            } catch (e) {
                return false;
            }
        }

        var replay_top = $wbwindow;

        while ((replay_top.parent != replay_top) && next_parent(replay_top.parent)) {
            replay_top = replay_top.parent;
        }

        $wbwindow.__WB_replay_top = replay_top;

        var real_parent = replay_top.__WB_orig_parent || replay_top.parent;

        // Check to ensure top frame is different window and directly accessible (later refactor to support postMessage)
        //try {
        //    if ((real_parent == $wbwindow) || !real_parent.wbinfo || !real_parent.wbinfo.is_frame) {
        //        real_parent = undefined;
        //    }
        //} catch (e) {
        //    real_parent = undefined;
        //}
        if (real_parent == $wbwindow || !wb_info.is_framed) {
            real_parent = undefined;
        }

        if (real_parent) {
            $wbwindow.__WB_top_frame = real_parent;

            init_frameElement_override($wbwindow);

        } else {
            $wbwindow.__WB_top_frame = undefined;
        }

        // Fix .parent only if not embeddable, otherwise leave for accessing embedding window
        if (!wb_opts.embedded && (replay_top == $wbwindow)) {
            $wbwindow.__WB_orig_parent = $wbwindow.parent;
            $wbwindow.parent = replay_top;
        }
    }

    function init_frameElement_override($wbwindow) {
        if (!Object.defineProperty) {
            return;
        }

        var getter = function() {
            var res = this.frameElement;

            if (this.__WB_replay_top == this) {
                return null;
            }

            return res;
        }

        def_prop($wbwindow.Object.prototype, "WB_wombat_frameElement", undefined, getter);

        // Also try disabling frameElement directly, though may no longer be supported in all browsers
        if ($wbwindow.__WB_replay_top == $wbwindow) {
            try {
                Object.defineProperty($wbwindow, "frameElement", {value: undefined, configurable: false});
            } catch (e) {}
        }
    }

    function init_wombat_top($wbwindow) {
        if (!Object.defineProperty) {
            return;
        }

        // from http://stackoverflow.com/a/6229603
        function isWindow(obj) {
            if (typeof(window.constructor) === 'undefined') {
                return obj instanceof window.constructor;
            } else {
                return obj.window === obj;
            }
        }

        var getter = function() {
            if (this.__WB_replay_top) {
                return this.__WB_replay_top;
            } else if (isWindow(this)) {
                return this;
            } else {
                return this.top;
            }
        }

        var setter = function(val) {
            this.top = val;
        }

        def_prop($wbwindow.Object.prototype, "WB_wombat_top", setter, getter);
    }




    // Utility functions used by rewriting rules
    function watch_elem(elem, func)
    {
        if (!$wbwindow.MutationObserver) {
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
