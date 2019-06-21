const { launch } = require('just-launch-chrome');
const Browser = require('chrome-remote-interface-extra/lib/browser/Browser');

const winPos = !process.env.NO_MOVE_WINDOW ? '--window-position=2000,0' : '';

const chromeArgs = [
  '--force-color-profile=srgb',
  '--disable-background-networking',
  '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows',
  '--disable-ipc-flooding-protection',
  '--enable-features=NetworkService,NetworkServiceInProcess,AwaitOptimization',
  '--disable-client-side-phishing-detection',
  '--disable-default-apps',
  '--disable-extensions',
  '--disable-popup-blocking',
  '--disable-hang-monitor',
  '--disable-prompt-on-repost',
  '--disable-sync',
  '--disable-domain-reliability',
  '--disable-infobars',
  '--disable-features=site-per-process,TranslateUI,BlinkGenPropertyTrees,LazyFrameLoading',
  '--disable-breakpad',
  '--disable-backing-store-limit',
  '--metrics-recording-only',
  '--no-first-run',
  '--safebrowsing-disable-auto-update',
  '--password-store=basic',
  '--use-mock-keychain',
  '--mute-audio',
  '--autoplay-policy=no-user-gesture-required',
  winPos,
  'about:blank'
];

/**
 *
 * @return {Promise<Browser>}
 */
async function initChrome() {
  const { browserWSEndpoint, closeBrowser, chromeProcess } = await launch({
    args: chromeArgs
  });
  const browser = await Browser.connect(browserWSEndpoint, {
    ignoreHTTPSErrors: true,
    additionalDomains: { workers: true },
    process: chromeProcess,
    closeCallback: closeBrowser
  });
  await browser.waitForTarget(t => t.type() === 'page');
  return browser;
}

module.exports = initChrome;
