import test from 'ava';
import {
  ElementGetSetAttribute,
  HTMLAssign,
  LinkAsTypes,
  TextNodeTest,
  WB_PREFIX,
  TagToMod
} from './helpers/testedValues';
import { extractModifier, parsedURL } from './helpers/utils';
import TestHelper from './helpers/testHelper';

/**
 * @type {TestHelper}
 */
let helper = null;

test.before(async t => {
  helper = await TestHelper.init(t);
  await helper.initWombat();
});

test.beforeEach(async t => {
  t.context.sandbox = helper.sandbox();
  t.context.server = helper.server();
  t.context.testPage = helper.testPage();
});

test.afterEach.always(async t => {
  if (t.title.includes('SharedWorker')) {
    await helper.fullRefresh();
  } else {
    await helper.ensureSandbox();
  }
});

test.after.always(async t => {
  await helper.stop();
});

test('document.title: should send the "title" message to the top frame when document.title is changed', async t => {
  const { sandbox, testPage } = t.context;
  await sandbox.evaluate(() => (document.title = 'abc'));
  const result = await testPage.evaluate(
    () =>
      window.overwatch.wbMessages.title != null &&
      window.overwatch.wbMessages.title === 'abc'
  );
  t.true(
    result,
    'the "title" message was not sent to the top frame on document.title changes'
  );
});

test('document.write: should not perform rewriting when "write" is called with no arguments', async t => {
  const { sandbox, testPage } = t.context;
  await sandbox.evaluate(() => {
    document.write();
    document.close();
  });
  t.deepEqual(
    await sandbox.evaluate(() => ({
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    })),
    { doctype: false, html: '<html><head></head><body></body></html>' },
    'this use case failed'
  );
});

test('document.write: should perform rewriting when "write" is called with one argument', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(expectedURL => {
    document.write('<a id="it" href="http://example.com">hi</a>');
    document.close();

    const elem = document.getElementById('it');
    if (!elem) return false;
    elem._no_rewrite = true;
    return elem.href === expectedURL;
  }, `${WB_PREFIX}mp_/http://example.com`);
  t.true(
    result,
    'wombat is not rewriting elements when document.write is used'
  );
});

test('document.write: should perform rewriting when "write" is called with multiple arguments', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(expectedURL => {
    document.write(
      '<a id="it" href="http://example.com">hi</a>',
      '<a id="it2" href="http://example.com">hi</a>'
    );
    document.close();
    const results = {
      it: { exists: false, rewritten: false },
      it2: { exists: false, rewritten: false }
    };
    const it = document.getElementById('it');
    if (!it) return results;
    results.it.exists = true;
    it._no_rewrite = true;
    results.it.rewritten = it.href === expectedURL;
    const it2 = document.getElementById('it2');
    if (!it2) return results;
    results.it2.exists = true;
    it2._no_rewrite = true;
    results.it2.rewritten = it.href === expectedURL;
    return results;
  }, `${WB_PREFIX}mp_/http://example.com`);
  t.deepEqual(
    result,
    {
      it: { exists: true, rewritten: true },
      it2: { exists: true, rewritten: true }
    },
    'wombat is not rewriting elements when document.write is used with multiple values'
  );
});

test('document.write: should perform rewriting when "write" is called with a full string of HTML starting with <!doctype html>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<!doctype html><html><head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body></html>`;
  const expectedHTML = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.write(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: {
        exists: document.doctype != null,
        name: document.doctype.name
      },
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: {
        exists: true,
        name: 'html'
      },
      html: expectedHTML
    },
    'wombat is not rewriting elements when document.write is used with full strings of html with <!doctype html>'
  );
});

test('document.write: should perform rewriting when "write" is called with a full string of HTML starting with <html>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<html><head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"/></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body></html>`;
  const expectedRW = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.write(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    { doctype: false, html: expectedRW },
    'wombat is not rewriting elements when document.write is used with full strings of html with <html>'
  );
});

test('document.write: should perform rewriting when "write" is called with a full string of HTML starting with <head>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"/></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body>`;
  const expectedRW = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.write(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: false,
      html: expectedRW
    },
    'wombat is not rewriting elements when document.write is used with full strings of html with <head>'
  );
});

