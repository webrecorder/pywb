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

var TS_REGEX = /\/([\d]{1,14})\//;

var curr_state = {};

var IFRAME_ID = "replay_iframe";

function make_url(url, ts, mod)
{
    if (ts || mod) {
        mod += "/";
    }

    if (ts) {
        return wbinfo.prefix + ts + mod + url;
    } else {
        return wbinfo.prefix + mod + url;
    }
}

function push_state(url, timestamp, request_ts, capture_str, is_live) {
    var frame = document.getElementById(IFRAME_ID).contentWindow;
    if (frame.WB_wombat_location) {
        var curr_href = frame.WB_wombat_location.href;

        // If not current url, don't update
        if (url != curr_href) {
            return;
        }
    }

    var state = {}
    state.timestamp = timestamp;
    state.request_ts = request_ts;
    state.outer_url = make_url(url, state.request_ts, wbinfo.frame_mod);
    state.inner_url = make_url(url, state.request_ts, wbinfo.replay_mod);
    state.url = url;
    state.capture_str = capture_str;
    state.is_live = is_live;

    var canon_url = make_url(url, state.request_ts, "");
    if (window.location.href != canon_url) {
        window.history.replaceState(state, "", canon_url);
    }

    set_state(state);
}

function pop_state(state) {
    set_state(state);

    var frame = document.getElementById(IFRAME_ID).contentWindow;
    frame.src = state.inner_url;
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
    if (label) {
        if (state.is_live) {
            label.innerHTML = _wb_js.banner_labels.LIVE_MSG;
        } else {
            label.innerHTML = _wb_js.banner_labels.REPLAY_MSG;
        }
    }

    curr_state = state;
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

function iframe_loaded(event) {
    var url;
    var ts;
    var request_ts;
    var capture_str;
    var is_live = false;
    var iframe = document.getElementById(IFRAME_ID).contentWindow;

    if (iframe.WB_wombat_location) {
        url = iframe.WB_wombat_location.href;
    } else {
        url = extract_replay_url(iframe.location.href);
    }

    if (iframe.wbinfo) {
        ts = iframe.wbinfo.timestamp;
        request_ts = iframe.wbinfo.request_ts;
        is_live = iframe.wbinfo.is_live;
    } else {
        ts = extract_ts_cookie(iframe.document.cookie);
        if (ts) {
            is_live = true;
        } else {
            ts = extract_ts(iframe.location.href);
        }
        request_ts = ts;
    }

    update_wb_url(url, ts, request_ts, is_live);
}


function init_pm() {
    var frame = document.getElementById(IFRAME_ID).contentWindow;

    window.addEventListener("message", function(event) {
        // Pass to replay frame
        if (event.source == window.parent) {
            frame.postMessage(event.data, "*");
        } else if (event.source == frame) {
        // Pass to parent
            window.parent.postMessage(event.data, "*");
        }
    });

    window.__WB_pmw = function(win) {
        this.pm_source = win;
        return this;
    }
}


function update_wb_url(url, ts, request_ts, is_live) {
    if (curr_state.url == url && curr_state.timestamp == ts) {
        return;
    }

    capture_str = _wb_js.ts_to_date(ts, true);

    push_state(url, ts, request_ts, capture_str, is_live);
}

// Load Banner
if (_wb_js) {
    _wb_js.load();
}

function init_hash_connect() {
    var frame = document.getElementById(IFRAME_ID).contentWindow;
    
    if (window.location.hash) {
        var curr_url = wbinfo.capture_url + window.location.hash;
        
        frame.location.href = make_url(curr_url, wbinfo.request_ts, wbinfo.replay_mod);
        //frame.location.hash = window.location.hash;
    }
    
    function outer_hash_changed() {             
        var the_frame = document.getElementById(IFRAME_ID).contentWindow;

        if (window.location.hash == the_frame.location.hash) {
            return;
        }
              
        the_frame.location.hash = window.location.hash;
        //the_frame.location.href = make_url(curr_url, curr_state.request_ts, wbinfo.replay_mod);
    }
    
    function inner_hash_changed() {
        var the_frame = document.getElementById(IFRAME_ID).contentWindow;

        if (window.location.hash == the_frame.location.hash) {
            return;
        }
 
        window.location.hash = the_frame.location.hash;
    }

    if ("onhashchange" in window) {
        window.addEventListener("hashchange", outer_hash_changed, false);
        frame.addEventListener("hashchange", inner_hash_changed, false);
    }

    // Init Post Message connect
    init_pm();
}

document.addEventListener("DOMContentLoaded", init_hash_connect);
