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


function ContentFrame(content_info) {
    this.last_inner_hash = window.location.hash;
    this.last_url = content_info.url;
    this.last_ts = content_info.request_ts;

    this.init_iframe = function() {
        var iframe = document.createElement("iframe");
        iframe.seamless = "seamless";
        iframe.scrolling = "yes";

        content_info.iframe_div = content_info.iframe_div || "#wb_iframe_div";
        content_info.iframe_class = content_info.iframe_class || "wb_iframe";

        var container = document.querySelector(content_info.iframe_div);

        if (!container) {
            console.warn("No Iframe container: " + content_info.iframe_div + " found");
            return;
        }

        this.extract_prefix();

        this.iframe = container.appendChild(iframe);

        if (content_info.iframe_class) {
            this.iframe.className += " " + content_info.iframe_class;
        }

        this.iframe.src = this.make_url(content_info.url + window.location.hash, content_info.request_ts, true);
    }

    this.extract_prefix = function() {
        if (content_info.prefix) {
            return;
        }

        var inx = window.location.href.indexOf(content_info.url);
        if (inx < 0) {
            inx = window.location.href.indexOf("/http") + 1;
            if (inx <= 0) {
                inx = window.location.href.indexOf("///") + 1;
                if (inx <= 0) {
                    console.warn("No Prefix Found!");
                }
            }
        }

        content_info.prefix = window.location.href.substr(0, inx);
    }


    this.make_url = function(url, ts, content_url) {
        var mod, prefix;

        if (content_url) {
            mod = "mp_";
            prefix = content_info.content_prefix || content_info.prefix;
        } else {
            mod = "";
            prefix = content_info.prefix;
        }

        if (ts || mod) {
            mod += "/";
        }

        if (ts) {
            return prefix + ts + mod + url;
        } else {
            return prefix + mod + url;
        }
    }

    this.handle_event = function(event) {
        var frame_win = this.iframe.contentWindow;
        if (event.source == window.parent) {
            // Pass to replay frame
            frame_win.postMessage(event.data, "*");
        } else if (event.source == frame_win) {

            // Check if iframe url change message
            if (typeof(event.data) == "object" && event.data["wb_type"]) {
                this.handle_message(event.data);

            } else {
                // Pass to parent
                window.parent.postMessage(event.data, "*");
            }
        }
    }

    this.handle_message = function(state) {
        var type = state.wb_type;

        if (type == "load" || type == "replace-url") {
            this.set_url(state);
        } else if (type == "hashchange") {
            this.inner_hash_changed(state);
        }
    }


    this.set_url = function(state) {
        if (state.url && (state.url != this.last_url || state.request_ts != this.last_ts)) {
            var new_url = this.make_url(state.url, state.request_ts, false);

            window.history.replaceState(state, "", new_url);

            this.last_url = state.url;
            this.last_ts = state.request_ts;
        }
    }

    this.inner_hash_changed = function(state) {
        if (window.location.hash != state.hash) {
            window.location.hash = state.hash;
        }
        this.last_inner_hash = state.hash;
    }

    this.outer_hash_changed = function(event) {
        if (window.location.hash == this.last_inner_hash) {
            return;
        }

        if (this.iframe) {
            var message = {"wb_type": "outer_hashchange", "hash": window.location.hash}

            this.iframe.contentWindow.postMessage(message, "*", undefined, true);
        }
    }

    var obj = this;

    document.addEventListener("DOMContentLoaded", function(event) { obj.init_iframe(event); });
    window.addEventListener("hashchange", function(event) { obj.outer_hash_changed(event); }, false);
    window.addEventListener("message", function(event) { obj.handle_event(event); });

    window.__WB_pmw = function(win) {
        this.pm_source = win;
        return this;
    }
}

