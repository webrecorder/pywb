import test from 'ava';
import TestHelper from './helpers/testHelper';

/**
 * @type {TestHelper}
 */
let helper = null;

test.serial.before(async t => {
  helper = await TestHelper.init(t);
});

test.serial.beforeEach(async t => {
  /**
   * @type {Frame}
   */
  t.context.sandbox = helper.sandbox();

  /**
   * @type {fastify.FastifyInstance<http2.Http2SecureServer, http2.Http2ServerRequest, http2.Http2ServerResponse>}
   */
  t.context.server = helper.server();
});

test.serial.afterEach.always(async t => {
  await helper.cleanup();
});

test.serial.after.always(async t => {
  await helper.stop();
});

test.serial(
  'should not be possible using the function Wombat a constructor',
  async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(() => {
      try {
        new window.Wombat(window, window.wbinfo);
        return false;
      } catch (e) {
        return true;
      }
    });
    t.true(result, 'Wombat can be used as an constructor');
  }
);

test.serial(
  'should not be possible by invoking the function Wombat',
  async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(() => {
      try {
        window.Wombat(window, window.wbinfo);
        return false;
      } catch (e) {
        return true;
      }
    });
    t.true(result, 'Wombat can be created via invoking the function Wombat');
  }
);

test.serial(
  'using _WBWombatInit as a plain function: should not throw an error',
  async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(() => {
      try {
        window._WBWombatInit(window.wbinfo);
        return window._wb_wombat != null;
      } catch (e) {
        return false;
      }
    });
    t.true(result, 'Wombat can not be initialized using _WBWombatInit');
  }
);

test.serial(
  'using _WBWombatInit as a plain function: should not return an object containing the exposed functions',
  async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(() => {
      try {
        return (
          window._WBWombatInit(window.wbinfo) == null &&
          window._wb_wombat != null
        );
      } catch (e) {
        return false;
      }
    });
    t.true(
      result,
      'window._WBWombatInit(window.wbinfo) should not return anything'
    );
  }
);

test.serial(
  'using _WBWombatInit as a plain function: should add the property _wb_wombat to the window which is an object containing the exposed functions',
  async t => {
    const { sandbox, server } = t.context;
    const result = await sandbox.evaluate(() => {
      window._WBWombatInit(window.wbinfo);
      return {
        actual: window._wb_wombat.actual,
        extract_orig: typeof window._wb_wombat.extract_orig,
        rewrite_url: typeof window._wb_wombat.rewrite_url,
        watch_elem: typeof window._wb_wombat.watch_elem,
        init_new_window_wombat: typeof window._wb_wombat.init_new_window_wombat,
        init_paths: typeof window._wb_wombat.init_paths,
        local_init: typeof window._wb_wombat.local_init
      };
    });
    t.deepEqual(
      result,
      {
        actual: true,
        extract_orig: 'function',
        rewrite_url: 'function',
        watch_elem: 'function',
        init_new_window_wombat: 'function',
        init_paths: 'function',
        local_init: 'function'
      },
      `window._wb_wombat does not have the expected interface`
    );
  }
);
