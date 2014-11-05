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

        if (wbinfo.url.indexOf("://www.youtube.com/watch") > 0) {
            var ytvideo = document.getElementsByTagName("video");
/*
            if (ytvideo.length == 1) {
                if (ytvideo[0].getAttribute("data-youtube-id") != "") {
                    // Wait to see if video is playing, if so, don't replace it
                    window.setTimeout(function() {
                        if (ytvideo[0].readyState == 0) {
                            console.log("Replacing Broken Video");
                            check_replacement(ytvideo[0], wbinfo.url);
                        }
                    }, 3000);
                }
            }
*/
        }
    }

    function check_replacement(elem, src) {
        if (!src) {
            return;
        }

        if (src.indexOf("javascript:") == 0) {
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

        var tag = elem.tagName.toLowerCase();
        console.log("REPLACING: " + video_url);

        var width, height;

        if (tag == "video") {
            elem = elem.parentNode;
            elem = elem.parentNode;

            width = elem.clientWidth;
            height = elem.clientHeight;

            elem = elem.parentNode;
            //elem.parentNode.setAttribute("id", "_wb_vid");
        } else {
            width = elem.clientWidth;
            height = elem.clientHeight;
        }

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

        if (tag == "iframe") {
            elem.parentNode.replaceChild(htmlvideo, elem);
        } else if (tag == "embed") {
            if (elem.parentNode && elem.parentElement.tagName.toLowerCase() == "object") {
                elem = elem.parentNode;
            }
            elem.parentNode.replaceChild(htmlvideo, elem);
        } else if (tag == "video") {
        //    elem = elem.parentNode;
        //    elem = elem.parentNode;
            elem.parentNode.replaceChild(htmlvideo, elem);
        }
    }

    document.addEventListener("DOMContentLoaded", check_videos);
})();
