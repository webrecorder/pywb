var sauceLabsConfig = {
    testName: 'pywb Client Tests',
};

// see https://github.com/karma-runner/karma-sauce-launcher/issues/73
if (process.env.TRAVIS_JOB_NUMBER) {
    sauceLabsConfig.startConnect = false;
    sauceLabsConfig.tunnelIdentifier = process.env.TRAVIS_JOB_NUMBER;
}

var WOMBAT_JS_PATH = 'pywb/static/wombat.js';

var sauceLaunchers = {
    sl_chrome: {
        base: 'SauceLabs',
        browserName: 'chrome',
    },

    sl_firefox: {
        base: 'SauceLabs',
        browserName: 'firefox',
    },

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
};

var localLaunchers = {
    localFirefox: {
        base: 'Firefox',
    },
};

var customLaunchers = {};

if (process.env['SAUCE_USERNAME'] && process.env['SAUCE_ACCESS_KEY']) {
    customLaunchers = sauceLaunchers;
} else {
    console.error('Sauce Labs account details not set, ' +
                  'Karma tests will be run only against local browsers.' +
                  'Set SAUCE_USERNAME and SAUCE_ACCESS_KEY environment variables to ' +
                  'run tests against Sauce Labs browsers');
    customLaunchers = localLaunchers;
}

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
      {
        pattern: 'karma-tests/dummy.html',
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

    // Set extended timeouts to account for the slowness
    // in connecting to remote browsers (eg. when using
    // Sauce Labs)
    //
    // See https://oligofren.wordpress.com/2014/05/27/running-karma-tests-on-browserstack/
    captureTimeout: 3 * 60000,
    browserNoActivityTimeout: 30 * 1000,
    browserDisconnectTimeout: 10 * 1000,
    browserDisconnectTolerance: 1,

    customLaunchers: customLaunchers,

    browsers: Object.keys(customLaunchers),

    singleRun: false,

    concurrency: Infinity
  })
};
