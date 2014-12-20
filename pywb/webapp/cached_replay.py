from rangecache import range_cache
from replay_views import ReplayView


#=================================================================
class CachedReplayView(ReplayView):
    """
    Extension for ReplayView supporting loading via the rangecache
    """
    def replay_capture(self, wbrequest, cdx, cdx_loader, failed_files):
        def get_capture():
            return super(CachedReplayView, self).replay_capture(
                    wbrequest,
                    cdx,
                    cdx_loader,
                    failed_files)

        range_status, range_iter = range_cache(wbrequest,
                                               cdx.get('digest'),
                                               get_capture)
        if range_status and range_iter:
            response = self.response_class(range_status,
                                           range_iter,
                                           wbrequest=wbrequest,
                                           cdx=cdx)
            return response

        return get_capture()

    def _redirect_if_needed(self, wbrequest, cdx):
        if wbrequest.extract_range():
            return None

        return super(CachedReplayView, self)._redirect_if_needed(wbrequest, cdx)
