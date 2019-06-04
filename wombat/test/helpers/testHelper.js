const initChrome = require('./initChrome');
const initServer = require('./initServer');
const { Browser } = require('chrome-remote-interface-extra');

class TestHelper {
  /**
   * @param {*} t
   * @param {boolean} [direct = false]
   * @return {Promise<TestHelper>}
   */
  static async init(t, direct = false) {
    const browser = await initChrome();
    const server = await initServer();
    const th = new TestHelper({
      server,
      browser,
      t,
      direct
    });
    await th.setup();
    return th;
  }

  /**
   * @param {TestHelperInit} init
   */
  constructor({ server, browser, t, direct }) {
    /**
     * @type {fastify.FastifyInstance}
     */
    this._server = server;

    /**
     * @type {Browser}
     */
    this._browser = browser;

    /** @type {*} */
    this._t = t;

    /** @type {Page} */
    this._testPage = null;

    /** @type {Frame} */
    this._sandbox = null;

    /** @type {boolean} */
    this._direct = direct;
  }

  /**
   * @return {fastify.FastifyInstance}
   */
  server() {
    return this._server;
  }

  /**
   * @return {Page}
   */
  testPage() {
    return this._testPage;
  }

  /**
   * @return {Frame}
   */
  sandbox() {
    return this._sandbox;
  }

  async initWombat() {
    await this._testPage.evaluate(() => {
      window.overwatch.initSandbox();
    });
  }

  async maybeInitWombat() {
    await this._testPage.evaluate(() => {
      window.overwatch.maybeInitSandbox();
    });
  }

  async setup() {
    this._testPage = await this._browser.newPage();
    await this.cleanup();
  }

  async cleanup() {
    const testPageURL = this._direct
      ? this._server.testPageDirect
      : this._server.testPage;
    await this._testPage.goto(testPageURL, {
      waitUntil: 'networkidle2'
    });
    this._sandbox = this._testPage.frames()[1];
  }

  async fullRefresh() {
    await this.cleanup();
    await this.initWombat();
  }

  async ensureSandbox() {
    const url = `https://tests.${this._direct ? 'direct.' : ''}wombat.io/`;
    if (!this._sandbox.url().endsWith(url)) {
      await this.fullRefresh();
    } else {
      await this.maybeInitWombat();
    }
  }

  async stop() {
    if (this._testPage) {
      try {
        await this._testPage.close();
      } catch (e) {
        console.log(`Exception closing test page ${e}`);
      }
    }
    try {
      if (this._browser) {
        await this._browser.close();
      }
    } catch (e) {
      console.log(`Exception closing browser ${e}`);
    }
    try {
      if (this._server) {
        await this._server.stop();
      }
    } catch (e) {
      console.log(`Exception stopping server ${e}`);
    }
  }
}

module.exports = TestHelper;

/**
 * @typedef {Object} TestHelperInit
 * @property {fastify.FastifyInstance} server
 * @property {*} t
 * @property {Browser} browser
 * @property {boolean} direct
 */
