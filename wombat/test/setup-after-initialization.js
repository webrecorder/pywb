import test from 'ava';
import TestHelper from './helpers/testHelper';
import * as testedChanges from './helpers/testedValues';

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
  t.context.testPage = helper.testPage();
  t.context.server = helper.server();
});

test.after.always(async t => {
  await helper.stop();
});

test('internal globals: should not have removed _WBWombat from window', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      _WBWombat: {
        exists: window._WBWombat != null,
        type: typeof window._WBWombat
      },
      _WBWombatInit: {
        exists: window._WBWombatInit != null,
        type: typeof window._WBWombatInit
      }
    })),
    {
      _WBWombat: { exists: true, type: 'function' },
      _WBWombatInit: { exists: true, type: 'function' }
    },
    'The internal globals _WBWombat and _WBWombatInit are not as expected after initialization'
  );
});

test('internal globals: should add the property __WB_replay_top to window that is equal to the same window', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      exists: window.__WB_replay_top != null,
      eq: window.__WB_replay_top === window
    })),
    {
      exists: true,
      eq: true
    },
    'The internal global __WB_replay_top is not as expected after initialization'
  );
});

test('internal globals: should define the property __WB_top_frame when it is the top replayed page', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      exists: window.__WB_top_frame != null,
      neq: window.__WB_top_frame !== window
    })),
    {
      exists: true,
      neq: true
    },
    'The internal global __WB_top_frame is not as expected after initialization'
  );
});

test('internal globals: should define the WB_wombat_top property on Object.prototype', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => {
      const descriptor = Reflect.getOwnPropertyDescriptor(
        Object.prototype,
        'WB_wombat_top'
      );
      if (!descriptor) return { exists: false };
      return {
        exists: true,
        configurable: descriptor.configurable,
        enumerable: descriptor.enumerable,
        get: typeof descriptor.get,
        set: typeof descriptor.set
      };
    }),
    {
      exists: true,
      configurable: true,
      enumerable: false,
      get: 'function',
      set: 'function'
    },
    'The property descriptor added to the prototype of Object for WB_wombat_top is not correct'
  );
});

test('internal globals: should add the _WB_wombat_location property to window', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      _WB_wombat_location: {
        exists: window._WB_wombat_location != null,
        type: typeof window._WB_wombat_location
      },
      WB_wombat_location: {
        exists: window.WB_wombat_location != null,
        type: typeof window.WB_wombat_location
      }
    })),
    {
      _WB_wombat_location: { exists: true, type: 'object' },
      WB_wombat_location: { exists: true, type: 'object' }
    },
    'Wombat location properties on window are not correct'
  );
});

test('internal globals: should add the __wb_Date_now property to window', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      exists: window.__wb_Date_now != null,
      type: typeof window.__wb_Date_now
    })),
    { exists: true, type: 'function' },
    'The __wb_Date_now property of window is incorrect'
  );
});

test('internal globals: should add the __WB_timediff property to window.Date', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      exists: window.Date.__WB_timediff != null,
      type: typeof window.Date.__WB_timediff
    })),
    { exists: true, type: 'number' },
    'The __WB_timediff property of window.Date is incorrect'
  );
});

test('internal globals: should persist the original window.postMessage as __orig_postMessage', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => ({
      exists: window.__orig_postMessage != null,
      type: typeof window.__orig_postMessage,
      isO: window.__orig_postMessage.toString().includes('[native code]')
    })),
    { exists: true, type: 'function', isO: true },
    'The __WB_timediff property of window.Date is incorrect'
  );
});

test('internal globals: should not expose WombatLocation on window', async t => {
  const { sandbox, server } = t.context;
  t.true(
    await sandbox.evaluate(() => !('WombatLocation' in window)),
    'WombatLocation should not be exposed directly'
  );
});

test('exposed functions - extract_orig: should should extract the original url', async t => {
  const { sandbox, server } = t.context;
  t.true(
    await sandbox.evaluate(
      () =>
        window._wb_wombat.extract_orig(
          'http://localhost:3030/jberlin/sw/20180510171123/https://n0tan3rd.github.io/replay_test/'
        ) === 'https://n0tan3rd.github.io/replay_test/'
    ),
    'extract_orig could not extract the original URL'
  );
});

test('exposed functions - extract_orig: should not modify an un-rewritten url', async t => {
  const { sandbox, server } = t.context;
  t.true(
    await sandbox.evaluate(
      () =>
        window._wb_wombat.extract_orig(
          'https://n0tan3rd.github.io/replay_test/'
        ) === 'https://n0tan3rd.github.io/replay_test/'
    ),
    'extract_orig modified an original URL'
  );
});

