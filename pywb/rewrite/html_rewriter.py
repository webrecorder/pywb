#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys

from six.moves.html_parser import HTMLParser
from six.moves.urllib.parse import urljoin, urlsplit, urlunsplit


from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.regex_rewriters import JSRewriter, CSSRewriter

import six.moves.html_parser
six.moves.html_parser.unescape = lambda x: x
from six import text_type


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
            'image':   {'src': 'im_', 'xlink:href': 'im_'},
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
        }

        return rewrite_tags

    STATE_TAGS = ['script', 'style']

    # tags allowed in the <head> of an html document
    HEAD_TAGS = ['html', 'head', 'base', 'link', 'meta',
                 'title', 'style', 'script', 'object', 'bgsound']

    BEFORE_HEAD_TAGS = ['html', 'head']

    DATA_RW_PROTOCOLS = ('http://', 'https://', '//')

    #===========================
    class AccumBuff:
        def __init__(self):
            self.ls = []

        def write(self, string):
            self.ls.append(string)

        def getvalue(self):
            return ''.join(self.ls)


    # ===========================
    def __init__(self, url_rewriter,
                 head_insert=None,
                 js_rewriter_class=JSRewriter,
                 css_rewriter_class=CSSRewriter,
                 url = '',
                 defmod='',
                 parse_comments=False):

        self.url_rewriter = url_rewriter
        self._wb_parse_context = None

        self.js_rewriter = js_rewriter_class(url_rewriter)
        self.css_rewriter = css_rewriter_class(url_rewriter)

        self.head_insert = head_insert
        self.parse_comments = parse_comments

        self.orig_url = url
        self.defmod = defmod
        self.rewrite_tags = self._init_rewrite_tags(defmod)

        # get opts from urlrewriter
        self.opts = url_rewriter.rewrite_opts

        self.force_decl = self.opts.get('force_html_decl', None)

        self.parsed_any = False
        self.has_base = False

    # ===========================
    META_REFRESH_REGEX = re.compile('^[\\d.]+\\s*;\\s*url\\s*=\\s*(.+?)\\s*$',
                                    re.IGNORECASE | re.MULTILINE)

    ADD_WINDOW = re.compile('(?<![.])(WB_wombat_)')

    def _rewrite_meta_refresh(self, meta_refresh):
        if not meta_refresh:
            return ''

        m = self.META_REFRESH_REGEX.match(meta_refresh)
        if not m:
            return meta_refresh

        meta_refresh = (meta_refresh[:m.start(1)] +
                        self._rewrite_url(m.group(1)) +
                        meta_refresh[m.end(1):])

        return meta_refresh

    def _rewrite_base(self, url, mod=''):
        if not url:
            return ''

        url = self._ensure_url_has_path(url)

        base_url = self._rewrite_url(url, mod)

        self.url_rewriter = (self.url_rewriter.
                             rebase_rewriter(base_url))
        self.has_base = True

        if self.opts.get('rewrite_base', True):
            return base_url
        else:
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
        inx = url.find('://')
        if inx > 0:
            rest = url[inx + 3:]
        elif url.startswith('//'):
            rest = url[2:]
        else:
            rest = url

        if '/' in rest:
            return url

        scheme, netloc, path, query, frag = urlsplit(url)
        if not path:
            path = '/'

        url = urlunsplit((scheme, netloc, path, query, frag))
        return url

    def _rewrite_url(self, value, mod=None):
        if not value:
            return ''

        value = value.strip()
        if not value:
            return ''

        value = self.try_unescape(value)
        return self.url_rewriter.rewrite(value, mod)

    def try_unescape(self, value):
        if not value.startswith('http'):
            return value

        try:
            new_value = HTMLParser.unescape(self, value)
        except:
            return value

        if value != new_value:
            # ensure utf-8 encoded to avoid %-encoding query here
            if isinstance(new_value, text_type):
                new_value = new_value.encode('utf-8')

        return new_value

    def _rewrite_srcset(self, value, mod=''):
        if not value:
            return ''

        values = value.split(',')
        values = [self._rewrite_url(v.strip()) for v in values]
        return ', '.join(values)

    def _rewrite_css(self, css_content):
        if css_content:
            return self.css_rewriter.rewrite(css_content)
        else:
            return ''

    def _rewrite_script(self, script_content, ensure_window=False):
        if not script_content:
            return ''

        content = self.js_rewriter.rewrite(script_content)
        if ensure_window:
            content = self.ADD_WINDOW.sub('window.\\1', content)

        return content

    def has_attr(self, tag_attrs, attr):
        name, value = attr
        for attr_name, attr_value in tag_attrs:
            if attr_name == name:
                return value.lower() == attr_value.lower()
        return False

    def _rewrite_tag_attrs(self, tag, tag_attrs):
        # special case: head insertion, before-head tags
        if (self.head_insert and
              not self._wb_parse_context
              and (tag not in self.BEFORE_HEAD_TAGS)):
            self.out.write(self.head_insert)
            self.head_insert = None

        # special case: script or style parse context
        if ((tag in self.STATE_TAGS) and not self._wb_parse_context):
            self._wb_parse_context = tag

        # attr rewriting
        handler = self.rewrite_tags.get(tag)
        if not handler:
            handler = {}

        self.out.write('<' + tag)

        for attr_name, attr_value in tag_attrs:
            empty_attr = False
            if attr_value is None:
                attr_value = ''
                empty_attr = True

            # special case: inline JS/event handler
            if ((attr_value and attr_value.startswith('javascript:'))
                 or attr_name.startswith('on')):
                attr_value = self._rewrite_script(attr_value, True)

            # special case: inline CSS/style attribute
            elif attr_name == 'style':
                attr_value = self._rewrite_css(attr_value)

            # special case: deprecated background attribute
            elif attr_name == 'background':
                rw_mod = 'im_'
                attr_value = self._rewrite_url(attr_value, rw_mod)

            # special case: srcset list
            elif attr_name == 'srcset':
                rw_mod = handler.get(attr_name, '')
                attr_value = self._rewrite_srcset(attr_value, rw_mod)

            # special case: disable crossorigin and integrity attr
            # as they may interfere with rewriting semantics
            elif attr_name in ('crossorigin', 'integrity'):
                attr_name = '_' + attr_name

            # special case: if rewrite_canon not set,
            # don't rewrite rel=canonical
            elif tag == 'link' and attr_name == 'href':
                rw_mod = handler.get(attr_name)

                if self.has_attr(tag_attrs, ('rel', 'canonical')):
                    if self.opts.get('rewrite_rel_canon', True):
                        attr_value = self._rewrite_url(attr_value, rw_mod)
                    else:
                        # resolve relative rel=canonical URLs so that they
                        # refer to the same absolute URL as on the original
                        # page (see https://github.com/hypothesis/via/issues/65
                        # for context)
                        attr_value = urljoin(self.orig_url, attr_value)
                else:
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # special case: meta tag
            elif (tag == 'meta') and (attr_name == 'content'):
                if self.has_attr(tag_attrs, ('http-equiv', 'refresh')):
                    attr_value = self._rewrite_meta_refresh(attr_value)
                elif attr_value.startswith(self.DATA_RW_PROTOCOLS):
                    rw_mod = handler.get(attr_name)
                    attr_value = self._rewrite_url(attr_value, rw_mod)

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

            elif attr_name == 'href':
                rw_mod = self.defmod
                attr_value = self._rewrite_url(attr_value, rw_mod)

            else:
                # rewrite url using tag handler
                rw_mod = handler.get(attr_name)
                if rw_mod is not None:
                    attr_value = self._rewrite_url(attr_value, rw_mod)

            # write the attr!
            self._write_attr(attr_name, attr_value, empty_attr)

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
            if not self.has_base:
                self._write_default_base()

            self.out.write('</head>')

        return True

    def _write_attr(self, name, value, empty_attr):
        # if empty_attr is set, just write 'attr'!
        if empty_attr:
            self.out.write(' ' + name)

        # write with value, if set
        elif value:

            self.out.write(' ' + name + '="' + value.replace('"', '&quot;') + '"')

        # otherwise, 'attr=""' is more common, so use that form
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

        # track that something was parsed
        self.parsed_any = self.parsed_any or bool(string)

        # Clear buffer to create new one for next rewrite()
        self.out = None

        if self.force_decl:
            result = self.force_decl + '\n' + result
            self.force_decl = None

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
        if sys.version_info > (3,4):  #pragma: no cover
            HTMLParser.__init__(self, convert_charrefs=False)
        else:  #pragma: no cover
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
        except Exception as e:  # pragma: no cover
            import traceback
            traceback.print_exc()
            self.out.write(string)

    def _internal_close(self):
        if (self._wb_parse_context):
            end_tag = '</' + self._wb_parse_context + '>'
            self.feed(end_tag)
            self._wb_parse_context = None

        # if haven't insert head_insert, but wrote some content
        # out, then insert head_insert now
        if self.head_insert and self.parsed_any:
            self.out.write(self.head_insert)
            self.head_insert = None

        try:
            HTMLParser.close(self)
        except Exception:  # pragma: no cover
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

        if tag == 'head' and not self.has_base:
            self._write_default_base()

        self.out.write('</' + tag + '>')

    def handle_data(self, data):
        self.parse_data(data)

    # overriding regex so that these are no longer called
    #def handle_entityref(self, data):
    #    self.out.write('&' + data + ';')

    #def handle_charref(self, data):
    #    self.out.write('&#' + data + ';')

    def handle_comment(self, data):
        self.out.write('<!--')
        if self.parse_comments:
            #data = self._rewrite_script(data)

            # Rewrite with seperate HTMLRewriter
            comment_rewriter = HTMLRewriter(self.url_rewriter,
                                            defmod=self.defmod)

            data = comment_rewriter.rewrite(data)
            data += comment_rewriter.close()
            self.out.write(data)
        else:
            self.parse_data(data)
        self.out.write('-->')

    def handle_decl(self, data):
        self.out.write('<!' + data + '>')
        self.force_decl = None

    def handle_pi(self, data):
        self.out.write('<?' + data + '>')

    def unknown_decl(self, data):
        self.out.write('<![')
        self.parse_data(data)
        self.out.write(']>')
