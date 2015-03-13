#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re

from HTMLParser import HTMLParser, HTMLParseError
from urlparse import urlsplit

from url_rewriter import UrlRewriter
from regex_rewriters import JSRewriter, CSSRewriter

import cgi


#=================================================================
class HTMLRewriterMixin(object):
    """
    HTML-Parsing Rewriter for custom rewriting, also delegates
    to rewriters for script and css
    """

    @staticmethod
    def _init_rewrite_tags(defmod):
        rewrite_tags = {
            'a':       {'href': defmod},
            'applet':  {'codebase': 'oe_',
                        'archive': 'oe_'},
            'area':    {'href': defmod},
            'audio':   {'src': 'oe_'},
            'base':    {'href': defmod},
            'blockquote': {'cite': defmod},
            'body':    {'background': 'im_'},
            'button':  {'formaction': defmod},
            'command': {'icon': 'im_'},
            'del':     {'cite': defmod},
            'embed':   {'src': 'oe_'},
            'head':    {'': defmod},  # for head rewriting
            'iframe':  {'src': 'if_'},
            'img':     {'src': 'im_',
                        'srcset': 'im_'},
            'ins':     {'cite': defmod},
            'input':   {'src': 'im_',
                        'formaction': defmod},
            'form':    {'action': defmod},
            'frame':   {'src': 'fr_'},
            'link':    {'href': 'oe_'},
            'meta':    {'content': defmod},
            'object':  {'codebase': 'oe_',
                        'data': 'oe_'},
            'param':   {'value': 'oe_'},
            'q':       {'cite': defmod},
            'ref':     {'href': 'oe_'},
            'script':  {'src': 'js_'},
            'source':  {'src': 'oe_'},
            'video':   {'src': 'oe_',
                        'poster': 'im_'},

            'div':     {'data-src': defmod,
                        'data-uri': defmod},
            'li':      {'data-src': defmod,
                        'data-uri': defmod},
        }

        return rewrite_tags

    STATE_TAGS = ['script', 'style']

    # tags allowed in the <head> of an html document
    HEAD_TAGS = ['html', 'head', 'base', 'link', 'meta',
                 'title', 'style', 'script', 'object', 'bgsound']

    DATA_RW_PROTOCOLS = ('http://', 'https://', '//')

    #===========================
    class AccumBuff:
        def __init__(self):
            self.ls = []

        def write(self, string):
            self.ls.append(bytes(string))

        def getvalue(self):
            return b''.join(self.ls)

    # ===========================
    def __init__(self, url_rewriter,
                 head_insert=None,
                 js_rewriter_class=JSRewriter,
                 css_rewriter_class=CSSRewriter,
                 defmod='',
                 parse_comments=False):

        self.url_rewriter = url_rewriter
        self._wb_parse_context = None

        self.js_rewriter = js_rewriter_class(url_rewriter)
        self.css_rewriter = css_rewriter_class(url_rewriter)

        self.head_insert = head_insert
        self.parse_comments = parse_comments

        self.rewrite_tags = self._init_rewrite_tags(defmod)

        # get opts from urlrewriter
        self.opts = url_rewriter.rewrite_opts

    # ===========================
    META_REFRESH_REGEX = re.compile('^[\\d.]+\\s*;\\s*url\\s*=\\s*(.+?)\\s*$',
                                    re.IGNORECASE | re.MULTILINE)

    def _rewrite_meta_refresh(self, meta_refresh):
        if not meta_refresh:
            return None

        m = self.META_REFRESH_REGEX.match(meta_refresh)
        if not m:
            return meta_refresh

        meta_refresh = (meta_refresh[:m.start(1)] +
                        self._rewrite_url(m.group(1)) +
                        meta_refresh[m.end(1):])

        return meta_refresh

    def _rewrite_base(self, value, mod=''):
        if not value.endswith('/'):
            # check if hostname with no path,
            # eg http://example.com
            if not urlsplit(value).path:
                value += '/'

        base_value = self._rewrite_url(value, mod)

        if self.opts.get('rewrite_base', True):
            value = base_value

        self.url_rewriter = (self.url_rewriter.
                             rebase_rewriter(base_value))
        return value

    def _rewrite_url(self, value, mod=None):
        if value:
            return self.url_rewriter.rewrite(value, mod)
        else:
            return None

    def _rewrite_srcset(self, value, mod=''):
        values = value.split(',')
        values = map(lambda x: self._rewrite_url(x.strip()), values)
        return ', '.join(values)

    def _rewrite_css(self, css_content):
        if css_content:
            return self.css_rewriter.rewrite(css_content)
        else:
            return None

    def _rewrite_script(self, script_content):
        if script_content:
            return self.js_rewriter.rewrite(script_content)
        else:
            return None

    def has_attr(self, tag_attrs, attr):
        name, value = attr
        for attr_name, attr_value in tag_attrs:
            if attr_name == name:
                return value.lower() == attr_value.lower()
        return False

    def _rewrite_tag_attrs(self, tag, tag_attrs):
        # special case: script or style parse context
        if ((tag in self.STATE_TAGS) and not self._wb_parse_context):
            self._wb_parse_context = tag

        # special case: head insertion, non-head tags
        elif (self.head_insert and
              not self._wb_parse_context
              and (tag not in self.HEAD_TAGS)):
            self.out.write(self.head_insert)
            self.head_insert = None

        # attr rewriting
        handler = self.rewrite_tags.get(tag)
        if not handler:
            handler = {}

        self.out.write('<' + tag)

        for attr_name, attr_value in tag_attrs:

            # special case: inline JS/event handler
            if ((attr_value and attr_value.startswith('javascript:'))
                 or attr_name.startswith('on')):
                attr_value = self._rewrite_script(attr_value)

            # special case: inline CSS/style attribute
            elif attr_name == 'style':
                attr_value = self._rewrite_css(attr_value)

            # special case: srcset list
            elif attr_name == 'srcset':
                rw_mod = handler.get(attr_name, '')
                attr_value = self._rewrite_srcset(attr_value, rw_mod)

            # special case: disable crossorigin attr
            # as they may interfere with rewriting semantics
            elif attr_name == 'crossorigin':
                attr_name = '_crossorigin'

            # special case: if rewrite_canon not set,
            # don't rewrite rel=canonical
            elif tag == 'link' and attr_name == 'href':
                if (self.opts.get('rewrite_rel_canon', True) or
                     not self.has_attr(tag_attrs, ('rel', 'canonical'))):
                    rw_mod = handler.get(attr_name)
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # special case: meta tag
            elif (tag == 'meta') and (attr_name == 'content'):
                if self.has_attr(tag_attrs, ('http-equiv', 'refresh')):
                    attr_value = self._rewrite_meta_refresh(attr_value)

            # special case: param value, conditional rewrite
            elif (tag == 'param'):
                if attr_value.startswith(self.DATA_RW_PROTOCOLS):
                    rw_mod = handler.get(attr_name)
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # special case: data- attrs, conditional rewrite
            elif attr_name and attr_value and attr_name.startswith('data-'):
                if attr_value.startswith(self.DATA_RW_PROTOCOLS):
                    rw_mod = 'oe_'
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # special case: base tag
            elif (tag == 'base') and (attr_name == 'href') and attr_value:
                rw_mod = handler.get(attr_name)
                attr_value = self._rewrite_base(attr_value, rw_mod)
            else:
                # rewrite url using tag handler
                rw_mod = handler.get(attr_name)
                if rw_mod is not None:
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # write the attr!
            self._write_attr(attr_name, attr_value)

        return True

    def _rewrite_head(self, start_end):
        # special case: head tag

        # if no insert or in context, no rewrite
        if not self.head_insert or self._wb_parse_context:
            return False

        self.out.write('>')
        self.out.write(self.head_insert)
        self.head_insert = None

        if start_end:
            self.out.write('</head>')

        return True

    def _write_attr(self, name, value):
        # parser doesn't differentiate between 'attr=""' and just 'attr'
        # 'attr=""' is more common, so use that form
        if value:
            self.out.write(' ' + name + '="' + value + '"')
        else:
            self.out.write(' ' + name + '=""')

    def parse_data(self, data):
        if self._wb_parse_context == 'script':
            data = self._rewrite_script(data)
        elif self._wb_parse_context == 'style':
            data = self._rewrite_css(data)

        self.out.write(data)

    def rewrite(self, string):
        self.out = self.AccumBuff()

        self.feed(string)

        result = self.out.getvalue()

        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result

    def close(self):
        self.out = self.AccumBuff()

        self._internal_close()

        result = self.out.getvalue()

        # Clear buffer to create new one for next rewrite()
        self.out = None

        return result

    def _internal_close(self):  # pragma: no cover
        raise NotImplementedError('Base method')