test('exposed functions - extract_orig: should be able to extract the original url from an encoded string', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => {
      const expected = 'https://n0tan3rd.github.io/replay_test/';
      const extractO = window._wb_wombat.extract_orig;
      const unicode = extractO(
        '\u0068\u0074\u0074\u0070\u003a\u002f\u002f\u006c\u006f\u0063\u0061\u006c\u0068\u006f\u0073\u0074\u003a\u0033\u0030\u0033\u0030\u002f\u006a\u0062\u0065\u0072\u006c\u0069\u006e\u002f\u0073\u0077\u002f\u0032\u0030\u0031\u0038\u0030\u0035\u0031\u0030\u0031\u0037\u0031\u0031\u0032\u0033\u002f\u0068\u0074\u0074\u0070\u0073\u003a\u002f\u002f\u006e\u0030\u0074\u0061\u006e\u0033\u0072\u0064\u002e\u0067\u0069\u0074\u0068\u0075\u0062\u002e\u0069\u006f\u002f\u0072\u0065\u0070\u006c\u0061\u0079\u005f\u0074\u0065\u0073\u0074\u002f'
      );
      const hex = extractO(
        '\x68\x74\x74\x70\x3a\x2f\x2f\x6c\x6f\x63\x61\x6c\x68\x6f\x73\x74\x3a\x33\x30\x33\x30\x2f\x6a\x62\x65\x72\x6c\x69\x6e\x2f\x73\x77\x2f\x32\x30\x31\x38\x30\x35\x31\x30\x31\x37\x31\x31\x32\x33\x2f\x68\x74\x74\x70\x73\x3a\x2f\x2f\x6e\x30\x74\x61\x6e\x33\x72\x64\x2e\x67\x69\x74\x68\x75\x62\x2e\x69\x6f\x2f\x72\x65\x70\x6c\x61\x79\x5f\x74\x65\x73\x74\x2f'
      );
      return {
        unicode:
          unicode === expected &&
          unicode ===
            '\u0068\u0074\u0074\u0070\u0073\u003a\u002f\u002f\u006e\u0030\u0074\u0061\u006e\u0033\u0072\u0064\u002e\u0067\u0069\u0074\u0068\u0075\u0062\u002e\u0069\u006f\u002f\u0072\u0065\u0070\u006c\u0061\u0079\u005f\u0074\u0065\u0073\u0074\u002f',
        hex:
          hex === expected &&
          hex ===
            '\x68\x74\x74\x70\x73\x3a\x2f\x2f\x6e\x30\x74\x61\x6e\x33\x72\x64\x2e\x67\x69\x74\x68\x75\x62\x2e\x69\x6f\x2f\x72\x65\x70\x6c\x61\x79\x5f\x74\x65\x73\x74\x2f'
      };
    }),
    { unicode: true, hex: true },
    'extract_orig could not extract the original URL from an encoded string'
  );
});

test('exposed functions - rewrite_url: should be able to rewrite an encoded string', async t => {
  const { sandbox, server } = t.context;
  t.deepEqual(
    await sandbox.evaluate(() => {
      const expected = 'https://n0tan3rd.github.io/replay_test/';
      const rewrite_url = window._wb_wombat.rewrite_url;
      const unicode = rewrite_url(
        '\u0068\u0074\u0074\u0070\u0073\u003a\u002f\u002f\u006e\u0030\u0074\u0061\u006e\u0033\u0072\u0064\u002e\u0067\u0069\u0074\u0068\u0075\u0062\u002e\u0069\u006f\u002f\u0072\u0065\u0070\u006c\u0061\u0079\u005f\u0074\u0065\u0073\u0074\u002f'
      );
      const hex = rewrite_url(
        '\x68\x74\x74\x70\x73\x3a\x2f\x2f\x6e\x30\x74\x61\x6e\x33\x72\x64\x2e\x67\x69\x74\x68\x75\x62\x2e\x69\x6f\x2f\x72\x65\x70\x6c\x61\x79\x5f\x74\x65\x73\x74\x2f'
      );
      return {
        unicode:
          unicode ===
          `${window.wbinfo.prefix}${window.wbinfo.wombat_ts}${
            window.wbinfo.mod
          }/${expected}`,
        hex:
          hex ===
          `${window.wbinfo.prefix}${window.wbinfo.wombat_ts}${
            window.wbinfo.mod
          }/${expected}`
      };
    }),
    { unicode: true, hex: true },
    'rewrite_url could not rewrite an encoded string'
  );
});

