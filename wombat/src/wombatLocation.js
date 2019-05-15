/* eslint-disable camelcase */
import { addToStringTagToClass } from './wombatUtils';

/**
 * A re-implementation of the Location interface that ensure that operations
 * on the location interface behaves as expected during replay.
 * @param {Location} orig_loc
 * @param {Wombat} wombat
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Location
 * @see https://html.spec.whatwg.org/multipage/browsers.html#the-location-interface
 */
export default function WombatLocation(orig_loc, wombat) {
  // hide our values from enumeration, spreed, et al
  Object.defineProperties(this, {
    _orig_loc: {
      configurable: true,
      enumerable: false,
      value: orig_loc
    },
    wombat: {
      configurable: true,
      enumerable: false,
      value: wombat
    },
    orig_getter: {
      enumerable: false,
      value: function(prop) {
        return this._orig_loc[prop];
      }
    },
    orig_setter: {
      enumerable: false,
      value: function(prop, value) {
        this._orig_loc[prop] = value;
      }
    }
  });

  wombat.initLocOverride(this, this.orig_setter, this.orig_getter);

  wombat.setLoc(this, orig_loc.href);

  for (var prop in orig_loc) {
    if (!this.hasOwnProperty(prop) && typeof orig_loc[prop] !== 'function') {
      this[prop] = orig_loc[prop];
    }
  }
}

/**
 * Replaces the current resource with the one at the provided URL.
 * The difference from the assign() method is that after using replace() the
 * current page will not be saved in session History, meaning the user won't
 * be able to use the back button to navigate to it.
 * @param {string} url
 * @return {*}
 */
WombatLocation.prototype.replace = function replace(url) {
  var new_url = this.wombat.rewriteUrl(url);
  var orig = this.wombat.extractOriginalURL(new_url);
  if (orig === this.href) {
    return orig;
  }
  return this._orig_loc.replace(new_url);
};

/**
 * Loads the resource at the URL provided in parameter
 * @param {string} url
 * @return {*}
 */
WombatLocation.prototype.assign = function assign(url) {
  var new_url = this.wombat.rewriteUrl(url);
  var orig = this.wombat.extractOriginalURL(new_url);
  if (orig === this.href) {
    return orig;
  }
  return this._orig_loc.assign(new_url);
};

/**
 * Reloads the resource from the current URL. Its optional unique parameter
 * is a Boolean, which, when it is true, causes the page to always be reloaded
 * from the server. If it is false or not specified, the browser may reload
 * the page from its cache.
 * @param {boolean} [forcedReload = false]
 * @return {*}
 */
WombatLocation.prototype.reload = function reload(forcedReload) {
  return this._orig_loc.reload(forcedReload || false);
};

/**
 * @return {string}
 */
WombatLocation.prototype.toString = function toString() {
  return this.href;
};

/**
 * @return {WombatLocation}
 */
WombatLocation.prototype.valueOf = function valueOf() {
  return this;
};

addToStringTagToClass(WombatLocation, 'Location');
