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

// Creates the default pywb banner.
// Override this function/script to create a different type of banner


_wb_js.create_banner_element = function(banner_id)
{

    var banner = document.createElement("wb_div", true);
    banner.setAttribute("id", banner_id);
    banner.setAttribute("lang", "en");

    var text;

    if (wbinfo.is_frame) {
        text = _wb_js.banner_labels.LOADING_MSG;
    } else if (wbinfo.is_live) {
        text = _wb_js.banner_labels.LIVE_MSG;
    } else {
        text = _wb_js.banner_labels.REPLAY_MSG;
    }
    
    text = "<span id='_wb_label'>" + text + "</span>";

    var capture_str = "";
    if (wbinfo && wbinfo.timestamp) {
        capture_str = _wb_js.ts_to_date(wbinfo.timestamp, true);
    }

    text += "<b id='_wb_capture_info'>" + capture_str + "</b>";

    if (wbinfo.proxy_magic && wbinfo.url) {
        var select_url = wbinfo.proxy_magic + "/" + wbinfo.url;
        var query_url = wbinfo.proxy_magic + "/*/" + wbinfo.url;
        text += '&nbsp;<a href="//query.' + query_url + '">All Capture Times</a>';
        text += '<br/>'
        text += 'From collection <b>"' + wbinfo.coll + '"</b>&nbsp;<a href="//select.' + select_url + '">All Collections</a>';
    }
    
    banner.innerHTML = text;
    document.body.insertBefore(banner, document.body.firstChild);
}
