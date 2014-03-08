#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re

from HTMLParser import HTMLParser, HTMLParseError

from url_rewriter import UrlRewriter
from regex_rewriters import JSRewriter, CSSRewriter

#=================================================================
# HTMLRewriter -- html parser for custom rewriting, also handlers for script and css
#=================================================================
class HTMLRewriter(HTMLParser):
    """
    HTML-Parsing Rewriter
    """

    REWRITE_TAGS = {
        'a':       {'href': ''},
        'applet':  {'codebase': 'oe_',
                    'archive': 'oe_'},
        'area':    {'href': ''},
        'base':    {'href': ''},
        'blockquote': {'cite': ''},
        'body':    {'background': 'im_'},
        'del':     {'cite': ''},
        'embed':   {'src': 'oe_'},
        'head':    {'': ''}, # for head rewriting
        'iframe':  {'src': 'if_'},
        'img':     {'src': 'im_'},
        'ins':     {'cite': ''},
        'input':   {'src': 'im_'},
        'form':    {'action': ''},
        'frame':   {'src': 'fr_'},
        'link':    {'href': 'oe_'},
        'meta':    {'content': ''},
        'object':  {'codebase': 'oe_',
                    'data': 'oe_'},
        'q':       {'cite': ''},
        'ref':     {'href': 'oe_'},
        'script':  {'src': 'js_'},
        'div':     {'data-src' : '',
                    'data-uri' : ''},
        'li':      {'data-src' : '',
                    'data-uri' : ''},
    }

    STATE_TAGS = ['script', 'style']

    HEAD_TAGS = ['html', 'head', 'base', 'link', 'meta', 'title', 'style', 'script', 'object', 'bgsound']

    class AccumBuff:
        def __init__(self):
            self.buff = ''

        def write(self, string):
            self.buff += string


    def __init__(self, url_rewriter, outstream = None, head_insert = None, js_rewriter_class = JSRewriter, css_rewriter_class = CSSRewriter):
        HTMLParser.__init__(self)

        self.url_rewriter = url_rewriter
        self._wb_parse_context = None
        self.out = outstream if outstream else self.AccumBuff()

        self.js_rewriter = js_rewriter_class(url_rewriter)
        self.css_rewriter = css_rewriter_class(url_rewriter)

        self.head_insert = head_insert


    # ===========================
    META_REFRESH_REGEX = re.compile('^[\\d.]+\\s*;\\s*url\\s*=\\s*(.+?)\\s*$', re.IGNORECASE | re.MULTILINE)

    def _rewrite_meta_refresh(self, meta_refresh):
        if not meta_refresh:
            return None

        m = self.META_REFRESH_REGEX.match(meta_refresh)
        if not m:
            return meta_refresh

        try:
            meta_refresh = meta_refresh[:m.start(1)] + self._rewrite_url(m.group(1)) + meta_refresh[m.end(1):]
        except Exception:
            pass

        return meta_refresh
    # ===========================

    def _rewrite_url(self, value, mod = None):
        return self.url_rewriter.rewrite(value, mod) if value else None


    def _rewrite_css(self, css_content):
        return self.css_rewriter.rewrite(css_content) if css_content else None

    def _rewrite_script(self, script_content):
        return self.js_rewriter.rewrite(script_content) if script_content else None

    def has_attr(self, tag_attrs, attr):
        name, value = attr
        for attr_name, attr_value in tag_attrs:
            if attr_name == name:
                return value.lower() == attr_value.lower()
        return False

    def rewrite_tag_attrs(self, tag, tag_attrs, is_start_end):
        # special case: script or style parse context
        if (tag in self.STATE_TAGS) and (self._wb_parse_context == None):
            self._wb_parse_context = tag

        # special case: head insertion, non-head tags
        elif (self.head_insert and (self._wb_parse_context == None) and (tag not in self.HEAD_TAGS)):
            self.out.write(self.head_insert)
            self.head_insert = None

        # attr rewriting
        handler = self.REWRITE_TAGS.get(tag)
        if not handler:
            handler = self.REWRITE_TAGS.get('')

        if not handler:
            return False

        self.out.write('<' + tag)

        for attr in tag_attrs:
            attr_name, attr_value = attr

            # special case: inline JS/event handler
            if (attr_value and attr_value.startswith('javascript:')) or attr_name.startswith('on'):
                attr_value = self._rewrite_script(attr_value)

            # special case: inline CSS/style attribute
            elif attr_name == 'style':
                attr_value = self._rewrite_css(attr_value)

            # special case: meta tag
            elif (tag == 'meta') and (attr_name == 'content'):
                if self.has_attr(tag_attrs, ('http-equiv', 'refresh')):
                    attr_value = self._rewrite_meta_refresh(attr_value)

            else:
                # special case: base tag
                if (tag == 'base') and (attr_name == 'href') and attr_value:
                    self.url_rewriter.set_base_url(attr_value)

                rw_mod = handler.get(attr_name)
                if rw_mod is not None:
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # parser doesn't differentiate between 'attr=""' and just 'attr'
            # 'attr=""' is more common, so use that form
            if attr_value:
                self.out.write(' ' + attr_name + '="' + attr_value + '"')
            else:
                self.out.write(' ' + attr_name + '=""')

        self.out.write('/>' if is_start_end else '>')

        # special case: head tag
        if (self.head_insert) and (self._wb_parse_context == None) and (tag == 'head'):
            self.out.write(self.head_insert)
            self.head_insert = None

        return True


    def parse_data(self, data):
        if self._wb_parse_context == 'script':
            data = self._rewrite_script(data)
        elif self._wb_parse_context == 'style':
            data = self._rewrite_css(data)

        self.out.write(data)

    def rewrite(self, string):
        if not self.out:
            self.out = self.AccumBuff()

        try:
            self.feed(string)
        except HTMLParseError:
            self.out.write(string)

        result = self.out.buff
        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result

    # HTMLParser overrides below
    def close(self):
        if (self._wb_parse_context):
            end_tag = '</' + self._wb_parse_context + '>'
            result = self.rewrite(end_tag)
            if result.endswith(end_tag):
                result = result[:-len(end_tag)]
            self._wb_parse_context = None
        else:
            result = ''

        try:
            HTMLParser.close(self)
        except HTMLParseError:
            pass

        return result

    # called to unescape attrs -- do not unescape!
    def unescape(self, s):
        return s

    def handle_starttag(self, tag, attrs):
        if not self.rewrite_tag_attrs(tag, attrs, False):
            self.out.write(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if not self.rewrite_tag_attrs(tag, attrs, True):
            self.out.write(self.get_starttag_text())

    def handle_endtag(self, tag):
        if (tag == self._wb_parse_context):
            self._wb_parse_context = None

        self.out.write('</' + tag + '>')

    def handle_data(self, data):
        self.parse_data(data)

    def handle_entityref(self, data):
        self.out.write('&' + data + ';')

    def handle_charref(self, data):
        self.out.write('&#' + data + ';')

    def handle_comment(self, data):
        self.out.write('<!--')
        self.parse_data(data)
        self.out.write('-->')

    def handle_decl(self, data):
        self.out.write('<!' + data + '>')

    def handle_pi(self, data):
        self.out.write('<?' + data + '>')

    def unknown_decl(self, data):
        self.out.write('<![')
        self.parse_data(data)
        self.out.write(']>')
