#!/usr/bin/env python
# -*- coding: utf-8 -*-

ur"""
# full seq
#>>> print RewriteContent._decode_buff('\xce\xb4\xce\xbf\xce\xba', BytesIO(''), 'utf-8')
δοκ

# read split bytes, read rest
#>>> b = BytesIO('\xbf\xce\xba')
#>>> sys.stdout.write(RewriteContent._decode_buff('\xce\xb4\xce', b, 'utf-8')); sys.stdout.write(RewriteContent._decode_buff(b.read(), b, 'utf-8'))
δοκ

# invalid seq
#>>> print RewriteContent._decode_buff('\xce\xb4\xce', BytesIO('\xfe'), 'utf-8')
Traceback (most recent call last):
"UnicodeDecodeError: 'utf8' codec can't decode byte 0xce in position 2: invalid continuation byte"

>>> text_type, stream = RewriteContent._resolve_text_type('js', 'html', BytesIO(' <html></html>'))
>>> print (text_type, stream.read())
('html', ' <html></html>')

>>> text_type, stream = RewriteContent._resolve_text_type('js', 'html', BytesIO(' function() { return 0; }'))
>>> print (text_type, stream.read())
('js', ' function() { return 0; }')


"""

from pywb.rewrite.rewrite_content import RewriteContent
from io import BytesIO
import sys

if __name__ == "__main__":
    import doctest
    doctest.testmod()
