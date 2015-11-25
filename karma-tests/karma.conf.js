if (!process.env['SAUCE_USERNAME'] || !process.env['SAUCE_ACCESS_KEY']) {
    console.error('Sauce Labs account details not set, skipping Karma tests');
    process.exit(0);
}

var sauceLabsConfig = {
    testName: 'PyWB Client Tests',
};

// see https://github.com/karma-runner/karma-sauce-launcher/issues/73
if (process.env.TRAVIS_JOB_NUMBER) {
    sauceLabsConfig.startConnect = false;
    sauceLabsConfig.tunnelIdentifier = process.env.TRAVIS_JOB_NUMBER;
}

var WOMBAT_JS_PATH = 'pywb/static/wombat.js';

var customLaunchers = {
    sl_chrome: {
        base: 'SauceLabs',
        browserName: 'chrome',
    },

    sl_firefox: {
        base: 'SauceLabs',
        browserName: 'firefox',
    },

/*  Safari and Edge are currently broken in
    pywb.

    See: https://github.com/ikreymer/pywb/issues/148 (Edge)
         https://github.com/ikreymer/pywb/issues/147 (Safari)

    sl_safari: {
        base: 'SauceLabs',
        browserName: 'safari',
        platform: 'OS X 10.11',
        version: '9.0',
    },
    sl_edge: {
        base: 'SauceLabs',
        browserName: 'MicrosoftEdge',
    },
*/
};

module.exports = function(config) {
  config.set({
    basePath: '../',

    frameworks: ['mocha', 'chai'],

    files: [
      {
        pattern: WOMBAT_JS_PATH,
        watched: true,
        included: false,
        served: true,
      },
      'karma-tests/*.spec.js',
    ],

    preprocessors: {},

    reporters: ['progress'],

    port: 9876,

    colors: true,

    logLevel: config.LOG_INFO,

    autoWatch: true,

    sauceLabs: sauceLabsConfig,

    // use an extended timeout for capturing Sauce Labs
    // browsers in case the service is busy
    captureTimeout: 3 * 60000,

    customLaunchers: customLaunchers,

    browsers: Object.keys(customLaunchers),

    singleRun: false,

    concurrency: Infinity
  })
};