testedChanges.TestedPropertyDescriptorUpdates.forEach(aTest => {
  const msg = 'an property descriptor override should have been applied';
  aTest.props.forEach(prop => {
    if (aTest.docOrWin) {
      test(`${aTest.docOrWin}.${prop}: ${msg}`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          testFn,
          aTest.docOrWin,
          prop,
          aTest.expectedInterface,
          aTest.skipGet,
          aTest.skipSet
        );
        t.deepEqual(
          result.main,
          { exists: true, good: true },
          `The property descriptor for ${aTest.docOrWin}.${prop} is incorrect`
        );
        for (let i = 0; i < result.sub.length; i++) {
          const subTest = result.sub[i];
          t.true(subTest.result, subTest.what);
        }
      });
    } else if (aTest.objPaths) {
      aTest.objPaths.forEach(objPath => {
        test(`${objPath.replace('window.', '')}.${prop}: ${msg}`, async t => {
          const { sandbox, server } = t.context;
          const result = await sandbox.evaluate(
            testFn,
            objPath,
            prop,
            aTest.expectedInterface,
            aTest.skipGet,
            aTest.skipSet
          );
          t.deepEqual(
            result.main,
            { exists: true, good: true },
            `The property descriptor for ${objPath.replace(
              'window.',
              ''
            )}.${prop} is incorrect`
          );
          for (let i = 0; i < result.sub.length; i++) {
            const subTest = result.sub[i];
            t.true(subTest.result, subTest.what);
          }
        });
      });
    } else {
      test(`${aTest.objPath.replace(
        'window.',
        ''
      )}.${prop}: ${msg}`, async t => {
        const { sandbox, server } = t.context;
        const result = await sandbox.evaluate(
          testFn,
          aTest.objPath,
          prop,
          aTest.expectedInterface,
          aTest.skipGet,
          aTest.skipSet
        );
        t.deepEqual(
          result.main,
          { exists: true, good: true },
          `The property descriptor for ${aTest.objPath.replace(
            'window.',
            ''
          )}.prop is incorrect`
        );
        for (let i = 0; i < result.sub.length; i++) {
          const subTest = result.sub[i];
          t.true(subTest.result, subTest.what);
        }
      });
    }
  });
  function testFn(objectPath, prop, expectedInterface, skipGet, skipSet) {
    // get the original and wombat object represented by the object path expression
    // eg if objectPath is window.Node.prototype then original === window.Node.prototype and obj === wombatSandbox.window.Node.prototype
    const original = window.WombatTestUtil.getOriginalWinDomViaPath(objectPath);
    const existing = window.WombatTestUtil.getViaPath(
      window.wombatSandbox,
      objectPath
    );
    // sometimes we need to skip a property get/set toString check
    let skipGetCheck = !!(skipGet && skipGet.indexOf(prop) > -1);
    let skipSetCheck = !!(skipSet && skipSet.indexOf(prop) > -1);
    // use the reflect object in the wombat sandbox context
    const newPD = Reflect.getOwnPropertyDescriptor(existing, prop);
    const expectedEntries = Object.entries(expectedInterface);
    const tResults = {
      main: {
        exists: newPD != null,
        good: expectedEntries.every(([pk, ptype]) => typeof newPD[pk] === ptype)
      },
      sub: []
    };
    const originalPD = window.WombatTestUtil.getOriginalPropertyDescriptorFor(
      original,
      prop
    );
    if (originalPD) {
      // do a quick deep check first to see if we modified something
      tResults.sub.push({
        what: 'newPD !== originalPD',
        result: expectedEntries.some(
          ([pk, ptype]) => newPD[pk] !== originalPD[pk]
        )
      });
      // now check each part of the expected property descriptor to make sure nothing went wrong
      if (
        !skipGetCheck &&
        expectedInterface.get &&
        newPD.get &&
        originalPD.get
      ) {
        tResults.sub.push({
          what: `${objectPath}.${prop} getter.toString() !== original getter.toString()`,
          result: newPD.get.toString() !== originalPD.get.toString()
        });
      }
      if (
        !skipSetCheck &&
        expectedInterface.set &&
        newPD.set &&
        originalPD.set
      ) {
        tResults.sub.push({
          what: `${objectPath}.${prop} setter.toString() !== original setter.toString()`,
          result: newPD.set.toString() !== originalPD.set.toString()
        });
      }
      if (originalPD.configurable != null && newPD.configurable != null) {
        tResults.sub.push({
          what: `${objectPath}.${prop} the "new" configurable pd does not equals the original`,
          result: newPD.configurable === originalPD.configurable
        });
      }
      if (originalPD.writable != null && newPD.writable != null) {
        tResults.sub.push({
          what: `${objectPath}.${prop} the "new" writable pd does not equals the original`,
          result: newPD.writable === originalPD.writable
        });
      }
      if (originalPD.value != null && newPD.value != null) {
        tResults.sub.push({
          what: `${objectPath}.${prop} the "new" value pd does equals the original`,
          result: newPD.value !== originalPD.value
        });
      }
    }
    return tResults;
  }
});

