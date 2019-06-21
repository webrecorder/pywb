import get from 'lodash-es/get';

/**
 * @typedef {Object} TestOverwatchInit
 * @property {HTMLIFrameElement} sandbox
 * @property {Object} [domStructure]
 * @property {boolean} [direct]
 */

window.TestOverwatch = class TestOverwatch {
  /**
   * @param {TestOverwatchInit} init
   */
  constructor({ sandbox, domStructure, direct }) {
    /**
     * @type {{document: Document, window: Window}}
     */
    this.ownContextWinDoc = { window, document };
    this.wbMessages = { load: false };
    this.domStructure = domStructure;
    this.direct = direct;

    /**
     * @type {HTMLIFrameElement}
     */
    this.sandbox = sandbox;
    if (!this.direct) {
      window.addEventListener(
        'message',
        event => {
          if (event.data) {
            const { data } = event;
            switch (data.wb_type) {
              case 'load':
                this.wbMessages.load =
                  this.wbMessages.load || data.readyState === 'complete';
                this.domStructure.load.url.data = data.url;
                this.domStructure.load.title.data = data.title;
                this.domStructure.load.readyState.data = data.readyState;
                break;
              case 'replace-url':
                this.wbMessages['replace-url'] = data;
                this.domStructure.replaceURL.url.data = data.url;
                this.domStructure.replaceURL.title.data = data.title;
                break;
              case 'title':
                this.wbMessages.title = data.title;
                this.domStructure.titleMsg.data = data.title;
                break;
              case 'hashchange':
                this.domStructure.hashchange.data = data.title;
                this.wbMessages.hashchange = data.hash;
                break;
              case 'cookie':
                this.domStructure.cookie.domain = data.domain;
                this.domStructure.cookie.cookie = data.cookie;
                this.wbMessages.cookie = data;
                break;
              default:
                this.domStructure.unknown.data = JSON.stringify(data);
                break;
            }
          }
        },
        false
      );
    }
  }

  /**
   * This function initializes the wombat in the sandbox and ads a single
   * additional property to the sandbox's window WombatTestUtil, an object that provides
   * any functionality required for tests. This is done in order to ensure testing
   * environment purity.
   */
  initSandbox() {
    if (this.domStructure) {
      this.domStructure.reset();
    }
    this.wbMessages = { load: false };
    this.sandbox.contentWindow._WBWombatInit(this.sandbox.contentWindow.wbinfo);
    this.sandbox.contentWindow.WombatTestUtil = {
      didWombatSendTheLoadMsg: () => this.wbMessages.load,
      wombatSentTitleUpdate: () => this.wbMessages.title,
      wombatSentReplaceUrlMsg: () => this.wbMessages['replace-url'],
      createUntamperedWithElement: init => this.createElement(init),
      getElementPropertyAsIs: (elem, prop) =>
        this.getElementPropertyAsIs(elem, prop),
      getElementNSPropertyAsIs: (elem, ns, prop) =>
        this.getElementNSPropertyAsIs(elem, ns, prop),
      getOriginalWinDomViaPath: objectPath =>
        this.getOriginalWinDomViaPath(objectPath),
      getViaPath: (obj, objectPath) => get(obj, objectPath),
      getOriginalPropertyDescriptorFor: (elem, prop) =>
        this.ownContextWinDoc.window.Reflect.getOwnPropertyDescriptor(
          elem,
          prop
        ),
      getStylePropertyAsIs: (elem, prop) =>
        this.getStylePropertyAsIs(elem, prop),
      getCSSPropertyAsIs: (elem, prop) => this.getCSSPropertyAsIs(elem, prop)
    };
  }

  maybeInitSandbox() {
    if (this.sandbox.contentWindow.WB_wombat_location != null) return;
    this.initSandbox();
  }

  /**
   * Creates a DOM element(s) based on the supplied creation options.
   * @param {Object} init - Options for new element creation
   * @return {HTMLElement|Node} - The newly created element
   */
  createElement(init) {
    if (typeof init === 'string') {
      return this.ownContextWinDoc.document.createElement(init);
    }
    if (init.tag === 'textNode') {
      var tn = this.ownContextWinDoc.document.createTextNode(init.value || '');
      if (init.ref) init.ref(tn);
      return tn;
    }
    var elem = this.ownContextWinDoc.document.createElement(init.tag);
    if (init.id) elem.id = init.id;
    if (init.className) elem.className = init.className;
    if (init.style) elem.style = init.style;
    if (init.innerText) elem.innerText = init.innerText;
    if (init.innerHTML) elem.innerHTML = init.innerHTML;
    if (init.attributes) {
      var atts = init.attributes;
      for (var attributeName in atts) {
        elem.setAttribute(attributeName, atts[attributeName]);
      }
    }
    if (init.dataset) {
      var dataset = init.dataset;
      for (var dataName in dataset) {
        elem.dataset[dataName] = dataset[dataName];
      }
    }
    if (init.events) {
      var events = init.events;
      for (var eventName in events) {
        elem.addEventListener(eventName, events[eventName]);
      }
    }
    if (init.child) {
      elem.appendChild(this.createElement(init.child));
    }
    if (init.children) {
      var kids = init.children;
      for (var i = 0; i < kids.length; i++) {
        elem.appendChild(this.createElement(kids[i]));
      }
    }
    if (init.ref) init.ref(elem);
    return elem;
  }

  /**
   * Returns the value of an elements property bypassing wombat rewriting
   * @param {Node} elem
   * @param {string} prop
   * @return {*}
   */
  getElementPropertyAsIs(elem, prop) {
    return this.ownContextWinDoc.window.Element.prototype.getAttribute.call(
      elem,
      prop
    );
  }

  getElementNSPropertyAsIs(elem, ns, prop) {
    return this.ownContextWinDoc.window.Element.prototype.getAttributeNS.call(
      elem,
      ns,
      prop
    );
  }

  getStylePropertyAsIs(elem, prop) {
    var getter = this.ownContextWinDoc.window.CSSStyleDeclaration.prototype.__lookupGetter__(
      prop
    );
    return getter.call(elem, prop);
  }

  getCSSPropertyAsIs(elem, prop) {
    return this.ownContextWinDoc.window.CSSStyleDeclaration.prototype.getPropertyValue.call(
      elem,
      prop
    );
  }

  getOriginalWinDomViaPath(objectPath) {
    return get(this.ownContextWinDoc, objectPath);
  }
};
