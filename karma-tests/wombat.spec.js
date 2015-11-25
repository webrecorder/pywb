var WOMBAT_SRC = '../pywb/static/wombat.js';

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
    testFrame.src = '/dummy.html';
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

        // expose chai assertions to the <iframe>
        window.assert = assert;

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
            assert = window.parent.assert;
            reportError = window.parent.reportError;
        });

        try {
            runFunctionInIFrame(testCase.initScript);
        } catch (e) {
            throw new Error('Configuring Wombat failed: ' + e.toString());
        }

        try {
            testFrame.contentWindow.eval(testCase.wombatScript);
            runFunctionInIFrame(function () {
                new window._WBWombat(wbinfo);
            });
        } catch (e) {
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
                };
            },
            wombatScript: wombatScript,
        }, done);
    });

    it('should rewrite document.baseURI', function (done) {
        runWombatTest({
            initScript: function () {
                wbinfo = {
                    wombat_opts: {},
                    prefix: window.location.origin,
                    wombat_ts: '',
                };
            },
            wombatScript: wombatScript,
            testScript: function () {
                var baseURI = document.baseURI;
                if (typeof baseURI !== 'string') {
                    throw new Error('baseURI is not a string');
                }
                assert.equal(baseURI, 'http:///dummy.html');
            },
        }, done);
    });

    it('should rewrite links in dynamically injected <a> tags', function (done) {
        runWombatTest({
            initScript: function () {
                wbinfo = {
                    wombat_opts: {},
                    prefix: window.location.origin,
                    wombat_ts: '',
                };
            },
            wombatScript: wombatScript,
            html: '<a href="foobar.html" id="link">A link</a>',
            testScript: function () {
                var link = document.getElementById('link');
                assert.equal(link.href, 'http:///foobar.html');
            },
        }, done);
    });
});
