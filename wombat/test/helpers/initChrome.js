const cp = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs-extra');
const readline = require('readline');
const chromeFinder = require('chrome-launcher/dist/chrome-finder');
const criHelper = require('chrome-remote-interface-extra/lib/helper');

const CHROME_PROFILE_PATH = path.join(os.tmpdir(), 'temp_chrome_profile-');
const winPos = !process.env.NO_MOVE_WINDOW ? '--window-position=2000,0' : '';

const chromeArgs = userDataDir => [
  '--enable-automation',
  '--force-color-profile=srgb',
  '--remote-debugging-port=9222',
  '--disable-background-networking',
  '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows',
  '--disable-ipc-flooding-protection',
  '--enable-features=NetworkService,NetworkServiceInProcess',
  '--disable-client-side-phishing-detection',
  '--disable-default-apps',
  '--disable-extensions',
  '--disable-popup-blocking',
  '--disable-hang-monitor',
  '--disable-prompt-on-repost',
  '--disable-sync',
  '--disable-domain-reliability',
  '--disable-infobars',
  '--disable-features=site-per-process,TranslateUI',
  '--disable-breakpad',
  '--disable-backing-store-limit',
  '--metrics-recording-only',
  '--no-first-run',
  '--safebrowsing-disable-auto-update',
  '--password-store=basic',
  '--use-mock-keychain',
  '--mute-audio',
  '--autoplay-policy=no-user-gesture-required',
  `--user-data-dir=${userDataDir}`,
  winPos,
  'about:blank'
];

const preferredExes = {
  linux: [
    'google-chrome-unstable',
    'google-chrome-beta',
    'google-chrome-stable'
  ],
  darwin: ['Chrome Canary', 'Chrome'],
  win32: []
};

function findChrome() {
  const findingFn = chromeFinder[process.platform];
  if (findingFn == null) {
    throw new Error(
      `Can not find chrome exe, unsupported platform - ${process.platform}`
    );
  }
  const exes = findingFn();
  const preferred = preferredExes[process.platform] || [];
  let exe;
  for (let i = 0; i < preferred.length; i++) {
    exe = exes.find(anExe => anExe.includes(preferred[i]));
    if (exe) return exe;
  }
  return exes[0];
}

/**
 *
 * @return {Promise<{chromeProcess: ChildProcess, killChrome: function(): void}>}
 */
async function initChrome() {
  const executable = findChrome();
  const userDataDir = await fs.mkdtemp(CHROME_PROFILE_PATH);
  const chromeArguments = chromeArgs(userDataDir);
  const chromeProcess = cp.spawn(executable, chromeArguments, {
    stdio: ['ignore', 'ignore', 'pipe'],
    env: process.env,
    detached: process.platform !== 'win32'
  });

  const maybeRemoveUDataDir = () => {
    try {
      fs.removeSync(userDataDir);
    } catch (e) {}
  };

  let killed = false;

  const killChrome = () => {
    if (killed) {
      return;
    }
    killed = true;
    chromeProcess.kill('SIGKILL');
    // process.kill(-chromeProcess.pid, 'SIGKILL')
    maybeRemoveUDataDir();
  };

  process.on('exit', killChrome);
  chromeProcess.once('exit', maybeRemoveUDataDir);

  process.on('SIGINT', () => {
    killChrome();
    process.exit(130);
  });
  process.once('SIGTERM', killChrome);
  process.once('SIGHUP', killChrome);
  await waitForWSEndpoint(chromeProcess, 15 * 1000);
  return { chromeProcess, killChrome };
}

module.exports = initChrome;

// module.exports = initChrome
function waitForWSEndpoint(chromeProcess, timeout) {
  return new Promise((resolve, reject) => {
    const rl = readline.createInterface({ input: chromeProcess.stderr });
    let stderr = '';
    const listeners = [
      criHelper.helper.addEventListener(rl, 'line', onLine),
      criHelper.helper.addEventListener(rl, 'close', onClose),
      criHelper.helper.addEventListener(chromeProcess, 'exit', onClose),
      criHelper.helper.addEventListener(chromeProcess, 'error', onClose)
    ];
    const timeoutId = timeout ? setTimeout(onTimeout, timeout) : 0;

    function onClose() {
      cleanup();
      reject(new Error(['Failed to launch chrome!', stderr].join('\n')));
    }

    function onTimeout() {
      cleanup();
      reject(
        new Error(
          `Timed out after ${timeout} ms while trying to connect to Chrome!`
        )
      );
    }

    /**
     * @param {string} line
     */
    function onLine(line) {
      stderr += line + '\n';
      const match = line.match(/^DevTools listening on (ws:\/\/.*)$/);
      if (!match) {
        return;
      }
      cleanup();
      resolve(match[1]);
    }

    function cleanup() {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      criHelper.helper.removeEventListeners(listeners);
      rl.close();
    }
  });
}
