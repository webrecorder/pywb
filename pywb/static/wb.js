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

function __WbJsInit() {

var bid = undefined;


function init_banner() {
    var PLAIN_BANNER_ID = "_wb_plain_banner";
    var FRAME_BANNER_ID = "_wb_frame_top_banner";

    if (!window.wbinfo || (window.__WB_replay_top && window != window.__WB_replay_top)) {
        return;
    }

    if (!bid) {
        if (wbinfo.is_frame) {
            bid = FRAME_BANNER_ID;
        } else {
            bid = PLAIN_BANNER_ID;
        }
    }

    if (!document || !document.body) {
        return;
    }

    if (document.getElementById(bid) != null) {
        return;
    }

    var res = _wb_js.create_banner_element(bid);
    if (res) {
        bid = res;
    }
}

this.banner_labels = {LOADING_MSG: "Loading...",
                      REPLAY_MSG: "This is an <b>archived</b> page from ",
                      LIVE_MSG: "This is a <b>live</b> page loaded on "};

this.create_banner_element = function() {
    // No banner by default
    return null;
}

this.ts_to_date = function(ts, is_gmt)
{
    if (!ts) {
        return "";
    }

    if (ts.length < 14) {
        ts += "00000000000000".substr(ts.length);
    }

    var datestr = (ts.substring(0, 4) + "-" +
                  ts.substring(4, 6) + "-" +
                  ts.substring(6, 8) + "T" +
                  ts.substring(8, 10) + ":" +
                  ts.substring(10, 12) + ":" +
                  ts.substring(12, 14) + "-00:00");

    var date = new Date(datestr);
    if (is_gmt) {
        return date.toGMTString();
    } else {
        return date.toLocaleString();
    }
}

function add_event(name, func, object) {
    if (object.addEventListener) {
        object.addEventListener(name, func);
        return true;
    } else if (object.attachEvent) {
        object.attachEvent("on" + name, func);
        return true;
    } else {
        return false;
    }
}

function remove_event(name, func, object) {
    if (object.removeEventListener) {
        object.removeEventListener(name, func);
        return true;
    } else if (object.detachEvent) {
        object.detachEvent("on" + name, func);
        return true;
    } else {
        return false;
    }
}

function notify_top(event) {
    if (!window.__WB_top_frame) {
        return;
    }

    if (!window.WB_wombat_location) {
        return;
    }

    if (typeof(window.WB_wombat_location.href) != "string") {
        return;
    }

    var message = {
               "url": window.WB_wombat_location.href,
               "ts": wbinfo.timestamp,
               "request_ts": wbinfo.request_ts,
               "is_live": wbinfo.is_live,
               "title": document ? document.title : "",
               "wb_type": "load",
              }

    window.__WB_top_frame.postMessage(message, "*");

    //remove_event("readystatechange", notify_top, document);
}

this.load = function() {
    if (window._wb_js_inited) {
        return;
    }

    window._wb_js_inited = true;

    // Non-Framed Replay OR top frame for framed replay!
    if (window.wbinfo && !window.__WB_top_frame) {
        if (wbinfo.is_framed && wbinfo.mod != "bn_") {
            var hash = window.location.hash;

            var loc = window.location.href.replace(window.location.hash, "");
            loc = decodeURI(loc);

            var top_url = wbinfo.top_url;

            if (wbinfo.top_url && (loc != decodeURI(wbinfo.top_url))) {
                // Auto-redirect to top frame
                window.location.replace(wbinfo.top_url + hash);
                return;
            }
        }
        // Init Banner (no frame or top frame)
        add_event("readystatechange", init_banner, document);

    // Framed Replay
    } else if (window.__WB_top_frame) {
        add_event("readystatechange", notify_top, document);
    }
}

};


_wb_js = new __WbJsInit();