test('document.write: should perform rewriting when "write" is called with a full string of HTML starting with <body>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<body><script id="theScript" src="http://javaScript.com/script.js"></script></body>`;
  const expectedRW = `<html><head></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.write(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: false,
      html: expectedRW
    },
    'wombat is not rewriting elements when document.write is used with full strings of html with <body>'
  );
});

test('document.write: should perform rewriting when "write" is called with an arbitrary string of HTML', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<script id="theScript" src="http://javaScript.com/script.js"></script>`;
  const expectedRW = `<html><head><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></head></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.write(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: false,
      html: expectedRW
    },
    'wombat is not rewriting elements when document.write is used with full strings of html with <body>'
  );
});

test('document.writeln: should not perform rewriting when "writeln" is called with no arguments', async t => {
  const { sandbox, testPage } = t.context;
  await sandbox.evaluate(() => {
    document.writeln();
    document.close();
  });
  const result = await sandbox.evaluate(() => ({
    doctype: document.doctype != null,
    html: document.documentElement.outerHTML
  }));
  t.deepEqual(
    result,
    { doctype: false, html: '<html><head></head><body></body></html>' },
    'this use case failed'
  );
});

test('document.writeln: should perform rewriting when "writeln" is called with one argument', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(expectedURL => {
    document.writeln('<a id="it" href="http://example.com">hi</a>');
    document.close();
    const elem = document.getElementById('it');
    if (!elem) return false;
    elem._no_rewrite = true;
    return elem.href === expectedURL;
  }, `${WB_PREFIX}mp_/http://example.com`);
  t.true(
    result,
    'wombat is not rewriting elements when document.writeln is used'
  );
});

test('document.writeln: should perform rewriting when "writeln" is called with multiple arguments', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(expectedURL => {
    document.writeln(
      '<a id="it" href="http://example.com">hi</a>',
      '<a id="it2" href="http://example.com">hi</a>'
    );
    document.close();
    const results = {
      it: { exists: false, rewritten: false },
      it2: { exists: false, rewritten: false }
    };
    const it = document.getElementById('it');
    if (!it) return results;
    results.it.exists = true;
    it._no_rewrite = true;
    results.it.rewritten = it.href === expectedURL;
    const it2 = document.getElementById('it2');
    if (!it2) return results;
    results.it2.exists = true;
    it2._no_rewrite = true;
    results.it2.rewritten = it.href === expectedURL;
    return results;
  }, `${WB_PREFIX}mp_/http://example.com`);
  t.deepEqual(
    result,
    {
      it: { exists: true, rewritten: true },
      it2: { exists: true, rewritten: true }
    },
    'wombat is not rewriting elements when document.writeln is used with multiple values'
  );
});

test('document.writeln: should perform rewriting when "writeln" is called with a full string of HTML starting with <!doctype html>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<!doctype html><html><head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body></html>`;
  const expectedHTML = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.writeln(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: {
        exists: document.doctype != null,
        name: document.doctype.name
      },
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: {
        exists: true,
        name: 'html'
      },
      html: expectedHTML
    },
    'wombat is not rewriting elements when document.writeln is used with full strings of html with <!doctype html>'
  );
});

test('document.writeln: should perform rewriting when "writeln" is called with a full string of HTML starting with <html>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<html><head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"/></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body></html>`;
  const expectedRW = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.writeln(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    { doctype: false, html: expectedRW },
    'wombat is not rewriting elements when document.writeln is used with full strings of html with <html>'
  );
});

test('document.writeln: should perform rewriting when "writeln" is called with a full string of HTML starting with <head>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"/></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body>`;
  const expectedRW = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.writeln(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: false,
      html: expectedRW
    },
    'wombat is not rewriting elements when document.writeln is used with full strings of html with <head>'
  );
});

test('document.writeln: should perform rewriting when "writeln" is called with a full string of HTML starting with <body>', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<body><script id="theScript" src="http://javaScript.com/script.js"></script></body>`;
  const expectedRW = `<html><head></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.writeln(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: false,
      html: expectedRW
    },
    'wombat is not rewriting elements when document.writeln is used with full strings of html with <body>'
  );
});

