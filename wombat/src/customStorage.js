import {
  addToStringTagToClass,
  ensureNumber,
  ThrowExceptions
} from './wombatUtils';

/**
 * A re-implementation of the Storage interface.
 * This re-implementation is required for replay in order to ensure
 * that web pages that require local or session storage work as expected as
 * there is sometimes a limit on the amount of storage space that can be used.
 * This re-implementation ensures that limit is unlimited as it would be in
 * the live-web.
 * @param {Wombat} wombat
 * @param {string} proxying
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Storage
 * @see https://html.spec.whatwg.org/multipage/webstorage.html#the-storage-interface
 */
export default function Storage(wombat, proxying) {
  if (ThrowExceptions.yes) {
    // there is no constructor exposed for this interface however there is an
    // interface object exposed, thus we must throw an TypeError if userland
    // attempts to create us
    throw new TypeError('Illegal constructor');
  }
  // hide our values from enumeration, spreed, et al
  Object.defineProperties(this, {
    data: {
      enumerable: false,
      value: {}
    },
    wombat: {
      enumerable: false,
      value: wombat
    },
    proxying: {
      enumerable: false,
      value: proxying
    },
    _deleteItem: {
      enumerable: false,
      value: function(item) {
        delete this.data[item];
      }
    }
  });
}

/**
 * When passed a key name, will return that key's value
 * @param {string} name
 * @return {*}
 */
Storage.prototype.getItem = function getItem(name) {
  return this.data.hasOwnProperty(name) ? this.data[name] : null;
};

/**
 * When passed a key name and value, will add that key to the storage,
 * or update that key's value if it already exists
 * @param {string} name
 * @param {*} value
 * @return {*}
 */
Storage.prototype.setItem = function setItem(name, value) {
  var sname = String(name);
  var svalue = String(value);
  var old = this.getItem(sname);
  this.data[sname] = value;
  this.fireEvent(sname, old, svalue);
  return undefined;
};

/**
 * When passed a key name, will remove that key from the storage
 * @param {string} name
 * @return {undefined}
 */
Storage.prototype.removeItem = function removeItem(name) {
  var old = this.getItem(name);
  this._deleteItem(name);
  this.fireEvent(name, old, null);
  return undefined;
};

/**
 * When invoked, will empty all keys out of the storage
 * @return {undefined}
 */
Storage.prototype.clear = function clear() {
  this.data = {};
  this.fireEvent(null, null, null);
  return undefined;
};

/**
 * When passed a number n, this method will return the name of the nth key in the storage
 * @param {number} index
 * @return {*}
 */
Storage.prototype.key = function key(index) {
  var n = ensureNumber(index);
  if (n == null || n < 0) return null;
  var keys = Object.keys(this.data);
  if (n < keys.length) return keys[n];
  return null;
};

/**
 * Because we are re-implementing the storage interface we must fire StorageEvent
 * ourselves, this function does just that.
 * @param {?string} key
 * @param {*} oldValue
 * @param {*} newValue
 * @see https://html.spec.whatwg.org/multipage/webstorage.html#send-a-storage-notification
 */
Storage.prototype.fireEvent = function fireEvent(key, oldValue, newValue) {
  var sevent = new StorageEvent('storage', {
    key: key,
    newValue: newValue,
    oldValue: oldValue,
    url: this.wombat.$wbwindow.WB_wombat_location.href
  });
  // storage is a read only property of StorageEvent
  // that must be on the fired instance of the event
  Object.defineProperty(sevent, 'storageArea', {
    value: this,
    writable: false,
    configurable: false
  });
  sevent._storageArea = this;
  this.wombat.storage_listeners.map(sevent);
};

/**
 * An override of the valueOf function that returns wombat's Proxy for the
 * specific storage this class is for, either local or session storage.
 * @return {Proxy<Storage>}
 */
Storage.prototype.valueOf = function valueOf() {
  return this.wombat.$wbwindow[this.proxying];
};

// the length getter is on the prototype (__proto__ modern browsers)
Object.defineProperty(Storage.prototype, 'length', {
  enumerable: false,
  get: function length() {
    return Object.keys(this.data).length;
  }
});

addToStringTagToClass(Storage, 'Storage');
