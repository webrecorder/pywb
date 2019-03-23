from pywb.warcserver.inputrequest import DirectWSGIInputRequest
from pywb.utils.loaders import extract_client_cookie

from six import iteritems
from six.moves.urllib.parse import urlsplit
import re


try:  # pragma: no cover
    import brotli

    has_brotli = True
except Exception:  # pragma: no cover
    has_brotli = False
    print(
        "Warning: brotli module could not be loaded, will not be able to replay brotli-encoded content"
    )


# =============================================================================
class RewriteInputRequest(DirectWSGIInputRequest):
    RANGE_ARG_RX = re.compile(
        ".*.googlevideo.com/videoplayback.*([&?]range=(\d+)-(\d+))"
    )

    RANGE_HEADER = re.compile("bytes=(\d+)-(\d+)?")

    SKIPPED_HEADERS = {
        "HTTP_X_PYWB_REQUESTED_WITH",
        "HTTP_CONNECTION",
        "HTTP_PROXY_CONNECTION",
        "HTTP_IF_MODIFIED_SINCE",
        "HTTP_IF_UNMODIFIED_SINCE",
    }

    UNDERSCORE_TO_DASH_HEADERS = {"CONTENT_LENGTH", "CONTENT_TYPE"}

    def __init__(self, env, urlkey, url, rewriter):
        super(RewriteInputRequest, self).__init__(env)
        self.urlkey = urlkey
        self.url = url
        self.rewriter = rewriter
        self.extra_cookie = None

        is_proxy = "wsgiprox.proxy_host" in env

        self.splits = urlsplit(self.url) if not is_proxy else None

        self._header_normalizer_fns = {
            "HTTP_HOST": self._normalize_host_header,
            "HTTP_ORIGIN": self._normalize_origin_header,
            "HTTP_X_CSRFTOKEN": self._normalize_x_csrftoken,
            "HTTP_X_FORWARDED_PROTO": self._normalize_x_forward_proto,
            "HTTP_ACCEPT_ENCODING": self._normalize_accept_encoding,
        }

    def get_full_request_uri(self):
        if not self.splits:
            return self.url

        uri = self.splits.path
        if not uri:
            uri = "/"

        if self.splits.query:
            return uri + "?" + self.splits.query

        return uri

    def get_req_headers(self):
        headers = {}

        for name, value in iteritems(self.env):
            if name in self.SKIPPED_HEADERS:
                continue

            header_normalizer = self._header_normalizer_fns.get(name)
            if header_normalizer is not None:
                new_name, new_value = header_normalizer(value)
            else:
                new_name, new_value = self._default_header_normalizer(name, value)

            if new_value:
                headers[new_name] = new_value

        if self.extra_cookie:
            headers["Cookie"] = self.extra_cookie + ";" + headers.get("Cookie", "")

        return headers

    def extract_range(self):
        use_206 = False
        start = None
        end = None
        url = self.url

        range_h = self.env.get("HTTP_RANGE")

        if range_h:
            m = self.RANGE_HEADER.match(range_h)
            if m:
                start = m.group(1)
                end = m.group(2)
                use_206 = True

        else:
            m = self.RANGE_ARG_RX.match(url)
            if m:
                start = m.group(2)
                end = m.group(3)
                url = url[: m.start(1)] + url[m.end(1) :]
                use_206 = False

        if not start:
            return None

        start = int(start)

        if end:
            end = int(end)
        else:
            end = ""

        result = (url, start, end, use_206)
        return result

    def _normalize_host_header(self, value):
        new_value = value
        if self.splits:
            new_value = self.splits.netloc
        return "Host", new_value

    def _normalize_origin_header(self, value):
        new_value = value
        referrer = self.env.get("HTTP_REFERER")
        if referrer:
            splits = urlsplit(referrer)
        else:
            splits = self.splits
        if splits:
            new_value = splits.scheme + "://" + splits.netloc
        return "Origin", new_value

    def _normalize_x_csrftoken(self, value):
        new_value = value
        if self.splits:
            cookie_val = extract_client_cookie(self.env, "csrftoken")
            if cookie_val:
                new_value = cookie_val
        return "X-CSRFToken", new_value

    def _normalize_x_forward_proto(self, value):
        new_value = value
        if self.splits:
            new_value = self.splits.scheme
        return "X-Forwarded-Proto", new_value

    def _normalize_accept_encoding(self, value):
        new_value = value
        if not has_brotli and "br" in value:
            # if brotli not available, remove 'br' from accept-encoding to avoid
            # capture brotli encoded content
            new_value = ",".join(
                [enc for enc in value.split(",") if enc.strip() != "br"]
            )
        return "Accept-Encoding", new_value

    def _default_header_normalizer(self, name, value):
        new_name = name
        new_value = value
        if name in self.UNDERSCORE_TO_DASH_HEADERS:
            new_name = name.title().replace("_", "-")
        elif name.startswith("HTTP_"):
            new_name = name[5:].title().replace("_", "-")
        else:
            new_value = None
        return new_name, new_value
