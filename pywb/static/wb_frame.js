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

var LIVE_COOKIE_REGEX = /pywb.timestamp=([\d]{1,14})/;

var TS_REGEX = /\/([\d]{1,14})(?:\w+_)?\/(?:\w+[:])?\/\//;

//var curr_state = {};

var IFRAME_ID = "replay_iframe";

var last_inner_hash = undefined;

function make_url(url, ts, mod, prefix)
{
    if (ts || mod) {
        mod += "/";
    }

    prefix = prefix || wbinfo.prefix;

    if (ts) {
        return prefix + ts + mod + url;
    } else {
        return prefix + mod + url;
    }
}

function push_state(state) {
    /*
    var frame = document.getElementById(IFRAME_ID).contentWindow;
    if (frame.WB_wombat_location) {
        var curr_href = frame.WB_wombat_location.href;

        // If not current url, don't update
        if (state.url != curr_href) {
            return;
        }
    }
    */

    state.outer_url = make_url(state.url, state.request_ts, wbinfo.frame_mod, wbinfo.outer_prefix);
    state.inner_url = make_url(state.url, state.request_ts, wbinfo.replay_mod);

    var canon_url = make_url(state.url, state.request_ts, "", wbinfo.outer_prefix);

    if (window.location.href != canon_url) {
        if (state.wb_type != "pushState") {
            window.history.replaceState(state, "", canon_url);
        } else {
            window.history.pushState(state, "", canon_url);
        }
    }

    set_state(state);
}

function pop_state(state) {
    set_state(state);

    //var frame = document.getElementById(IFRAME_ID);
    //frame.src = state.inner_url;
}

function extract_ts(url)
{
    var result = url.match(TS_REGEX);
    if (!result) {
        return "";
    }

    return result[1];
}

function extract_replay_url(url) {
    var inx = url.indexOf("/http:");
    if (inx < 0) {
        inx = url.indexOf("/https:");
        if (inx < 0) {
            return "";
        }
    }
    return url.substring(inx + 1);
}

function set_state(state) {
    var capture_info = document.getElementById("_wb_capture_info");
    if (capture_info) {
        capture_info.innerHTML = state.capture_str;
    }

    var label = document.getElementById("_wb_label");
    if (label && window._wb_js) {
        if (state.is_live) {
            label.innerHTML = _wb_js.banner_labels.LIVE_MSG;
        } else {
            label.innerHTML = _wb_js.banner_labels.REPLAY_MSG;
        }
    }

    //curr_state = state;
}

window.onpopstate = function(event) {
    var state = event.state;

    if (state) {
        pop_state(state);
    }
}

function extract_ts_cookie(value) {
    var result = value.match(LIVE_COOKIE_REGEX);
    if (result) {
        return result[1];
    } else {
        return "";
    }
}


function init_pm(frame) {
    if (!frame) {
        return;
    }

    var frame_win = frame.contentWindow;

    window.addEventListener("message", function(event) {
        if (event.source == window.parent) {
            // Pass to replay frame
            frame_win.postMessage(event.data, "*");
        } else if (event.source == frame_win) {

            // Check if iframe url change message
            if (typeof(event.data) == "object" && event.data["wb_type"]) {
                handle_message(event.data);

            } else {
                // Pass to parent
                window.parent.postMessage(event.data, "*");
            }
        }
    });

    window.__WB_pmw = function(win) {
        this.pm_source = win;
        return this;
    }
}


function handle_message(state) {
    var type = state.wb_type;

    if (type == "load" || type == "pushState" || type == "replaceState") {
        update_wb_url(state);
    } else if (type == "go") {
        window.history.go(state.param);
    } else if (type == "back") {
        window.history.back();
    } else if (type == "forward") {
        window.history.forward();
    } else if (type == "hashchange") {
        inner_hash_changed(state);
    }
}


function update_wb_url(state) {
    if (window._wb_js) {
        state['capture_str'] = _wb_js.ts_to_date(state.ts, true);
    }

    push_state(state);
}

function inner_hash_changed(state) {
    if (window.location.hash != state.hash) {
        window.location.hash = state.hash;
    }
    last_inner_hash = state.hash;
}

function outer_hash_changed(event) {
    if (window.location.hash == last_inner_hash) {
        return;
    }

    var frame = document.getElementById(IFRAME_ID);

    if (frame) {
        var message = {"wb_type": "outer_hashchange", "hash": window.location.hash}

        frame.contentWindow.postMessage(message, "*", undefined, true);
    }
}

function init_hash_connect() {
    var frame = document.getElementById(IFRAME_ID);

    if (!frame) {
        return;
    }
    
    if (window.location.hash) {
        var curr_url = wbinfo.capture_url + window.location.hash;

        frame.src = make_url(curr_url, wbinfo.request_ts, wbinfo.replay_mod);

        last_inner_hash = window.location.hash;
        //frame.location.href = make_url(curr_url, wbinfo.request_ts, wbinfo.replay_mod);
        //frame.location.hash = window.location.hash;
    }

    if ("onhashchange" in window) {
        window.addEventListener("hashchange", outer_hash_changed, false);
    }

    // Init Post Message connect
    init_pm(frame);
}

document.addEventListener("DOMContentLoaded", init_hash_connect);

// Load Banner
if (window._wb_js) {
    _wb_js.load();
}



