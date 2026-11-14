# Parts of this module are derived from PyAMF / py3AMF
# (https://github.com/StdCarrot/Py3AMF), used under the following licenses:
#
# Forked License (MIT License)
# Copyright (c) 2017 StdCarrot. Some rights reserved.
#
# Original License (MIT License)
# Copyright (c) 2007-2010 The PyAMF Project. All rights reserved.
#   - Arnar Birgisson
#   - Thijs Triemstra
#   - Nick Joyce
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
A small, data-only decoder for AMF (Action Message Format) remoting requests.
"""

import datetime
import struct
import uuid


MAX_DEPTH = 256
# Limits how many values a request may expand to through shared references,
# in addition to a few values per input byte
MAX_EXPANDED_VALUES = 100000

RESPONSE_SUFFIXES = ('/onResult', '/onStatus', '/onDebugEvents')

ARRAY_COLLECTION = 'flex.messaging.io.ArrayCollection'
OBJECT_PROXY = 'flex.messaging.io.ObjectProxy'

ABSTRACT = ('body', 'clientId', 'destination', 'headers', 'messageId', 'timestamp', 'timeToLive')
ASYNC = ABSTRACT + ('correlationId',)
COMMAND = ASYNC + ('operation',)
REMOTING = ABSTRACT + ('operation', 'source')
ERROR = ASYNC + ('extendedData', 'faultCode', 'faultDetail', 'faultString', 'rootCause')
SEQUENCED = ASYNC + ('sequenceId', 'sequenceProxies', 'sequenceSize', 'dataMessage')

# Flex message aliases:
# (class name, attributes, attributes required when decoded as a regular
# object, which parts of the externalized "small message" format it reads)
FLEX_MESSAGES = {
    'flex.messaging.messages.AbstractMessage': ('AbstractMessage', ABSTRACT, ABSTRACT, 'abstract'),
    'flex.messaging.messages.AsyncMessage': ('AsyncMessage', ASYNC, ASYNC, 'async'),
    'flex.messaging.messages.AcknowledgeMessage': ('AcknowledgeMessage', ASYNC, ASYNC, 'ack'),
    'flex.messaging.messages.CommandMessage': ('CommandMessage', COMMAND, COMMAND, 'command'),
    'flex.messaging.messages.ErrorMessage': ('ErrorMessage', ERROR, ERROR, 'ack'),
    'flex.messaging.messages.RemotingMessage': ('RemotingMessage', REMOTING, REMOTING, 'abstract'),
    'flex.data.messages.DataMessage': ('DataMessage', ASYNC + ('identity', 'operation'), ASYNC, 'async'),
    'flex.data.messages.SequencedMessage': ('SequencedMessage', SEQUENCED, ASYNC, 'ack'),
    'flex.data.messages.PagedMessage': ('PagedMessage', SEQUENCED + ('pageCount', 'pageIndex'), ASYNC, 'ack'),
    'flex.data.messages.DataErrorMessage': ('DataErrorMessage', ERROR + ('cause', 'propertyNames', 'serverObject'),
                                            ERROR, 'ack'),
    'DSK': ('AcknowledgeMessageExt', ASYNC, (), 'ack'),
    'DSC': ('CommandMessageExt', COMMAND, (), 'command'),
    'DSA': ('AsyncMessageExt', ASYNC, (), 'async'),
}


class AMFError(Exception):
    pass


# ============================================================================
class Envelope(object):
    def __init__(self, version):
        self.version = version
        # (response name, Request) pairs
        self.bodies = []


class Request(object):
    def __init__(self, target, body):
        self.target = target
        self.body = body or []


class AMFObject(object):
    """ A typed object: a class name and a dict of properties, which is all
    that its representation uses """
    def __init__(self, class_name, props):
        self.class_name = class_name
        self.props = props


class UndefinedType(AMFObject):
    def __init__(self):
        AMFObject.__init__(self, 'UndefinedType', {})

    def __repr__(self):
        return 'pyamf.Undefined'


UNDEFINED = UndefinedType()


class ASObject(dict):
    """ An anonymous object: a dict that is hashable by identity """
    __hash__ = object.__hash__


class ArrayCollection(list):
    def __repr__(self):
        return '<flex.messaging.io.ArrayCollection %s>' % list.__repr__(self)


class ObjectProxy(AMFObject):
    def __init__(self):
        AMFObject.__init__(self, 'ObjectProxy', {'_amf_object': None})

    def __repr__(self):
        return '<flex.messaging.io.ObjectProxy %r>' % (self.props['_amf_object'],)


class FlexMessage(AMFObject):
    def __init__(self, alias):
        class_name, attr_names, self.required, self.small_format = FLEX_MESSAGES[alias]
        props = {}
        for name in attr_names:
            props[name] = {} if name in ('headers', 'extendedData', 'rootCause') else None

        AMFObject.__init__(self, class_name, props)

    def __repr__(self):
        return '<%s %s />' % (self.class_name, ''.join(' %s=%r' % item for item in self.props.items()))


def _to_datetime(secs):
    return datetime.datetime.fromtimestamp(secs, datetime.timezone.utc).replace(tzinfo=None)


def _to_uuid(value):
    # Flex sends uuids as 16 byte ByteArrays
    if not isinstance(value, bytearray):
        raise AMFError('Expected a ByteArray for a uuid')

    return uuid.UUID(bytes=bytes(value))


def _new_object(alias):
    if alias in FLEX_MESSAGES:
        return FlexMessage(alias)
    if alias == ARRAY_COLLECTION:
        return ArrayCollection()
    if alias == OBJECT_PROXY:
        return ObjectProxy()

    return {}


def _set_properties(obj, props):
    """ Set the properties of an object that was not externalized """
    if isinstance(obj, FlexMessage):
        missing = set(obj.required) - set(props)
        if missing:
            raise AMFError('Missing properties %r for %s' % (sorted(missing), obj.class_name))

        obj.props.update(props)

    elif isinstance(obj, ArrayCollection):
        if set(props) - {'length'}:
            raise AMFError('Unexpected ArrayCollection properties')

    elif isinstance(obj, ObjectProxy):
        raise AMFError('ObjectProxy must be externalized')

    else:
        obj.update(props)


def _collection_items(value):
    """ The items of an externalized ArrayCollection """
    inner = value
    while isinstance(inner, ObjectProxy):
        inner = inner.props['_amf_object']

    if isinstance(inner, FlexMessage) and 'source' in inner.props:
        return inner.props['source']

    if isinstance(value, ASObject) and 'source' in value:
        return value['source']

    if isinstance(value, (list, str, dict, tuple)):
        return value

    raise AMFError('Unable to read a list for ArrayCollection')


# ============================================================================
class _Stream(object):
    """ The input, shared by the AMF0 and AMF3 decoders """
    def __init__(self, data):
        self.data = bytes(data)
        self.pos = 0
        self.depth = 0

    def read(self, length):
        if self.pos + length > len(self.data):
            raise AMFError('Unexpected end of data')

        self.pos += length
        return self.data[self.pos - length:self.pos]

    def peek(self):
        return self.data[self.pos:self.pos + 1]

    def unpack(self, fmt):
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))[0]


class _BaseDecoder(object):
    READERS = {}

    def __init__(self, stream):
        self.stream = stream
        self.read = stream.read
        self.peek = stream.peek
        self.unpack = stream.unpack
        self.reset()

    def read_value(self):
        self.stream.depth += 1
        try:
            if self.stream.depth > MAX_DEPTH:
                raise AMFError('Maximum nesting depth exceeded')

            marker = self.read(1)[0]
            reader = self.READERS.get(marker)
            if not reader:
                raise AMFError('Unsupported type 0x%02x' % marker)

            return reader(self)
        finally:
            self.stream.depth -= 1


# ============================================================================
class _AMF0Decoder(_BaseDecoder):
    def __init__(self, stream):
        self.amf3 = _AMF3Decoder(stream)
        _BaseDecoder.__init__(self, stream)

    def reset(self):
        self.refs = []
        self.amf3.reset()

    def read_string(self, length_format='>H'):
        return self.read(self.unpack(length_format)).decode('utf-8')

    def read_number(self):
        # AMF0 does not distinguish integers and floats
        value = self.unpack('>d')
        try:
            if value == int(value):
                return int(value)
        except (OverflowError, ValueError):
            pass

        return value

    def read_properties(self):
        props = {}
        key = self.read_string()
        while self.peek() != b'\x09':
            props[key] = self.read_value()
            key = self.read_string()

        self.read(1)
        return props

    def read_object(self, obj):
        self.refs.append(obj)
        _set_properties(obj, self.read_properties())
        return obj

    def read_reference(self):
        index = self.unpack('>H')
        if index >= len(self.refs):
            raise AMFError('Unknown reference')

        return self.refs[index]

    def read_ecma_array(self):
        self.read(4)
        obj = {}
        self.refs.append(obj)
        for key, value in self.read_properties().items():
            try:
                key = int(key)
            except ValueError:
                pass

            obj[key] = value

        return obj

    def read_array(self):
        obj = []
        self.refs.append(obj)
        for i in range(self.unpack('>L')):
            obj.append(self.read_value())

        return obj

    def read_date(self):
        secs = self.unpack('>d') / 1000.0
        # timezone, ignored
        self.read(2)
        obj = _to_datetime(secs)
        self.refs.append(obj)
        return obj

    def read_xml(self):
        # XML is kept as text, it is not parsed
        obj = self.read_string('>L')
        self.refs.append(obj)
        return obj

    READERS = {
        0x00: read_number,
        0x01: lambda d: bool(d.unpack('>B')),
        0x02: read_string,
        0x03: lambda d: d.read_object(ASObject()),
        0x05: lambda d: None,
        0x06: lambda d: UNDEFINED,
        0x07: read_reference,
        0x08: read_ecma_array,
        0x0a: read_array,
        0x0b: read_date,
        0x0c: lambda d: d.read_string('>L'),
        0x0d: lambda d: None,
        0x0f: read_xml,
        0x10: lambda d: d.read_object(_new_object(d.read_string())),
        0x11: lambda d: d.amf3.read_value(),
    }


# ============================================================================
class _AMF3Decoder(_BaseDecoder):
    def reset(self):
        self.refs = []
        self.strings = []
        self.traits = []

    def read_int(self, signed=False):
        result = 0
        for i in range(3):
            byte = self.unpack('>B')
            if not byte & 0x80:
                return (result << 7) | byte

            result = (result << 7) | (byte & 0x7f)

        result = (result << 8) | self.unpack('>B')
        if result & 0x10000000:
            result = result - 0x20000000 if signed else (result << 1) + 1

        return result

    def read_header(self):
        """ Returns (value, is_reference) """
        header = self.read_int()
        return header >> 1, not header & 1

    def get_ref(self, index):
        return self.refs[index] if index < len(self.refs) else None

    def add_ref(self, obj):
        self.refs.append(obj)
        return obj

    def read_raw_string(self):
        """ Returns bytes, or None for an unknown string reference """
        length, is_ref = self.read_header()
        if is_ref:
            return self.strings[length] if length < len(self.strings) else None

        if length == 0:
            return b''

        self.strings.append(self.read(length))
        return self.strings[-1]

    def read_string(self):
        value = self.read_raw_string()
        if value is None:
            raise AMFError('Unknown string reference')

        return value.decode('utf-8')

    def read_referenceable(self, read_new):
        """ Reads a reference to an earlier object, or a new object with
        read_new(length) """
        length, is_ref = self.read_header()
        if is_ref:
            return self.get_ref(length)

        return self.add_ref(read_new(length))

    def read_date(self):
        return self.read_referenceable(lambda unused: _to_datetime(self.unpack('>d') / 1000.0))

    def read_array(self):
        size, is_ref = self.read_header()
        if is_ref:
            return self.get_ref(size)

        key = self.read_raw_string()
        if key == b'':
            obj = self.add_ref([])
            for i in range(size):
                obj.append(self.read_value())

            return obj

        # an unknown string reference also ends the associative part
        obj = self.add_ref({})
        while key:
            obj[key.decode('utf-8')] = self.read_value()
            key = self.read_raw_string()

        for i in range(size):
            obj[i] = self.read_value()

        return obj

    def read_traits(self, header):
        if not header & 1:
            if header >> 1 >= len(self.traits):
                raise AMFError('Unknown traits reference')

            return self.traits[header >> 1]

        name = self.read_raw_string()
        alias = None if name is None else name.decode('utf-8')
        encoding = (header >> 1) & 0x03
        sealed_names = [self.read_string() for i in range(header >> 3)]

        self.traits.append((alias, encoding, sealed_names))
        return self.traits[-1]

    def read_object(self):
        header, is_ref = self.read_header()
        if is_ref:
            if header >= len(self.refs):
                raise AMFError('Unknown reference')

            return self.refs[header]

        alias, encoding, sealed_names = self.read_traits(header)
        obj = self.add_ref(ASObject() if alias == '' else _new_object(alias))

        # externalizable
        if encoding & 0x01:
            self.read_externalized(obj)
            return obj

        props = {}
        for name in sealed_names:
            props[name] = self.read_value()

        # dynamic
        if encoding == 0x02:
            key = self.read_raw_string()
            while key:
                props[key.decode('utf-8')] = self.read_value()
                key = self.read_raw_string()

        _set_properties(obj, props)
        return obj

    def read_externalized(self, obj):
        if isinstance(obj, FlexMessage):
            self.read_small_message(obj)

        elif isinstance(obj, ArrayCollection):
            obj.extend(_collection_items(self.read_value()))

        elif isinstance(obj, ObjectProxy):
            value = self.read_value()
            obj.props['_amf_object'] = dict(value) if isinstance(value, dict) else value

        else:
            raise AMFError('Unable to read externalized object')

    def read_flags(self, max_count):
        flags = [self.unpack('>B')]
        while flags[-1] & 0x80:
            flags[-1] &= 0x7f
            flags.append(self.unpack('>B'))

        if len(flags) > max_count:
            raise AMFError('Unexpected small message flags')

        return flags

    def read_small_message(self, msg):
        flags = self.read_flags(2)

        for bit, name in enumerate(ABSTRACT):
            if flags[0] & (1 << bit):
                value = self.read_value()
                if name in ('timestamp', 'timeToLive'):
                    value = _to_datetime(value / 1000.0)

                msg.props[name] = value

        if len(flags) > 1:
            for bit, name in enumerate(('clientId', 'messageId')):
                if flags[1] & (1 << bit):
                    msg.props[name] = _to_uuid(self.read_value())

        if msg.small_format == 'abstract':
            return

        flags = self.read_flags(1)
        if flags[0] & 0x01:
            msg.props['correlationId'] = self.read_value()
        if flags[0] & 0x02:
            msg.props['correlationId'] = _to_uuid(self.read_value())

        if msg.small_format == 'ack':
            self.read_flags(1)

        elif msg.small_format == 'command':
            if self.read_flags(1)[0] & 0x01:
                msg.props['operation'] = self.read_value()

    def read_xml(self):
        return self.read_referenceable(lambda length: self.read(length).decode('utf-8'))

    def read_bytearray(self):
        return self.read_referenceable(lambda length: bytearray(self.read(length)))

    def read_dictionary(self):
        length = self.read_int(True) >> 1
        weak_keys = self.read(1)
        if weak_keys not in (b'\x00', b'\x01'):
            raise AMFError('Invalid boolean')

        obj = {}
        for i in range(length):
            key = self.read_value()
            obj[key] = self.read_value()

        return obj, weak_keys == b'\x01'

    READERS = {
        0x00: lambda d: UNDEFINED,
        0x01: lambda d: None,
        0x02: lambda d: False,
        0x03: lambda d: True,
        0x04: lambda d: d.read_int(True),
        0x05: lambda d: d.unpack('>d'),
        0x06: read_string,
        0x07: read_xml,
        0x08: read_date,
        0x09: read_array,
        0x0a: read_object,
        0x0b: read_xml,
        0x0c: read_bytearray,
        0x11: read_dictionary,
    }


def decode(data):
    """ Decode an AMF remoting request, from bytes or a file-like object, into
    an Envelope """
    if hasattr(data, 'read'):
        data = data.read()

    decoder = _AMF0Decoder(_Stream(data))

    envelope = Envelope(decoder.unpack('>H'))
    if envelope.version > 9:
        raise AMFError('Invalid AMF version %d' % envelope.version)

    # headers are not used, but must be valid
    for i in range(decoder.unpack('>H')):
        decoder.read_string()
        # required flag and length
        decoder.read(5)
        decoder.read_value()

    # response name -> Request, a repeated name replaces the earlier request
    requests = {}

    for i in range(decoder.unpack('>h')):
        decoder.reset()

        target = decoder.read_string()
        response = decoder.read_string()
        if target.endswith(RESPONSE_SUFFIXES):
            raise AMFError('Not an AMF request')

        # length
        decoder.read(4)

        if decoder.peek() == b'\x11' and envelope.version == 3:
            body = decoder.read_value()
        elif decoder.peek() == b'\x0a':
            decoder.read(1)
            body = [decoder.read_value() for i in range(decoder.unpack('>L'))]
        else:
            raise AMFError('Request body must be an array')

        requests[response] = Request(target, body)

    envelope.bodies = list(requests.items())

    _check_expanded_size(envelope, len(decoder.stream.data))
    return envelope


def _check_expanded_size(envelope, data_length):
    """ Shared references let a small request expand to an exponentially
    larger structure, so limit the number of values reachable from the
    envelope. Without shared references there are only a few per input byte.
    """
    limit = MAX_EXPANDED_VALUES + 10 * data_length
    pending = [envelope]

    while pending:
        limit -= 1
        if limit < 0:
            raise AMFError('AMF request expands to too many values')

        obj = pending.pop()

        if isinstance(obj, Envelope):
            pending.extend(request for name, request in obj.bodies)
        elif isinstance(obj, Request):
            pending.append(obj.body)
        elif isinstance(obj, AMFObject):
            pending.extend(obj.props.values())
        elif isinstance(obj, dict):
            pending.extend(obj.keys())
            pending.extend(obj.values())
        elif isinstance(obj, (list, tuple)):
            pending.extend(obj)
