#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# full seq
#>>> print RewriteContent._decode_buff(b'\xce\xb4\xce\xbf\xce\xba', BytesIO(b''), 'utf-8')
δοκ

# read split bytes, read rest
#>>> b = BytesIO('\xbf\xce\xba')
#>>> sys.stdout.write(RewriteContent._decode_buff(b'\xce\xb4\xce', b, 'utf-8')); sys.stdout.write(RewriteContent._decode_buff(b.read(), b, 'utf-8'))
δοκ

# invalid seq
#>>> print RewriteContent._decode_buff(b'\xce\xb4\xce', BytesIO(b'\xfe'), 'utf-8')
Traceback (most recent call last):
"UnicodeDecodeError: 'utf8' codec can't decode byte 0xce in position 2: invalid continuation byte"


"""

from pywb.rewrite.rewrite_content import RewriteContent
from io import BytesIO
import sys



def test_type_detect_1():
    text_type, stream = RewriteContent._resolve_text_type('js', 'html', BytesIO(b' <html></html>'))
    assert(text_type == 'html')
    assert(stream.read() == b' <html></html>')


def test_type_detect_2():
    text_type, stream = RewriteContent._resolve_text_type('js', 'html', BytesIO(b' function() { return 0; }'))
    assert(text_type == 'js')
    assert(stream.read() == b' function() { return 0; }')





if __name__ == "__main__":
    import doctest
    doctest.testmod()
