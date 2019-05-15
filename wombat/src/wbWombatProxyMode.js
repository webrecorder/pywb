import WombatLite from './wombatLite';

window._WBWombat = WombatLite;
window._WBWombatInit = function(wbinfo) {
  if (!this._wb_wombat || !this._wb_wombat.actual) {
    var wombat = new WombatLite(this, wbinfo);
    wombat.actual = true;
    this._wb_wombat = wombat.wombatInit();
    this._wb_wombat.actual = true;
  } else if (!this._wb_wombat) {
    console.warn('_wb_wombat missing!');
  }
};
