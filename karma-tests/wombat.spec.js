var DEFAULT_TIMEOUT = 20000;

// creates a new document in an <iframe> and runs
// a WombatJS test case in it.
//
// A new <iframe> is used for each test so that each
// case is run with fresh Document and Window objects,
// since Wombat monkey-patches many Document and Window
// functions
//
function runWombatTest(testCase, done) {
    // create an <iframe>
    var testFrame = document.createElement('iframe');
    testFrame.src = '/base/karma-tests/dummy.html';
    document.body.appendChild(testFrame);

    testFrame.contentWindow.addEventListener('load', function () {
        var testDocument = testFrame.contentDocument;

        function runFunctionInIFrame(func) {
            testFrame.contentWindow.eval('(' + func.toString() + ')()');
        }

        // expose an error reporting function to the <iframe>
        window.reportError = function(ex) {
            done(new Error(ex));
        };

        // expose utility methods for assertion testing in tests.
        // (We used to expose chai asserts here but Karma's default
        //  error reporter replaces URLs in exception messages with
        //  the corresponding file paths, which is unhelpful for us
        //  since assert.equal() will often be called with URLs in our tests)
        window.assert = {
            equal: function (a, b) {
                if (a !== b) {
                    console.error('Mismatch between', a, 'and', b);
                    throw new Error('AssertionError');
                }
            }
        };

        runFunctionInIFrame(function () {
            // re-assign the iframe's console object to the parent window's
            // console so that messages are intercepted by Karma
            // and output to wherever it is configured to send
            // console logs (typically stdout)
            console = window.parent.console;
            window.onerror = function (message, url, line, col, error) {
                if (error) {
                    console.log(error.stack);
                }
                reportError(new Error(message));
            };

            // expose chai's assertion testing API to the test script
            window.assert = window.parent.assert;
            window.reportError = window.parent.reportError;

            // helpers which check whether DOM property overrides are supported
            // in the current browser
            window.domTests = {
                areDOMPropertiesConfigurable: function () {
                    var descriptor = Object.getOwnPropertyDescriptor(Node.prototype, 'baseURI');
                    if (descriptor && !descriptor.configurable) {
                        return false;
                    } else {
                        return true;
                    }
                }
            };
        });

        try {
            runFunctionInIFrame(testCase.initScript);
        } catch (e) {
            throw new Error('Configuring Wombat failed: ' + e.toString());
        }

        try {
            testFrame.contentWindow.eval(testCase.wombatScript);
            runFunctionInIFrame(function () {
                new window._WBWombat(window, wbinfo);
            });
        } catch (e) {
            console.error(e.stack);
            throw new Error('Initializing WombatJS failed: ' + e.toString());
        }

        if (testCase.html) {
            testDocument.body.innerHTML = testCase.html;
        }

        if (testCase.testScript) {
            try {
                runFunctionInIFrame(testCase.testScript);
            } catch (e) {
                throw new Error('Test script failed: ' + e.toString());
            }
        }

        testFrame.remove();
        done();
    });
}

describe('WombatJS', function () {
    this.timeout(DEFAULT_TIMEOUT);

    var wombatScript;

    before(function (done) {
        // load the source of the WombatJS content
        // rewriting script
        var req = new XMLHttpRequest();
        req.open('GET', '/base/pywb/static/wombat.js');
        req.onload = function () {
            wombatScript = req.responseText;
            done();
        };
        req.send();
    });

    it('should load', function (done) {
        runWombatTest({
            initScript: function () {
                wbinfo = {
                    wombat_opts: {},
                    wombat_ts: '',
                    is_live: false,
                    top_url: ''
                };
            },
            wombatScript: wombatScript,
        }, done);
    });

    describe('anchor rewriting', function () {
        var config;
        beforeEach(function () {
            config = {
                initScript: function () {
                    wbinfo = {
                        wombat_opts: {},
                        wombat_scheme: 'http',
                        prefix: window.location.origin,
                        wombat_ts: '',
                        is_live: false,
                        top_url: ''
                    };
                },
                wombatScript: wombatScript,
                html: '<a href="foobar.html" id="link">A link</a>',
            };
        });

        it('should rewrite links in dynamically injected <a> tags', function (done) {
            config.testScript = function () {
                if (domTests.areDOMPropertiesConfigurable()) {
                    var link = document.getElementById('link');
                    assert.equal(link.href, 'http:///base/karma-tests/foobar.html');
                }
            };

            runWombatTest(config, done);
        });

        it('toString() should return the rewritten URL', function (done) {
            config.testScript = function () {
                if (domTests.areDOMPropertiesConfigurable()) {
                    var link = document.getElementById('link');
                    assert.equal(link.href, link.toString());
                }
            };
            runWombatTest(config, done);
        });
    });

    describe('base URL overrides', function () {
        it('document.baseURI should return the original URL', function (done) {
            runWombatTest({
                initScript: function () {
                    wbinfo = {
                        wombat_opts: {},
                        prefix: window.location.origin,
                        wombat_ts: '',
                        wombat_scheme: 'http',
                        is_live: false,
                        top_url: ''
                    };
                },
                wombatScript: wombatScript,
                testScript: function () {
                    var baseURI = document.baseURI;
                    if (typeof baseURI !== 'string') {
                        throw new Error('baseURI is not a string');
                    }
                    if (domTests.areDOMPropertiesConfigurable()) {
                        assert.equal(baseURI, 'http:///base/karma-tests/dummy.html');
                    }
                },
            }, done);
        });

        it('should allow base.href to be assigned', function (done) {
            runWombatTest({
                initScript: function () {
                    wbinfo = {
                        wombat_opts: {},
                        wombat_scheme: 'http',
                        is_live: false,
                        top_url: ''
                    };
                },
                wombatScript: wombatScript,
                testScript: function () {
                    'use strict';
                    var baseElement = document.createElement('base');
                    baseElement.href = 'http://foobar.com/base';
                    assert.equal(baseElement.href, 'http://foobar.com/base');
                },
            }, done);
        });
    });
});
