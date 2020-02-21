#=================================================================
"""
# Merge Sort Multipe CDX Sources
>>> cdx_ops_test(url = 'http://iana.org/', sources = {'dupes': test_cdx_dir + 'dupes.cdx', 'iana': test_cdx_dir + 'iana.cdx'})
org,iana)/ 20140126200624 http://www.iana.org/ text/html 200 OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 2258 334 iana.warc.gz
org,iana)/ 20140127171238 http://iana.org unk 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 343 1858 dupes.warc.gz
org,iana)/ 20140127171238 http://www.iana.org/ warc/revisit - OSSAPWJ23L56IYVRW3GFEAR4MCJMGPTB - - 536 2678 dupes.warc.gz


# Limit CDX Stream
>>> cdx_ops_test('http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', limit = 3)
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200625 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 117166 198285 iana.warc.gz
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200654 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf warc/revisit - YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 548 482544 iana.warc.gz
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200706 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf warc/revisit - YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 495230 iana.warc.gz


# Reverse CDX Stream
>>> cdx_ops_test('http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', reverse = True, resolveRevisits = True, limit = 3)
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201308 https://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 551 783712 iana.warc.gz 117166 198285 iana.warc.gz
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201249 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 771773 iana.warc.gz 117166 198285 iana.warc.gz
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126201240 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 551 757988 iana.warc.gz 117166 198285 iana.warc.gz


>>> cdx_ops_test('http://iana.org/_js/2013.1/jquery.js', reverse = True, resolveRevisits = True, limit = 1)
org,iana)/_js/2013.1/jquery.js 20140126201307 https://www.iana.org/_js/2013.1/jquery.js application/x-javascript 200 AAW2RS7JB7HTF666XNZDQYJFA6PDQBPO - - 543 778507 iana.warc.gz 33449 7311 iana.warc.gz

# From & To
>>> cdx_ops_test('http://example.com/', sources = {'dir': test_cdx_dir}, from_ts='2013', to='2013')
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz

>>> cdx_ops_test('http://example.com/', sources = {'dir': test_cdx_dir}, from_ts='2014')
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

# No results
>>> cdx_ops_test('http://example.com/', sources = {'dir': test_cdx_dir}, to='2012')

# No matching results
>>> cdx_ops_test('http://iana.org/dont_have_this', reverse = True, resolveRevisits = True, limit = 2)

# No matching -- limit=1
>>> cdx_ops_test('http://iana.org/dont_have_this', reverse = True, resolveRevisits = True, limit = 1)

# Filter cdx (default: contains)
>>> cdx_ops_test(url = 'http://iana.org/domains', matchType = 'prefix', filter = ['mimetype:html'])
org,iana)/domains 20140126200825 http://www.iana.org/domains text/html 200 7UPSCLNWNZP33LGW6OJGSF2Y4CDG4ES7 - - 2912 610534 iana.warc.gz
org,iana)/domains/arpa 20140126201248 http://www.iana.org/domains/arpa text/html 200 QOFZZRN6JIKAL2JRL6ZC2VVG42SPKGHT - - 2939 759039 iana.warc.gz
org,iana)/domains/idn-tables 20140126201127 http://www.iana.org/domains/idn-tables text/html 200 HNCUFTJMOQOGAEY6T56KVC3T7TVLKGEW - - 8118 715878 iana.warc.gz
org,iana)/domains/int 20140126201239 http://www.iana.org/domains/int text/html 200 X32BBNNORV4SPEHTQF5KI5NFHSKTZK6Q - - 2482 746788 iana.warc.gz
org,iana)/domains/reserved 20140126201054 http://www.iana.org/domains/reserved text/html 200 R5AAEQX5XY5X5DG66B23ODN5DUBWRA27 - - 3573 701457 iana.warc.gz
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz

# Filter cdx (regex)
>>> cdx_ops_test(url = 'http://iana.org/domains', matchType = 'prefix', filter = ['~mimetype:.*/html$'])
org,iana)/domains 20140126200825 http://www.iana.org/domains text/html 200 7UPSCLNWNZP33LGW6OJGSF2Y4CDG4ES7 - - 2912 610534 iana.warc.gz
org,iana)/domains/arpa 20140126201248 http://www.iana.org/domains/arpa text/html 200 QOFZZRN6JIKAL2JRL6ZC2VVG42SPKGHT - - 2939 759039 iana.warc.gz
org,iana)/domains/idn-tables 20140126201127 http://www.iana.org/domains/idn-tables text/html 200 HNCUFTJMOQOGAEY6T56KVC3T7TVLKGEW - - 8118 715878 iana.warc.gz
org,iana)/domains/int 20140126201239 http://www.iana.org/domains/int text/html 200 X32BBNNORV4SPEHTQF5KI5NFHSKTZK6Q - - 2482 746788 iana.warc.gz
org,iana)/domains/reserved 20140126201054 http://www.iana.org/domains/reserved text/html 200 R5AAEQX5XY5X5DG66B23ODN5DUBWRA27 - - 3573 701457 iana.warc.gz
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz

# Filter cdx (regex)
>>> cdx_ops_test(url = 'http://iana.org/domains', matchType = 'prefix', filter = ['=mimetype:text/html'])
org,iana)/domains 20140126200825 http://www.iana.org/domains text/html 200 7UPSCLNWNZP33LGW6OJGSF2Y4CDG4ES7 - - 2912 610534 iana.warc.gz
org,iana)/domains/arpa 20140126201248 http://www.iana.org/domains/arpa text/html 200 QOFZZRN6JIKAL2JRL6ZC2VVG42SPKGHT - - 2939 759039 iana.warc.gz
org,iana)/domains/idn-tables 20140126201127 http://www.iana.org/domains/idn-tables text/html 200 HNCUFTJMOQOGAEY6T56KVC3T7TVLKGEW - - 8118 715878 iana.warc.gz
org,iana)/domains/int 20140126201239 http://www.iana.org/domains/int text/html 200 X32BBNNORV4SPEHTQF5KI5NFHSKTZK6Q - - 2482 746788 iana.warc.gz
org,iana)/domains/reserved 20140126201054 http://www.iana.org/domains/reserved text/html 200 R5AAEQX5XY5X5DG66B23ODN5DUBWRA27 - - 3573 701457 iana.warc.gz
org,iana)/domains/root 20140126200912 http://www.iana.org/domains/root text/html 200 YWA2R6UVWCYNHBZJKBTPYPZ5CJWKGGUX - - 2691 657746 iana.warc.gz
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz
org,iana)/domains/root/servers 20140126201227 http://www.iana.org/domains/root/servers text/html 200 AFW34N3S4NK2RJ6QWMVPB5E2AIUETAHU - - 3137 733840 iana.warc.gz

>>> cdx_ops_test(url = 'http://iana.org/_css/2013.1/screen.css', filter = 'statuscode:200')
org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz

# Filter Alt field name
>>> cdx_ops_test(url = 'http://iana.org/_css/2013.1/screen.css', filter = 'status:200')
org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz

# Filter -- no field specified, check whether filter query contained in entire line
>>> cdx_ops_test(url = 'http://iana.org/_css/2013.1/screen.css', filter = 'screen.css 20140126200625')
org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz

# Filter -- no such field, no matches
>>> cdx_ops_test(url = 'http://iana.org/_css/2013.1/screen.css', filter = 'blah:200')

# Filter exact -- (* prefix)
>>> cdx_ops_test(url = 'http://example.com*', sources = {'dir': test_cdx_dir}, filter = '=urlkey:com,example)/?example=1')
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz

# Filter exact invert
>>> cdx_ops_test(url = 'http://example.com', sources = {'dir': test_cdx_dir}, matchType = 'prefix', filter = ['!=urlkey:com,example)/?example=1', '!=urlkey:com,example)/?example=2', '!=urlkey:com,example)/?example=3'])
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

# Filter contains
>>> cdx_ops_test(url = 'http://example.com', sources = {'dir': test_cdx_dir}, matchType = 'prefix', filter = 'urlkey:example=1')
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz

# Filter contains invert
>>> cdx_ops_test(url = 'http://example.com', sources = {'dir': test_cdx_dir}, matchType = 'prefix', filter = '!urlkey:example=')
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

# Filter regex
>>> cdx_ops_test(url = 'http://example.com', sources = {'dir': test_cdx_dir}, matchType = 'prefix', filter = '~urlkey:.*example=1$')
com,example)/?example=1 20140103030321 http://example.com?example=1 text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1043 333 example.warc.gz
com,example)/?example=1 20140103030341 http://example.com?example=1 warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 1864 example.warc.gz

# Filter regex invert
>>> cdx_ops_test(url = 'http://example.com', sources = {'dir': test_cdx_dir}, matchType = 'prefix', filter = '!~urlkey:.*example=[0-9]$')
com,example)/ 20130729195151 http://test@example.com/ warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 591 355 example-url-agnostic-revisit.warc.gz
com,example)/ 20140127171200 http://example.com text/html 200 B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 1046 334 dupes.warc.gz
com,example)/ 20140127171251 http://example.com warc/revisit - B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A - - 553 11875 dupes.warc.gz

# Collapse by timestamp
# unresolved revisits, different statuscode results in an extra repeat
>>> cdx_ops_test(url = 'http://iana.org/_css/2013.1/screen.css', collapseTime = 11)
org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz
org,iana)/_css/2013.1/screen.css 20140126200653 http://www.iana.org/_css/2013.1/screen.css warc/revisit - BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 533 328367 iana.warc.gz
org,iana)/_css/2013.1/screen.css 20140126201054 http://www.iana.org/_css/2013.1/screen.css warc/revisit - BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 543 706476 iana.warc.gz

# resolved revisits
>>> cdx_ops_test(url = 'http://iana.org/_css/2013.1/screen.css', collapseTime = '11', resolveRevisits = True)
org,iana)/_css/2013.1/screen.css 20140126200625 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 8754 41238 iana.warc.gz - - -
org,iana)/_css/2013.1/screen.css 20140126201054 http://www.iana.org/_css/2013.1/screen.css text/css 200 BUAEPXZNN44AIX3NLXON4QDV6OY2H5QD - - 543 706476 iana.warc.gz 8754 41238 iana.warc.gz

# Sort by closest timestamp + field select output
>>> cdx_ops_test(closest = '20140126200826', url = 'http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', fields = 'timestamp', limit = 10)
20140126200826
20140126200816
20140126200805
20140126200912
20140126200738
20140126200930
20140126200718
20140126200706
20140126200654
20140126200625

# In case of both reverse and closest, closest takes precedence
# 'reverse closest' not supported at this time
# if it is, this test will reflect the change
>>> cdx_ops_test(closest = '20140126200826', url = 'http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', fields = 'timestamp', limit = 3, reverse = True)
20140126200826
20140126200816
20140126200805

>>> cdx_ops_test(closest = '20140126201306', url = 'http://iana.org/dnssec', resolveRevisits = True, sources = {'dupes': test_cdx_dir + 'dupes.cdx', 'iana': test_cdx_dir + 'iana.cdx'})
org,iana)/dnssec 20140126201306 http://www.iana.org/dnssec text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 442 772827 iana.warc.gz - - -
org,iana)/dnssec 20140126201307 https://www.iana.org/dnssec text/html 200 PHLRSX73EV3WSZRFXMWDO6BRKTVUSASI - - 2278 773766 iana.warc.gz - - -


>>> cdx_ops_test(closest = '20140126201307', url = 'http://iana.org/dnssec', resolveRevisits = True)
org,iana)/dnssec 20140126201307 https://www.iana.org/dnssec text/html 200 PHLRSX73EV3WSZRFXMWDO6BRKTVUSASI - - 2278 773766 iana.warc.gz - - -
org,iana)/dnssec 20140126201306 http://www.iana.org/dnssec text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 442 772827 iana.warc.gz - - -

# equal dist prefer earlier
>>> cdx_ops_test(closest = '20140126200700', url = 'http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', resolveRevisits = True, limit = 2)
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200654 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 548 482544 iana.warc.gz 117166 198285 iana.warc.gz
org,iana)/_css/2013.1/fonts/opensans-bold.ttf 20140126200706 http://www.iana.org/_css/2013.1/fonts/OpenSans-Bold.ttf application/octet-stream 200 YFUR5ALIWJMWV6FAAFRLVRQNXZQF5HRW - - 552 495230 iana.warc.gz 117166 198285 iana.warc.gz

>>> cdx_ops_test(closest = '20140126200659', url = 'http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', resolveRevisits = True, limit = 2, fields = 'timestamp')
20140126200654
20140126200706

>>> cdx_ops_test(closest = '20140126200701', url = 'http://iana.org/_css/2013.1/fonts/opensans-bold.ttf', resolveRevisits = True, limit = 2, fields = 'timestamp')
20140126200706
20140126200654


# Resolve Revisits
>>> cdx_ops_test('http://iana.org/_css/2013.1/fonts/inconsolata.otf', resolveRevisits = True)
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200826 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 34054 620049 iana.warc.gz - - -
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200912 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 546 667073 iana.warc.gz 34054 620049 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126200930 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 534 697255 iana.warc.gz 34054 620049 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126201055 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 547 714833 iana.warc.gz 34054 620049 iana.warc.gz
org,iana)/_css/2013.1/fonts/inconsolata.otf 20140126201249 http://www.iana.org/_css/2013.1/fonts/Inconsolata.otf application/octet-stream 200 LNMEDYOENSOEI5VPADCKL3CB6N3GWXPR - - 551 768625 iana.warc.gz 34054 620049 iana.warc.gz

>>> cdx_ops_test('http://iana.org/domains/root/db', resolveRevisits = True)
org,iana)/domains/root/db 20140126200927 http://www.iana.org/domains/root/db/ text/html 302 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 446 671278 iana.warc.gz - - -
org,iana)/domains/root/db 20140126200928 http://www.iana.org/domains/root/db text/html 200 DHXA725IW5VJJFRTWBQT6BEZKRE7H57S - - 18365 672225 iana.warc.gz - - -

"""

