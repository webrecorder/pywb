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

function init_banner() {
    var PLAIN_BANNER_ID = "_wb_plain_banner";
    var FRAME_BANNER_ID = "_wb_frame_top_banner";

    if (wbinfo.is_embed) {
        return;
    }

    if (window.top != window.self) {
        return;
    }

    if (wbinfo.is_frame) {
        bid = FRAME_BANNER_ID;
    } else {
        bid = PLAIN_BANNER_ID;
    }

    var banner = document.getElementById(bid);
    
    if (!banner) {
        banner = document.createElement("wb_div");
        banner.setAttribute("id", bid);
        banner.setAttribute("lang", "en");

        text = "This is an archived page ";
        if (wbinfo && wbinfo.capture_str) {
            text += " from <b>" + wbinfo.capture_str + "</b>";
        }
        banner.innerHTML = text;

        document.body.insertBefore(banner, document.body.firstChild);
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

var notified_top = false;

var detect_on_init = function() {
    if (!notified_top && window && window.top && (window.self != window.top) && window.WB_wombat_location) {
        if (!wbinfo.is_embed) {
            window.top.postMessage(window.WB_wombat_location.href, "*");
        }
        notified_top = true;
    }

    if (document.readyState === "interactive" ||
        document.readyState === "complete") {
        
        init_banner();

        remove_event("readystatechange", detect_on_init, document);
    }
}

add_event("readystatechange", detect_on_init, document);


if (wbinfo.is_frame_mp && wbinfo.canon_url &&
   (window.self == window.top) && 
   window.location.href != wbinfo.canon_url) {
    
    console.log('frame');
    window.location.replace(wbinfo.canon_url);
}
