import test from 'ava';
import { CSS } from './helpers/testedValues';
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
  await helper.ensureSandbox();
});

test.after.always(async t => {
  await helper.stop();
});

for (const attrToProp of CSS.styleAttrs.attrs) {
  test(`style.${attrToProp.attr}: assignments should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.styleAttrs.testFNAttr,
      attrToProp
    );
    t.notDeepEqual(result, CSS.styleAttrs.unrw);
  });
}

for (const attrToProp of CSS.styleAttrs.attrs) {
  test(`style["${
    attrToProp.attr
  }"]: assignments should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.styleAttrs.testFNPropName,
      attrToProp
    );
    t.notDeepEqual(result, CSS.styleAttrs.unrw);
  });

  if (attrToProp.attr !== attrToProp.propName) {
    test(`style["${
      attrToProp.propName
    }"]: assignments should be rewritten`, async t => {
      const { sandbox } = t.context;
      const result = await sandbox.evaluate(
        CSS.styleAttrs.testFNPropName,
        attrToProp
      );
      t.notDeepEqual(result, CSS.styleAttrs.unrw);
    });
  }
}

for (const attrToProp of CSS.styleAttrs.attrs) {
  test(`style.setProperty("${
    attrToProp.attr
  }", "value"): value should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.styleAttrs.testFNSetProp,
      attrToProp.attr,
      attrToProp.unrw
    );
    t.notDeepEqual(result, attrToProp.unrw);
  });
  if (attrToProp.attr !== attrToProp.propName) {
    test(`style.setProperty("${
      attrToProp.propName
    }", "value"): value should be rewritten`, async t => {
      const { sandbox } = t.context;
      const result = await sandbox.evaluate(
        CSS.styleAttrs.testFNSetProp,
        attrToProp.propName,
        attrToProp.unrw
      );
      t.notDeepEqual(result, attrToProp.unrw);
    });
  }
}

for (const attrToProp of CSS.styleAttrs.attrs) {
  test(`style.cssText: assignments of '${
    attrToProp.propName
  }' should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.styleAttrs.testFNCssText,
      attrToProp
    );
    t.notDeepEqual(result, attrToProp.unrw);
  });
}

for (const aTest of CSS.styleTextContent.tests) {
  test(`style.textContent: assignments using an css definitions containing '${
    aTest.name
  }' should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.styleTextContent.testFN,
      aTest.unrw
    );
    t.notDeepEqual(result, aTest.unrw);
  });
}

for (const aTest of CSS.StyleSheetInsertRule.tests) {
  test(`CSSStyleSheet.insertRule: inserting a new rule containing '${
    aTest.name
  }' should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.StyleSheetInsertRule.testFN,
      aTest.unrw
    );
    t.notDeepEqual(result, aTest.unrw);
  });
}

for (const aTest of CSS.CSSRuleCSSText.tests) {
  test(`CSSRule.cssText: modifying an existing rule to become a new rule containing '${
    aTest.name
  }' should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.CSSRuleCSSText.testFN,
      aTest.unrw
    );
    t.notDeepEqual(result, aTest.unrw);
  });
}

for (const attrToProp of CSS.StylePropertyMap.tests) {
  test(`StylePropertyMap.set("${
    attrToProp.attr
  }", "value"): value should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.StylePropertyMap.testFNSet,
      attrToProp.propName,
      attrToProp.unrw
    );
    t.notDeepEqual(result, attrToProp.unrw);
  });

  if (!CSS.StylePropertyMap.noAppend.has(attrToProp.attr)) {
    test(`StylePropertyMap.append("${
      attrToProp.attr
    }", "value"): value should be rewritten`, async t => {
      const { sandbox } = t.context;
      const result = await sandbox.evaluate(
        CSS.StylePropertyMap.testFNAppend,
        attrToProp.propName,
        attrToProp.unrw
      );
      t.notDeepEqual(result, attrToProp.unrw);
    });
  }
}

for (const attrToProp of CSS.CSSKeywordValue.tests) {
  test(`new CSSKeywordValue("${
    attrToProp.propName
  }", "value"): value should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.CSSKeywordValue.testFN,
      attrToProp.propName,
      attrToProp.unrw
    );
    t.notDeepEqual(result, attrToProp.unrw);
  });
}

for (const attrToProp of CSS.CSSStyleValue.tests) {
  if (CSS.CSSStyleValue.skipped.has(attrToProp.attr)) continue;
  test(`CSSStyleValue.parse("${
    attrToProp.propName
  }", "value"): value should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.CSSStyleValue.testFNParse,
      attrToProp.propName,
      attrToProp.unrw
    );
    t.notDeepEqual(result, attrToProp.unrw);
  });

  test(`CSSStyleValue.parseAll("${
    attrToProp.propName
  }", "value"): value should be rewritten`, async t => {
    const { sandbox } = t.context;
    const result = await sandbox.evaluate(
      CSS.CSSStyleValue.testFNParseAll,
      attrToProp.propName,
      attrToProp.unrw
    );
    t.notDeepEqual(result, attrToProp.unrw);
  });
}
