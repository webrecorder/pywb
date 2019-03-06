import test from 'ava';
import { mpURL } from './helpers/testedValues';
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

test('XMLHttpRequest: should rewrite the URL argument of "open"', async t => {
  const { sandbox, server } = t.context;
  const response = await sandbox.evaluate(async () => {
    let reqDone;
    let to;
    const prom = new Promise(resolve => {
      reqDone = resolve;
      to = setTimeout(() => resolve(false), 5000);
    });
    const onLoad = () => {
      clearTimeout(to);
      reqDone(true);
    };
    const xhr = new XMLHttpRequest();
    xhr.addEventListener('load', onLoad);
    xhr.open('GET', '/test');
    xhr.send();
    const loaded = await prom;
    if (!loaded) throw new Error('no reply from server in 5 seconds');
    return JSON.parse(xhr.responseText);
  });
  t.is(response.headers['x-pywb-requested-with'], 'XMLHttpRequest');
  t.is(response.url, '/live/20180803160549mp_/https://tests.wombat.io/test');
});

test('XMLHttpRequest: should rewrite the "responseURL" property', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(async () => {
    let reqDone;
    let to;
    const prom = new Promise(resolve => {
      reqDone = resolve;
      to = setTimeout(() => resolve(false), 5000);
    });
    const onLoad = () => {
      clearTimeout(to);
      reqDone(true);
    };
    const xhr = new XMLHttpRequest();
    xhr.addEventListener('load', onLoad);
    xhr.open('GET', '/test');
    xhr.send();
    const loaded = await prom;
    if (!loaded) throw new Error('no reply from server in 5 seconds');
    return xhr.responseURL === 'https://tests.wombat.io/test';
  });
  t.true(result);
});

test('fetch: should rewrite the input argument when it is a string (URL)', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(async () => {
    let to;
    let response = await Promise.race([
      fetch('/test'),
      new Promise(resolve => {
        to = setTimeout(() => resolve('timed out'), 5000);
      })
    ]);
    if (response === 'timed out')
      throw new Error('no reply from server in 5 seconds');
    clearTimeout(to);
    const data = await response.json();
    return data.url === '/live/20180803160549mp_/https://tests.wombat.io/test';
  });
  t.true(result);
});

test('fetch: should rewrite the input argument when it is an Request object', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(async () => {
    let to;
    let response = await Promise.race([
      fetch(
        new Request('/test', {
          method: 'GET'
        })
      ),
      new Promise(resolve => {
        to = setTimeout(() => resolve('timed out'), 5000);
      })
    ]);
    if (response === 'timed out')
      throw new Error('no reply from server in 5 seconds');
    clearTimeout(to);
    const data = await response.json();
    return data.url === '/live/20180803160549mp_/https://tests.wombat.io/test';
  });
  t.true(result);
});

test('fetch: should rewrite the input argument when it is a object with an href property', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(async () => {
    let to;
    let response = await Promise.race([
      fetch({ href: '/test' }),
      new Promise(resolve => {
        to = setTimeout(() => resolve('timed out'), 10000);
      })
    ]);
    if (response === 'timed out')
      throw new Error('no reply from server in 10 seconds');
    clearTimeout(to);
    const data = await response.json();
    return data.url === '/live/20180803160549mp_/https://tests.wombat.io/test';
  });
  t.true(result);
});

test('Request: should rewrite the input argument to the constructor when it is a string (URL)', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const req = new Request('/test', { method: 'GET' });
    return req.url;
  });
  t.true(result === mpURL('https://tests.wombat.io/test'));
});

test('Request: should rewrite the input argument to the constructor when it is an object with a url property', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const req = new Request({ url: '/test' }, { method: 'GET' });
    return req.url;
  });
  t.true(result === mpURL('https://tests.wombat.io/test'));
});