#=================================================================
class HTMLRewriter(HTMLRewriterMixin, HTMLParser):
    PARSETAG = re.compile('[<]')

    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self)
        super(HTMLRewriter, self).__init__(*args, **kwargs)

    def reset(self):
        HTMLParser.reset(self)
        self.interesting = self.PARSETAG

    def clear_cdata_mode(self):
        HTMLParser.clear_cdata_mode(self)
        self.interesting = self.PARSETAG

    def feed(self, string):
        try:
            HTMLParser.feed(self, string)
        except HTMLParseError:  # pragma: no cover
            # only raised in 2.6
            self.out.write(string)

    def _internal_close(self):
        if (self._wb_parse_context):
            end_tag = '</' + self._wb_parse_context + '>'
            self.feed(end_tag)
            self._wb_parse_context = None

        try:
            HTMLParser.close(self)
        except HTMLParseError:  # pragma: no cover
            # only raised in 2.6
            pass

    # called to unescape attrs -- do not unescape!
    def unescape(self, s):
        return s

    def handle_starttag(self, tag, attrs):
        self._rewrite_tag_attrs(tag, attrs)

        if tag != 'head' or not self._rewrite_head(False):
            self.out.write('>')

    def handle_startendtag(self, tag, attrs):
        self._rewrite_tag_attrs(tag, attrs)

        if tag != 'head' or not self._rewrite_head(True):
            self.out.write('/>')

    def handle_endtag(self, tag):
        if (tag == self._wb_parse_context):
            self._wb_parse_context = None

        self.out.write('</' + tag + '>')

    def handle_data(self, data):
        self.parse_data(data)

    # overriding regex so that these are no longer called
    #def handle_entityref(self, data):
    #    self.out.write('&' + data + ';')
    #
    #def handle_charref(self, data):
    #    self.out.write('&#' + data + ';')

    def handle_comment(self, data):
        self.out.write('<!--')
        if self.parse_comments:
            data = self._rewrite_script(data)
            self.out.write(data)
        else:
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
