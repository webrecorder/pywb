from pywb.warcserver.amf import Amf

import pyamf
import uuid

from io import BytesIO
from pyamf.remoting import Envelope, Request, encode, decode
from pyamf.flex.messaging import RemotingMessage


class CustomObject:
    secret = None


pyamf.register_class(CustomObject, "custom.object")


def generate_amf_request(request_body=None):
    req = Request(target='UserService', body=request_body)
    ev = Envelope(pyamf.AMF3)
    ev['/0'] = req

    return encode(ev).getvalue()


def generate_flex_request(message_body=None):
    msg = RemotingMessage(operation='retrieveUser',
                          messageId=str(uuid.uuid4()).upper(),
                          body=message_body)
    return generate_amf_request([msg])


class TestAmf(object):

    def test_can_parse_custom_object(self):
        a = CustomObject()
        a.secret = "a"

        encoded = generate_amf_request(request_body=[a])
        decoded = decode(BytesIO(encoded))

        assert Amf.get_representation(decoded) == \
               '<Envelope>[<Request target=UserService>[<CustomObject>{"secret": "a"}</CustomObject>]</Request>]</Envelope>'

    def test_parse_amf_request_with_envelope(self):
        encoded = generate_amf_request([{"the": "body"}])
        decoded = decode(BytesIO(encoded))
        assert Amf.get_representation(decoded) == \
               '<Envelope>[<Request target=UserService>[{"the": "body"}]</Request>]</Envelope>'

    def test_parse_flex_request_with_envelope(self):
        encoded = generate_flex_request([{"the": "body"}])
        decoded = decode(BytesIO(encoded))
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
        a = CustomObject()
        a.secret = a

        encoded = generate_amf_request(request_body=[a])
        decoded = decode(BytesIO(encoded))
        try:
            Amf.get_representation(decoded)
            assert False, "should not be called"
        except Exception as e:
            assert "maximum number of calls reached" in str(e)
