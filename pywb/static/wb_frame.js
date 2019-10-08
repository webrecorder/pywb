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

/**
 * @param {Object} content_info - Information about the contents to be replayed
 */
function ContentFrame(content_info) {
  if (!(this instanceof ContentFrame)) return new ContentFrame(content_info);
  this.last_inner_hash = window.location.hash;
  this.last_url = content_info.url;
  this.last_ts = content_info.request_ts;
  this.content_info = content_info;
  // bind event callbacks
  this.outer_hash_changed = this.outer_hash_changed.bind(this);
  this.handle_event = this.handle_event.bind(this);
  this.wbBanner = null;
  this.checkBannerToId = null;

  window.addEventListener('hashchange', this.outer_hash_changed, false);
  window.addEventListener('message', this.handle_event);

  if (document.readyState === 'complete') {
    this.init_iframe();
  } else {
    document.addEventListener('DOMContentLoaded', this.init_iframe.bind(this), {
      once: true
    });
  }

  window.__WB_pmw = function(win) {
    this.pm_source = win;
    return this;
  };
}

/**
 * @desc Initializes the replay iframe. If a banner exists (exposed on window as WBBanner)
 * then the init function of the banner is called.
 */
ContentFrame.prototype.init_iframe = function() {
  if (typeof this.content_info.iframe === 'string') {
    this.iframe = document.querySelector(this.content_info.iframe);
  } else {
    this.iframe = this.content_info.iframe;
  }

  if (!this.iframe) {
    console.warn('no iframe found ' + this.content_info.iframe + ' found');
    return;
  }

  this.extract_prefix();
  if (window.WBBanner) {
    this.wbBanner = window.WBBanner;
    this.wbBanner.init();
  }
  this.load_url(this.content_info.url, this.content_info.request_ts);
};

/**
 * @desc Initializes the prefixes used to load the pages to be replayed
 */
ContentFrame.prototype.extract_prefix = function() {
  this.app_prefix = this.content_info.app_prefix || this.content_info.prefix;
  this.content_prefix =
    this.content_info.content_prefix || this.content_info.prefix;

  if (this.app_prefix && this.content_prefix) {
    return;
  }

  var inx = window.location.href.indexOf(this.content_info.url);

  if (inx < 0) {
    inx = window.location.href.indexOf('/http') + 1;
    if (inx <= 0) {
      inx = window.location.href.indexOf('///') + 1;
      if (inx <= 0) {
        console.warn('No Prefix Found!');
      }
    }
  }

  this.prefix = window.location.href.substr(0, inx);

  this.app_prefix = this.app_prefix || this.prefix;
  this.content_prefix = this.content_prefix || this.prefix;
};

/**
 * @desc Returns an absolute URL (with correct prefix and replay modifier) given
 * the replayed pages URL and optional timestamp and content_url
 * @param {string} url - The URL of the replayed page
 * @param {?string} ts - The timestamp of the replayed page
 * @param {?boolean} content_url - Is the abs URL to be constructed using the content_prefix or app_prefix
 * @returns {string}
 */
ContentFrame.prototype.make_url = function(url, ts, content_url) {
  var mod, prefix;

  if (content_url) {
    mod = 'mp_';
    prefix = this.content_prefix;
  } else {
    mod = '';
    prefix = this.app_prefix;
  }

  if (ts || mod) {
    mod += '/';
  }

  if (ts) {
    return prefix + ts + mod + url;
  } else {
    return prefix + mod + url;
  }
};

/**
 * @desc Handles and routes all messages received from the replay iframe.
 * @param {MessageEvent} event - A message event potentially containing a message from the replay iframe
 */
ContentFrame.prototype.handle_event = function(event) {
  var frame_win = this.iframe.contentWindow;
  if (event.source === window.parent) {
    // Pass to replay frame
    frame_win.postMessage(event.data, '*');
  } else if (event.source === frame_win) {
    // Check if iframe url change message
    if (typeof event.data === 'object' && event.data['wb_type']) {
      this.handle_message(event);
    } else {
      // Pass to parent
      window.parent.postMessage(event.data, '*');
    }
  }
};

