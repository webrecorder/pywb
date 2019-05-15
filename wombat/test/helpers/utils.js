const { URL } = require('url');

exports.delay = howMuch =>
  new Promise(resolve => {
    setTimeout(resolve, howMuch);
  });

const extractModifier = /\/live\/[0-9]+([a-z_]+)\/.+/;

exports.extractModifier = rwURL => {
  const purl = new URL(rwURL);
  const result = extractModifier.exec(purl.pathname);
  if (result) return result[1];
  return null;
};

exports.parsedURL = url => new URL(url);
