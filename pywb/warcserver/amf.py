import json
from pywb.utils.amf_decoder import Envelope, Request, AMFObject


class Amf:

    @staticmethod
    def get_representation(request_object, max_calls=500):

        max_calls = max_calls - 1

        if max_calls < 0:
            raise Exception("Amf.get_representation maximum number of calls reached")

        if isinstance(request_object, Envelope):
            # Remove order of Request
            bodies = []
            for i in request_object.bodies:
                bodies.append(Amf.get_representation(i[1], max_calls))
            bodies = sorted(bodies)

            return "<Envelope>{bodies}</Envelope>".format(bodies="[" + ",".join(bodies) + "]")

        elif isinstance(request_object, Request):
            # Remove cyclic reference
            target = request_object.target
            body = Amf.get_representation(request_object.body, max_calls)
            return "<Request target={target}>{body}</Request>".format(**locals())

        elif isinstance(request_object, AMFObject) and request_object.class_name == 'RemotingMessage':
            # Remove random properties
            operation = request_object.props['operation']
            body = Amf.get_representation(request_object.props['body'], max_calls)
            return "<RemotingMessage operation={operation}>{body}</RemotingMessage>".format(**locals())

        elif isinstance(request_object, dict):
            return json.dumps(request_object, sort_keys=True)

        elif isinstance(request_object, list):
            bodies = []
            for i in request_object:
                bodies.append(Amf.get_representation(i, max_calls))
            return "[" + ",".join(bodies) + "]"

        elif isinstance(request_object, str):
            return request_object

        elif request_object is None:
            return ""

        elif isinstance(request_object, AMFObject):
            classname = request_object.class_name
            properties = request_object.props
            bodies = dict()
            for prop in properties:
                bodies[prop] = Amf.get_representation(properties[prop], max_calls)
            bodies = Amf.get_representation(bodies, max_calls)

            return '<{classname}>{bodies}</{classname}>'.format(**locals())

        elif isinstance(request_object, bytearray):
            # py3AMF requests with a ByteArray here had no representation
            raise Exception("Amf.get_representation unsupported ByteArray")

        else:
            return repr(request_object)
