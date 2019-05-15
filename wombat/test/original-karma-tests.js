import test from 'ava';
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

test('anchor rewriting - should rewrite links in dynamically injected <a> tags', async t => {
  const { sandbox } = t.context;
  const result = await sandbox.evaluate(() => {
    document.body.innerHTML = '<a href="foobar.html" id="link">A link</a>';
    const a = document.getElementById('link');
    if (a == null) return { exists: false };
    const result = { exists: true, href: a.href };
    a.remove();
    return result;
  });
  t.deepEqual(result, {
    exists: true,
    href: 'https://tests.wombat.io/foobar.html'
  });
});

test('anchor rewriting - should rewrite links in dynamically injected <a> tags and toString() should return the resolved original URL', async t => {
  const { sandbox } = t.context;
  const result = await sandbox.evaluate(() => {
    document.body.innerHTML = '<a href="foobar.html" id="link">A link</a>';
    const a = document.getElementById('link');
    if (a == null) return { exists: false };
    a.remove();
    return { exists: true, toString: a.toString() };
  });
  t.deepEqual(result, {
    exists: true,
    toString: 'https://tests.wombat.io/foobar.html'
  });
});

test('base URL overrides - document.baseURI should return the original URL', async t => {
  const { sandbox } = t.context;
  const result = await sandbox.evaluate(() => {
    var baseURI = document.baseURI;
    return { type: typeof baseURI, baseURI };
  });
  t.deepEqual(result, { type: 'string', baseURI: 'https://tests.wombat.io/' });
});

test('base URL overrides - should allow base.href to be assigned', async t => {
  const { sandbox } = t.context;
  const result = await sandbox.evaluate(() => {
    var baseElement = document.createElement('base');
    baseElement.href = 'http://foobar.com/base';
    return baseElement.href;
  });
  t.is(result, 'http://foobar.com/base');
});
