export class PywbI18N {
  static #locale = ''; // private (can only be set here)
  static getLocale() { // get via public static method
    return PywbI18N.#locale;
  }
  static init = (locale, config) => {
    if (PywbI18N.instance) {
      throw new Error('cannot instantiate PywbI18N twice');
    }
    PywbI18N.#locale = locale;
    PywbI18N.instance = new PywbI18N(config);
  }

  // PywbI18N expects from the i18n string source to receive months SHORT and LONG names in the config like this:
  // config.jan_short, config.jan_long, ...., config.<mmm>_short, config.<mmm>_long
  static monthIdPrefix = {1:"jan", 2:"feb",3:"mar",4:"apr",5:"may",6:"jun",7:"jul",8:"aug",9:"sep",10:"oct",11:"nov",12:"dec"};

  /**
   *
   * @type {PywbI18N|null}
   */
  static instance = null;

  constructor(config) {
    this.config = {...config}; // make a copy of config
  }

  // can get long (default) or short month string
  getMonth(id, type='long') {
    return decodeURIComponent(this.config[PywbI18N.monthIdPrefix[id]+'_'+type]);
  }
  // can get long (default) or short day string or intial
  // PywbI18N expects to receive day's initials like:
  // config.mon_short, config.tue_long, ...., config.<mmm>_short, config.<mmm>_long
  getWeekDay(id, type='long') {
    return decodeURIComponent(this.config[id+'_'+type])
  }
  getWeekDays(type='long') {
    return ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'].map(d => this.getWeekDay(d, type));
  }
  getText(id, embeddedVariableStrings=null) {
    const translated = decodeURIComponent(this.config[id] || id);
    if (embeddedVariableStrings && id.indexOf('{') >= 0 && id.indexOf('}') >= 0 ) {
      return translated.replace(/{(\w+)}/g, (match, stringId) => embeddedVariableStrings[stringId]);
    }
    return translated
  }
  _(id, embeddedVariableStrings=null) {
    return this.getText(id, embeddedVariableStrings);
  }
}
