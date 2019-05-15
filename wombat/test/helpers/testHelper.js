const initChrome = require('./initChrome');
const initServer = require('./initServer');
const { CRIExtra, Browser, Events } = require('chrome-remote-interface-extra');

const testDomains = { workers: true };

class TestHelper {
  /**
   * @param {*} t
   * @return {Promise<TestHelper>}
   */
  static async init(t) {
    const { chromeProcess, killChrome } = await initChrome();
    const server = await initServer();
    const { webSocketDebuggerUrl } = await CRIExtra.Version();
    const client = await CRIExtra({ target: webSocketDebuggerUrl });
    const browser = await Browser.create(client, {
      ignoreHTTPSErrors: true,
      process: chromeProcess,
      additionalDomains: testDomains,
      async closeCallback() {
        killChrome();
      }
    });
    await browser.waitForTarget(t => t.type() === 'page');
    const th = new TestHelper({ server, client, browser, t, killChrome });
    await th.setup();
    return th;
  }

  /**
   * @param {TestHelperInit} init
   */
  constructor({ server, client, browser, t, killChrome }) {
    /**
     * @type {fastify.FastifyInstance}
     */
    this._server = server;

    /**
     * @type {CRIConnection}
     */
    this._client = client;

    /**
     * @type {Browser}
     */
    this._browser = browser;

    /** @type {*} */
    this._t = t;

    this._killChrome = killChrome;

    /** @type {Page} */
    this._testPage = null;

    /** @type {Frame} */
    this._sandbox = null;
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
    await this._testPage.goto(this._server.testPage, {
      waitUntil: 'networkidle2'
    });
    this._sandbox = this._testPage.frames()[1];
  }

  async fullRefresh() {
    await this.cleanup();
    await this.initWombat();
  }

  async ensureSandbox() {
    if (!this._sandbox.url().endsWith('https://tests.wombat.io/')) {
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
 * @property {Browser} browser
 * @property {CRIConnection} client
 * @property {fastify.FastifyInstance} server
 * @property {*} t
 * @property {function(): void} killChrome
 */
