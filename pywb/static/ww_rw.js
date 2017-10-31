// pywb mini rewriter for injection into web worker scripts

function WBWombat(info) {

    function rewrite_url(url) {
        if (info.prefix) {
            return info.prefix + url;
        } else {
            return url;
        }
    }

    function init_ajax_rewrite() {
        var orig = self.XMLHttpRequest.prototype.open;

        function open_rewritten(method, url, async, user, password) {
            url = rewrite_url(url);

            // defaults to true
            if (async != false) {
                async = true;
            }

            result = orig.call(this, method, url, async, user, password);

            if (url.indexOf("data:") != 0) {
                this.setRequestHeader('X-Pywb-Requested-With', 'XMLHttpRequest');
            }
        }

        self.XMLHttpRequest.prototype.open = open_rewritten;
    }

    init_ajax_rewrite();
}