/**
 * @desc Handles messages intended for the content frame (indicated by data.wb_type). If a banner
 * is exposed, calls the onMessage function of the exposed banner.
 * @param {MessageEvent} event - The message event containing a message from the replay iframe
 */
ContentFrame.prototype.handle_message = function(event) {
  if (this.wbBanner) {
    this.wbBanner.onMessage(event);
  }
  var state = event.data;
  var type = state.wb_type;

  if (type === 'load' || type === 'replace-url') {
    this.set_url(state);
  } else if (type === 'hashchange') {
    this.inner_hash_changed(state);
  }
};

/**
 * @desc Updates the URL of the top frame
 * @param {Object} state - The contents of a message rreceived from the replay iframe
 */
ContentFrame.prototype.set_url = function(state) {
  if (
    state.url &&
    (state.url !== this.last_url || state.request_ts !== this.last_ts)
  ) {
    var new_url = this.make_url(state.url, state.request_ts, false);

    window.history.replaceState(state, '', new_url);

    this.last_url = state.url;
    this.last_ts = state.request_ts;
  }
};

/**
 * @desc Checks to see if the banner is still indicating the replay iframe is still loading
 * 2 seconds after the load event is fired by the replay iframe. If the banner is still
 * indicating the replayed page is loading. Updates the displayed information using
 * newURL and newTS
 * @param {string} newUrl - The new URL of the replay iframe
 * @param {?string} newTs - The new timestamp of the replay iframe. Is falsy if
 * operating in live mode
 */
ContentFrame.prototype.initBannerUpdateCheck = function(newUrl, newTs) {
  if (!this.wbBanner) return;
  var contentFrame = this;
  var replayIframeLoaded = function() {
    contentFrame.iframe.removeEventListener('load', replayIframeLoaded);
    contentFrame.checkBannerToId = setTimeout(function() {
      contentFrame.checkBannerToId = null;
      if (contentFrame.wbBanner.stillIndicatesLoading()) {
        contentFrame.wbBanner.updateCaptureInfo(
          newUrl,
          newTs,
          contentFrame.content_prefix.indexOf('/live') !== -1
        );
      }
    }, 2000);
  };
  if (this.checkBannerToId) {
    clearTimeout(this.checkBannerToId);
  }
  this.iframe.addEventListener('load', replayIframeLoaded);
};

/**
 * @desc Navigates the replay iframe to a newURL and if a banner is exposed
 * the initBannerUpdateCheck function is called.
 * @param {string} newUrl - The new URL of the replay iframe
 * @param {?string} newTs - The new timestamp of the replay iframe. Is falsy if
 * operating in live mode
 */
ContentFrame.prototype.load_url = function(newUrl, newTs) {
  this.iframe.src = this.make_url(newUrl, newTs, true);
  if (this.wbBanner) {
    this.initBannerUpdateCheck(newUrl, newTs);
  }
};

/**
 * @desc Updates this frames hash to the one inside the replay iframe
 * @param {Object} state - The contents of message received from the replay iframe
 */
ContentFrame.prototype.inner_hash_changed = function(state) {
  if (window.location.hash !== state.hash) {
    window.location.hash = state.hash;
  }
  this.last_inner_hash = state.hash;
};

/**
 * @desc Updates the hash of the replay iframe on a hash change in this frame
 * @param event
 */
ContentFrame.prototype.outer_hash_changed = function(event) {
  if (window.location.hash === this.last_inner_hash) {
    return;
  }

  if (this.iframe) {
    var message = { wb_type: 'outer_hashchange', hash: window.location.hash };

    this.iframe.contentWindow.postMessage(message, '*', undefined, true);
  }
};

/**
 * @desc Cleans up any event listeners added by the content frame
 */
ContentFrame.prototype.close = function() {
  window.removeEventListener('hashchange', this.outer_hash_changed);
  window.removeEventListener('message', this.handle_event);
};