testedChanges.TestFunctionChanges.forEach(aTest => {
  if (aTest.constructors) {
    aTest.constructors.forEach(ctor => {
      const niceC = ctor.replace('window.', '');
      test(`${niceC}: an constructor override should have been applied`, async t => {
        const { sandbox, server } = t.context;
        t.true(
          await sandbox.evaluate(testFN, ctor),
          `The ${ctor} was not updated`
        );
        function testFN(ctor) {
          const existing = window.WombatTestUtil.getViaPath(
            window.wombatSandbox,
            ctor
          );
          const original = window.WombatTestUtil.getOriginalWinDomViaPath(ctor);
          return existing.toString() !== original.toString();
        }
      });
    });
  } else if (aTest.objPath && aTest.origs) {
    for (let i = 0; i < aTest.fns.length; i++) {
      const fn = aTest.fns[i];
      const ofn = aTest.origs[i];
      const niceWhat = `${aTest.objPath.replace('window.', '')}.${fn}`;
      test(`${niceWhat}: an function override should have been applied`, async t => {
        const { sandbox, server } = t.context;
        t.deepEqual(
          await sandbox.evaluate(testFN, aTest.objPath, fn, ofn),
          { ne: true, persisted: true },
          `The ${niceWhat} was not updated correctly`
        );
        function testFN(objPath, fn, ofn) {
          const existing = window.WombatTestUtil.getViaPath(
            window.wombatSandbox,
            objPath
          );
          const original = window.WombatTestUtil.getOriginalWinDomViaPath(
            objPath
          );
          return {
            ne: existing[fn].toString() !== original[fn].toString(),
            persisted: existing[ofn].toString() === original[fn].toString()
          };
        }
      });
    }
  } else if (aTest.fnPath) {
    test(`${
      aTest.fnPath
    }: an function override should have been applied`, async t => {
      const { sandbox, server } = t.context;
      const result = await sandbox.evaluate(testFN, aTest.fnPath, aTest.oPath);
      t.true(result.ne, `${aTest.fnPath} was not updated`);
      if (result.originalPersisted) {
        t.true(
          result.originalPersisted,
          `The persisted original function for ${
            aTest.fnPath
          } does not match the original`
        );
      }
      function testFN(fnPath, oPath) {
        const existing = window.WombatTestUtil.getViaPath(
          window.wombatSandbox,
          fnPath
        );
        const original = window.WombatTestUtil.getOriginalWinDomViaPath(fnPath);
        const result = {
          ne: existing.toString() !== original.toString()
        };
        if (oPath) {
          const ofnOnfn = window.WombatTestUtil.getViaPath(
            window.wombatSandbox,
            oPath
          );
          result.originalPersisted = ofnOnfn.toString() === original.toString();
        }
        return result;
      }
    });
  } else if (aTest.fns) {
    aTest.fns.forEach(fn => {
      const niceWhat = `${aTest.objPath.replace('window.', '')}.${fn}`;
      test(`${niceWhat}: an function override should have been applied`, async t => {
        const { sandbox, server } = t.context;
        const results = await sandbox.evaluate(testFn, aTest.objPath, fn);
        if (results.tests) {
          results.tests.forEach(({ test, msg }) => {
            t.true(test, msg);
          });
        } else {
          t.true(results.test, `${aTest.objPath}.${fn} was not updated`);
        }
        function testFn(objPath, fn) {
          const existing = window.WombatTestUtil.getViaPath(
            window.wombatSandbox,
            objPath
          );
          const original = window.WombatTestUtil.getOriginalWinDomViaPath(
            objPath
          );
          const result = {};
          if (existing[fn] && original[fn]) {
            result.test = existing[fn].toString() !== original[fn].toString();
          } else if (existing[fn]) {
            result.tests = [
              {
                test: existing[fn] !== null,
                msg: `${objPath}.${fn} was not overridden (is undefined/null)`
              },
              {
                test: !existing[fn].toString().includes('[native code]'),
                msg: `${objPath}.${fn} was not overridden at all`
              }
            ];
          } else {
            result.test = false;
          }
          return result;
        }
      });
    });
  } else if (aTest.persisted) {
    aTest.persisted.forEach(fn => {
      const niceWhat = `${aTest.objPath.replace('window.', '')}.${fn}`;
      test(`${niceWhat}: the original function should exist on the overridden object`, async t => {
        const { sandbox, server } = t.context;
        t.true(
          await sandbox.evaluate(testFn, aTest.objPath, fn),
          `the original function '${niceWhat}' was not persisted`
        );
        function testFn(objPath, fn) {
          const existing = window.WombatTestUtil.getViaPath(
            window.wombatSandbox,
            objPath
          );
          const original = window.WombatTestUtil.getOriginalWinDomViaPath(
            objPath
          );
          return existing[fn].toString() === original[fn].toString();
        }
      });
    });
  }
});
