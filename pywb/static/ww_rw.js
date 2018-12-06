// pywb mini rewriter for injection into web worker scripts

function WBWombat(info) {
    function maybeResolveURL(origURL) {
        try {
            var resolved = new URL(origURL, info.originalURL);
            return resolved.href;
        } catch (e) {
            return origURL;
        }
    }

    function rewrite_url(url) {
        if (url.indexOf('blob:') === 0) return url;
        if (url && info.originalURL && url.indexOf('/') === 0) {
            url = maybeResolveURL(url);
        }
        if (info.prefix) {
            return info.prefix + url;
        }
        return url;
    }

    function init_ajax_rewrite() {
        var orig = self.XMLHttpRequest.prototype.open;

        function open_rewritten(method, url, async, user, password) {
            url = rewrite_url(url);

            // defaults to true
            if (async != false) {
                async = true;
            }

            var result = orig.call(this, method, url, async, user, password);

            if (url.indexOf('data:') !== 0) {
                this.setRequestHeader('X-Pywb-Requested-With', 'XMLHttpRequest');
            }
        }

        self.XMLHttpRequest.prototype.open = open_rewritten;
    }

    init_ajax_rewrite();

    function rewriteArgs(argsObj) {
        // recreate the original arguments object just with URLs rewritten
        var newArgObj = new Array(argsObj.length);
        for (var i = 0; i < newArgObj.length; i++) {
            var arg = argsObj[i];
            newArgObj[i] = rewrite_url(arg);
        }
        return newArgObj;
    }

    var origImportScripts = self.importScripts;
    self.importScripts = function importScripts() {
        // rewrite the arguments object and call original function via fn.apply
        var rwArgs = rewriteArgs(arguments);
        return origImportScripts.apply(this, rwArgs);
    };

    if (self.fetch != null) {
        // this fetch is Worker.fetch
        var orig_fetch = self.fetch;
        self.fetch = function(input, init_opts) {
            var inputType = typeof(input);
            if (inputType === 'string') {
                input = rewrite_url(input);
            } else if (inputType === 'object' && input.url) {
                var new_url = rewrite_url(input.url);
                if (new_url !== input.url) {
                    input = new Request(new_url, input);
                }
            }
            init_opts = init_opts || {};
            init_opts['credentials'] = 'include';
            return orig_fetch.call(this, input, init_opts);
        };
    }
}
