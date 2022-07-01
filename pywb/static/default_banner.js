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
    this.title = '';
    this.bannerUrlSet = false;
    this.onMessage = this.onMessage.bind(this);
  }

  // Functions required to be exposed by all banners

  /**
   * @desc Initialize (display) the banner
   */
  DefaultBanner.prototype.init = function () {
    this.createBanner('_wb_frame_top_banner');

    if (window.wbinfo) {
      this.set_banner(
        window.wbinfo.url,
        window.wbinfo.timestamp,
        window.wbinfo.is_live,
        window.wbinfo.is_framed ? '' : document.title
      );
    }
  };

  /**
   * @desc Fetches the prior and next capture timestamp from the cdx API
   * and adds them to the banner_info as previous_ts and next_ts
   * 
   * @param {string} url - The URL of the replayed page
   * @param {string} ts - The timestamp of the replayed page.
   */
  DefaultBanner.prototype.adjacentCrawls = function (url, timestamp) {
    prefix = window.banner_info.prefix
    cdxj_query = `${prefix}cdx?url=${url}&output=json`
    var request = new XMLHttpRequest()
    request.open('GET', cdxj_query)
    request.onload = function () {
      var data = this.response.trim().split(/\r?\n/)
      var currentTimestamp = `${timestamp}`
      data.forEach(function (crawl, index, data) {
        crawl = JSON.parse(crawl)
        if (crawl.timestamp == currentTimestamp) {
          // Get Previous Capture Link
          if (index > 0) {
            // Assign the value into the banner_info object for access later
            window.banner_info.previous_ts = JSON.parse(data[index - 1]).timestamp
          }

          // Get Next Capture Link
          if (index < data.length - 1) {
            // Assign the value into the banner_info object for access later
            window.banner_info.next_ts = JSON.parse(data[index + 1]).timestamp
          }
        }
      })
    }
    request.send()
  }

  /**
   * @desc Called by ContentFrame to detect if the banner is still showing
   * that the page is loading
   * @returns {boolean}
   */
  DefaultBanner.prototype.stillIndicatesLoading = function () {
    return !this.bannerUrlSet;
  };

  /**
   * @param {string} url - The URL of the replayed page
   * @param {?string} ts - The timestamp of the replayed page.
   * If we are in live mode this is undefined/empty string
   * @param {boolean} is_live - A bool indicating if we are operating in live mode
   */
  DefaultBanner.prototype.updateCaptureInfo = function (url, ts, is_live) {
    if (is_live && !ts) {
      ts = new Date().toISOString().replace(/[-T:.Z]/g, '');
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

    if (type === 'load' || type === 'replace-url') {
      this.state = event.data;
      this.last_state = this.state;
      this.title = event.data.title || this.title;
    } else if (type === 'title') {
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

    this.set_banner(
      this.state.url,
      this.state.ts,
      this.state.is_live,
      this.title
    );
  };

  // Functions internal to the default banner

  /**
   * @desc Navigate to different language, if available
   */

  DefaultBanner.prototype.changeLanguage = function (lang, evt) {
    evt.preventDefault();
    var path = window.location.href;
    if (path.indexOf(window.banner_info.prefix) == 0) {
      path = path.substring(window.banner_info.prefix.length);
      if (window.banner_info.locale_prefixes && window.banner_info.locale_prefixes[lang]) {
        window.location.pathname = window.banner_info.locale_prefixes[lang] + path;
      }
    }
  }

  /**
   * @desc Creates the underlying HTML elements comprising the banner
   * @param {string} bid - The id for the banner
   */
  DefaultBanner.prototype.createBanner = function (bid) {
    this.banner = document.createElement('wb_div', true);
    this.banner.setAttribute('id', bid);
    this.banner.setAttribute('lang', 'en');

    if (window.banner_info.logoImg) {
      var logo = document.createElement("a");
      logo.setAttribute("href", "/" + (window.banner_info.locale ? window.banner_info.locale + "/" : ""));
      logo.setAttribute("class", "_wb_linked_logo");

      var logoContents = "";
      logoContents += "<img src='" + window.banner_info.logoImg + "' alt='" + window.banner_info.logoAlt + "'>";
      logoContents += "<img src='" + window.banner_info.logoImg + "' class='_wb_mobile' alt='" + window.banner_info.logoAlt + "'>";

      logo.innerHTML = logoContents;
      this.banner.appendChild(logo);
    }

    // Create the container for the crawl info and links.
    this.captureDiv = document.createElement("div")
    this.captureDiv.setAttribute("class", "container")

    // Create the row to capture the columns
    this.captureDivRow = document.createElement("div")
    this.captureDivRow.setAttribute("class", "row")

    // Create the previous capture column
    this.previousCapture = document.createElement("div")
    this.previousCapture.setAttribute("class", "col-sm text-right")
    this.previousCaptureLink = document.createElement("a");
    this.previousCaptureLink.setAttribute("class", "align-middle font-weight-light text-light");
    this.previousCaptureLink.setAttribute("href", "#");
    this.previousCapture.appendChild(this.previousCaptureLink)

    // Create the next capture column
    this.nextCapture = document.createElement("div")
    this.nextCapture.setAttribute("class", "col-sm text-left")
    this.nextCaptureLink = document.createElement("a");
    this.nextCaptureLink.setAttribute("class", "align-middle font-weight-light text-light capture-link");
    this.nextCaptureLink.setAttribute("href", "#");
    this.nextCapture.appendChild(this.nextCaptureLink)

    // Create the capture info column
    this.captureInfoDiv = document.createElement("div")
    this.captureInfoDiv.setAttribute("class", "col-sm text-center")
    this.captureInfo = document.createElement("span");
    this.captureInfo.setAttribute("id", "_wb_capture_info");
    this.captureInfo.innerHTML = window.banner_info.loadingLabel;
    this.captureInfoDiv.appendChild(this.captureInfo)

    // Append the capture info columns ot the captuer info container
    this.captureDivRow.appendChild(this.previousCapture)
    this.captureDivRow.appendChild(this.captureInfoDiv);
    this.captureDivRow.appendChild(this.nextCapture)
    this.captureDiv.appendChild(this.captureDivRow)
    this.banner.appendChild(this.captureDiv)

    var ancillaryLinks = document.createElement("div");
    ancillaryLinks.setAttribute("id", "_wb_ancillary_links");

    var calendarImg = window.banner_info.calendarImg || window.banner_info.staticPrefix + "/calendar.svg";

    var calendarLink = document.createElement("a");
    calendarLink.setAttribute("id", "calendarLink");
    calendarLink.setAttribute("href", "#");
    calendarLink.innerHTML = "<img src='" + calendarImg + "' alt='" + window.banner_info.calendarAlt + "'><span class='_wb_no-mobile'>&nbsp;" + window.banner_info.calendarLabel + "</span>";
    ancillaryLinks.appendChild(calendarLink);
    this.calendarLink = calendarLink;

    if (typeof window.banner_info.locales !== "undefined" && window.banner_info.locales.length > 1) {
      var locales = window.banner_info.locales;
      var languages = document.createElement("div");

      var label = document.createElement("span");
      label.setAttribute("class", "_wb_no-mobile");
      label.appendChild(document.createTextNode(window.banner_info.choiceLabel + " "));
      languages.appendChild(label);

      for (var i = 0; i < locales.length; i++) {
        var locale = locales[i];
        var langLink = document.createElement("a");
        langLink.setAttribute("href", "#");
        langLink.addEventListener("click", this.changeLanguage.bind(this, locale));
        langLink.appendChild(document.createTextNode(locale));

        languages.appendChild(langLink);
        if (i !== locales.length - 1) {
          languages.appendChild(document.createTextNode(" / "));
        }
      }

      ancillaryLinks.appendChild(languages);
    }

    this.banner.appendChild(ancillaryLinks);

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
      return '';
    }

    if (ts.length < 14) {
      ts += '00000000000000'.substr(ts.length);
    }

    var datestr =
      ts.substring(0, 4) +
      '-' +
      ts.substring(4, 6) +
      '-' +
      ts.substring(6, 8) +
      'T' +
      ts.substring(8, 10) +
      ':' +
      ts.substring(10, 12) +
      ':' +
      ts.substring(12, 14) +
      '-00:00';

    var date = new Date(datestr);

    if (is_gmt) {
      return date.toGMTString();
    } else {
      return date.toLocaleString(window.banner_info.locale);
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

    if (!url) {
      this.captureInfo.innerHTML = window.banner_info.loadingLabel;
      this.bannerUrlSet = false;
      return;
    }

    if (!ts) {
      return;
    }

    if (title) {
      capture_str = title;
    } else {
      capture_str = url;
    }

    this.adjacentCrawls(url, ts)

    title_str = capture_str;

    capture_str = "<b id='title_or_url' title='" + capture_str + "'>" + capture_str + "</b>";

    capture_str += "<span class='_wb_capture_date'>";

    if (is_live) {
      title_str = window.banner_info.liveMsg + " " + title_str;
      capture_str += "<b>" + window.banner_info.liveMsg + "&nbsp;</b>";
    }

    capture_str += this.ts_to_date(ts, window.banner_info.is_gmt);
    capture_str += "</span>";

    this.calendarLink.setAttribute("href", window.banner_info.prefix + "*/" + url);
    this.calendarLink.style.display = is_live ? "none" : "";

    this.captureInfo.innerHTML = capture_str;

    window.document.title = title_str;

    if (window.banner_info.previous_ts) {
      this.previousCaptureLink.setAttribute("href", window.banner_info.prefix + window.banner_info.previous_ts + "/" + url)
      this.previousCaptureLink.innerHTML = "<strong><</strong> previous capture"
    }

    if (window.banner_info.next_ts) {
      this.nextCaptureLink.setAttribute("href", window.banner_info.prefix + window.banner_info.next_ts + "/" + url)
      this.nextCaptureLink.innerHTML = "next capture <strong>></strong>"
    }

    this.bannerUrlSet = true;
  };

  // all banners will expose themselves by adding themselves as WBBanner on window
  window.WBBanner = new DefaultBanner();

  // if wbinfo.url is set and not-framed, init banner in content frame
  if (window.wbinfo && window.wbinfo.url && !window.wbinfo.is_framed) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        window.WBBanner.init();
      });
    } else {
      window.WBBanner.init();
    }
  }

})();