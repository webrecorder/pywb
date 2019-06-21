/**
 * Ensures the supplied argument is a number or if it is not (can not be coerced to a number)
 * this function returns null.
 * @param {*} maybeNumber
 * @return {?number}
 */
export function ensureNumber(maybeNumber) {
  try {
    switch (typeof maybeNumber) {
      case 'number':
      case 'bigint':
        return maybeNumber;
    }
    var converted = Number(maybeNumber);
    return !isNaN(converted) ? converted : null;
  } catch (e) {}
  return null;
}

/**
 * Sets the supplied object's toStringTag IFF
 * self.Symbol && self.Symbol.toStringTag are defined
 * @param {Object} clazz
 * @param {string} tag
 */
export function addToStringTagToClass(clazz, tag) {
  if (
    typeof self.Symbol !== 'undefined' &&
    typeof self.Symbol.toStringTag !== 'undefined'
  ) {
    Object.defineProperty(clazz.prototype, self.Symbol.toStringTag, {
      value: tag,
      enumerable: false
    });
  }
}

/**
 * Binds every function this, except the constructor, of the supplied object
 * to the instance of the supplied object
 * @param {Object} clazz
 */
export function autobind(clazz) {
  var proto = clazz.__proto__ || clazz.constructor.prototype || clazz.prototype;
  var clazzProps = Object.getOwnPropertyNames(proto);
  var len = clazzProps.length;
  var prop;
  var propValue;
  for (var i = 0; i < len; i++) {
    prop = clazzProps[i];
    propValue = clazz[prop];
    if (prop !== 'constructor' && typeof propValue === 'function') {
      clazz[prop] = propValue.bind(clazz);
    }
  }
}

/**
 * Because we overriding specific interfaces (e.g. Storage) that do not expose
 * an constructor only an interface object with our own we must have a way
 * to indicate to our overrides when it is proper to throw exceptions
 * @type {{yes: boolean}}
 */
export var ThrowExceptions = { yes: false };
