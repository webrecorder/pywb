import Wombat from './wombat';

window._WBWombat = Wombat;
window._WBWombatInit = function(wbinfo) {
  if (!this._wb_wombat || !this._wb_wombat.actual) {
    var wombat = new Wombat(this, wbinfo);
    wombat.actual = true;
    this._wb_wombat = wombat.wombatInit();
    this._wb_wombat.actual = true;
  } else if (!this._wb_wombat) {
    console.warn('_wb_wombat missing!');
  }
};
