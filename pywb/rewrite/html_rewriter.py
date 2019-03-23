#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import traceback
from collections import defaultdict

import six.moves.html_parser
from six.moves.html_parser import HTMLParser
from six.moves.urllib.parse import urljoin, urlsplit, urlunsplit

from pywb.rewrite.content_rewriter import StreamingRewriter
from pywb.rewrite.regex_rewriters import CSSRewriter, JSRewriter

try:
    orig_unescape = six.moves.html_parser.unescape
    six.moves.html_parser.unescape = lambda x: x
except Exception:
    orig_unescape = None

try:
    import _markupbase as markupbase
except Exception:
    import markupbase as markupbase

# ensure invalid cond ending ']-->' closing decl
# is treated same as ']>'
markupbase._msmarkedsectionclose = re.compile(r"]\s*-{0,2}>")


class AccumBuff:
    __slots__ = ("ls",)

    def __init__(self):
        self.ls = []

    def write(self, string):
        self.ls.append(string)

    def getvalue(self):
        return "".join(self.ls)


# =================================================================
class HTMLParsingRewriter(HTMLParser):
    # tags allowed in the <head> of an html document
    HEAD_TAGS = [
        "html",
        "head",
        "base",
        "link",
        "meta",
        "title",
        "style",
        "script",
        "object",
        "bgsound",
    ]

    BEFORE_HEAD_TAGS = ["html", "head"]

    DATA_RW_PROTOCOLS = ("http://", "https://", "//")

    PRELOAD_TYPES = {
        "script": "js_",
        "worker": "js_",
        "style": "cs_",
        "image": "im_",
        "document": "if_",
        "fetch": "mp_",
        "font": "oe_",
        "audio": "oe_",
        "video": "oe_",
        "embed": "oe_",
        "object": "oe_",
        "track": "oe_",
    }

    META_REFRESH_REGEX = re.compile(
        "^[\\d.]+\\s*;\\s*url\\s*=\\s*(.+?)\\s*$", re.IGNORECASE | re.MULTILINE
    )

    ADD_WINDOW = re.compile("(?<![.])(WB_wombat_)")

    SRCSET_REGEX = re.compile("\s*(\S*\s+[\d\.]+[wx]),|(?:\s*,(?:\s+|(?=https?:)))")

    PARSETAG = re.compile("[<]")

    @staticmethod
    def _init_rewrite_tags(defmod):
        """

        :param str defmod:
        :return:
        :rtype: dict[str, dict[str, str]]
        """
        rewrite_tags = {
            "a": {"href": defmod},
            "applet": {"codebase": "oe_", "archive": "oe_"},
            "area": {"href": defmod},
            "audio": {"src": "oe_"},
            "base": {"href": defmod},
            "blockquote": {"cite": defmod},
            "body": {"background": "im_"},
            "button": {"formaction": defmod},
            "command": {"icon": "im_"},
            "del": {"cite": defmod},
            "embed": {"src": "oe_"},
            "head": {"": defmod},  # for head rewriting
            "iframe": {"src": "if_"},
            "image": {"src": "im_", "xlink:href": "im_"},
            "img": {"src": "im_", "srcset": "im_"},
            "ins": {"cite": defmod},
            "input": {"src": "im_", "formaction": defmod},
            "form": {"action": defmod},
            "frame": {"src": "fr_"},
            "link": {"href": "oe_"},
            "meta": {"content": defmod},
            "object": {"codebase": "oe_", "data": "oe_"},
            "param": {"value": "oe_"},
            "q": {"cite": defmod},
            "ref": {"href": "oe_"},
            "script": {
                "src": "js_",
                "xlink:href": "js_",
            },  # covers both HTML and SVG script tags
            "source": {"src": "oe_"},
            "video": {"src": "oe_", "poster": "im_"},
        }

        return rewrite_tags

    def __init__(
        self,
        url_rewriter,
        head_insert=None,
        js_rewriter=None,
        css_rewriter=None,
        url="",
        defmod="",
        parse_comments=False,
        charset="utf-8",
    ):
        if sys.version_info > (3, 4):  # pragma: no cover
            super(HTMLParsingRewriter, self).__init__(convert_charrefs=False)
        else:  # pragma: no cover
            super(HTMLParsingRewriter, self).__init__()

        self.charset = charset
        self._wb_parse_context = None
        self.url_rewriter = url_rewriter
        self.js_rewriter = js_rewriter
        self.css_rewriter = css_rewriter
        self.head_insert = head_insert
        self.parse_comments = parse_comments
        self.orig_url = url
        self.defmod = defmod
        self.rewrite_tags = self._init_rewrite_tags(defmod)

        # get opts from urlrewriter
        self.opts = url_rewriter.rewrite_opts

        self.force_decl = self.opts.get("force_html_decl", None)

        self._tags_to_attr_rewrite_fns = {
            "link": self._init_tag_attr_rewrite_lookup(href=self._rewrite_link_href),
            "meta": self._init_tag_attr_rewrite_lookup(
                content=self._rewrite_meta_content
            ),
            "base": self._init_tag_attr_rewrite_lookup(href=self._rewrite_base_href),
            "script": self._init_tag_attr_rewrite_lookup(src=self._rewrite_script_src),
            "param": defaultdict(self._rewrite_param_tag),
        }

        self._attr_rewrite_fns = self._init_tag_attr_rewrite_lookup()

        self.parsed_any = False
        self.has_base = False
        self.out = None

    def _init_tag_attr_rewrite_lookup(self, **kwargs):
        tag_attr_rewrite_fns = {
            "href": self._rewrite_href_attr,
            "srcset": self._rewrite_srcset_attr,
            "crossorigin": self._attr_name_prefix_rewrite,
            "integrity": self._attr_name_prefix_rewrite,
            "style": self._rewrite_style_attr,
            "background": self._rewrite_background_attr,
        }
        tag_attr_rewrite_fns.update(**kwargs)
        return tag_attr_rewrite_fns

    def rewrite(self, string):
        self.out = AccumBuff()

        self.feed(string)

        result = self.out.getvalue()

        # track that something was parsed
        self.parsed_any = self.parsed_any or bool(string)

        # Clear buffer to create new one for next rewrite()
        self.out = None

        if self.force_decl:
            result = self.force_decl + "\n" + result
            self.force_decl = None

        return result

    def end(self):
        self.out = AccumBuff()

        self._internal_close()

        result = self.out.getvalue()

        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result

    def parse_data(self, data):
        if self._wb_parse_context == "script":
            data = self._rewrite_script(data)
        elif self._wb_parse_context == "style":
            data = self._rewrite_css(data)

        self.out.write(data)

    def try_unescape(self, value):
        if not value.startswith("http"):
            return value

        try:
            if orig_unescape:
                new_value = orig_unescape(value)
            else:
                new_value = super(HTMLParsingRewriter, self).unescape(value)
        except Exception as e:
            return value

        return new_value

    def has_attr(self, tag_attrs, attr):
        name, value = attr
        attr_value = self.get_attr(tag_attrs, name)
        if attr_value is None:
            return False

        return attr_value.lower() == value.lower()

    def get_attr(self, tag_attrs, match_name):
        for attr_name, attr_value in tag_attrs:
            if attr_name == match_name:
                return attr_value

        return None

    def reset(self):
        super(HTMLParsingRewriter, self).reset()
        self.interesting = self.PARSETAG

    def clear_cdata_mode(self):
        super(HTMLParsingRewriter, self).clear_cdata_mode()
        self.interesting = self.PARSETAG

    def feed(self, string):
        try:
            super(HTMLParsingRewriter, self).feed(string)
        except Exception as e:  # pragma: no cover
            traceback.print_exc()
            self.out.write(string)

    # called to unescape attrs -- do not unescape!
    def unescape(self, s):
        return s

    def handle_starttag(self, tag, attrs):
        self._rewrite_tag_attrs(tag, attrs)

        if tag != "head" or not self._rewrite_head(False):
            self.out.write(">")

    def handle_startendtag(self, tag, attrs):
        self._rewrite_tag_attrs(tag, attrs, False)

        if tag != "head" or not self._rewrite_head(True):
            self.out.write("/>")

    def handle_endtag(self, tag):
        if tag == self._wb_parse_context:
            self._wb_parse_context = None

        if tag == "head" and not self.has_base:
            self._write_default_base()

        self.out.write("</" + tag + ">")

    def handle_data(self, data):
        self.parse_data(data)

    def handle_comment(self, data):
        self.out.write("<!--")
        if self.parse_comments:
            # data = self._rewrite_script(data)

            # Rewrite with seperate HTMLRewriter
            comment_rewriter = HTMLRewriter(
                self.url_rewriter,
                head_insert=self.head_insert,
                js_rewriter=self.js_rewriter,
                css_rewriter=self.css_rewriter,
                url=self.orig_url,
                defmod=self.defmod,
                parse_comments=self.parse_comments,
                charset=self.charset,
            )
            data = comment_rewriter.rewrite_complete(data)
            self.out.write(data)
        else:
            self.parse_data(data)
        self.out.write("-->")

    def handle_decl(self, data):
        self.out.write("<!" + data + ">")
        self.force_decl = None

    def handle_pi(self, data):
        self.out.write("<?" + data + ">")

    def unknown_decl(self, data):
        self.out.write("<![")
        self.parse_data(data)
        self.out.write("]>")

    def error(self, message):
        print(message)

    def _rewrite_meta_refresh(self, meta_refresh):
        """

        :param meta_refresh:
        :return:
        :rtype: str
        """
        if not meta_refresh:
            return ""

        m = self.META_REFRESH_REGEX.match(meta_refresh)
        if not m:
            return meta_refresh

        meta_refresh = (
            meta_refresh[: m.start(1)]
            + self._rewrite_url(m.group(1))
            + meta_refresh[m.end(1) :]
        )

        return meta_refresh

    def _rewrite_base(self, url, mod=""):
        """

        :param url:
        :param mod:
        :return:
        :rtype: str
        """
        if not url:
            return ""

        url = self._ensure_url_has_path(url)

        base_url = self._rewrite_url(url, mod)

        self.url_rewriter = self.url_rewriter.rebase_rewriter(url)

        self.has_base = True

        if self.opts.get("rewrite_base", True):
            return base_url
        return url

    def _write_default_base(self):
        if not self.orig_url:
            return

        base_url = self._ensure_url_has_path(self.orig_url)

        # write default base only if different from implicit base
        if self.orig_url != base_url:
            base_url = self._rewrite_url(base_url)
            self.out.write('<base href="{0}"/>'.format(base_url))

        self.has_base = True

    def _ensure_url_has_path(self, url):
        """ ensure the url has a path component
        eg. http://example.com#abc converted to http://example.com/#abc
        """
        inx = url.find("://")
        if inx > 0:
            rest = url[inx + 3 :]
        elif url.startswith("//"):
            rest = url[2:]
        else:
            rest = url

        if "/" in rest:
            return url

        scheme, netloc, path, query, frag = urlsplit(url)
        if not path:
            path = "/"

        url = urlunsplit((scheme, netloc, path, query, frag))
        return url

    def _rewrite_url(self, value, mod=None, force_abs=False):
        if not value:
            return ""

        value = value.strip()
        if not value:
            return ""

        orig_value = value

        # if not utf-8, then stream was encoded as iso-8859-1, and need to reencode
        # into correct charset
        if self.charset != "utf-8" and self.charset != "iso-8859-1":
            try:
                value = value.encode("iso-8859-1").decode(self.charset)
            except Exception:
                pass

        unesc_value = self.try_unescape(value)
        rewritten_value = self.url_rewriter.rewrite(unesc_value, mod, force_abs)

        # if no rewriting has occured, ensure we return original, not reencoded value
        if rewritten_value == value:
            return orig_value

        if unesc_value != value and rewritten_value != unesc_value:
            rewritten_value = rewritten_value.replace(unesc_value, value)

        return rewritten_value

    def _rewrite_srcset(self, value, mod=""):
        if not value:
            return ""
        values = [
            self._rewrite_url(url.strip())
            for url in re.split(self.SRCSET_REGEX, value)
            if url
        ]
        return ", ".join(values)

    def _rewrite_css(self, css_content):
        if css_content:
            return self.css_rewriter.rewrite_complete(css_content)
        return ""

    def _rewrite_script(self, script_content, inline_attr=False):
        if not script_content:
            return ""

        content = self.js_rewriter.rewrite_complete(
            script_content, inline_attr=inline_attr
        )

        if inline_attr:
            return self.ADD_WINDOW.sub("window.\\1", content)

        return content

    def _default_attr_rewrite(self, handler, tag_attrs, attr_name, attr_value):
        rw_value = attr_value
        # special case: data- attrs, conditional rewrite
        if attr_name and attr_value and attr_name.startswith("data-"):
            if attr_value.startswith(self.DATA_RW_PROTOCOLS):
                rw_mod = "oe_"
                rw_value = self._rewrite_url(attr_value, rw_mod)
        # rewrite url using tag handler
        else:
            rw_mod = handler.get(attr_name)
            if rw_mod is not None:
                rw_value = self._rewrite_url(attr_value, rw_mod)

        return attr_name, rw_value

    def _rewrite_background_attr(self, rw_mod, tag_attrs, attr_name, attr_value):
        return attr_name, self._rewrite_url(attr_value, "im_")

    def _rewrite_style_attr(self, handler, tag_attrs, attr_name, attr_value):
        return attr_name, self._rewrite_css(attr_value)

    def _attr_name_prefix_rewrite(self, handler, tag_attrs, attr_name, attr_value):
        return "_" + attr_name, attr_value

    def _rewrite_href_attr(self, handler, tag_attrs, attr_name, attr_value):
        return attr_name, self._rewrite_url(attr_value, self.defmod)

    def _rewrite_srcset_attr(self, handler, tag_attrs, attr_name, attr_value):
        rw_value = attr_value
        if attr_value:
            values = [
                self._rewrite_url(url.strip())
                for url in re.split(self.SRCSET_REGEX, attr_value)
                if url
            ]
            rw_value = ", ".join(values)
        return attr_name, rw_value

    def _rewrite_link_href(self, handler, tag_attrs, attr_name, attr_value):
        rw_mod = handler.get(attr_name)
        # rel="canonical"
        rel = self.get_attr(tag_attrs, "rel")
        if rel is not None:
            if rel == "canonical":
                if self.opts.get("rewrite_rel_canon", True):
                    rw_value = self._rewrite_url(attr_value, rw_mod)
                else:
                    # resolve relative rel=canonical URLs so that they
                    # refer to the same absolute URL as on the original
                    # page (see https://github.com/hypothesis/via/issues/65
                    # for context)
                    rw_value = urljoin(self.orig_url, attr_value)
                return attr_name, rw_value

            # find proper mod for preload
            elif rel == "preload":
                preload = self.get_attr(tag_attrs, "as")
                rw_mod = self.PRELOAD_TYPES.get(preload, rw_mod)

            # for html imports with an optional as (google exclusive)
            elif rel == "import":
                rw_mod = "mp_"

            elif rel == "stylesheet":
                rw_mod = "cs_"

        return attr_name, self._rewrite_url(attr_value, rw_mod)

    def _rewrite_meta_content(self, handler, tag_attrs, attr_name, attr_value):
        rw_name = attr_name
        rw_value = attr_value
        if self.has_attr(tag_attrs, ("http-equiv", "refresh")):
            rw_value = self._rewrite_meta_refresh(attr_value)
        elif self.has_attr(tag_attrs, ("http-equiv", "content-security-policy")):
            rw_name = "_" + attr_name
        elif self.has_attr(tag_attrs, ("name", "referrer")):
            rw_value = "no-referrer-when-downgrade"
        elif attr_value.startswith(self.DATA_RW_PROTOCOLS):
            rw_mod = handler.get(attr_name)
            rw_value = self._rewrite_url(attr_value, rw_mod)
        return rw_name, rw_value

    def _rewrite_param_tag(self, handler, tag_attrs, attr_name, attr_value):
        if not attr_value.startswith(self.DATA_RW_PROTOCOLS):
            return self._default_attr_rewrite(handler, tag_attrs, attr_name, attr_value)
        rw_mod = handler.get(attr_name)
        return attr_name, self._rewrite_url(attr_value, rw_mod)

    def _rewrite_base_href(self, handler, tag_attrs, attr_name, attr_value):
        rw_mod = handler.get(attr_name)
        rw_value = self._rewrite_base(attr_value, rw_mod)
        return attr_name, rw_value

    def _rewrite_script_src(self, handler, tag_attrs, attr_name, attr_value):
        rw_mod = handler.get(attr_name)
        ov = attr_value
        rw_value = self._rewrite_url(attr_value, rw_mod)
        if rw_value == ov and not ov.startswith(
            self.url_rewriter.NO_REWRITE_URI_PREFIX
        ):
            # URL not skipped, likely src='js/....', forcing abs to make sure, cause PHP MIME(JS) === HTML
            rw_value = self._rewrite_url(rw_value, rw_mod, True)
            self._write_attr("__wb_orig_src", ov, empty_attr=None)
        return attr_name, rw_value

    def _is_inline_js(self, attr_name, attr_value):
        return (attr_value and attr_value.startswith("javascript:")) or (
            attr_name.startswith("on") and attr_name[2:3] != "-"
        )

    def _rewrite_tag_attrs(self, tag, tag_attrs, set_parsing_context=True):
        """Rewrite a tags attributes.

        If set_parsing_context is false then the parsing context will not set.
        If the head insert has not been added to the HTML being rewritten, there
        is no parsing context and the tag is not in BEFORE_HEAD_TAGS then the
        head_insert will be "inserted" and set to None

        :param str tag: The name of the tag to be rewritten
        :param list[tuple[str, str]] tag_attrs: A list of tuples representing
        the tags attributes
        :param bool set_parsing_context: Boolean indicating if the parsing
        context should be set
        :return: True
        :rtype: bool
        """
        # special case: head insertion, before-head tags
        if (
            self.head_insert
            and not self._wb_parse_context
            and (tag not in self.BEFORE_HEAD_TAGS)
        ):
            self.out.write(self.head_insert)
            self.head_insert = None

        if set_parsing_context:
            self._set_parse_context(tag, tag_attrs)

        # attr rewriting
        handler = self.rewrite_tags.get(tag, {})

        self.out.write("<" + tag)

        attr_rewrite_fns = self._tags_to_attr_rewrite_fns.get(
            tag, self._attr_rewrite_fns
        )

        for attr_name, attr_value in tag_attrs:
            empty_attr = False
            if attr_value is None:
                attr_value = ""
                empty_attr = True

            # special case: inline JS/event handler
            if self._is_inline_js(attr_name, attr_value):
                rw_name = attr_name
                rw_value = self._rewrite_script(attr_value, True)
            else:
                rewrite_fn = attr_rewrite_fns.get(attr_name, self._default_attr_rewrite)
                rw_name, rw_value = rewrite_fn(handler, tag_attrs, attr_name, attr_value)

            self._write_attr(rw_name, rw_value, empty_attr)

        return True

    def _set_parse_context(self, tag, tag_attrs):
        # special case: script or style parse context
        if not self._wb_parse_context:
            if tag == "style":
                self._wb_parse_context = "style"

            elif tag == "script" and self._allow_js_type(tag_attrs):
                self._wb_parse_context = "script"

    def _allow_js_type(self, tag_attrs):
        type_value = self.get_attr(tag_attrs, "type")

        if not type_value:
            return True

        tv_l = type_value.lower()

        if "javascript" in tv_l:
            return True

        return "ecmascript" in tv_l

    def _rewrite_head(self, start_end):
        # special case: head tag

        # if no insert or in context, no rewrite
        if not self.head_insert or self._wb_parse_context:
            return False

        self.out.write(">")
        self.out.write(self.head_insert)
        self.head_insert = None

        if start_end:
            if not self.has_base:
                self._write_default_base()

            self.out.write("</head>")

        return True

    def _write_attr(self, name, value, empty_attr):
        # if empty_attr is set, just write 'attr'!
        if empty_attr:
            self.out.write(" " + name)

        # write with value, if set
        elif value:

            self.out.write(" " + name + '="' + value.replace('"', "&quot;") + '"')

        # otherwise, 'attr=""' is more common, so use that form
        else:
            self.out.write(" " + name + '=""')

    def _internal_close(self):
        if self._wb_parse_context:
            end_tag = "</" + self._wb_parse_context + ">"
            self.feed(end_tag)
            self._wb_parse_context = None

        # if haven't insert head_insert, but wrote some content
        # out, then insert head_insert now
        if self.head_insert and self.parsed_any:
            self.out.write(self.head_insert)
            self.head_insert = None

        try:
            super(HTMLParsingRewriter, self).close()
        except Exception:  # pragma: no cover
            # only raised in 2.6
            pass


