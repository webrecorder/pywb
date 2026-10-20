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
from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.cdxops import cdx_sort_closest, process_cdx, CLOSEST_WARN_CAPTURES
from pywb.warcserver.index.query import CDXQuery

from warcio.timeutils import timestamp_to_sec

import datetime
import heapq
import os
import random
import re
import sys
import time
import six
import logging

from mock import patch

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


#=================================================================
# cdx_sort_closest
def closest_reference(closest, cdx_list, limit):
    """ Brute force cdx_sort_closest: the `limit` captures nearest to
    `closest`, by distance, and by input order on equal distance.
    """
    closest_sec = timestamp_to_sec(closest)

    def sort_key(pos_cdx):
        pos, cdx = pos_cdx
        return (abs(closest_sec - timestamp_to_sec(cdx['timestamp'])), pos)

    ordered = sorted(enumerate(cdx_list), key=sort_key)
    return [cdx for pos, cdx in ordered[:max(limit, 0)]]


def make_captures(timestamps, urlkey='com,example)/'):
    # plain dicts are not orderable: comparing two of them raises TypeError
    return [{'urlkey': urlkey, 'timestamp': ts, 'pos': pos}
            for pos, ts in enumerate(timestamps)]


def positions(cdx_iter):
    return [cdx['pos'] for cdx in cdx_iter]


class CountingIter(object):
    def __init__(self, items):
        self.items = iter(items)
        self.count = 0

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self.items)
        self.count += 1
        return item


def random_timestamps(rng, count):
    # few distinct values within a short span: many duplicates and equal distances
    base = datetime.datetime(2014, 1, 26, 20, 0, 0)
    span = rng.choice([10, 600, 3 * 86400])
    return [(base + datetime.timedelta(seconds=rng.randint(0, span))).strftime('%Y%m%d%H%M%S')
            for _ in range(count)]


def random_closest(rng, timestamps):
    # before, inside and after the captures, padded and unpadded
    choices = ['19990101000000', '2013', '2014', '201401', '20140126', '20140126200005', '2015']
    if timestamps:
        choices.extend([timestamps[0], timestamps[-1], rng.choice(timestamps),
                        rng.choice(timestamps)[:12]])

    return rng.choice(choices)


def random_limits(rng, count):
    return [1, 2, 3, 10, count, count + 5, rng.randint(1, count + 1)]


def test_sort_closest_same_as_reference_random():
    rng = random.Random(1671)
    for _ in range(200):
        count = rng.randint(0, 60)
        timestamps = random_timestamps(rng, count)
        closest = random_closest(rng, timestamps)

        unsorted_cdx = make_captures(timestamps)
        sorted_cdx = make_captures(sorted(timestamps))

        for limit in random_limits(rng, count):
            expected = positions(closest_reference(closest, unsorted_cdx, limit))
            res = cdx_sort_closest(closest, iter(unsorted_cdx), limit)
            assert positions(res) == expected, (closest, timestamps, limit)

            expected = positions(closest_reference(closest, sorted_cdx, limit))
            res = cdx_sort_closest(closest, iter(sorted_cdx), limit)
            assert positions(res) == expected, (closest, sorted(timestamps), limit)

            res = cdx_sort_closest(closest, iter(sorted_cdx), limit, sorted_input=True)
            assert positions(res) == expected, (closest, sorted(timestamps), limit)


def test_sort_closest_sorted_input_merged_sources_random():
    # the sources of an exact query are merged in ascending timestamp order, but
    # a remote source may return its captures nearest first (sort=closest)
    rng = random.Random(1504)
    for _ in range(200):
        count = rng.randint(1, 60)
        timestamps = random_timestamps(rng, count)
        closest = random_closest(rng, timestamps)
        closest_sec = timestamp_to_sec(closest)

        split = rng.randint(0, count)
        local = sorted(timestamps[:split])
        remote = sorted(timestamps[split:],
                        key=lambda ts: abs(closest_sec - timestamp_to_sec(ts)))

        for sources in ([remote], [local, remote]):
            cdx_list = make_captures(heapq.merge(*sources))
            for limit in random_limits(rng, count):
                expected = positions(closest_reference(closest, cdx_list, limit))
                res = cdx_sort_closest(closest, iter(cdx_list), limit, sorted_input=True)
                assert positions(res) == expected, (closest, sources, limit)


