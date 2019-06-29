exports.TestedPropertyDescriptorUpdates = [
  {
    docOrWin: 'document',
    props: ['title', 'domain', 'cookie'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    docOrWin: 'document',
    props: ['origin', 'referrer'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    docOrWin: 'window',
    props: ['origin', 'localStorage', 'sessionStorage'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    },
    // original setter remains
    skipSet: ['origin']
  },
  {
    docOrWin: 'window',
    props: ['onmessage', 'onstorage'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.CSSStyleSheet.prototype',
    props: ['href'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.Document.prototype',
    props: ['URL', 'documentURI'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.Node.prototype',
    props: ['baseURI', 'ownerDocument'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.Attr.prototype',
    props: ['nodeValue', 'value'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    },
    skipSet: ['value']
  },
  {
    objPath: 'window.Element.prototype',
    props: ['innerHTML', 'outerHTML'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLIFrameElement.prototype',
    props: ['srcdoc'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLStyleElement.prototype',
    props: ['textContent'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLLinkElement.prototype',
    props: ['href'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLImageElement.prototype',
    props: ['src', 'srcset'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLIFrameElement.prototype',
    props: ['src'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLScriptElement.prototype',
    props: ['src'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLVideoElement.prototype',
    props: ['src', 'poster'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLAudioElement.prototype',
    props: ['src', 'poster'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLSourceElement.prototype',
    props: ['src', 'srcset'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLInputElement.prototype',
    props: ['src'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLEmbedElement.prototype',
    props: ['src'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLObjectElement.prototype',
    props: ['data'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLBaseElement.prototype',
    props: ['href'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLMetaElement.prototype',
    props: ['content'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLFormElement.prototype',
    props: ['action'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLHtmlElement.prototype',
    props: ['parentNode'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.HTMLFrameElement.prototype',
    props: ['src'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLQuoteElement.prototype',
    props: ['cite'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLModElement.prototype',
    props: ['cite'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLAreaElement.prototype',
    props: [
      'href',
      'hash',
      'pathname',
      'host',
      'hostname',
      'protocol',
      'origin',
      'search',
      'port'
    ],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.HTMLAnchorElement.prototype',
    props: [
      'href',
      'hash',
      'pathname',
      'host',
      'hostname',
      'protocol',
      'origin',
      'search',
      'port'
    ],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.Text.prototype',
    props: ['wholeText'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.Text.prototype',
    props: ['data'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: `window.CSSStyleDeclaration.prototype`,
    props: [
      'cssText',
      'background',
      'backgroundImage',
      'cursor',
      'listStyle',
      'listStyleImage',
      'border',
      'borderImage',
      'borderImageSource',
      'maskImage'
    ],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    },
    skipGet: ['cssText']
  },
  {
    objPath: 'window.CSSRule.prototype',
    props: ['cssText'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    },
    skipGet: ['cssText']
  },
  {
    objPath: 'window.Object.prototype',
    props: ['WB_wombat_location', 'WB_wombat_top', '__WB_pmw'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function',
      set: 'function'
    }
  },
  {
    objPath: 'window.MessageEvent.prototype',
    props: [
      'target',
      'srcElement',
      'currentTarget',
      'eventPhase',
      'path',
      'source'
    ],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.StorageEvent.prototype',
    props: ['storageArea'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.MouseEvent.prototype',
    props: ['view'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.Event.prototype',
    props: ['target'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPath: 'window.XMLHttpRequest.prototype',
    props: ['responseURL'],
    expectedInterface: {
      configurable: 'boolean',
      enumerable: 'boolean',
      get: 'function'
    }
  },
  {
    objPaths: ['window.MouseEvent.prototype', 'window.FontFace.prototype'],
    props: ['constructor'],
    expectedInterface: {
      value: 'function'
    }
  }
];

const maybeInitUIEvents = [
  'window.UIEvent',
  'window.MouseEvent',
  'window.TouchEvent',
  'window.FocusEvent',
  'window.KeyboardEvent',
  'window.WheelEvent',
  'window.InputEvent',
  'window.CompositionEvent'
];

exports.TestFunctionChanges = [
  {
    constructors: [
      'window.Date',
      'window.Request',
      'window.Audio',
      'window.Worker',
      'window.SharedWorker',
      'window.FontFace'
    ].concat(maybeInitUIEvents)
  },
  {
    objPath: 'window.history',
    fns: ['replaceState', 'pushState'],
    origs: ['_orig_replaceState', '_orig_pushState']
  },
  {
    fnPath: 'window.postMessage',
    oPath: 'window.__orig_postMessage'
  },
  {
    objPath: 'window.Window.prototype',
    fns: ['postMessage']
  },
  {
    objPath: 'window.Document.prototype',
    fns: [
      'write',
      'writeln',
      'open',
      'createElementNS',
      'evaluate',
      'createTreeWalker'
    ]
  },
  {
    objPath: 'window.Node.prototype',
    fns: [
      'compareDocumentPosition',
      'contains',
      'replaceChild',
      'appendChild',
      'insertBefore'
    ]
  },
  {
    objPath: 'window.XMLHttpRequest.prototype',
    fns: ['open']
  },
  {
    objPath: 'window.navigator',
    fns: ['sendBeacon', 'registerProtocolHandler']
  },
  {
    objPath: 'window.ServiceWorkerContainer.prototype',
    fns: ['register']
  },
  {
    objPath: 'window.navigator.serviceWorker',
    fns: ['register']
  },
  {
    objPath: 'window',
    fns: ['fetch', 'setInterval', 'setTimeout', 'getComputedStyle']
  },
  {
    objPath: 'window.Math',
    fns: ['random']
  },
  {
    objPath: 'window.crypto',
    fns: ['getRandomValues']
  },
  {
    objPath: 'window.Notification',
    fns: ['requestPermission']
  },
  {
    objPath: 'window.Crypto.prototype',
    fns: ['getRandomValues']
  },
  {
    objPath: 'window.Date',
    fns: ['now']
  },
  {
    objPath: 'window.Element.prototype',
    fns: [
      'getAttribute',
      'setAttribute',
      'insertAdjacentElement',
      'insertAdjacentHTML'
    ]
  },
  {
    objPath: 'window.SVGImageElement.prototype',
    fns: ['getAttribute', 'getAttributeNS', 'setAttribute', 'setAttributeNS']
  },
  {
    objPath: 'window.MutationObserver.prototype',
    fns: ['observe']
  },
  {
    objPath: 'window.Function.prototype',
    fns: ['apply']
  },
  {
    objPath: 'window.CSSStyleSheet.prototype',
    fns: ['insertRule']
  },
  {
    objPath: `window.CSSStyleDeclaration.prototype`,
    fns: ['setProperty']
  },
  {
    objPath: 'window.Text.prototype',
    fns: ['appendData', 'insertData', 'replaceData']
  },
  {
    objPath: 'window.XSLTProcessor.prototype',
    fns: ['transformToFragment']
  },
  {
    objPath: 'document',
    fns: [
      'write',
      'writeln',
      'open',
      'createElementNS',
      'evaluate',
      'createTreeWalker'
    ]
  },
  {
    objPath: `window.EventTarget.prototype`,
    fns: ['addEventListener', 'removeEventListener']
  },
  {
    objPath: 'window.navigator.geolocation',
    fns: ['getCurrentPosition', 'watchPosition']
  },
  {
    objPath: 'window.Worklet.prototype',
    fns: ['addModule']
  },
  {
    objPath: 'window.StylePropertyMap.prototype',
    fns: ['set', 'append']
  },
  { objPath: 'window.UIEvent.prototype', fns: ['initUIEvent'] },
  { objPath: 'window.MouseEvent.prototype', fns: ['initMouseEvent'] },
  { objPath: 'window.KeyboardEvent.prototype', fns: ['initKeyboardEvent'] },
  {
    objPath: 'window.CompositionEvent.prototype',
    fns: ['initCompositionEvent']
  },
  {
    objPath: 'window.Date',
    persisted: ['UTC', 'parse']
  }
];

exports.URLParts = [
  'href',
  'hash',
  'pathname',
  'host',
  'hostname',
  'protocol',
  'origin',
  'search',
  'port'
];
const WB_PREFIX = `http://localhost:3030/live/20180803160549`;
exports.WB_PREFIX = WB_PREFIX;

exports.mpURL = url => `${WB_PREFIX}mp_/${url}`;

exports.fullHTML = ({ prefix, onlyBody, onlyHead, onlyHTML } = {}) => {
  const cssPrefix = prefix != null ? `${prefix}cs_/` : '';
  const jsPrefix = prefix != null ? `${prefix}js_/` : '';
  const body = `<body><script id="theScript" src="${jsPrefix}http://javaScript.com/script.js"></script></body>`;
  if (onlyBody) return body;
  const headString = `<head><link id="theLink" rel="stylesheet" href="${cssPrefix}http://cssHeaven.com/angelic.css"></head>`;
  let topMatter = `<!doctype html><html>${headString}${body}`;
  let bottomMatter = `</html>`;
  if (onlyHTML) {
    topMatter = `<html>${headString}${body}`;
    bottomMatter = `</html>`;
  } else if (onlyHead) {
    topMatter = headString;
    bottomMatter = '';
  }
  return `${topMatter}${bottomMatter}`;
};

exports.TextNodeTest = {
  fnTests: ['appendData', 'insertData', 'replaceData'],
  theStyle: '.hi { background-image: url(https://funky/png.png); }',
  theStyleRw: `.hi { background-image: url(${WB_PREFIX}mp_/https://funky/png.png); }`,
  evaluationFN(fn, theStyle, theStyleRw, inStyle) {
    const tn = document.createTextNode('');
    const tnParent = document.createElement(inStyle ? 'style' : 'p');
    tnParent.appendChild(tn);
    if (fn === 'insertData') {
      tn[fn](0, theStyle);
    } else if (fn === 'replaceData') {
      tn[fn](0, 0, theStyle);
    } else {
      tn[fn](theStyle);
    }
    const result = tnParent.innerText === (inStyle ? theStyleRw : theStyle);
    tnParent.remove();
    return result;
  }
};

exports.HTMLAssign = {
  innerOuterHTML: {
    tests: [
      {
        which: 'innerHTML',
        unrw: '<a href="http://example.com">hi</a>',
        rw: `<a href="${WB_PREFIX}mp_/http://example.com">hi</a>`
      },
      {
        which: 'outerHTML',
        unrw: '<div id="oHTML"><a href="http://example.com">hi</a></div>',
        rw: `<div id="oHTML"><a href="${WB_PREFIX}mp_/http://example.com">hi</a></div>`
      },
      {
        which: 'ShadowRoot.innerHTML',
        unrw: '<a href="http://example.com">hi</a>',
        rw: `<a href="${WB_PREFIX}mp_/http://example.com">hi</a>`
      }
    ],
    assignmentFN(which, unrw, rw) {
      const div = document.createElement('div');
      let results;
      document.body.appendChild(div);
      switch (which) {
        case 'innerHTML':
          div.innerHTML = unrw;
          div._no_rewrite = true;
          results = div.innerHTML === rw;
          break;
        case 'ShadowRoot.innerHTML':
          const shadowRoot = div.attachShadow({ mode: 'open' });
          shadowRoot.innerHTML = unrw;
          shadowRoot._no_rewrite = true;
          results = shadowRoot.innerHTML === rw;
          break;
        default:
          div.outerHTML = unrw;
          const elem = document.getElementById('oHTML');
          elem._no_rewrite = true;
          results = elem.outerHTML === rw;
          break;
      }
      while (document.body.firstChild) {
        document.body.removeChild(document.body.firstChild);
      }
      return results;
    },
    retrieval(which, unrw, rw) {
      const div = document.createElement('div');
      let results;
      document.body.appendChild(div);
      switch (which) {
        case 'innerHTML':
          div.innerHTML = unrw;
          results = div.innerHTML;
          break;
        case 'ShadowRoot.innerHTML':
          const shadowRoot = div.attachShadow({ mode: 'open' });
          shadowRoot.innerHTML = unrw;
          results = shadowRoot.innerHTML;
          break;
        default:
          div.outerHTML = unrw;
          results = document.getElementById('oHTML').outerHTML;
          break;
      }
      while (document.body.firstChild) {
        document.body.removeChild(document.body.firstChild);
      }
      return results;
    },
    assignmentToRetrieval(which, unrw, rw) {
      const div = document.createElement('div');
      const div2 = document.createElement('div');
      let results;
      document.body.appendChild(div);
      document.body.appendChild(div2);
      switch (which) {
        case 'innerHTML':
          div.innerHTML = unrw;
          div2.innerHTML = div.innerHTML;
          results = div2.innerHTML === unrw;
          break;
        case 'ShadowRoot.innerHTML':
          const shadowRoot = div.attachShadow({ mode: 'open' });
          shadowRoot.innerHTML = unrw;
          div2.innerHTML = shadowRoot.innerHTML;
          results = div2.innerHTML === unrw;
          break;
        default:
          div.outerHTML = unrw;
          div2.outerHTML = document.getElementById('oHTML').outerHTML;
          results = document.getElementById('oHTML').outerHTML === unrw;
          break;
      }
      while (document.body.firstChild) {
        document.body.removeChild(document.body.firstChild);
      }
      return results;
    }
  }
};

exports.LinkAsTypes = {
  script: 'js_',
  worker: 'js_',
  style: 'cs_',
  image: 'im_',
  document: 'if_',
  fetch: 'mp_',
  font: 'oe_',
  audio: 'oe_',
  video: 'oe_',
  embed: 'oe_',
  object: 'oe_',
  track: 'oe_'
};

exports.TagToMod = {
  elements: {
    a: { href: 'mp_' },
    area: { href: 'mp_' },
    audio: { src: 'oe_', poster: 'im_' },
    base: { href: 'mp_' },
    embed: { src: 'oe_' },
    form: { action: 'mp_' },
    frame: { src: 'fr_' },
    iframe: { src: 'if_' },
    img: { src: 'im_' },
    input: { src: 'oe_' },
    ins: { cite: 'mp_' },
    meta: { content: 'mp_' },
    object: { data: 'oe_', codebase: 'oe_' },
    q: { cite: 'mp_' },
    // covers both html and svg script element,
    script: { src: 'js_' },
    source: { src: 'oe_' },
    track: { src: 'oe_' },
    video: { src: 'oe_', poster: 'im_' }
  },
  testFNDirect(tag, attr, unRW) {
    const elem = document.createElement(tag);
    elem[attr] = unRW;
    return WombatTestUtil.getElementPropertyAsIs(elem, attr);
  },
  testFNSetAttr(tag, attr, unRW) {
    const elem = document.createElement(tag);
    elem.setAttribute(attr, unRW);
    return WombatTestUtil.getElementPropertyAsIs(elem, attr);
  }
};

exports.ElementGetSetAttribute = [
  {
    elem: 'link',
    prop: 'href',
    unrw: 'http://example.com/whatever'
  },
  {
    elem: 'img',
    props: ['src', 'srcset'],
    unrws: ['http://example.com/whatever', 'http://example.com/whatever']
  },
  {
    elem: 'iframe',
    props: ['src'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'script',
    props: ['src'],
    unrws: ['http://example.com/whatever.js']
  },
  {
    elem: 'video',
    props: ['src', 'poster'],
    unrws: ['http://example.com/whatever', 'http://example.com/whatever']
  },
  {
    elem: 'audio',
    props: ['src', 'poster'],
    unrws: ['http://example.com/whatever', 'http://example.com/whatever']
  },
  {
    elem: 'source',
    props: ['src', 'srcset'],
    unrws: ['http://example.com/whatever', 'http://example.com/whatever']
  },
  {
    elem: 'input',
    props: ['src'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'embed',
    props: ['src'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'base',
    props: ['href'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'meta',
    props: ['content'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'form',
    props: ['action'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'frame',
    props: ['src'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'track',
    props: ['src'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'area',
    props: ['href'],
    unrws: ['http://example.com/whatever']
  },
  {
    elem: 'a',
    props: ['href'],
    unrws: ['http://example.com/whatever']
  }
];

const cssAttrImageUnrw = 'url("https://example.com/ping.png")';
const CSSAttrsToPropName = [
  { attr: 'background', propName: 'background', unrw: cssAttrImageUnrw },
  {
    attr: 'backgroundImage',
    propName: 'background-image',
    unrw: cssAttrImageUnrw
  },
  { attr: 'border', propName: 'border', unrw: cssAttrImageUnrw },
  {
    attr: 'borderImage',
    propName: 'border-image',
    unrw: `${cssAttrImageUnrw} 100% / 1 / 0 stretch`
  },
  {
    attr: 'borderImageSource',
    propName: 'border-image-source',
    unrw: cssAttrImageUnrw
  },
  { attr: 'cursor', propName: 'cursor', unrw: `${cssAttrImageUnrw}, pointer` },
  { attr: 'listStyle', propName: 'list-style', unrw: cssAttrImageUnrw },
  {
    attr: 'listStyleImage',
    propName: 'list-style-image',
    unrw: cssAttrImageUnrw
  },
  {
    attr: 'maskImage',
    propName: 'mask-image',
    unrw: `image(${cssAttrImageUnrw})`
  }
];

const CSSRules = [
  {
    name: '@import "url"',
    unrw: '@import "http://cssHeaven.com/angelic.css"'
  },
  {
    name: '@import url("url")',
    unrw: '@import url("http://cssHeaven.com/angelic.css")'
  },
  {
    name: '@import url(url)',
    unrw: '@import url(http://cssHeaven.com/angelic.css)'
  },
  {
    name: '@font-face',
    unrw: `@font-face {
 font-family: 'TheDude';
 src: url('https://theDude.com/Abides.woff2') format('woff2');
}`
  }
].concat(
  CSSAttrsToPropName.map(aTest =>
    Object.assign({ name: aTest.propName }, aTest, {
      unrw: `.clzz { ${aTest.propName}: ${aTest.unrw} }`
    })
  )
);

const CSSOmSkipped = new Set(['border', 'maskImage']);

exports.CSS = {
  styleAttrs: {
    attrs: CSSAttrsToPropName,
    unrw: 'https://example.com/ping.png',
    testFNAttr(test) {
      const div = document.createElement('div');
      div.style[test.attr] = test.unrw;
      return div.style[test.attr];
    },
    testFNPropName(test) {
      const div = document.createElement('div');
      div.style[test.propName] = test.unrw;
      return div.style[test.propName];
    },
    testFNSetProp(prop, unrw) {
      const div = document.createElement('div');
      div.style.setProperty(prop, unrw);
      return div.style[prop];
    },
    testFNCssText(aTest) {
      const div = document.createElement('div');
      div.style.cssText = `${aTest.propName}: ${aTest.unrw}`;
      return div.style.cssText;
    }
  },
  styleTextContent: {
    tests: CSSRules,
    testFN(unrw) {
      const style = document.createElement('style');
      style.textContent = unrw;
      return style.textContent;
    }
  },
  StyleSheetInsertRule: {
    tests: CSSRules,
    testFN(unrw) {
      const style = document.createElement('style');
      style.textContent = '.dummy {}';
      document.body.appendChild(style);
      style.sheet.insertRule(unrw, 0);
      const cssText = style.sheet.rules[0].cssText;
      style.remove();
      return cssText;
    }
  },
  CSSRuleCSSText: {
    tests: CSSRules,
    testFN(unrw) {
      const style = document.createElement('style');
      style.textContent = '.dummy {}';
      document.body.appendChild(style);
      style.sheet.rules[0].cssText = unrw;
      const cssText = style.sheet.rules[0].cssText;
      style.remove();
      return cssText;
    }
  },
  StylePropertyMap: {
    noAppend: new Set([
      'background',
      'cursor',
      'listStyle',
      'listStyleImage',
      'borderImage',
      'borderImageSource'
    ]),
    tests: CSSAttrsToPropName.filter(it => !CSSOmSkipped.has(it.attr)),
    testFNSet(prop, unrw) {
      const div = document.createElement('div');
      div.attributeStyleMap.set(prop, unrw);
      return div.attributeStyleMap.get(prop).toString();
    },
    testFNAppend(prop, unrw) {
      const div = document.createElement('div');
      div.attributeStyleMap.append(prop, unrw);
      return div.attributeStyleMap.get(prop).toString();
    }
  },
  CSSKeywordValue: {
    tests: CSSAttrsToPropName,
    testFN(prop, unrw) {
      const cssValue = new CSSKeywordValue(prop, unrw);
      return cssValue.toString();
    }
  },
  CSSStyleValue: {
    tests: CSSAttrsToPropName,
    skipped: new Set(['border', 'maskImage']),
    testFNParse(prop, unrw) {
      const result = CSSStyleValue.parse(prop, unrw);
      return result.toString();
    },
    testFNParseAll(prop, unrw) {
      const result = CSSStyleValue.parseAll(prop, unrw);
      return result[0].toString();
    }
  }
};

exports.NativeFnTest = {
  testFN() {
    const funkyFunction = function() {};
    funkyFunction.toString = function() {
      throw new Error('blah');
    };
    return {
      native: wombat.isNativeFunction(blur),
      notNative: wombat.isNativeFunction(() => {}),
      funkyFn: wombat.isNativeFunction(funkyFunction),
      null: wombat.isNativeFunction(null),
      undefined: wombat.isNativeFunction(undefined),
      obj: wombat.isNativeFunction({})
    };
  },
  expectedValue: {
    native: true,
    notNative: false,
    funkyFn: false,
    null: false,
    undefined: false,
    obj: false
  }
};

exports.SaveSrcSetDataSrcSet = {
  values: [
    { name: 'IMG', tagName: 'IMG', expected: true },
    { name: 'VIDEO', tagName: 'VIDEO', expected: true },
    { name: 'AUDIO', tagName: 'AUDIO', expected: true },
    {
      name: 'SOURCE with no parent',
      tagName: 'SOURCE',
      expected: false
    },
    {
      name: 'SOURCE with PICTURE parent',
      tagName: 'SOURCE',
      parentElement: 'PICTURE',
      expected: true
    },
    {
      name: 'SOURCE with VIDEO parent',
      tagName: 'SOURCE',
      parentElement: 'VIDEO',
      expected: true
    },
    {
      name: 'SOURCE with AUDIO parent',
      tagName: 'SOURCE',
      parentElement: 'AUDIO',
      expected: true
    },
    {
      name: 'IFRAME',
      tagName: 'IFRAME',
      expected: false
    },
    {
      name: 'SOURCE with DIV parent',
      tagName: 'SOURCE',
      parentElement: 'DIV',
      expected: false
    }
  ],
  testFnSS(tagName, parentElementTagName) {
    const testValue = { tagName };
    if (parentElementTagName) {
      testValue.parentElement = {
        tagName: parentElementTagName
      };
    }
    return wombat.isSavedSrcSrcset(testValue);
  },
  testFnDSS(tagName, parentElementTagName) {
    const testValue = { tagName };
    if (parentElementTagName) {
      testValue.parentElement = {
        tagName: parentElementTagName
      };
    }
    return {
      without: wombat.isSavedDataSrcSrcset(testValue),
      with: wombat.isSavedSrcSrcset(
        Object.assign(
          {
            dataset: { srcset: true }
          },
          testValue
        )
      )
    };
  }
};