test('document.writeln: should perform rewriting when "write" is called with an arbitrary string of HTML', async t => {
  const { sandbox, server } = t.context;
  const unRW = `<script id="theScript" src="http://javaScript.com/script.js"></script>`;
  const expectedRW = `<html><head><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></head></html>`;
  const result = await sandbox.evaluate(notRW => {
    document.writeln(notRW);
    document.close();
    document.documentElement._no_rewrite = true;
    return {
      doctype: document.doctype != null,
      html: document.documentElement.outerHTML
    };
  }, unRW);
  t.deepEqual(
    result,
    {
      doctype: false,
      html: expectedRW
    },
    'wombat is not rewriting elements when document.write is used with full strings of html with <body>'
  );
});

test(`document.URL: retrievals should be rewritten`, async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => document.URL === 'https://tests.wombat.io/'
  );
  t.true(result);
});

test(`document.documentURI: retrievals should be rewritten`, async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => document.documentURI === 'https://tests.wombat.io/'
  );
  t.true(result);
});

test(`document.baseURI: retrievals should be rewritten`, async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => document.baseURI === 'https://tests.wombat.io/'
  );
  t.true(result);
});

test(`HTMLStyleElement.textContent: assignments should be rewritten`, async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    (theStyle, theStyleRw) => {
      const style = document.createElement('style');
      style.textContent = theStyle;
      style._no_rewrite = true;
      return style.textContent === theStyleRw;
    },
    TextNodeTest.theStyle,
    TextNodeTest.theStyleRw
  );
  t.true(result);
});

test(`HTMLIframeElement.srcdoc: assignments should be rewritten`, async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const iframe = document.createElement('iframe');
    const unRW = `<html><head><link id="theLink" rel="stylesheet" href="https://cssHeaven.com/angelic.css"/></head><body><script id="theScript" src="http://javaScript.com/script.js"></script></body></html>`;
    const expectedRW = `<html><head><link id="theLink" rel="stylesheet" href="http://localhost:3030/live/20180803160549cs_/https://cssHeaven.com/angelic.css"></head><body><script id="theScript" src="http://localhost:3030/live/20180803160549js_/http://javaScript.com/script.js"></script></body></html>`;
    iframe.srcdoc = unRW;
    return (
      window.WombatTestUtil.getElementPropertyAsIs(iframe, 'srcdoc') ===
      expectedRW
    );
  });
  t.true(result);
});

test('Element.insertAdjacentElement: should rewrite elements', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    const a = window.WombatTestUtil.createUntamperedWithElement('a');
    a.href = 'http://example.com';
    a.id = 'aa';
    div.insertAdjacentElement('afterend', a);
    const results = window.WombatTestUtil.getElementPropertyAsIs(
      div.nextElementSibling,
      'href'
    );
    div.remove();
    return results.endsWith('mp_/http://example.com');
  });
  t.true(result);
});

test('Element.insertAdjacentHTML: should rewrite strings of html', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    div.insertAdjacentHTML(
      'afterend',
      '<a id="aa" href="http://example.com"></a>'
    );
    const results = window.WombatTestUtil.getElementPropertyAsIs(
      div.nextElementSibling,
      'href'
    );
    div.remove();
    return results.endsWith('mp_/http://example.com');
  });
  t.true(result);
});