# =================================================================
class HTMLRewriter(StreamingRewriter):
    def __init__(
        self,
        url_rewriter,
        head_insert=None,
        js_rewriter_class=None,
        js_rewriter=None,
        css_rewriter=None,
        css_rewriter_class=None,
        url="",
        defmod="",
        parse_comments=False,
        charset="utf-8",
    ):
        super(HTMLRewriter, self).__init__(url_rewriter, False)

        if js_rewriter:
            self.js_rewriter = js_rewriter
        elif js_rewriter_class:
            self.js_rewriter = js_rewriter_class(url_rewriter)
        else:
            self.js_rewriter = JSRewriter(url_rewriter)

        if css_rewriter:
            self.css_rewriter = css_rewriter
        elif css_rewriter_class:
            self.css_rewriter = css_rewriter_class(url_rewriter)
        else:
            self.css_rewriter = CSSRewriter(url_rewriter)

        self.parsing_rewriter = HTMLParsingRewriter(
            url_rewriter,
            head_insert,
            self.js_rewriter,
            self.css_rewriter,
            url,
            defmod,
            parse_comments,
            charset,
        )

    def rewrite(self, string):
        return self.parsing_rewriter.rewrite(string)

    def final_read(self):
        return self.parsing_rewriter.end()

    def close(self):
        return self.final_read()

