r"""
Load Rules

>>> (canon, fuzzy) = load_domain_specific_cdx_rules(None, True)
>>> canon('http://test.example.example/path/index.html?a=b&id=value&c=d')
'example,example,test)/path/index.html?id=value'


# Fuzzy Query Args Builder
>>> CDXDomainSpecificRule.make_query_match_regex(['para', 'id', 'abc'])
'[?&](abc=[^&]+).*[?&](id=[^&]+).*[?&](para=[^&]+)'

>>> CDXDomainSpecificRule.make_query_match_regex(['id[0]', 'abc()'])
'[?&](abc\\(\\)=[^&]+).*[?&](id\\[0\\]=[^&]+)'


# Fuzzy Match Query + Args

# list
>>> CDXDomainSpecificRule.make_regex(['para', 'id', 'abc']).pattern
'[?&](abc=[^&]+).*[?&](id=[^&]+).*[?&](para=[^&]+)'

# dict
>>> CDXDomainSpecificRule.make_regex(dict(regex='com,test,.*\)/', args=['para', 'id', 'abc'])).pattern
'com,test,.*\\)/[?&](abc=[^&]+).*[?&](id=[^&]+).*[?&](para=[^&]+)'

# string
>>> CDXDomainSpecificRule.make_regex('com,test,.*\)/[?&](abc=[^&]+).*[?&](id=[^&]+).*[?&](para=[^&]+)').pattern
'com,test,.*\\)/[?&](abc=[^&]+).*[?&](id=[^&]+).*[?&](para=[^&]+)'

"""


from pywb.cdx.cdxdomainspecific import CDXDomainSpecificRule
from pywb.cdx.cdxdomainspecific import load_domain_specific_cdx_rules


if __name__ == "__main__":
    import doctest
    doctest.testmod()