for (const aTest of ElementGetSetAttribute) {
  if (aTest.elem === 'link') {
    for (const [as, mod] of Object.entries(LinkAsTypes)) {
      test(`<link rel="preload" as="${as}">: should rewrite the value set by setAttribute for the href attribute`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          (theElem, prop, asV, unrw, theMod) => {
            const elem = document.createElement(theElem);
            elem.rel = 'preload';
            elem.as = asV;
            elem.setAttribute(prop, unrw);
            const asis = window.WombatTestUtil.getElementPropertyAsIs(
              elem,
              prop
            );
            return {
              attr: elem.getAttribute(prop) === unrw,
              asis: asis !== unrw
            };
          },
          aTest.elem,
          aTest.prop,
          as,
          aTest.unrw,
          mod
        );
        t.deepEqual(result, { attr: true, asis: true });
      });

      test(`<link rel="preload" as="${as}">: should rewrite the value set by setAttribute for the href attribute using the correct modifier`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          (theElem, prop, asV, unrw, theMod) => {
            const elem = document.createElement(theElem);
            elem.rel = 'preload';
            elem.as = asV;
            elem.setAttribute(prop, unrw);
            return window.WombatTestUtil.getElementPropertyAsIs(elem, prop);
          },
          aTest.elem,
          aTest.prop,
          as,
          aTest.unrw,
          mod
        );
        t.true(
          result.includes(mod),
          `<link rel="preload" as="${as}"> was not rewritten using the "${mod}"`
        );
      });

      test(`<link rel="import" as="${as}">: should rewrite the value set by setAttribute for the href attribute`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          (theElem, prop, asV, unrw, theMod) => {
            const elem = document.createElement(theElem);
            elem.rel = 'import';
            elem.as = asV;
            elem.setAttribute(prop, unrw);
            const asis = window.WombatTestUtil.getElementPropertyAsIs(
              elem,
              prop
            );
            return {
              attr: elem.getAttribute(prop) === unrw,
              asis: asis !== unrw
            };
          },
          aTest.elem,
          aTest.prop,
          as,
          aTest.unrw,
          mod
        );
        t.deepEqual(result, { attr: true, asis: true });
      });

      test(`<link rel="import" as="${as}">: should rewrite the value set by setAttribute for the href attribute using the correct modifier`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          (theElem, prop, asV, unrw, theMod) => {
            const elem = document.createElement(theElem);
            elem.rel = 'import';
            elem.as = asV;
            elem.setAttribute(prop, unrw);
            return window.WombatTestUtil.getElementPropertyAsIs(elem, prop);
          },
          aTest.elem,
          aTest.prop,
          as,
          aTest.unrw,
          mod
        );
        t.true(
          result.includes(mod),
          `<link rel="import" as="${as}"> was not rewritten using the "${mod}"`
        );
      });

      test(`<link rel="preload" as="${as}">: should un-rewrite the value returned by getAttribute for the href attribute`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          (theElem, prop, asV, unrw) => {
            const elem = document.createElement(theElem);
            elem.rel = 'preload';
            elem.as = asV;
            elem.setAttribute(prop, unrw);
            return elem.getAttribute(prop) === unrw;
          },
          aTest.elem,
          aTest.prop,
          as,
          aTest.unrw
        );
        t.true(result);
      });

      test(`<link rel="import" as="${as}">: should un-rewrite the value returned by getAttribute for the href attribute `, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          (theElem, prop, asV, unrw) => {
            const elem = document.createElement(theElem);
            elem.rel = 'import';
            elem.as = asV;
            elem.setAttribute(prop, unrw);
            return elem.getAttribute(prop) === unrw;
          },
          aTest.elem,
          aTest.prop,
          as,
          aTest.unrw
        );
        t.true(result);
      });
    }

    test(`<link rel="stylesheet">: value for href set by setAttribute should be rewritten`, async t => {
      const { sandbox, server } = t.context;
      const result = await sandbox.evaluate(
        (theElem, prop, unrw) => {
          const elem = document.createElement(theElem);
          elem.rel = 'stylesheet';
          elem.setAttribute(prop, unrw);
          return (
            window.WombatTestUtil.getElementPropertyAsIs(elem, prop) !== unrw
          );
        },
        aTest.elem,
        aTest.prop,
        aTest.unrw
      );
      t.true(result);
    });

    test(`<link rel="stylesheet">: values returned by getAttribute for the href attribute should be un-rewritten`, async t => {
      const { sandbox, server } = t.context;
      const result = await sandbox.evaluate(
        (theElem, prop, unrw) => {
          const elem = document.createElement(theElem);
          elem.rel = 'stylesheet';
          elem.setAttribute(prop, unrw);
          return elem.getAttribute(prop) === unrw;
        },
        aTest.elem,
        aTest.prop,
        aTest.unrw
      );
      t.true(result);
    });
  } else {
    for (let i = 0; i < aTest.props.length; i++) {
      const prop = aTest.props[i];
      const unrw = aTest.unrws[i];
      test(`${
        aTest.elem
      }.${prop}: the value set using setAttribute should be rewritten`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(testFn, aTest.elem, prop, unrw);
        t.true(result);
        function testFn(theElem, prop, unrw) {
          const elem = document.createElement(theElem);
          elem.setAttribute(prop, unrw);
          return (
            window.WombatTestUtil.getElementPropertyAsIs(elem, prop) !== unrw
          );
        }
      });

      test(`${
        aTest.elem
      }.${prop}: the value retrieved by getAttribute should be un-rewritten`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(testFn, aTest.elem, prop, unrw);
        t.true(result);
        function testFn(theElem, prop, unrw) {
          const elem = document.createElement(theElem);
          elem.setAttribute(prop, unrw);
          return elem.getAttribute(prop) === unrw;
        }
      });
    }
  }
}

