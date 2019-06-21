const path = require('path');
const fs = require('fs-extra');
const createServer = require('fastify');

const host = '127.0.0.1';
const port = 3030;
const gracefullShutdownTimeout = 50000;
const shutdownOnSignals = ['SIGINT', 'SIGTERM', 'SIGHUP'];
const assetsPath = path.join(__dirname, '..', 'assets');
const httpsSandboxPath = path.join(assetsPath, 'sandbox.html');
const sandboxDirectPath = path.join(assetsPath, 'sandboxDirect.html');
const theyFoundItPath = path.join(assetsPath, 'it.html');

const testPageURL = `http://localhost:${port}/testPage.html`;
const testPageDirectURL = `http://localhost:${port}/testPageDirect.html`;

function promiseResolveReject() {
  const prr = { promise: null, resolve: null, reject: null };
  prr.promise = new Promise((resolve, reject) => {
    let to = setTimeout(
      () => reject(new Error('wait for request timed-out')),
      15000
    );
    prr.resolve = () => {
      clearTimeout(to);
      resolve();
    };
    prr.reject = reason => {
      clearTimeout(to);
      reject(reason);
    };
  });
  return prr;
}

/**
 * @return {Promise<fastify.FastifyInstance>}
 */
async function initServer() {
  const serverOpts = { logger: false };
  const requestSubscribers = new Map();
  const checkReqSubscribers = (pathName, request, reply) => {
    const handler = requestSubscribers.get(pathName);
    if (handler) {
      handler.resolve(request);
      requestSubscribers.delete(pathName);
    }
  };

  const fastify = createServer(serverOpts);

  fastify
    .get(
      '/live/20180803160549wkr_/https://tests.wombat.io/testWorker.js',
      async (request, reply) => {
        const init = `new WBWombat({'prefix': 'http://localhost:${port}/live/20180803160549', 'prefixMod': 'http://localhost:${port}/live/20180803160549wkr_/', 'originalURL': 'https://tests.wombat.io/testWorker.js'});`;
        reply
          .code(200)
          .type('application/javascript; charset=UTF-8')
          .send(
            `self.importScripts('/testWorker.js');(function() { self.importScripts('/wombatWorkers.js'); ${init}})();`
          );
      }
    )
    .get(
      '/live/20180803160549sw_/https://tests.wombat.io/testServiceWorker.js',
      (request, reply) => {
        reply
          .code(200)
          .type('application/javascript; charset=UTF-8')
          .header(
            'Service-Worker-Allowed',
            `${address}/live/20180803160549mp_/https://tests.wombat.io/`
          )
          .send('console.log("hi")');
      }
    )
    .get(
      '/live/20180803160549mp_/https://tests.wombat.io/it',
      async (request, reply) => {
        reply.type('text/html').status(200);
        return fs.createReadStream(theyFoundItPath);
      }
    )
    .get(
      '/live/20180803160549mp_/https://tests.wombat.io/',
      async (request, reply) => {
        reply.type('text/html').status(200);
        return fs.createReadStream(httpsSandboxPath);
      }
    )
    .get(
      '/live/20180803160549mp_/https://tests.direct.wombat.io/',
      (request, reply) => {
        reply
          .type('text/html')
          .status(200)
          .send(fs.createReadStream(sandboxDirectPath));
      }
    )
    .get(
      '/live/20180803160549mp_/https://tests.wombat.io/test',
      async (request, reply) => {
        reply.type('application/json; charset=utf-8').status(200);
        return { headers: request.headers, url: request.raw.originalUrl };
      }
    )
    .decorate('reset', () => {
      const error = new Error('Static Server has been reset');
      for (const prr of requestSubscribers.values()) {
        prr.reject.call(null, error);
      }
      requestSubscribers.clear();
    })
    .decorate('stop', () => {
      fastify.reset();
      return fastify.close();
    })
    .decorate('testPage', testPageURL)
    .decorate('testPageDirect', testPageDirectURL)
    .decorate('waitForRequest', route => {
      let prr = requestSubscribers.get(route);
      if (prr) return prr.promise;
      prr = promiseResolveReject();
      requestSubscribers.set(route, prr);
      return prr.promise;
    })
    .addHook('onRequest', (request, reply, next) => {
      checkReqSubscribers(request.raw.url, request, reply);
      // console.log(`${request.raw.method} ${request.raw.url}`);
      next();
    })
    .register(require('fastify-favicon'))
    .register(require('fastify-static'), {
      root: assetsPath,
      etag: false,
      lastModified: false
    });

  shutdownOnSignals.forEach(signal => {
    process.once(signal, () => {
      setTimeout(() => {
        console.error(
          `received ${signal} signal, terminate process after timeout of ${gracefullShutdownTimeout}ms`
        );
        process.exit(1);
      }, gracefullShutdownTimeout).unref();
      console.log(`received ${signal} signal, triggering close hook`);
      fastify.stop().then(() => {
        process.exit(0);
      });
    });
  });
  const address = await fastify.listen(port, host);
  return fastify;
}

module.exports = initServer;
