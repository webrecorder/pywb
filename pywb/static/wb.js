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
    var BANNER_ID = "_wayback_banner";

    var banner = document.getElementById(BANNER_ID);

    if (wbinfo.is_embed) {
        return;
    }

    if (!banner) {
        banner = document.createElement("wb_div");
        banner.setAttribute("id", BANNER_ID);
        banner.setAttribute("lang", "en");

        text = "This is an archived page ";
        if (wbinfo && wbinfo.capture_str) {
            text += " from <b>" + wbinfo.capture_str + "</b>";
        }
        banner.innerHTML = text;

        document.body.insertBefore(banner, document.body.firstChild);
    }
}

var readyStateCheckInterval = setInterval(function() {
    if (document.readyState === "interactive" ||
        document.readyState === "complete") {
        
        init_banner();
        
        clearInterval(readyStateCheckInterval);
    }
}, 10);
