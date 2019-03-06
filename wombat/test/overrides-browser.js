import test from 'ava';
import { URLParts, WB_PREFIX } from './helpers/testedValues';
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

test('The actual top should have been sent the loadMSG', async t => {
  const { testPage, server } = t.context;
  const result = await testPage.evaluate(
    () => window.overwatch.wbMessages.load
  );
  t.true(
    result,
    'The message sent by wombat to inform top it has loaded should have been sent'
  );
});

test('init_top_frame: should set __WB_replay_top correctly', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.__WB_replay_top === window
  );

  t.true(result, 'The replay top should equal to frames window object');
});

test('init_top_frame: should set __WB_orig_parent correctly', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.__WB_orig_parent === window.top
  );
  t.true(result, '__WB_orig_parent should equal the actual top');
});

test('init_top_frame: should set parent to itself (__WB_replay_top)', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.parent === window.__WB_replay_top
  );
  t.true(result, 'window.parent should equal to itself (__WB_replay_top)');
});

test('WombatLocation: should be added to window as WB_wombat_location', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.WB_wombat_location != null
  );
  t.true(result, 'WB_wombat_location was not added to window');
});

for (let i = 0; i < URLParts.length; i++) {
  const urlPart = URLParts[i];
  test(`WombatLocation: should make available '${urlPart}'`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      upart => window.WB_wombat_location[upart] != null,
      urlPart
    );
    t.true(result, `WB_wombat_location does not make available '${urlPart}'`);
  });

  test(`WombatLocation: the '${urlPart}' property should be equal to the same value as would be returned on the live web`, async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(
      upart =>
        new URL(window.wbinfo.url)[upart] === window.WB_wombat_location[upart],
      urlPart
    );
    t.true(
      result,
      `WB_wombat_location return a value equal to the original for '${urlPart}'`
    );
  });
}

test('WombatLocation: should return the href property as the value for toString', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.WB_wombat_location.toString() === window.wbinfo.url
  );
  t.true(
    result,
    `WB_wombat_location does not return the href property as the value for toString`
  );
});

test('WombatLocation: should return itself as the value for valueOf', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.WB_wombat_location.valueOf() === window.WB_wombat_location
  );
  t.true(
    result,
    `WB_wombat_location does not return itself as the value for valueOf`
  );
});

test('WombatLocation: should have a Symbol.toStringTag value of "Location"', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () =>
      window.WB_wombat_location[window.Symbol.toStringTag] ===
      location[window.Symbol.toStringTag]
  );
  t.true(
    result,
    `WB_wombat_location does not have a Symbol.toStringTag value of "Location"`
  );
});

test('WombatLocation browser navigation control: should rewrite Location.replace usage', async t => {
  const { sandbox, server } = t.context;
  const [navigationResponse] = await Promise.all([
    sandbox.waitForNavigation(),
    sandbox.evaluate(() => {
      window.WB_wombat_location.replace('/it');
    })
  ]);
  t.is(
    navigationResponse.url(),
    `${WB_PREFIX}mp_/https://tests.wombat.io/it`,
    'using WB_wombat_location.replace did not navigate the page'
  );
});

test('WombatLocation browser navigation control: should rewrite Location.assign usage', async t => {
  const { sandbox, server } = t.context;
  const [navigationResponse] = await Promise.all([
    sandbox.waitForNavigation(),
    sandbox.evaluate(() => {
      window.WB_wombat_location.assign('/it');
    })
  ]);
  t.is(
    navigationResponse.url(),
    `${WB_PREFIX}mp_/https://tests.wombat.io/it`,
    'using WB_wombat_location.assign did not navigate the page'
  );
});

test('WombatLocation browser navigation control: should reload the page via Location.reload usage', async t => {
  const { sandbox, server } = t.context;
  const [originalLoc, navigationResponse] = await Promise.all([
    sandbox.evaluate(() => window.location.href),
    sandbox.waitForNavigation(),
    sandbox.evaluate(() => {
      window.WB_wombat_location.reload();
    })
  ]);
  t.is(
    navigationResponse.url(),
    originalLoc,
    'using WB_wombat_location.reload did not reload the page'
  );
});

test('browser history control: should rewrite history.pushState', async t => {
  const { sandbox, server } = t.context;
  const [originalLoc, newloc] = await Promise.all([
    sandbox.evaluate(() => window.location.href),
    sandbox.evaluate(() => {
      window.history.pushState(null, null, '/it');
      return window.location.href;
    })
  ]);
  t.is(
    newloc,
    `${originalLoc}it`,
    'history navigations using pushState are not rewritten'
  );
  const result = await sandbox.evaluate(
    () => window.WB_wombat_location.href === 'https://tests.wombat.io/it'
  );
  t.true(
    result,
    'WB_wombat_location.href does not update after history.pushState usage'
  );
});

test('browser history control: should rewrite history.replaceState', async t => {
  const { sandbox, server } = t.context;
  const [originalLoc, newloc] = await Promise.all([
    sandbox.evaluate(() => window.location.href),
    sandbox.evaluate(() => {
      window.history.replaceState(null, null, '/it2');
      return window.location.href;
    })
  ]);
  t.is(
    newloc,
    `${originalLoc}it2`,
    'history navigations using pushState are not rewritten'
  );
  const result = await sandbox.evaluate(
    () => window.WB_wombat_location.href === 'https://tests.wombat.io/it2'
  );
  t.true(
    result,
    'WB_wombat_location.href does not update after history.replaceState usage'
  );
});

test('browser history control: should send the "replace-url" msg to the top frame on history.pushState usage', async t => {
  const { sandbox, testPage } = t.context;
  await sandbox.evaluate(() => window.history.pushState(null, null, '/it3'));
  const result = await testPage.evaluate(
    () =>
      window.overwatch.wbMessages['replace-url'].url != null &&
      window.overwatch.wbMessages['replace-url'].url ===
        'https://tests.wombat.io/it3'
  );
  t.true(
    result,
    'the "replace-url" message was not sent to the top frame on history.pushState usage'
  );
});

test('browser history control: should send the "replace-url" msg to the top frame on history.replaceState usage', async t => {
  const { sandbox, testPage } = t.context;
  await sandbox.evaluate(() => window.history.replaceState(null, null, '/it4'));
  t.true(
    await testPage.evaluate(
      () =>
        window.overwatch.wbMessages['replace-url'].url != null &&
        window.overwatch.wbMessages['replace-url'].url ===
          'https://tests.wombat.io/it4'
    ),
    'the "replace-url" message was not sent to the top frame on history.pushState usage'
  );
});
