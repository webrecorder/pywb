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
  if (t.title.includes('SharedWorker')) {
    await helper.fullRefresh();
  } else {
    await helper.ensureSandbox();
  }
});

test.after.always(async t => {
  await helper.stop();
});

test('Web Workers: should rewrite the URL argument to the constructor of "Worker"', async t => {
  const { sandbox, server, testPage } = t.context;
  await Promise.all([
    new Promise((resolve, reject) => {
      const to = setTimeout(
        () => reject(new Error('the worker was not started')),
        15000
      );
      testPage.once('workercreated', w => {
        clearTimeout(to);
        resolve();
      });
    }),
    server.waitForRequest(
      '/live/20180803160549wkr_/https://tests.wombat.io/testWorker.js'
    ),
    sandbox.evaluate(() => {
      window.theWorker = new Worker('testWorker.js');
    })
  ]);
  await sandbox.evaluate(() => {
    window.theWorker.terminate();
  });
  t.pass(
    'The worker URL was rewritten when using Worker and is working on the page'
  );
});

test('Web Workers: should have a light override applied', async t => {
  const { sandbox, server, testPage } = t.context;
  const [worker] = await Promise.all([
    new Promise((resolve, reject) => {
      const to = setTimeout(
        () => reject(new Error('the worker was not started')),
        15000
      );
      testPage.once('workercreated', w => {
        clearTimeout(to);
        resolve(w);
      });
    }),
    server.waitForRequest(
      '/live/20180803160549wkr_/https://tests.wombat.io/testWorker.js'
    ),
    sandbox.evaluate(() => {
      window.theWorker = new Worker('testWorker.js');
    })
  ]);
  const result = await worker
    .evaluate(() => ({
      fetch: self.isFetchOverridden(),
      importScripts: self.isImportScriptOverridden(),
      open: self.isAjaxRewritten()
    }))
    .then(async results => {
      await sandbox.evaluate(() => {
        window.theWorker.terminate();
      });
      return results;
    });
  t.deepEqual(
    result,
    { fetch: true, importScripts: true, open: true },
    'The light web worker overrides were not applied properly'
  );
});

test('Web Workers: should rewrite the URL argument to the constructor of "SharedWorker"', async t => {
  const { sandbox, server, testPage } = t.context;
  await Promise.all([
    server.waitForRequest(
      '/live/20180803160549wkr_/https://tests.wombat.io/testWorker.js'
    ),
    sandbox.evaluate(() => {
      window.theWorker = new SharedWorker('testWorker.js');
    })
  ]);
  t.pass(
    'The worker URL was rewritten when using SharedWorker and is working on the page'
  );
});

test('Service Worker: should rewrite the URL argument of "navigator.serviceWorker.register"', async t => {
  const { sandbox, server, testPage } = t.context;
  const result = await sandbox.evaluate(async () => {
    const sw = await window.navigator.serviceWorker.register(
      '/testServiceWorker.js'
    );
    await sw.unregister();
    return sw.scope;
  });
  t.true(
    result.includes('mp_/https://tests.wombat.io/'),
    'rewriting of service workers is not correct'
  );
});