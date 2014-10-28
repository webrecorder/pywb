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

// VidRw 1.0 -- video rewriting

__wbvidrw = (function() {

    var already_checked = false;

    function check_videos() {
        if (already_checked) {
            return;
        }

        var iframes = document.getElementsByTagName("iframe");

        for (var i = 0; i < iframes.length; i++) {
            already_checked = true;
            check_replacement(iframes[i], iframes[i].getAttribute("src"));
        }

        var embeds = document.getElementsByTagName("embed");

        for (var i = 0; i < embeds.length; i++) {
            already_checked = true;
            check_replacement(embeds[i], embeds[i].getAttribute("src"));
        }
    }

    function check_replacement(elem, src) {
        if (!src) {
            return;
        }

        src = _wb_wombat.extract_orig(src);

        var xhr = new XMLHttpRequest();
        xhr._no_rewrite = true;
        xhr.open('GET', wbinfo.prefix + 'vi_/' + src, true);
        xhr.onload = function() {
            if (xhr.status == 200) {
                do_replace_video(elem, JSON.parse(xhr.responseText));
            }
        };
        xhr.send();
    }

    function do_replace_video(elem, video_info) {
        // TODO: select based on size?
        var video_url = video_info.url;
        video_url = wbinfo.prefix + video_url;

        console.log("REPLACING: " + video_url);
        var width = elem.getAttribute("width");
        var height = elem.getAttribute("height");

        console.log(video_info.ext);

        // Try HTML5 Video
        var htmlvideo = document.createElement("video");

        htmlvideo.setAttribute("src", video_url);
        htmlvideo.setAttribute("width", width);
        htmlvideo.setAttribute("height", height);
        htmlvideo.setAttribute("controls", "1");
        htmlvideo.style.backgroundColor = "#000";

        if (video_info.thumbnail) {
            var thumbnail = wbinfo.prefix + video_info.thumbnail;
            htmlvideo.setAttribute("thumbnail", thumbnail);
        }

        htmlvideo.addEventListener("error", function() {
            console.log("html5 video error");
        });

        htmlvideo.addEventListener("loadstart", function() {
            console.log("html5 video success");
        });

        console.log(elem.tagName);

        if (elem.tagName.toLowerCase() == "iframe") {
            elem.parentNode.replaceChild(htmlvideo, elem);
        } else if (elem.tagName.toLowerCase() == "embed") {
            if (elem.parentNode && elem.parentElement.tagName.toLowerCase() == "object") {
                elem = elem.parentNode;
            }
            elem.parentNode.replaceChild(htmlvideo, elem);
        }
    }

    document.addEventListener("DOMContentLoaded", check_videos);
})();