test('Node.ownerDocument: should return the document Proxy object when accessed', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => document.body.ownerDocument === document._WB_wombat_obj_proxy
  );
  t.true(result);
});

test('Node.appendChild: should rewrite a element with no children are supplied', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    const a = window.WombatTestUtil.createUntamperedWithElement('a');
    a.href = 'http://example.com';
    div.appendChild(a);
    return window.WombatTestUtil.getElementPropertyAsIs(a, 'href').endsWith(
      'mp_/http://example.com'
    );
  });
  t.true(result);
});

test('Node.appendChild: should rewrite a element with multiple children are supplied', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    const a1 = window.WombatTestUtil.createUntamperedWithElement('a');
    const a2 = window.WombatTestUtil.createUntamperedWithElement('a');
    const a3 = window.WombatTestUtil.createUntamperedWithElement('a');
    a1.href = 'http://example1.com';
    a2.href = 'http://example2.com';
    a3.href = 'http://example3.com';
    div.appendChild(a2);
    div.appendChild(a3);
    div.appendChild(a1);
    return {
      a1: window.WombatTestUtil.getElementPropertyAsIs(a1, 'href').endsWith(
        'mp_/http://example1.com'
      ),
      a2: window.WombatTestUtil.getElementPropertyAsIs(a2, 'href').endsWith(
        'mp_/http://example2.com'
      ),
      a3: window.WombatTestUtil.getElementPropertyAsIs(a3, 'href').endsWith(
        'mp_/http://example3.com'
      )
    };
  });
  t.deepEqual(result, { a1: true, a2: true, a3: true });
});

test('Node.insertBefore: should rewrite a element with no children are supplied', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    const a = window.WombatTestUtil.createUntamperedWithElement('a');
    a.href = 'http://example.com';
    document.body.insertBefore(a, div);
    const result = window.WombatTestUtil.getElementPropertyAsIs(
      a,
      'href'
    ).endsWith('mp_/http://example.com');
    div.remove();
    a.remove();
    return result;
  });
  t.true(result);
});

test('Node.insertBefore: should rewrite a element with multiple children are supplied', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    const div2 = document.createElement('div');
    document.body.appendChild(div);
    const a1 = window.WombatTestUtil.createUntamperedWithElement('a');
    const a2 = window.WombatTestUtil.createUntamperedWithElement('a');
    const a3 = window.WombatTestUtil.createUntamperedWithElement('a');
    a1.href = 'http://example1.com';
    a2.href = 'http://example2.com';
    a3.href = 'http://example3.com';
    div2.appendChild(a1);
    div2.appendChild(a2);
    div2.appendChild(a3);
    document.body.insertBefore(div2, div);
    const result = {
      a1: window.WombatTestUtil.getElementPropertyAsIs(a1, 'href').endsWith(
        'mp_/http://example1.com'
      ),
      a2: window.WombatTestUtil.getElementPropertyAsIs(a2, 'href').endsWith(
        'mp_/http://example2.com'
      ),
      a3: window.WombatTestUtil.getElementPropertyAsIs(a3, 'href').endsWith(
        'mp_/http://example3.com'
      )
    };
    div.remove();
    a1.remove();
    return result;
  });
  t.deepEqual(result, { a1: true, a2: true, a3: true });
});

test('Node.replaceChild: should rewrite a element with no children are supplied', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    document.body.appendChild(div);
    const a = window.WombatTestUtil.createUntamperedWithElement('a');
    a.href = 'http://example.com';
    document.body.replaceChild(a, div);
    const result = window.WombatTestUtil.getElementPropertyAsIs(
      a,
      'href'
    ).endsWith('mp_/http://example.com');
    a.remove();
    return result;
  });
  t.true(result);
});

