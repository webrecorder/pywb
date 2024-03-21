r"""
#=================================================================
# Custom Regex
#=================================================================
# Test https->http converter (other tests below in subclasses)
>>> RegexRewriter(urlrewriter, [(RxRules.HTTPX_MATCH_STR, RxRules.remove_https, 0)]).rewrite('a = https://example.com; b = http://example.com; c = https://some-url/path/https://embedded.example.com')
'a = http://example.com; b = http://example.com; c = http://some-url/path/http://embedded.example.com'


#=================================================================
# JS Rewriting
#=================================================================

>>> _test_js('location = "http://example.com/abc.html"')
'WB_wombat_location = "/web/20131010/http://example.com/abc.html"'

>>> _test_js(r'location = "http:\/\/example.com/abc.html"')
'WB_wombat_location = "/web/20131010/http:\\/\\/example.com/abc.html"'

>>> _test_js(r'location = "http:\\/\\/example.com/abc.html"')
'WB_wombat_location = "/web/20131010/http:\\\\/\\\\/example.com/abc.html"'

>>> _test_js(r"location = 'http://example.com/abc.html/'")
"WB_wombat_location = '/web/20131010/http://example.com/abc.html/'"

>>> _test_js(r'location = http://example.com/abc.html/')
'WB_wombat_location = http://example.com/abc.html/'

>>> _test_js(r'location = "http://example.com/abc.html?^foo=~bar!@#abc"')
'WB_wombat_location = "/web/20131010/http://example.com/abc.html?^foo=~bar!@#abc"'

>>> _test_js(r'location = "http://example.com/abc.html?^foo=http://abc.example.com"')
'WB_wombat_location = "/web/20131010/http://example.com/abc.html?^foo=http://abc.example.com"'

# don't rewrite comments, only scheme rel urls
>>> _test_js(r'location = "http://example.com/abc.html?^foo=http://abc.example.com";//some comments')
'WB_wombat_location = "/web/20131010/http://example.com/abc.html?^foo=http://abc.example.com";//some comments'

>>> _test_js(r'location = "//example.com/abc.html?^foo=http://abc.example.com"//some comments')
'WB_wombat_location = "/web/20131010///example.com/abc.html?^foo=http://abc.example.com"//some comments'

# not rewritten -- to be handled on client side
>>> _test_js(r'location = "/abc.html"')
'WB_wombat_location = "/abc.html"'

>>> _test_js(r'location = /http:\/\/example.com/abc.html/')
'WB_wombat_location = /http:\\/\\/example.com/abc.html/'

>>> _test_js(r'location = \/http:\/\/example.com\/abc.html\/')
'WB_wombat_location = \\/http:\\/\\/example.com\\/abc.html\\/'

>>> _test_js('"/location" == some_location_val; locations = location;')
'"/location" == some_location_val; locations = WB_wombat_location;'

>>> _test_js('cool_Location = "http://example.com/abc.html"')
'cool_Location = "/web/20131010/http://example.com/abc.html"'

>>> _test_js('$location = cond ? a.location: location; location$')
'$location = cond ? a.WB_wombat_location: WB_wombat_location; location$'

>>> _test_js('location$ = cond?a.location:location;')
'location$ = cond?a.WB_wombat_location:WB_wombat_location;'

>>> _test_js('location$ = {location: "location", top: " location "}')
'location$ = {location: "location", top: " WB_wombat_location "}'



# not rewriting WB_wombat_domain
#>>> _test_js('window.location = "http://example.com/abc.html" document.domain = "anotherdomain.com"')
#'window.WB_wombat_location = "/web/20131010/http://example.com/abc.html" document.WB_wombat_domain = "anotherdomain.com"'

#>>> _test_js('document_domain = "anotherdomain.com"; window.document.domain = "example.com"')
#'document_domain = "anotherdomain.com"; window.document.WB_wombat_domain = "example.com"'

>>> _test_js('win.frameElement != undefined')
'win.WB_wombat_frameElement != undefined'

# top test
>>> _test_js('window.top != window')
'window.WB_wombat_top != window'

>>> _test_js('if(parent!=top)')
'if(parent!=WB_wombat_top)'

>>> _test_js('top != window')
'WB_wombat_top != window'

# all 'top' now rewritten, WB_wombat_top defaults to top
>>> _test_js('top = top + 5')
'WB_wombat_top = WB_wombat_top + 5'

# protocol-rel escapes -- keep protocol relative
>>> _test_js('"//example.com/"')
'"/web/20131010///example.com/"'

>>> _test_js(r'"\/\/example.com/"')
'"/web/20131010/\\/\\/example.com/"'

>>> _test_js(r'"\\/\\/example.com/"')
'"/web/20131010/\\\\/\\\\/example.com/"'

# custom rules added
>>> _test_js('window.location = "http://example.com/abc.html"; some_func(); ', [('some_func\(\).*', RxRules.format('/*{0}*/'), 0)])
'window.WB_wombat_location = "/web/20131010/http://example.com/abc.html"; /*some_func(); */'

# scheme-agnostic
>>> _test_js('cool_Location = "//example.com/abc.html" //comment')
'cool_Location = "/web/20131010///example.com/abc.html" //comment'

>>> _test_js('A = B;//C + D;')
'A = B;//C + D;'

# not rewriting document.cookie
# document.cookie test
#>>> _test_js('document.cookie = "a=b; Path=/"')
#'document.WB_wombat_cookie = "a=b; Path=/"'

# js-escaped
>>> _test_js('&quot;http:\\/\\/www.example.com\\/some\\/path\\/?query=1&quot;')
'&quot;/web/20131010/http:\\/\\/www.example.com\\/some\\/path\\/?query=1&quot;'

>>> _test_js('"http:\/\/sub-site.example.com\/path-dashes\/path_other\/foo_bar.txt"')
'"/web/20131010/http:\\/\\/sub-site.example.com\\/path-dashes\\/path_other\\/foo_bar.txt"'

>>> _test_js('"a=b&amp;http:\/\/example.com/;c=d"')
'"a=b&amp;/web/20131010/http:\\/\\/example.com/;c=d"'

#=================================================================
# JS Obj Proxy Rewriter
#=================================================================

>>> _test_js_obj_proxy('var foo = this;   location = bar')
'var foo = _____WB$wombat$check$this$function_____(this);   location = ((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || {}).href = bar'

>>> _test_js_obj_proxy('var that =    this\n   location = bar')
'var that =    _____WB$wombat$check$this$function_____(this)\n   location = ((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || {}).href = bar'

>>> _test_js_obj_proxy('location = "xyz"')
'location = ((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || {}).href = "xyz"'

>>> _test_js_obj_proxy('var foo = this.location')
'var foo = _____WB$wombat$check$this$function_____(this).location'

>>> _test_js_obj_proxy('A = B\nthis.location = "foo"')
'A = B\n_____WB$wombat$check$this$function_____(this).location = "foo"'

>>> _test_js_obj_proxy('var foo = this.location2')
'var foo = this.location2'

>>> _test_js_obj_proxy('func(Function("return this"));')
'func(Function("return _____WB$wombat$check$this$function_____(this)"));'

>>> _test_js_obj_proxy('A.call(function() { return  this });')
'A.call(function() { return  _____WB$wombat$check$this$function_____(this) });'

>>> _test_js_obj_proxy('this.document.location = foo')
'_____WB$wombat$check$this$function_____(this).document.location = foo'

>>> _test_js_obj_proxy('if (that != this) { ... }')
'if (that != _____WB$wombat$check$this$function_____(this)) { ... }'

>>> _test_js_obj_proxy('function(){...} (this)')
'function(){...} (_____WB$wombat$check$this$function_____(this))'

>>> _test_js_obj_proxy('function(){...} )   (this); foo(this)')
'function(){...} )   (_____WB$wombat$check$this$function_____(this)); foo(this)'

>>> _test_js_obj_proxy('var foo = that || this  ;')
'var foo = that || _____WB$wombat$check$this$function_____(this)  ;'

>>> _test_js_obj_proxy('a||this||that')
'a||_____WB$wombat$check$this$function_____(this)||that'

>>> _test_js_obj_proxy('a||this)')
'a||_____WB$wombat$check$this$function_____(this))'

>>> _test_js_obj_proxy(r'(a,b,Q.contains(i[t], this))')
'(a,b,Q.contains(i[t], _____WB$wombat$check$this$function_____(this)))'

# not rewritten
>>> _test_js_obj_proxy('var window = this$')
'var window = this$'

>>> _test_js_obj_proxy('var window = $this')
'var window = $this'

>>> _test_js_obj_proxy('|||this|||')
'|||this|||'

>>> _test_js_obj_proxy('a||this|that')
'a||this|that'

>>> _test_js_obj_proxy('a||this$')
'a||this$'

>>> _test_js_obj_proxy('return this.foo')
'return this.foo'

>>> _test_js_obj_proxy('{foo: bar, this: other}')
'{foo: bar, this: other}'

>>> _test_js_obj_proxy(r'this.$location = http://example.com/')
'this.$location = http://example.com/'

>>> _test_js_obj_proxy(r'this.  $location = http://example.com/')
'this.  $location = http://example.com/'

>>> _test_js_obj_proxy(r'this. _location = http://example.com/')
'this. _location = http://example.com/'

>>> _test_js_obj_proxy(r'this. alocation = http://example.com/')
'this. alocation = http://example.com/'

>>> _test_js_obj_proxy(r'this. location = http://example.com/')
'this. location = ((self.__WB_check_loc && self.__WB_check_loc(location, arguments)) || {}).href = http://example.com/'

>>> _test_js_obj_proxy('eval(a)')
'WB_wombat_runEval2((_______eval_arg, isGlobal) => { var ge = eval; return isGlobal ? ge(_______eval_arg) : eval(_______eval_arg); }).eval(this, (function() { return arguments })(),a)'

>>> _test_js_obj_proxy('abc eval(a)')
'abc WB_wombat_runEval2((_______eval_arg, isGlobal) => { var ge = eval; return isGlobal ? ge(_______eval_arg) : eval(_______eval_arg); }).eval(this, (function() { return arguments })(),a)'



>>> _test_js_obj_proxy(',eval(a)')
',eval(a)'

>>> _test_js_obj_proxy('this.$eval(a)')
'this.$eval(a)'

>>> _test_js_obj_proxy('x = this.$eval; x(a);')
'x = this.$eval; x(a);'

>>> _test_js_obj_proxy('x = eval; x(a);')
'x = self.eval; x(a);'

>>> _test_js_obj_proxy('$eval = eval; $eval(a);')
'$eval = self.eval; $eval(a);'

>>> _test_js_obj_proxy('foo(a, eval(data));')
'foo(a, WB_wombat_runEval2((_______eval_arg, isGlobal) => { var ge = eval; return isGlobal ? ge(_______eval_arg) : eval(_______eval_arg); }).eval(this, (function() { return arguments })(),data));'

>>> _test_js_obj_proxy('function eval() {}')
'function eval() {}'

>>> _test_js_obj_proxy('window.eval(a);')
'window.eval(a);'

>>> _test_js_obj_proxy('x = window.eval; x(a);')
'x = window.eval; x(a);'

>>> _test_js_obj_proxy('obj = { eval : 1 }')
'obj = { eval : 1 }'

>>> _test_js_obj_proxy('x = obj.eval')
'x = obj.eval'

>>> _test_js_obj_proxy('x = obj.eval(a)')
'x = obj.eval(a)'

>>> _test_js_obj_proxy('x = obj._eval(a)')
'x = obj._eval(a)'

>>> _test_js_obj_proxy('x = obj.$eval(a)')
'x = obj.$eval(a)'


#=================================================================
# XML Rewriting
#=================================================================

>>> _test_xml('<tag xmlns="http://www.example.com/ns" attr="http://example.com"></tag>')
'<tag xmlns="http://www.example.com/ns" attr="/web/20131010/http://example.com"></tag>'

>>> _test_xml('<tag xmlns:xsi="http://www.example.com/ns" attr=" http://example.com"></tag>')
'<tag xmlns:xsi="http://www.example.com/ns" attr=" /web/20131010/http://example.com"></tag>'

>>> _test_xml('<tag> http://example.com<other>abchttp://example.com</other></tag>')
'<tag> /web/20131010/http://example.com<other>abchttp://example.com</other></tag>'

>>> _test_xml('<main>   http://www.example.com/blah</tag> <other xmlns:abcdef= " http://example.com"/> http://example.com </main>')
'<main>   /web/20131010/http://www.example.com/blah</tag> <other xmlns:abcdef= " http://example.com"/> /web/20131010/http://example.com </main>'

#=================================================================
# CSS Rewriting
#=================================================================

>>> _test_css("background: url('/some/path.html')")
"background: url('/web/20131010oe_/http://example.com/some/path.html')"

>>> _test_css("background: url('../path.html')")
"background: url('/web/20131010oe_/http://example.com/path.html')"

>>> _test_css("background: url(\"http://domain.com/path.html\")")
'background: url("/web/20131010oe_/http://domain.com/path.html")'

>>> _test_css('background: url("   http://domain.com/path.html   ")')
'background: url("   /web/20131010oe_/http://domain.com/path.html   ")'

>>> _test_css('background: url(" http://domain.com/path.html x ")')
'background: url(" /web/20131010oe_/http://domain.com/path.html x ")'

>>> _test_css("background: url(file.jpeg)")
'background: url(file.jpeg)'

>>> _test_css("background:#abc url('/static/styles/../images/layout/logo.png')")
"background:#abc url('/web/20131010oe_/http://example.com/static/images/layout/logo.png')"

>>> _test_css("background:#000 url('/static/styles/../../images/layout/logo.png')")
"background:#000 url('/web/20131010oe_/http://example.com/images/layout/logo.png')"

>>> _test_css("background: url('')")
"background: url('')"

>>> _test_css("background: url (\"weirdpath\')")
'background: url ("weirdpath\')'

>>> _test_css("@import   url ('/path.css')")
"@import   url ('/web/20131010cs_/http://example.com/path.css')"

>>> _test_css("@import url('path.css')")
"@import url('path.css')"

>>> _test_css("@import ( 'path.css')")
"@import ( 'path.css')"

>>> _test_css("@import  \"/path.css\"")
'@import  "/web/20131010cs_/http://example.com/path.css"'

>>> _test_css("@import ('../path.css\"")
'@import (\'/web/20131010cs_/http://example.com/path.css"'

>>> _test_css("@import ('../url.css\"")
'@import (\'/web/20131010cs_/http://example.com/url.css"'

>>> _test_css("@import (\"url.css\")")
'@import ("url.css")'

>>> _test_css("@import url(/url.css)\n@import  url(/anotherurl.css)\n @import  url(/and_a_third.css)")
'@import url(/web/20131010cs_/http://example.com/url.css)\n@import  url(/web/20131010cs_/http://example.com/anotherurl.css)\n @import  url(/web/20131010cs_/http://example.com/and_a_third.css)'

"""


#=================================================================
from pywb.rewrite.url_rewriter import UrlRewriter
from pywb.rewrite.regex_rewriters import RegexRewriter, JSRewriter, CSSRewriter, XMLRewriter, RxRules
from pywb.rewrite.regex_rewriters import JSWombatProxyRewriter


urlrewriter = UrlRewriter('20131010/http://example.com/', '/web/', 'https://localhost/web/')


def _test_js(string, extra = []):
    return JSRewriter(urlrewriter, extra).rewrite(string)

def _test_js_obj_proxy(string):
    rw = JSWombatProxyRewriter(urlrewriter)
    rw.first_buff = ''
    rw.close_string = ''
    return rw.rewrite(string)

def _test_xml(string):
    return XMLRewriter(urlrewriter).rewrite(string)

def _test_css(string):
    return CSSRewriter(urlrewriter).rewrite(string)

if __name__ == "__main__":
    import doctest
    doctest.testmod()


