/*
Copyright(c) 2013-2018 Rhizome and Ilya Kreymer. Released under the GNU General Public License.

This file is part of pywb, https://github.com/webrecorder/pywb

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
        if (typeof(content_info.iframe) === "string") {
            this.iframe = document.querySelector(content_info.iframe);
        } else {
            this.iframe = content_info.iframe;
        }

        if (!this.iframe) {
            console.warn("no iframe found " + content_info.iframe + " found");
            return;
        }

        this.extract_prefix();

        this.load_url(content_info.url, content_info.request_ts);
    }

    this.extract_prefix = function() {
        this.app_prefix = content_info.app_prefix || content_info.prefix;
        this.content_prefix = content_info.content_prefix || content_info.prefix;

        if (this.app_prefix && this.content_prefix) {
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

        this.prefix = window.location.href.substr(0, inx);

        this.app_prefix = this.app_prefix || this.prefix;
        this.content_prefix = this.content_prefix || this.prefix;
    }


    this.make_url = function(url, ts, content_url) {
        var mod, prefix;

        if (content_url) {
            mod = "mp_";
            prefix = this.content_prefix;
        } else {
            mod = "";
            prefix = this.app_prefix;
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

    this.load_url = function(newUrl, newTs) {
        this.iframe.src = this.make_url(newUrl, newTs, true);
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

    this.close = function() {
        window.removeEventListener("hashchange", this.outer_hash_changed);
        window.removeEventListener("message", this.handle_event);
    }

    // bind event callbacks
    this.outer_hash_changed = this.outer_hash_changed.bind(this);
    this.handle_event = this.handle_event.bind(this);

    window.addEventListener("hashchange", this.outer_hash_changed, false);
    window.addEventListener("message", this.handle_event);

    if (document.readyState === "complete") {
        this.init_iframe();
    } else {
        document.addEventListener("DOMContentLoaded", this.init_iframe.bind(this), { once: true });
    }

    window.__WB_pmw = function(win) {
        this.pm_source = win;
        return this;
    }
}
