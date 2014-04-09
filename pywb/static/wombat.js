/*
Copyright(c) 2013-2014 Ilya Kreymer. Released under the GNU General Public License.

This file is part of pywb.

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
// Wombat JS-Rewriting Library
//============================================
WB_wombat_init = (function() {

    // Globals
    var wb_replay_prefix;
    var wb_replay_date_prefix;
    var wb_capture_date_part;
    var wb_orig_host;

    var wb_wombat_updating = false;

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

    function starts_with(string, prefix) {
        if (string.indexOf(prefix) == 0) {
            return prefix;
        } else {
            return undefined;
        }
    }

    function ends_with(str, suffix) {
        if (str.indexOf(suffix, str.length - suffix.length) !== -1) {
            return suffix;
        } else {
            return undefined;
        }
    }

    //============================================
    var rewrite_url = rewrite_url_debug;

    function rewrite_url_debug(url) {
        rewritten = rewrite_url_(url);
        if (url != rewritten) {
            console.log('REWRITE: ' + url + ' -> ' + rewritten);
        } else {
            //console.log('NOT REWRITTEN ' + url);
        }
        return rewritten;
    }

    function rewrite_url_(url) {
        var http_prefix = "http://";
        var https_prefix = "https://";
        var rel_prefix = "//";

        // If not dealing with a string, just return it
        if (!url || (typeof url) != "string") {
            return url;
        }

        // ignore anchors
        if (starts_with(url, "#")) {
            return url;
        }

        // If starts with prefix, no rewriting needed
        // Only check replay prefix (no date) as date may be different for each
        // capture
        if (starts_with(url, wb_replay_prefix)) {
            return url;
        }

        // If server relative url, add prefix and original host
        if (url.charAt(0) == "/" && !starts_with(url, rel_prefix)) {

            // Already a relative url, don't make any changes!
            if (url.indexOf(wb_capture_date_part) >= 0) {
                return url;
            }

            return wb_replay_date_prefix + wb_orig_host + url;
        }

        // If full url starting with http://, add prefix

        var prefix = starts_with(url, http_prefix) || 
                     starts_with(url, https_prefix) || 
                     starts_with(url, rel_prefix);

        if (prefix) {
            if (starts_with(url, prefix + window.location.host + '/')) {
                return url;
            }
            return wb_replay_date_prefix + url;
        }

        // May or may not be a hostname, call function to determine
        // If it is, add the prefix and make sure port is removed
        if (is_host_url(url) && !starts_with(url, window.location.host + '/')) {
            return wb_replay_date_prefix + http_prefix + url;
        }

        return url;
    }

    //============================================
    function copy_object_fields(obj) {
        var new_obj = {};

        for (prop in obj) {
            if ((typeof obj[prop]) != "function") {
                new_obj[prop] = obj[prop];
            }
        }

        return new_obj;
    }

    //============================================
    function extract_orig(href) {
        if (!href) {
            return "";
        }
        
        href = href.toString();

        var index = href.indexOf("/http", 1);
        
        // extract original url from wburl
        if (index > 0) {
            href = href.substr(index + 1);
        }

        // remove trailing slash
        if (ends_with(href, "/")) {
            href = href.substring(0, href.length - 1);
        }

        return href;
    }

    //============================================
    function copy_location_obj(loc) {
        var new_loc = copy_object_fields(loc);

        new_loc._orig_loc = loc;
        new_loc._orig_href = loc.href;

        // Rewrite replace and assign functions
        new_loc.replace = function(url) {
            this._orig_loc.replace(rewrite_url(url));
        }
        new_loc.assign = function(url) {
            this._orig_loc.assign(rewrite_url(url));
        }
        new_loc.reload = loc.reload;

        // Adapted from:
        // https://gist.github.com/jlong/2428561
        var parser = document.createElement('a');
        parser.href = extract_orig(new_loc._orig_href);

        new_loc.hash = parser.hash;
        new_loc.host = parser.host;
        new_loc.hostname = parser.hostname;
        new_loc.href = parser.href;

        if (new_loc.origin) {
            new_loc.origin = parser.origin;
        }

        new_loc.pathname = parser.pathname;
        new_loc.port = parser.port
        new_loc.protocol = parser.protocol;
        new_loc.search = parser.search;

        new_loc.toString = function() {
            return this.href;
        }

        return new_loc;
    }

    //============================================
    function update_location(req_href, orig_href, actual_location) {
        if (!req_href || req_href == orig_href) {
            return;
        }

        ext_orig = extract_orig(orig_href);
        ext_req = extract_orig(req_href);

        if (!ext_orig || ext_orig == ext_req) {
            return;
        }

        var final_href = rewrite_url(req_href);

        console.log(actual_location.href + ' -> ' + final_href);

        actual_location.href = final_href;
    }

    //============================================
    function check_location_change(loc, is_top) {
        var locType = (typeof loc);

        var actual_location = (is_top ? window.top.location : window.location);

        //console.log(loc.href);

        // String has been assigned to location, so assign it
        if (locType == "string") {
            update_location(loc, actual_location.href, actual_location)

        } else if (locType == "object") {
            update_location(loc.href, loc._orig_href, actual_location);
        }
    }

    //============================================
    function check_all_locations() {
        if (wb_wombat_updating) {
            return false;
        }

        wb_wombat_updating = true;

        check_location_change(window.WB_wombat_location, false);

        if (window.self.location != window.top.location) {
            check_location_change(window.top.WB_wombat_location, true);
        }

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
        orig_func = history[func_name];

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
            url = rewrite_url(url);

            // defaults to true
            if (async != false) {
                async = true;
            }

            return orig.call(this, method, url, async, user, password);
        }

        window.XMLHttpRequest.prototype.open = open_rewritten;
    }

    function init_worker_override() {
        if (!window.Worker) {
            return;
        }

        // for now, disabling workers until override of worker content can be supported
        // hopefully, pages depending on workers will have a fallback
        window.Worker = undefined;
    }

    function rewrite_attr(elem, name) {
        if (!elem || !elem.getAttribute) {
            return;
        }

        value = elem.getAttribute(name);

        if (!value) {
            return;
        }

        if (starts_with(value, "javascript:")) {
            return;
        }

        orig_value = value;        
        value = rewrite_url(value);

        elem.setAttribute(name, value);
    }

    function init_dom_override() {
        if (!Node || !Node.prototype) {
            return;
        }

        function replace_dom_func(funcname) {
            var orig = Node.prototype[funcname];

            Node.prototype[funcname] = function() {
                rewrite_attr(arguments[0], "src");
                rewrite_attr(arguments[0], "href");

                child = arguments[0];

                var desc;

                if (child instanceof DocumentFragment) {
                    desc = child.querySelectorAll("*[href],*[src]");
                } else if (child.getElementsByTagName) {
                    desc = child.getElementsByTagName("*");
                }

                if (desc) {
                    for (var i = 0; i < desc.length; i++) {
                        rewrite_attr(desc[i], "src");
                        rewrite_attr(desc[i], "href");
                    }
                }

                result = orig.apply(this, arguments);
                return result;
            }
        }

        replace_dom_func("appendChild");
        replace_dom_func("insertBefore");
        replace_dom_func("replaceChild");
    }

    //============================================
    function wombat_init(replay_prefix, capture_date, orig_host, timestamp) {
        wb_replay_prefix = replay_prefix;
        wb_replay_date_prefix = replay_prefix + capture_date + "/";
        wb_capture_date_part = "/" + capture_date + "/";

        wb_orig_host = "http://" + orig_host;

        // Location
        window.WB_wombat_location = copy_location_obj(window.self.location);
        document.WB_wombat_location = window.WB_wombat_location;

        //if (window.self.location != window.top.location) {
        //    window.top.WB_wombat_location = copy_location_obj(window.top.location);
        //}
        window.top.WB_wombat_location = window.WB_wombat_location;

        //if (window.opener) {
        //    window.opener.WB_wombat_location = copy_location_obj(window.opener.location);
        //}

        // Domain
        document.WB_wombat_domain = orig_host;

        // History
        copy_history_func(window.history, 'pushState');
        copy_history_func(window.history, 'replaceState');

        // Ajax
        init_ajax_rewrite();
        init_worker_override();

        // DOM
        init_dom_override();

        // Random
        init_seeded_random(timestamp);       
    }

    // Check quickly after page load
    setTimeout(check_all_locations, 100);

    // Check periodically every few seconds
    setInterval(check_all_locations, 500);

    return wombat_init;

})(this);
