import pytest

from pywb.utils.amf_decoder import decode, AMFError
from pywb.warcserver.amf import Amf


def rep(data):
    return Amf.get_representation(decode(bytes.fromhex(data)))


# The encoded requests below were generated with py3AMF, and the expected
# representations are what py3AMF + Amf.get_representation() produced for
# them, to ensure lookup keys remain compatible.

# AMF0 request to 'UserService' with a typed object 'custom.object' {secret: 'a'}
CUSTOM_OBJECT_AMF0 = ('000000000001000b557365725365727669636500022f30000000000a'
                      '0000000110000d637573746f6d2e6f626a65637400067365637265740200016100'
                      '0009')

# an object containing itself
SELFREF_OBJ = ('000300000001000b557365725365727669636500022f30000000000a'
               '00000001110a0b010d7365637265740a0001')

# externalized small CommandMessage (DSC) with uuids
DSC = ('000300000001000b557365725365727669636500022f30000000000a00000001110a'
       '070744534384030603640c21000000000000000000000000000000020c2100000000'
       '00000000000000000000000101060363010405')

# [ArrayCollection(['x', 1.5, None, True]), ObjectProxy({'k': 'v'}), 'x', 'x',
#  datetime(2020, 1, 2, 3, 4, 5)]
MIXED_AMF3 = ('000300000001000b557365725365727669636500022f30000000000a00000005'
              '110a0743666c65782e6d6573736167696e672e696f2e4172726179436f6c6c65'
              '6374696f6e090901060378053ff80000000000000103110a073b666c65782e6d'
              '6573736167696e672e696f2e4f626a65637450726f78790a0b01036b06037601'
              '1106021106021108014276f6435cc88000')

# [1, 1.5, 'str', None, True, [1, 'a'], {'k': [1, 2]}, datetime(2020, 1, 2)]
TYPES_AMF0 = ('000000000001000b557365725365727669636500022f30000000000a00000008'
              '003ff0000000000000003ff80000000000000200037374720501010a00000002'
              '003ff0000000000000020001610300016b0a00000002003ff000000000000000'
              '40000000000000000000090b4276f638d44000000000')

# two requests, '/1' -> target 'b' [1] and '/2' -> target 'a' [2]
TWO_REQUESTS = ('00030000000200016200022f31000000000a0000000111040100016100022f'
                '32000000000a00000001110402')

# [RemotingMessage(operation='op', body=['x'], source=ByteArray(b'abc'))]
BYTEARRAY_IN_SOURCE = ('000300000001000353766300022f30000000000a00000001110a811b4f666c65'
                       '782e6d6573736167696e672e6d657373616765732e52656d6f74696e674d6573'
                       '7361676509626f647911636c69656e7449641764657374696e6174696f6e0f68'
                       '656164657273136d6573736167654964136f7065726174696f6e0d736f757263'
                       '651574696d65546f4c6976651374696d657374616d7009030106037801010a0b'
                       '010106036d06056f700c07616263010101')

# [RemotingMessage(operation='op', body=[ByteArray(b'abc')])]
BYTEARRAY_IN_BODY = ('000300000001000353766300022f30000000000a00000001110a811b4f666c65'
                     '782e6d6573736167696e672e6d657373616765732e52656d6f74696e674d6573'
                     '7361676509626f647911636c69656e7449641764657374696e6174696f6e0f68'
                     '656164657273136d6573736167654964136f7065726174696f6e0d736f757263'
                     '651574696d65546f4c6976651374696d657374616d700903010c076162630101'
                     '0a0b010106036d06056f7001010101')

# [ByteArray(b'abc')]
BYTEARRAY = '000300000001000353766300022f30000000000a00000001110c07616263'


class TestAmfDecoder(object):
    def test_response_not_parsed(self):
        # target ending in /onResult is a response, not a request
        data = bytes.fromhex('000300000001000c7376632f6f6e526573756c7400022f30'
                             '000000000a00000000')
        with pytest.raises(AMFError):
            decode(data)

    @pytest.mark.parametrize('data', [
        '',
        '0003',
        '000a00000000',
        # truncated body
        '000300000001000b557365725365727669636500022f30000000000a00000001110a0b',
        # unknown object reference
        '000300000001000b557365725365727669636500022f30000000000a00000001110a02',
        # unsupported AMF0 type
        '0000000000010001740000000000000a0000000104',
    ])
    def test_invalid(self, data):
        with pytest.raises(AMFError):
            decode(bytes.fromhex(data))

    def test_max_depth(self):
        depth = 1000
        data = (bytes.fromhex('00000000000100017400022f30000000000a00000001') +
                b'\x0a\x00\x00\x00\x01' * depth + b'\x05')

        with pytest.raises(AMFError):
            decode(data)

    def test_amf0_typed_object(self):
        assert rep(CUSTOM_OBJECT_AMF0) == \
               '<Envelope>[<Request target=UserService>[{"secret": "a"}]</Request>]</Envelope>'

    def test_self_reference_object(self):
        with pytest.raises(AMFError):
            rep(SELFREF_OBJ)

    def test_order_of_requests_ignored(self):
        assert rep(TWO_REQUESTS) == \
               '<Envelope>[<Request target=a>[2]</Request>,<Request target=b>[1]</Request>]</Envelope>'

    def test_small_message(self):
        assert rep(DSC) == (
            '<Envelope>[<Request target=UserService>[<CommandMessageExt>{'
            '"body": "", '
            '"clientId": "UUID(\'00000000-0000-0000-0000-000000000002\')", '
            '"correlationId": "c", "destination": "d", "headers": "{}", '
            '"messageId": "UUID(\'00000000-0000-0000-0000-000000000001\')", '
            '"operation": "5", "timeToLive": "", "timestamp": ""'
            '}</CommandMessageExt>]</Request>]</Envelope>')

    def test_amf3_types(self):
        assert rep(MIXED_AMF3) == (
            '<Envelope>[<Request target=UserService>[[x,1.5,,True],'
            '<ObjectProxy>{"_amf_object": "{\\"k\\": \\"v\\"}"}</ObjectProxy>,'
            'x,x,datetime.datetime(2020, 1, 2, 3, 4, 5)]</Request>]</Envelope>')

    def test_amf0_types(self):
        assert rep(TYPES_AMF0) == (
            '<Envelope>[<Request target=UserService>[1,1.5,str,,True,[1,a],'
            '{"k": [1, 2]},datetime.datetime(2020, 1, 2, 0, 0)]</Request>]</Envelope>')

    def test_shared_references_size_limit(self):
        # each list holds its child list twice, once inline and once by
        # reference, doubling the size of the representation at each level
        levels = 40

        def nested(k):
            if k == 0:
                return b'\x09\x01\x01'

            # index of the child list in the object reference table
            ref = levels - k + 1
            return b'\x09\x05\x01' + nested(k - 1) + b'\x09' + bytes([ref << 1])

        data = (bytes.fromhex('00030000000100017400022f30000000000a0000000111') +
                nested(levels))

        with pytest.raises(AMFError):
            decode(data)

    def test_bytearray_in_unused_property(self):
        assert rep(BYTEARRAY_IN_SOURCE) == \
               '<Envelope>[<Request target=Svc>[<RemotingMessage operation=op>[x]</RemotingMessage>]</Request>]</Envelope>'

    @pytest.mark.parametrize('data', [BYTEARRAY_IN_BODY, BYTEARRAY])
    def test_bytearray_not_represented(self, data):
        with pytest.raises(Exception, match='ByteArray'):
            rep(data)