#=================================================================
from pywb.warcserver.warcserver import init_index_agg

import os
import sys
import six

from pywb import get_test_dir

test_cdx_dir = get_test_dir() + 'cdx/'


def cdx_ops_test_data(url, sources=None, **kwparams):
    if not sources:
        sources = {'iana': test_cdx_dir + 'iana.cdx'}

    kwparams['url'] = url
    if not 'output' in kwparams:
        kwparams['output'] = 'raw'

    kwparams['nosource'] = 'true'

    server = init_index_agg(sources)
    #server = IndexHandler(server)

    results, errs = server(kwparams)
    res = list(results)
    return res


def cdx_ops_test(*args, **kwargs):
    results = cdx_ops_test_data(*args, **kwargs)

    fields = kwargs.get('fields')
    if fields:
        fields = fields.split(',')

    for x in results:
        if not isinstance(x, str) and kwargs.get('output') == 'json':
            l = x.to_json()
        elif not isinstance(x, str):
            l = x.to_text(fields).replace('\t', '    ')
        else:
            l = x

        sys.stdout.write(l)



def test_cdxj_resolve_revisit():
    # Resolve Revisit -- cdxj minimal -- output also json
    results = cdx_ops_test_data(url = 'http://example.com/?example=1', sources={'example': get_test_dir() + 'cdxj/example.cdxj'}, resolveRevisits=True)
    assert(len(results) == 2)
    assert(dict(results[0]) == {"urlkey": "com,example)/?example=1", "timestamp": "20140103030321", "url": "http://example.com?example=1", "length": "1043", "filename": "example.warc.gz", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "offset": "333", "orig.length": "-", "orig.offset": "-", "orig.filename": "-"})

    assert(dict(results[1]) == {"urlkey": "com,example)/?example=1", "timestamp": "20140103030341", "url": "http://example.com?example=1", "filename": "example.warc.gz", "length": "553", "mime": "", "offset": "1864", "digest": "B2LTWWPUOYAH7UIPQ7ZUPQ4VMBSVC36A", "orig.length": "1043", "orig.offset": "333", "orig.filename": "example.warc.gz"})



def test_cdxj_resolve_revisit_2():
    # Resolve Revisit -- cdxj minimal -- output also json
    results = cdx_ops_test_data(url = 'http://example.com/?example=1', sources={'nd-file': get_test_dir() + 'cdxj/example-no-digest.cdxj'}, resolveRevisits=True)
    assert(len(results) == 2)
    assert(dict(results[0]) == {"urlkey": "com,example)/?example=1", "timestamp": "20140103030321", "url": "http://example.com?example=1", "length": "1043", "filename": "example.warc.gz", "offset": "333", "orig.length": "-", "orig.offset": "-", "orig.filename": "-"})

    assert(dict(results[1]) == {"urlkey": "com,example)/?example=1", "timestamp": "20140103030341", "url": "http://example.com?example=1", "length": "553", "filename": "example.warc.gz", "mime": "warc/revisit", "offset": "1864", "orig.length": "-", "orig.offset": "-", "orig.filename": "-"})



if __name__ == "__main__":
    import doctest
    doctest.testmod()
