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

(function() {
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
  DefaultBanner.prototype.init = function() {
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
   * @desc Called by ContentFrame to detect if the banner is still showing
   * that the page is loading
   * @returns {boolean}
   */
  DefaultBanner.prototype.stillIndicatesLoading = function() {
    return !this.bannerUrlSet;
  };

  /**
   * @param {string} url - The URL of the replayed page
   * @param {?string} ts - The timestamp of the replayed page.
   * If we are in live mode this is undefined/empty string
   * @param {boolean} is_live - A bool indicating if we are operating in live mode
   */
  DefaultBanner.prototype.updateCaptureInfo = function(url, ts, is_live) {
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
  DefaultBanner.prototype.onMessage = function(event) {
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

  DefaultBanner.prototype.changeLanguage = function(lang, evt) {
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
  DefaultBanner.prototype.createBanner = function(bid) {
    this.header = document.createElement('header');
    this.header.setAttribute('role', 'banner');
    this.nav = document.createElement('nav');

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

    this.captureInfo = document.createElement("span");
    this.captureInfo.setAttribute("id", "_wb_capture_info");
    this.captureInfo.innerHTML = window.banner_info.loadingLabel;
    this.banner.appendChild(this.captureInfo);

    var ancillaryLinks = document.createElement("div");
    ancillaryLinks.setAttribute("id", "_wb_ancillary_links");

    var calendarImg = window.banner_info.calendarImg || window.banner_info.staticPrefix + "/calendar.svg";

    var calendarLink = document.createElement("a");
    calendarLink.setAttribute("id", "calendarLink");
    calendarLink.setAttribute("href", "#");
    calendarLink.innerHTML = "<img src='" + calendarImg + "' alt='" + window.banner_info.calendarAlt + "'><span class='_wb_no-mobile'>&nbsp;" +window.banner_info.calendarLabel + "</span>";
    ancillaryLinks.appendChild(calendarLink);
    this.calendarLink = calendarLink;

    if (typeof window.banner_info.locales !== "undefined" && window.banner_info.locales.length > 1) {
      var locales = window.banner_info.locales;
      var languages = document.createElement("div");

      var label = document.createElement("span");
      label.setAttribute("class", "_wb_no-mobile");
      label.appendChild(document.createTextNode(window.banner_info.choiceLabel + " "));
      languages.appendChild(label);

      for(var i = 0; i < locales.length; i++) {
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
    this.nav.appendChild(this.banner);
    this.header.appendChild(this.nav);
    document.body.insertBefore(this.header, document.body.firstChild);
  };

  /**
   * @desc Converts a timestamp to a date string. If is_gmt is truthy then
   * the returned data string will be the results of date.toGMTString otherwise
   * its date.toLocaleString()
   * @param {?string} ts - The timestamp to receive the correct date string for
   * @param {boolean} is_gmt - Is the returned date string to be in GMT time
   * @returns {string}
   */
  DefaultBanner.prototype.ts_to_date = function(ts, is_gmt) {
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
  DefaultBanner.prototype.set_banner = function(url, ts, is_live, title) {
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

    this.bannerUrlSet = true;
  };

  // all banners will expose themselves by adding themselves as WBBanner on window
  window.WBBanner = new DefaultBanner();

  // if wbinfo.url is set and not-framed, init banner in content frame
  if (window.wbinfo && window.wbinfo.url && !window.wbinfo.is_framed) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function() {
        window.WBBanner.init();
      });
    } else {
      window.WBBanner.init();
    }
  }

})();
