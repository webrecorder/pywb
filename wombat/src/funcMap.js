/**
 * A class that manages event listeners for the override applied to
 * EventTarget.[addEventListener, removeEventListener]
 */
export default function FuncMap() {
  /**
   * @type {Array<Function[]>}
   * @private
   */
  this._map = [];
}

/**
 * Adds a mapping of original listener -> wrapped original listener
 * @param {Function} fnKey - The original listener function
 * @param {Function} fnValue - The wrapped original listener function
 */
FuncMap.prototype.set = function(fnKey, fnValue) {
  this._map.push([fnKey, fnValue]);
};

/**
 * Returns the wrapped original listener that is mapped to the supplied function
 * if it exists in the FuncMap's mapping
 * @param {Function} fnKey - The original listener function
 * @return {?Function}
 */
FuncMap.prototype.get = function(fnKey) {
  for (var i = 0; i < this._map.length; i++) {
    if (this._map[i][0] === fnKey) {
      return this._map[i][1];
    }
  }
  return null;
};

/**
 * Returns the index of the wrapper for the supplied original function
 * if it exists in the FuncMap's mapping
 * @param {Function} fnKey - The original listener function
 * @return {number}
 */
FuncMap.prototype.find = function(fnKey) {
  for (var i = 0; i < this._map.length; i++) {
    if (this._map[i][0] === fnKey) {
      return i;
    }
  }
  return -1;
};

/**
 * Returns the wrapped original listener function for the supplied original
 * listener function. If the wrapped original listener does not exist in
 * FuncMap's mapping it is added.
 * @param {Function} func - The original listener function
 * @param {Function} initter - The a function that returns a wrapped version
 * of the original listener function
 * @return {?Function}
 */
FuncMap.prototype.add_or_get = function(func, initter) {
  var fnValue = this.get(func);
  if (!fnValue) {
    fnValue = initter();
    this.set(func, fnValue);
  }
  return fnValue;
};

/**
 * Removes the mapping of the original listener function to its wrapped counter part
 * @param {Function} func - The original listener function
 * @return {?Function}
 */
FuncMap.prototype.remove = function(func) {
  var idx = this.find(func);
  if (idx >= 0) {
    var fnMapping = this._map.splice(idx, 1);
    return fnMapping[0][1];
  }
  return null;
};

/**
 * Calls all wrapped listener functions contained in the FuncMap's mapping
 * with the supplied param
 * @param {*} param
 */
FuncMap.prototype.map = function(param) {
  for (var i = 0; i < this._map.length; i++) {
    this._map[i][1](param);
  }
};
