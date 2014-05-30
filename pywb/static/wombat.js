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
// Wombat JS-Rewriting Library v2.0
//============================================
WB_wombat_init = (function() {

    // Globals
    var wb_replay_prefix;
    var wb_replay_date_prefix;
    var wb_capture_date_part;
    var wb_orig_scheme;
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

        // just in case wombat reference made it into url!
        url = url.replace("WB_wombat_", "");

        // ignore anchors, about, data
        if (starts_with(url, IGNORE_PREFIXES)) {
            return url;
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

        // If full url starting with http://, add prefix

        var prefix = starts_with(url, VALID_PREFIXES);

        if (prefix) {
            if (starts_with(url, prefix + window.location.host + '/')) {
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
            console.log(e);
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
            return this._orig_loc.assign(rewrite_url(url));
        }
        this.reload = loc.reload;
              
        // Adapted from:
        // https://gist.github.com/jlong/2428561
        var parser = document.createElement('a');
        var href = extract_orig(this._orig_href);
        parser.href = href;
        
        //console.log(this._orig_href + " -> " + tmp_href);
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
        
        href = parser.href;
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
        if (window.self.WB_wombat_location != window.top.WB_wombat_location) {
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
            url = rewrite_url(url);

            // defaults to true
            if (async != false) {
                async = true;
            }

            return orig.call(this, method, url, async, user, password);
        }

        window.XMLHttpRequest.prototype.open = open_rewritten;
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
    function rewrite_attr(elem, name) {
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

        //var orig_value = value;        
        value = rewrite_url(value);

        elem.setAttribute(name, value);
    }
    
    //============================================
    function rewrite_elem(elem)
    {
        rewrite_attr(elem, "src");
        rewrite_attr(elem, "href");
        
        if (elem && elem.getAttribute && elem.getAttribute("crossorigin")) {
            elem.removeAttribute("crossorigin");
        }
    }

    //============================================
    function init_dom_override() {
        if (!Node || !Node.prototype) {
            return;
        }
        
        function override_attr(obj, attr) {
            var setter = function(orig) {
                var val = rewrite_url(orig);
                //console.log(orig + " -> " + val);
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

        function replace_dom_func(funcname) {
            var orig = Node.prototype[funcname];

            Node.prototype[funcname] = function() {
                var child = arguments[0];
                
                rewrite_elem(child);

                var desc;

                if (child instanceof DocumentFragment) {
     //               desc = child.querySelectorAll("*[href],*[src]");
                } else if (child.getElementsByTagName) {
     //               desc = child.getElementsByTagName("*");
                }

                if (desc) {
                    for (var i = 0; i < desc.length; i++) {
                        rewrite_elem(desc[i]);
                    }
                }

                var created = orig.apply(this, arguments);
                
                if (created.tagName == "IFRAME" || 
                    created.tagName == "IMG" || 
                    created.tagName == "SCRIPT") {
                    
                    override_attr(created, "src");
                    
                } else if (created.tagName == "A") {
                    override_attr(created, "href");
                }
                
                return created;
            }
        }

        replace_dom_func("appendChild");
        replace_dom_func("insertBefore");
        replace_dom_func("replaceChild");
    }
    
    var postmessage_rewritten;
    
    //============================================
    function init_postmessage_override()
    {   
        if (!Window.prototype.postMessage) {
            return;
        }
        
        var orig = Window.prototype.postMessage;
        
        postmessage_rewritten = function(message, targetOrigin, transfer) {
            if (targetOrigin && targetOrigin != "*") {
                targetOrigin = window.location.origin;
            }
            
            return orig.call(this, message, targetOrigin, transfer);
        }
        
        window.postMessage = postmessage_rewritten;
        window.Window.prototype.postMessage = postmessage_rewritten;
        
        for (var i = 0; i < window.frames.length; i++) {
            try {
                window.frames[i].postMessage = postmessage_rewritten;
            } catch (e) {
                console.log(e);
            }
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
    function wombat_init(replay_prefix, capture_date, orig_scheme, orig_host, timestamp) {
        wb_replay_prefix = replay_prefix;

        wb_replay_date_prefix = replay_prefix + capture_date + "em_/";
        
        if (capture_date.length > 0) {
            wb_capture_date_part = "/" + capture_date + "/";
        } else {
            wb_capture_date_part = "";
        }
        
        wb_orig_scheme = orig_scheme + '://';

        wb_orig_host = wb_orig_scheme + orig_host;
        
        init_bad_prefixes(replay_prefix);

        // Location
        var wombat_location = new WombatLocation(window.self.location);
        
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

        if (window.self.location != window.top.location) {
            if (is_framed) {
                window.top.WB_wombat_location = window.WB_wombat_location;
                window.WB_wombat_top = window.self;
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
        document.WB_wombat_domain = orig_host;
        document.WB_wombat_referrer = extract_orig(document.referrer);

        // History
        copy_history_func(window.history, 'pushState');
        copy_history_func(window.history, 'replaceState');
        
        // open
        init_open_override();

        // postMessage
        init_postmessage_override();
        
        // Ajax
        init_ajax_rewrite();
        init_worker_override();

        // DOM
        init_dom_override();

        // Random
        init_seeded_random(timestamp);
    }

    return wombat_init;

})(this);
