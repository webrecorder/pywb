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

// Creates the default pywb banner.

(function () {
    if (window.top !== window) {
        return;
    }

    /**
     * The default banner class
     */
    function DefaultBanner() {
        if (!(this instanceof DefaultBanner)) return new DefaultBanner();
        this.banner = null;
        this.captureInfo = null;
        this.last_state = {};
        this.state = null;
        this.title = "";
        this.loadingId = 'bannerLoading';
        this.onMessage = this.onMessage.bind(this);
    }

    // Functions required to be exposed by all banners

    /**
     * @desc Initialize (display) the banner
     */
    DefaultBanner.prototype.init = function () {
        if (window.wbinfo) {
            this.createBanner('_wb_plain_banner');
            this.set_banner(
                window.wbinfo.url,
                window.wbinfo.timestamp,
                window.wbinfo.is_live,
                window.wbinfo.is_framed ? "" : document.title
            );
        } else {
            this.createBanner('_wb_frame_top_banner');
        }
    };

    /**
     * @desc Called by ContentFrame to detect if the banner is still showing
     * that the page is loading
     * @returns {boolean}
     */
    DefaultBanner.prototype.stillIndicatesLoading = function () {
        return document.getElementById(this.loadingId) != null;
    };

    /**
     * @param {string} url - The URL of the replayed page
     * @param {?string} ts - The timestamp of the replayed page.
     * If we are in live mode this is undefined/empty string
     * @param {boolean} is_live - A bool indicating if we are operating in live mode
     */
    DefaultBanner.prototype.updateCaptureInfo = function (url, ts, is_live) {
        if (is_live && !ts) {
            ts = new Date().toISOString().replace(/[-T:.Z]/g, '')
        }
        this.set_banner(url, ts, is_live, null);
    };

    /**
     * @desc Called by ContentFrame when a message is received from the replay iframe
     * @param {MessageEvent} event - The message event containing the message received
     * from the replayed page
     */
    DefaultBanner.prototype.onMessage = function (event) {
        var type = event.data.wb_type;

        if (type === "load" || type === "replace-url") {
            this.state = event.data;
            this.last_state = this.state;
            this.title = event.data.title || this.title;
        } else if (type === "title") {
            this.state = this.last_state;
            this.title = event.data.title;
        } else {
            return;
        }

        // favicon update
        if (type === 'load') {
            var head = document.querySelector('head');
            var oldLink = document.querySelectorAll("link[rel*='icon']");
            var i = 0;
            for (; i < oldLink.length; i++) {
                head.removeChild(oldLink[i]);
            }

            if (this.state.icons) {
                for (i = 0; i < this.state.icons.length; i++) {
                    var icon = this.state.icons[i];
                    var link = document.createElement('link');
                    link.rel = icon.rel;
                    link.href = icon.href;
                    head.appendChild(link);
                }
            }
        }

        this.set_banner(this.state.url, this.state.ts, this.state.is_live, this.title);
    };

    // Functions internal to the default banner

    /**
     * @desc Creates the underlying HTML elements comprising the banner
     * @param {string} bid - The id for the banner
     */
    DefaultBanner.prototype.createBanner = function (bid) {
        this.banner = document.createElement("wb_div", true);
        this.banner.setAttribute("id", bid);
        this.banner.setAttribute("lang", "en");
        this.captureInfo = document.createElement('span');
        this.captureInfo.innerHTML = '<span id="' + this.loadingId + '">Loading...</span>';
        this.captureInfo.id = '_wb_capture_info';
        this.banner.appendChild(this.captureInfo);
        document.body.insertBefore(this.banner, document.body.firstChild);
    };

    /**
     * @desc Converts a timestamp to a date string. If is_gmt is truthy then
     * the returned data string will be the results of date.toGMTString otherwise
     * its date.toLocaleString()
     * @param {?string} ts - The timestamp to receive the correct date string for
     * @param {boolean} is_gmt - Is the returned date string to be in GMT time
     * @returns {string}
     */
    DefaultBanner.prototype.ts_to_date = function (ts, is_gmt) {
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
    };

    /**
     * @desc Updates the contents displayed by the banner
     * @param {?string} url - The URL of the replayed page to be displayed in the banner
     * @param {?string} ts - A timestamp to be displayed in the banner
     * @param {boolean} is_live - Are we in live mode
     * @param {?string} title - The title of the replayed page to be displayed in the banner
     */
    DefaultBanner.prototype.set_banner = function (url, ts, is_live, title) {
        var capture_str;
        var title_str;

        if (!ts) {
            return;
        }

        var date_str = this.ts_to_date(ts, true);

        if (title) {
            capture_str = title;
        } else {
            capture_str = url;
        }

        title_str = capture_str;
        capture_str = "<b id='title_or_url'>" + capture_str + "</b>";

        if (is_live) {
            title_str = " pywb Live: " + title_str;
            capture_str += "<i>Live on&nbsp;</i>";
        } else {
            title_str += "pywb Archived: " + title_str;
            capture_str += "<i>Archived on&nbsp;</i>";
        }

        title_str += " (" + date_str + ")";
        capture_str += date_str;
        this.captureInfo.innerHTML = capture_str;
        window.document.title = title_str;
    };

    // all banners will expose themselves by adding themselves as WBBanner on window
    window.WBBanner = new DefaultBanner();
})();


