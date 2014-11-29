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

    var found_embeds = false;

    function check_videos() {
        if (found_embeds) {
            return;
        }

        var tags = [];

        var iframes = document.getElementsByTagName("iframe");

       /* for (var i = 0; i < iframes.length; i++) {
            found_embeds = true;
            tags.push([iframes[i], iframes[i].getAttribute("src")]);
        }
        */

        var embeds = document.getElementsByTagName("embed");

        for (var i = 0; i < embeds.length; i++) {
            found_embeds = true;
            tags.push([embeds[i], embeds[i].getAttribute("src")]);
        }

        var objects = document.getElementsByTagName("object");

        for (var i = 0; i < objects.length; i++) {
            var obj_url = undefined;

/*            if (is_watch_page(wbinfo.url)) {
                check_replacement(objects[i], wbinfo.url);
                console.log('IS WATCH');
                continue;
            }
*/

            for (var j = 0; j < objects[i].children.length; j++) {
                var child = objects[i].children[j];

                if (child.tagName == "EMBED") {
                    break;
                }

                if (child.tagName == "PARAM") {
                    var name = child.getAttribute("name");
                    name = name.toLowerCase();
                    if (name == "flashvars") {
                        var value = child.getAttribute("value");
                        value = decodeURIComponent(value);
                        var inx = value.indexOf("=http");
                        if (inx >= 0) {
                            obj_url = value.substring(inx + 1);
                            break;
                        }
                    }

                    if (name == "movie") {
                        var value = child.getAttribute("value");
                        obj_url = value;
                        break;
                    }
                }
            }

            console.log("OBJ URL: " + obj_url);


            //check_replacement(objects[i], obj_url);
            tags.push([objects[i], obj_url]);
        }

        for (var i = 0; i < tags.length; i++) {
            check_replacement(tags[i][0], tags[i][1]);
        }

        // special case: yt
        if (!found_embeds && wbinfo.url.indexOf("://www.youtube.com/watch") > 0) {
            var ytvideo = document.getElementsByTagName("video");

            if (ytvideo.length == 1) {
                if (ytvideo[0].getAttribute("data-youtube-id") != "") {
                    // Wait to see if video is playing, if so, don't replace it
                    window.setTimeout(function() {
                        if (ytvideo[0].readyState == 0) {
                            check_replacement(ytvideo[0], wbinfo.url);
                        }
                    }, 4000);
                }
            }
        }
    }

    function is_watch_page(url) {
        if (url.indexOf("://www.dailymotion.com/") > 0) {
            return true;
        }

        return false;
    }

    var VIMEO_RX = /^https?:\/\/.*vimeo.*clip_id=([^&]+).*/;

    function check_replacement(elem, src, no_retry) {
        if (!src || src.indexOf("javascript:") == 0) {
            return;
        }

        src = _wb_wombat.extract_orig(src);

        // special cases
        if (src.indexOf("dailymotion.com/swf/") > 0) {
            src = src.replace("/swf/", "/video/");
        }

        src = src.replace(VIMEO_RX, "http://player.vimeo.com/video/$1");
        console.log(src);

        var xhr = new XMLHttpRequest();
        xhr._no_rewrite = true;
        xhr.open('GET', wbinfo.prefix + 'vi_/' + src, true);
        xhr.onload = function() {
            if (xhr.status == 200) {
                do_replace_video(elem, JSON.parse(xhr.responseText));
            } else if (!no_retry) {
                check_replacement(elem, wbinfo.url, true);
                console.log("REPL RETRY: " + wbinfo.url);
            }
        };
        xhr.send();
    }

    function do_replace_video(elem, info) {
        var video_url = video_url = wbinfo.prefix + info.url;

        var thumb_url = null;

        if (info.thumbnail) {
            thumb_url = wbinfo.prefix + info.thumbnail;
        }

        var tag = elem.tagName.toLowerCase();

        var width, height;

        if (tag == "video") {
            elem = elem.parentNode;
            elem = elem.parentNode;

            width = elem.clientWidth;
            height = elem.clientHeight;

            elem = elem.parentNode;
        } else {
            width = elem.clientWidth;
            height = elem.clientHeight;
        }

        // Try HTML5 Video
        var htmlvideo = document.createElement("video");

        var replacement = null;

        if (htmlvideo.canPlayType) {
            if (can_play(htmlvideo, info.ext, "video/")) {
               replacement = init_html_video(htmlvideo, width, height, video_url, thumb_url);
            } else if (can_play(htmlvideo, info.ext, "audio/")) {
               replacement = init_html_audio(video_url);
            } else {
                var best_match_heur = 1000000;
                var best_url = undefined;

                for (i = 0; i < info.formats.length; i++) {
                    if (can_play(htmlvideo, info.formats[i].ext)) {

                        if ((Math.abs(width - info.formats[i].width) + Math.abs(height - info.formats[i].height)) < best_match_heur) {
                            best_url = info.formats[i].url;
                            console.log("ALT: " + info.formats[i].ext);
                        }
                    }
                }

                if (best_url) {
                    var original_url = video_url;
                    video_url = wbinfo.prefix + best_url;
                    replacement = init_html_video(htmlvideo, width, height, video_url, thumb_url, original_url);
                }
            }
        }

        var vidId = undefined;

        if (!replacement) {
            replacement = document.createElement("div");

            vidId = "_wb_vid" + Date.now();
            replacement.setAttribute("id", vidId);
        }

        if (tag == "iframe" || tag == "object") {
            elem.parentNode.replaceChild(replacement, elem);
        } else if (tag == "embed") {
            if (elem.parentNode && elem.parentElement.tagName.toLowerCase() == "object") {
                elem = elem.parentNode;
            }
            elem.parentNode.replaceChild(replacement, elem);
        } else if (tag == "video") {
            elem.parentNode.replaceChild(replacement, elem);
        }

        if (vidId) {
            init_flash_player(vidId, width, height, video_url, thumb_url);
        }
    }

    function can_play(elem, ext, type) {
        if (!type) {
            type = "video/";
        }

        var canplay = elem.canPlayType(type + ext);
        if (canplay === "probably" || canplay === "maybe") {
            return true;
        } else {
            return false;
        }
    }

    function init_html_audio(audio_url) {
        var htmlaudio = document.createElement("audio");
        htmlaudio.setAttribute("src", audio_url);
        htmlaudio.setAttribute("controls", "1");
        htmlaudio.style.backgroundColor = "#000";

        htmlaudio.addEventListener("error", function() {
            console.log("html5 audio error");
        });

        htmlaudio.addEventListener("loadstart", function() {
            console.log("html5 audio success");
        });

        return htmlaudio;
    }

    function init_html_video(htmlvideo, width, height, video_url, thumb_url, original_url)
    {
        htmlvideo.setAttribute("src", video_url);
        htmlvideo.setAttribute("width", width);
        htmlvideo.setAttribute("height", height);
        htmlvideo.setAttribute("controls", "1");
        htmlvideo.style.backgroundColor = "#000";

        if (thumb_url) {
            htmlvideo.setAttribute("poster", thumb_url);
        }

        htmlvideo.addEventListener("error", function() {
            console.log("html5 video error");
            var replacement = document.createElement("div");

            var vidId = "_wb_vid" + Date.now();
            replacement.setAttribute("id", vidId);

            htmlvideo.parentNode.replaceChild(replacement, htmlvideo);

            init_flash_player(vidId, width, height, original_url, thumb_url);
        });

        htmlvideo.addEventListener("loadstart", function() {
            console.log("html5 video success");
        });

        return htmlvideo;
    }

    function init_flash_player(div_id, width, height, video_url, thumb_url)
    {
        var swf = "/static/default/flowplayer/flowplayer-3.2.18.swf";

        var style = 'width: ' + width + 'px; height: ' + height + 'px; display: block';
        document.getElementById(div_id).style.cssText += ';' + style;

        flashembed(div_id, swf, {config:
            {
                clip: {
                    url: video_url
                },

                plugins: {
                    rangeRequests: true
                }

            }});
    }

    document.addEventListener("DOMContentLoaded", check_videos);
})();