test('Node.replaceChild: should rewrite a element with multiple children are supplied', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const div = document.createElement('div');
    const div2 = document.createElement('div');
    document.body.appendChild(div);
    const a1 = window.WombatTestUtil.createUntamperedWithElement('a');
    const a2 = window.WombatTestUtil.createUntamperedWithElement('a');
    const a3 = window.WombatTestUtil.createUntamperedWithElement('a');
    a1.href = 'http://example1.com';
    a2.href = 'http://example2.com';
    a3.href = 'http://example3.com';
    div2.appendChild(a1);
    div2.appendChild(a2);
    div2.appendChild(a3);
    document.body.replaceChild(div2, div);
    const result = {
      a1: window.WombatTestUtil.getElementPropertyAsIs(a1, 'href').endsWith(
        'mp_/http://example1.com'
      ),
      a2: window.WombatTestUtil.getElementPropertyAsIs(a2, 'href').endsWith(
        'mp_/http://example2.com'
      ),
      a3: window.WombatTestUtil.getElementPropertyAsIs(a3, 'href').endsWith(
        'mp_/http://example3.com'
      )
    };
    a1.remove();
    return result;
  });
  t.deepEqual(result, { a1: true, a2: true, a3: true });
});

test('Audio: should rewrite the URL argument to the constructor', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () =>
      window.WombatTestUtil.getElementPropertyAsIs(
        new Audio('https://music.com/music.mp3'),
        'src'
      ) === '/live/20180803160549oe_/https://music.com/music.mp3'
  );
  t.true(result);
});

test('FontFace: should rewrite the source argument to the constructor', async t => {
  const { sandbox, server } = t.context;
  await Promise.all([
    server.waitForRequest(
      '/live/20180803160549mp_/https://tests.wombat.io/daFont.woff2'
    ),
    sandbox.evaluate(async () => {
      try {
        const ff = new FontFace('DaFont', 'url(daFont.woff2)');
        await ff.load();
      } catch (e) {}
    })
  ]);
  // the server will automatically reject the waitForRequest promise after 15s
  t.pass('URLs used in the construction of FontFaces are rewritten');
});

for (const fnTest of TextNodeTest.fnTests) {
  test(`Text.${fnTest}: data argument should be rewritten when it is a child of a style tag`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      TextNodeTest.evaluationFN,
      fnTest,
      TextNodeTest.theStyle,
      TextNodeTest.theStyleRw,
      true
    );
    t.true(result);
  });
  test(`Text.${fnTest}: data argument should not be rewritten when it is not a child of a style tag`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      TextNodeTest.evaluationFN,
      fnTest,
      TextNodeTest.theStyle,
      TextNodeTest.theStyleRw,
      false
    );
    t.true(result);
  });
}

for (const aTest of HTMLAssign.innerOuterHTML.tests) {
  test(`${aTest.which}: assignments should be rewritten`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      HTMLAssign.innerOuterHTML.assignmentFN,
      aTest.which,
      aTest.unrw,
      aTest.rw
    );
    t.true(result);
  });

  test(`${aTest.which}: retrials should be un-rewritten`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      HTMLAssign.innerOuterHTML.retrieval,
      aTest.which,
      aTest.unrw,
      aTest.rw
    );
    t.is(result, aTest.unrw);
  });

  test(`${
    aTest.which
  }: assignments to the retrial of the property should work`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      HTMLAssign.innerOuterHTML.assignmentToRetrieval,
      aTest.which,
      aTest.unrw,
      aTest.rw
    );
    t.true(result);
  });
}

for (const [tag, attrMods] of Object.entries(TagToMod.elements)) {
  for (const [attr, mod] of Object.entries(attrMods)) {
    test(`${tag}.${attr}: rewrites of direct attribute assignment should use the "${mod}" modifier`, async t => {
      const { sandbox, server } = t.context;
      const unRW = 'https://example.com';
      const result = await sandbox.evaluate(TagToMod.testFNDirect, tag, attr, unRW);
      t.true(
        result !== unRW,
        `Assignments to ${tag}.${attr} is not being rewritten`
      );
      const existingModifier = extractModifier(result);
      t.is(
        existingModifier,
        mod,
        `Assignments to ${tag}.${attr} is not being rewritten using the "${mod}" modifier`
      );
    });

    test(`${tag}.${attr}: rewrites of attribute assignment using setAttribute should use the "${mod}" modifier`, async t => {
      const { sandbox, server } = t.context;
      const unRW = 'https://example.com';
      const result = await sandbox.evaluate(TagToMod.testFNSetAttr, tag, attr, unRW);
      t.true(
        result !== unRW,
        `Assignments to ${tag}.${attr} is not being rewritten`
      );
      const existingModifier = extractModifier(result);
      t.is(
        existingModifier,
        mod,
        `Assignments to ${tag}.${attr} is not being rewritten using the "${mod}" modifier`
      );
    });
  }
}

