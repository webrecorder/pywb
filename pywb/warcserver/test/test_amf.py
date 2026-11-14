from pywb.warcserver.amf import Amf

from io import BytesIO
from pywb.utils.amf_decoder import Request, decode


# AMF3 requests to 'UserService', as generated with py3AMF

# body [CustomObject(secret='a')], where CustomObject has the alias 'custom.object'
CUSTOM_OBJECT_REQUEST = bytes.fromhex(
    '000300000001000b557365725365727669636500022f30000000000a00000001110a0b1b'
    '637573746f6d2e6f626a6563740d73656372657406036101')

# body [{'the': 'body'}]
AMF_REQUEST = bytes.fromhex(
    '000300000001000b557365725365727669636500022f30000000000a00000001110a0b01'
    '077468650609626f647901')

# body [RemotingMessage(operation='retrieveUser', body=[{'the': 'body'}])]
FLEX_REQUEST = bytes.fromhex(
    '000300000001000b557365725365727669636500022f30000000000a00000001110a811b'
    '4f666c65782e6d6573736167696e672e6d657373616765732e52656d6f74696e674d6573'
    '7361676509626f647911636c69656e7449641764657374696e6174696f6e0f6865616465'
    '7273136d6573736167654964136f7065726174696f6e0d736f757263651574696d65546f'
    '4c6976651374696d657374616d700903010a0b010774686506020101010a050106493842'
    '3245314237442d303030302d343030302d383030302d3030303030303030303030310619'
    '72657472696576655573657201010101')


class TestAmf(object):

    def test_can_parse_custom_object(self):
        decoded = decode(BytesIO(CUSTOM_OBJECT_REQUEST))

        # class aliases are never resolved, so typed objects are plain dicts
        assert Amf.get_representation(decoded) == \
               '<Envelope>[<Request target=UserService>[{"secret": "a"}]</Request>]</Envelope>'

    def test_parse_amf_request_with_envelope(self):
        decoded = decode(BytesIO(AMF_REQUEST))
        assert Amf.get_representation(decoded) == \
               '<Envelope>[<Request target=UserService>[{"the": "body"}]</Request>]</Envelope>'

    def test_parse_flex_request_with_envelope(self):
        decoded = decode(BytesIO(FLEX_REQUEST))
        assert Amf.get_representation(decoded) == \
               '<Envelope>[<Request target=UserService>[<RemotingMessage operation=retrieveUser>[{"the": "body"}]</RemotingMessage>]</Request>]</Envelope>'

    def test_position_in_dict_ignored(self):
        a = Request(target=None, body={"a": 1, "b": 2})
        b = Request(target=None, body={"b": 2, "a": 1})
        c = Request(target=None, body={"a": 2, "b": 1})

        assert Amf.get_representation(a) == Amf.get_representation(b)
        assert Amf.get_representation(a) != Amf.get_representation(c)

    def test_order_of_array_preserved(self):
        a = Request(target=None, body=[1, 2])
        b = Request(target=None, body=[2, 1])

        assert Amf.get_representation(a) != Amf.get_representation(b)

    def test_limit_recursive_calls(self):
        a = []
        a.append(a)

        try:
            Amf.get_representation(Request(target=None, body=[a]))
            assert False, "should not be called"
        except Exception as e:
            assert "maximum number of calls reached" in str(e)