def test_sort_closest_ties_prefer_earlier_input():
    cdx_list = make_captures(['20140101000000', '20140101000010', '20140101000010',
                              '20140101000020', '20140101000000', '20140101000020'])

    res = cdx_sort_closest('20140101000010', iter(cdx_list), 10)
    assert positions(res) == [1, 2, 0, 3, 4, 5]

    res = cdx_sort_closest('20140101000010', iter(cdx_list), 4)
    assert positions(res) == [1, 2, 0, 3]


def test_sort_closest_empty_or_no_limit():
    assert list(cdx_sort_closest('2014', iter([]), 10)) == []
    assert list(cdx_sort_closest('2014', iter([]), 10, sorted_input=True)) == []

    # nothing is kept, but the input is still read to the end
    for limit in (0, -1):
        cdx_iter = CountingIter(make_captures(['2013', '2014', '2015']))
        assert list(cdx_sort_closest('2014', cdx_iter, limit, sorted_input=True)) == []
        assert cdx_iter.count == 3


def test_sort_closest_sorted_input_stops_early():
    start = datetime.datetime(2010, 1, 1)
    timestamps = [(start + datetime.timedelta(hours=i)).strftime('%Y%m%d%H%M%S')
                  for i in range(1000)]
    cdx_list = make_captures(timestamps)
    closest = timestamps[100]

    expected = [100, 99, 101, 98, 102, 97, 103, 96, 104, 95]

    # stops at the first capture after closest that is not nearer than the kept ones
    cdx_iter = CountingIter(cdx_list)
    assert positions(cdx_sort_closest(closest, cdx_iter, 10, sorted_input=True)) == expected
    assert cdx_iter.count == 106

    cdx_iter = CountingIter(cdx_list)
    assert positions(cdx_sort_closest(closest, cdx_iter, 10)) == expected
    assert cdx_iter.count == 1000


def test_sort_closest_sorted_input_not_ascending():
    # input not in ascending order after all: must not stop early
    cdx_list = make_captures(['20120101000000', '20100101000000',
                              '20130101000000', '20110601000000'])

    res = cdx_sort_closest('20110601000000', iter(cdx_list), 1, sorted_input=True)
    assert positions(res) == [3]


def make_cdx_objects(captures):
    return [CDXObject('{0} {1} {{"url": "http://example.com/"}}'.format(urlkey, ts).encode('utf-8'))
            for urlkey, ts in captures]


def test_process_cdx_closest_multiple_urlkeys():
    # prefix query: each urlkey is in ascending timestamp order, but the whole
    # stream is not; the closest capture comes last
    captures = [('com,example)/a', '20100101000000'),
                ('com,example)/a', '20110101000000'),
                ('com,example)/a', '20120101000000'),
                ('com,example)/a', '20130101000000'),
                ('com,example)/b', '20090101000000'),
                ('com,example)/b', '20110601000000')]

    query = CDXQuery({'url': 'http://example.com/', 'matchType': 'prefix',
                      'closest': '20110601000000', 'limit': '1'})

    res = list(process_cdx(iter(make_cdx_objects(captures)), query))
    assert [(cdx['urlkey'], cdx['timestamp']) for cdx in res] == [('com,example)/b', '20110601000000')]


def test_process_cdx_closest_exact_stops_early():
    captures = [('com,example)/', '2010{0:02d}01000000'.format(month)) for month in range(1, 13)]
    cdx_iter = CountingIter(make_cdx_objects(captures))

    query = CDXQuery({'url': 'http://example.com/', 'closest': '20100301', 'limit': '2'})

    res = list(process_cdx(cdx_iter, query))
    assert [cdx['timestamp'] for cdx in res] == ['20100301000000', '20100201000000']
    assert cdx_iter.count == 4


