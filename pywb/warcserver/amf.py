import json
import six
from pyamf.remoting import Envelope, Request
from pyamf.flex.messaging import RemotingMessage


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

        elif isinstance(request_object, RemotingMessage):
            # Remove random properties
            operation = request_object.operation
            body = Amf.get_representation(request_object.body, max_calls)
            return "<RemotingMessage operation={operation}>{body}</RemotingMessage>".format(**locals())

        elif isinstance(request_object, dict):
            return json.dumps(request_object, sort_keys=True)

        elif isinstance(request_object, list):
            bodies = []
            for i in request_object:
                bodies.append(Amf.get_representation(i, max_calls))
            return "[" + ",".join(bodies) + "]"

        elif isinstance(request_object, six.string_types):
            return request_object

        elif request_object is None:
            return ""

        elif isinstance(request_object, object) and hasattr(request_object, "__dict__"):
            classname = request_object.__class__.__name__
            properties = request_object.__dict__
            bodies = dict()
            for prop in properties:
                bodies[prop] = Amf.get_representation(getattr(request_object, prop), max_calls)
            bodies = Amf.get_representation(bodies, max_calls)

            return '<{classname}>{bodies}</{classname}>'.format(**locals())

        else:
            return repr(request_object)
