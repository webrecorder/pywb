import test from 'ava';
import TestHelper from './helpers/testHelper';

/**
 * @type {TestHelper}
 */
let helper = null;

test.before(async t => {
  helper = await TestHelper.init(t);
});

test.beforeEach(async t => {
  /**
   * @type {Frame}
   */
  t.context.sandbox = helper.sandbox();

  /**
   * @type {fastify.FastifyInstance<http2.Http2SecureServer, http2.Http2ServerRequest, http2.Http2ServerResponse>}
   */
  t.context.server = helper.server();
});

test.after.always(async t => {
  await helper.stop();
});

test('should put _WBWombat on window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => {
    const wbWombat = window._WBWombat;
    return { exists: wbWombat != null, type: typeof wbWombat };
  });
  t.deepEqual(
    result,
    { exists: true, type: 'function' },
    '_WBWombat should be placed on window before initialization and should be a function'
  );
});

test('should not add __WB_replay_top to window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => window.__WB_replay_top == null);
  t.true(result, '__WB_replay_top should not exist on window');
});

test('should not add _WB_wombat_location to window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window._WB_wombat_location == null
  );
  t.true(result, '_WB_wombat_location should not exist on window');
});

test('should not add WB_wombat_location to window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.WB_wombat_location == null
  );
  t.true(result, 'WB_wombat_location should not exist on window');
});

test('should not add __WB_check_loc to window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => window.__WB_check_loc == null);
  t.true(result, '__WB_check_loc should not exist on window');
});

test('should not add __orig_postMessage property on window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.__orig_postMessage == null
  );
  t.true(result, '__orig_postMessage should not exist on window');
});

test('should not add __WB_top_frame to window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => window.__WB_top_frame == null);
  t.true(result, '__WB_top_frame should not exist on window');
});

test('should not add __wb_Date_now to window', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => window.__wb_Date_now == null);
  t.true(result, '__wb_Date_now should not exist on window');
});

test('should not expose CustomStorage', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() =>
    window.Storage.toString().includes('[native code]')
  );
  t.true(result, 'CustomStorage should not exist on window');
});

test('should not expose FuncMap', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => window.FuncMap == null);
  t.true(result, 'FuncMap should not exist on window');
});

test('should not expose SameOriginListener', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => window.SameOriginListener == null
  );
  t.true(result, 'SameOriginListener should not exist on window');
});

test('should not expose WrappedListener', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() => window.WrappedListener == null);
  t.true(result, 'WrappedListener should not exist on window');
});

test('should not add the __WB_pmw property to Object.prototype', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () => Object.prototype.__WB_pmw == null
  );
  t.true(result, 'Object.prototype.__WB_pmw should be undefined');
});

test('should not add the WB_wombat_top property to Object.prototype', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(
    () =>
      Object.prototype.WB_wombat_top == null &&
      !Object.hasOwnProperty('WB_wombat_top')
  );
  t.true(result, 'Object.prototype.WB_wombat_top should be undefined');
});

test('should not have patched Element.prototype.insertAdjacentHTML', async t => {
  const { sandbox, server } = t.context;
  const result = await sandbox.evaluate(() =>
    window.Element.prototype.insertAdjacentHTML
      .toString()
      .includes('[native code]')
  );
  t.true(
    result,
    'Element.prototype.insertAdjacentHTML should not have been patched'
  );
});
