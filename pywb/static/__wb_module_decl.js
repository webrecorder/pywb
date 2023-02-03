var wrapObj = function(name) {return (self._wb_wombat && self._wb_wombat.local_init && self._wb_wombat.local_init(name)) || self[name]; };
if (!self.__WB_pmw) { self.__WB_pmw = function(obj) { this.__WB_source = obj; return this; } }
const window = wrapObj("window");
const document = wrapObj("document");
const location = wrapObj("location");
const top = wrapObj("top");
const parent = wrapObj("parent");
const frames = wrapObj("frames");
const opener = wrapObj("opener");
const __self = wrapObj("self");
const __globalThis = wrapObj("globalThis");
export { window, document, location, top, parent, frames, opener, __self as self, __globalThis as globalThis };