def test_closest_prefix_query_same_as_reference():
    all_cdx = cdx_ops_test_data(url='http://iana.org/_css/', matchType='prefix')
    assert len(set(cdx['urlkey'] for cdx in all_cdx)) > 1

    for closest in ('20140126200625', '20140126200912', '20140126201240', '2015'):
        for limit in (1, 3, 10, 1000):
            expected = closest_reference(closest, all_cdx, limit)
            res = cdx_ops_test_data(url='http://iana.org/_css/', matchType='prefix',
                                    closest=closest, limit=limit)

            assert [cdx.to_text() for cdx in res] == [cdx.to_text() for cdx in expected]


def test_sort_closest_many_captures_perf():
    # was quadratic: about 20s for 200k captures, against about 1s to read
    # their timestamps. compare with that, so a slow machine doesn't fail it
    start = datetime.datetime(2008, 1, 1)
    count = 200000
    timestamps = [(start + datetime.timedelta(minutes=7 * i)).strftime('%Y%m%d%H%M%S')
                  for i in range(count)]
    cdx_list = make_captures(timestamps)
    closest = timestamps[count // 2]

    begin = time.time()
    for cdx in cdx_list:
        timestamp_to_sec(cdx['timestamp'])
    linear = time.time() - begin

    for limit in (100000, 10):
        begin = time.time()
        res = list(cdx_sort_closest(closest, iter(cdx_list), limit))
        elapsed = time.time() - begin

        assert len(res) == limit
        assert res[0]['timestamp'] == closest
        assert elapsed < 4 * linear + 0.5, (limit, elapsed, linear)


FONT_URL = 'http://iana.org/_css/2013.1/fonts/opensans-bold.ttf'
FONT_CAPTURES = 16

def closest_warnings(caplog, warn_captures, **kwparams):
    caplog.clear()
    with patch('pywb.warcserver.index.cdxops.CLOSEST_WARN_CAPTURES', warn_captures):
        with caplog.at_level(logging.WARNING, logger='warcserver'):
            results = cdx_ops_test_data(FONT_URL, **kwparams)

    return results, [r.getMessage() for r in caplog.records]


def test_closest_warning(caplog):
    # closest after all captures, and a limit above the number of captures:
    # all are read, also when only the captures around closest are read
    expected = cdx_ops_test_data(FONT_URL, closest='20200101', limit=100)
    assert len(expected) == FONT_CAPTURES

    results, warnings = closest_warnings(caplog, FONT_CAPTURES, closest='20200101', limit=100)
    assert results == expected
    assert warnings == ['Closest lookup read 16 captures: key=org,iana)/_css/2013.1/fonts/opensans-bold.ttf closest=20200101235959 limit=100']

    results, warnings = closest_warnings(caplog, FONT_CAPTURES + 1, closest='20200101', limit=100)
    assert results == expected
    assert warnings == []


def test_closest_warning_default(caplog):
    assert CLOSEST_WARN_CAPTURES == 50000

    with caplog.at_level(logging.WARNING, logger='warcserver'):
        results = cdx_ops_test_data(FONT_URL, closest='20200101', limit=100)

    assert len(results) == FONT_CAPTURES
    assert caplog.records == []


def test_closest_warning_early_exit(caplog):
    # an exact query stops reading after closest: only the captures read are counted
    results, warnings = closest_warnings(caplog, FONT_CAPTURES, closest='20140126200625', limit=1)
    assert len(results) == 1
    assert warnings == []

    results, warnings = closest_warnings(caplog, 1, closest='20140126200625', limit=1)
    assert results[0]['timestamp'] == '20140126200625'
    assert len(warnings) == 1
    scanned = int(re.match(r'Closest lookup read (\d+) captures: ', warnings[0]).group(1))
    assert 1 <= scanned < FONT_CAPTURES


def test_closest_warning_no_closest(caplog):
    results, warnings = closest_warnings(caplog, 1)
    assert len(results) == FONT_CAPTURES
    assert warnings == []

    results, warnings = closest_warnings(caplog, 1, reverse=True, limit=3)
    assert len(results) == 3
    assert warnings == []


def test_closest_warning_closest_not_logged_as_is(caplog):
    # closest is user input: the parsed timestamp is logged, on one line
    results, warnings = closest_warnings(caplog, 1, closest='2014\nWARNING forged line', limit=1)
    assert len(results) == 1
    assert len(warnings) == 1
    assert 'closest=20141231235959 ' in warnings[0]
    assert '\n' not in warnings[0]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
