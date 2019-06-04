import test from 'ava';
import TestHelper from './helpers/testHelper';

/**
 * @type {TestHelper}
 */
let helper = null;

test.before(async t => {
  helper = await TestHelper.init(t, true);
});

test.beforeEach(async t => {
  t.context.sandbox = helper.sandbox();
  t.context.testPage = helper.testPage();
  t.context.server = helper.server();
  await t.context.sandbox.evaluate(() => {
    window.fnsCalled = {
      nTn: {
        callCount: 0,
        params: []
      },
      nTa: {
        callCount: 0,
        params: []
      },
      aTn: {
        callCount: 0,
        params: []
      },
      aTa: {
        callCount: 0,
        params: []
      }
    };
    window.testedFNs = [
      {
        testName: 'nTn',
        key() {
          return 'key nTn';
        },
        value(param) {
          window.fnsCalled.nTn.callCount += 1;
          window.fnsCalled.nTn.params.push(param);
          return 'value nTn';
        }
      },
      {
        testName: 'nTa',
        key() {
          return 'key nTa';
        },
        value: param => {
          window.fnsCalled.nTa.callCount += 1;
          window.fnsCalled.nTa.params.push(param);
          return 'value nTa';
        }
      },
      {
        testName: 'aTn',
        key: () => 'key aTn',
        value(param) {
          window.fnsCalled.aTn.callCount += 1;
          window.fnsCalled.aTn.params.push(param);
          return 'value aTn';
        }
      },
      {
        testName: 'aTa',
        key: () => 'key aTa',
        value: param => {
          window.fnsCalled.aTa.callCount += 1;
          window.fnsCalled.aTa.params.push(param);
          return 'value aTa';
        }
      }
    ];
  });
});

test.after.always(async t => {
  await helper.stop();
});

test('Storage - creation: should not throw errors', async t => {
  const { sandbox, server } = t.context;
  const creationPromise = sandbox.evaluate(() => {
    new Storage();
  });
  await t.notThrowsAsync(creationPromise);
});

test('FuncMap - set: normal and arrow functions should be added', async t => {
  const { sandbox, server } = t.context;
  const numKeys = await sandbox.evaluate(() => {
    const fnm = new FuncMap();
    for (let i = 0; i < testedFNs.length; i++) {
      const { key, value } = testedFNs[i];
      fnm.set(key, value);
    }
    return fnm._map.length;
  });
  t.is(numKeys, 4);
});

test('FuncMap - get: normal and arrow functions that are added should be retrieved per the key', async t => {
  const { sandbox, server } = t.context;
  const testResult = await sandbox.evaluate(() => {
    const result = {
      nTn: false,
      nTa: false,
      aTn: false,
      aTa: false
    };
    const fnm = new FuncMap();
    for (let i = 0; i < testedFNs.length; i++) {
      const { key, value } = testedFNs[i];
      fnm.set(key, value);
    }
    for (let i = 0; i < testedFNs.length; i++) {
      const { testName, key, value } = testedFNs[i];
      const mappedValue = fnm.get(key);
      result[testName] = mappedValue === value && mappedValue() === value();
    }
    return result;
  });
  t.deepEqual(testResult, {
    nTn: true,
    nTa: true,
    aTn: true,
    aTa: true
  });
});

test('FuncMap - find: should return the correct index of the internal mapping', async t => {
  const { sandbox, server } = t.context;
  const testResult = await sandbox.evaluate(() => {
    const fnm = new FuncMap();
    for (let i = 0; i < testedFNs.length; i++) {
      const { key, value } = testedFNs[i];
      fnm.set(key, value);
    }
    return testedFNs.every(({ key, value }) => {
      const idx = fnm.find(key);
      return fnm._map[idx][1] === value;
    });
  });
  t.true(testResult);
});

test('FuncMap - add_or_get: should correctly add a function when no mapping exists and should return the existing mapping, not add a function, when a previous mapping was added', async t => {
  const { sandbox, server } = t.context;
  const testResult = await sandbox.evaluate(() => {
    const fnm = new FuncMap();
    let initerCalled = 0;
    const initer = () => {
      initerCalled += 1;
      return () => {};
    };
    const key = () => {};
    const fistCall = fnm.add_or_get(key, initer);
    const secondCall = fnm.add_or_get(key, initer);
    return {
      initerCalled,
      mappingCheck: fistCall === secondCall
    };
  });
  await t.deepEqual(testResult, {
    initerCalled: 1,
    mappingCheck: true
  });
});

test('FuncMap - remove: should remove the mapped function and return the mapped value if a mapping exists', async t => {
  const { sandbox, server } = t.context;
  const testResult = await sandbox.evaluate(() => {
    const result = {
      nTn: false,
      nTa: false,
      aTn: false,
      aTa: false,
      noMapping: false
    };
    const fnm = new FuncMap();
    for (let i = 0; i < testedFNs.length; i++) {
      const { key, value } = testedFNs[i];
      fnm.set(key, value);
    }
    for (let i = 0; i < testedFNs.length; i++) {
      const { testName, key, value } = testedFNs[i];
      result[testName] = fnm.remove(key) === value;
    }
    result.noMapping = fnm.remove(() => {}) == null;
    return result;
  });
  t.deepEqual(testResult, {
    nTn: true,
    nTa: true,
    aTn: true,
    aTa: true,
    noMapping: true
  });
});

test('FuncMap - map: should call every mapped with the supplied arguments', async t => {
  const { sandbox, server } = t.context;
  const testResult = await sandbox.evaluate(() => {
    const fnm = new FuncMap();
    for (let i = 0; i < testedFNs.length; i++) {
      const { key, value } = testedFNs[i];
      fnm.set(key, value);
    }
    fnm.map('the param 1');
    fnm.map('the param 2');
    return window.fnsCalled;
  });
  t.deepEqual(testResult, {
    nTn: {
      callCount: 2,
      params: ['the param 1', 'the param 2']
    },
    nTa: {
      callCount: 2,
      params: ['the param 1', 'the param 2']
    },
    aTn: {
      callCount: 2,
      params: ['the param 1', 'the param 2']
    },
    aTa: {
      callCount: 2,
      params: ['the param 1', 'the param 2']
    }
  });
});
