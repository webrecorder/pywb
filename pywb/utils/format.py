from six.moves.urllib.parse import quote, parse_qsl
import string


# ============================================================================
class ParamFormatter(string.Formatter):
    def __init__(self, params, name='', prefix='param.'):
        self.params = params
        self.prefix = prefix
        self.name = name

    def get_value(self, key, args, kwargs):
        # First, try the named param 'param.{name}.{key}'
        if self.name:
            named_key = self.prefix + self.name + '.' + key
            value = self.params.get(named_key)
            if value is not None:
                return value

        # Then, try 'param.{key}'
        named_key = self.prefix + key
        value = self.params.get(named_key)
        if value is not None:
            return value

        # try in extra params as just {key}
        value = kwargs.get(key)
        if value is not None:
            return value

        # try in params as just '{key}'
        value = self.params.get(key, '')
        return value


# =============================================================================
def res_template(template, params, **extra_params):
    formatter = params.get('_formatter')
    if not formatter:
        formatter = ParamFormatter(params)

    url = params.get('url', '')
    qi = template.find('?')
    if qi >= 0 and template.find('{url}') > qi:
        url = quote(url)

    res = formatter.format(template, url=url, **extra_params)

    return res


# =============================================================================
def to_bool(val):
    if not val:
        return False

    if isinstance(val, str):
        return val.lower() not in ('0', 'false', 'f', 'off')
    else:
        return bool(val)


# =============================================================================
def query_to_dict(query_str, multi=None):
    pairlist = parse_qsl(query_str)
    if not multi:
        return dict(pairlist)

    obj = {}
    for n, v in pairlist:
        if n not in multi:
            obj[n] = v
            continue

        # make_list
        if n not in obj:
            obj[n] = v
        elif isinstance(obj[n], list):
            obj[n].append(v)
        else:
            obj[n] = [obj[n], v]

    return obj


