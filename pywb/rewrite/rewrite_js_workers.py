from pywb.rewrite.content_rewriter import StreamingRewriter, WORKER_MODS

__all__ = ["JSWorkerRewriter"]

INJECT = "(function() { self.importScripts('%s'); new WBWombat(%s); })();"
INIT = "{'prefix': '%s', 'prefixMod': '%s/', 'originalURL': '%s'}"


class JSWorkerRewriter(StreamingRewriter):
    """A simple rewriter for rewriting web or service workers.
    The only rewriting that occurs is the injection of the init code
    for wombatWorkers.js.
    This allows for all them to operate as expected on the live web.
    """

    def __init__(self, url_rewriter, align_to_line=True, first_buff=''):
        """Initialize a new JSWorkerRewriter

        :param UrlRewriter url_rewriter: The url rewriter for this rewrite
        :param bool align_to_line: Should the response stream be aliened to line boundaries
        :param str first_buff: The first string to be added to the rewrite
        :rtype: None
        """
        super(JSWorkerRewriter, self).__init__(url_rewriter, align_to_line, first_buff)
        wb_url = self.url_rewriter.wburl
        if wb_url.mod in WORKER_MODS:
            rw_url = self.url_rewriter.pywb_static_prefix + "wombatWorkers.js"
            prefix = self.url_rewriter.full_prefix
            init = INIT % (prefix, prefix + 'wkrf_', wb_url.url)
            self.first_buff = INJECT % (rw_url, init)
