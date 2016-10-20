from io import BytesIO
from six.moves import zip
from pywb.rewrite.rewrite_content import RewriteContent


# ============================================================================
# Expiermental: not fully tested
class RewriteContentAMF(RewriteContent):  #pragma: no cover
    def handle_custom_rewrite(self, rewritten_headers, stream, urlrewriter, mod, env):
        if rewritten_headers.status_headers.get_header('Content-Type') == 'application/x-amf':
            stream = self.rewrite_amf(stream, env)

        return (super(RewriteContentAMF, self).
                handle_custom_rewrite(rewritten_headers, stream, urlrewriter, mod, env))

    def rewrite_amf(self, stream, env):
        try:
            from pyamf import remoting

            iobuff = BytesIO()
            while True:
                buff = stream.read()
                if not buff:
                    break
                iobuff.write(buff)

            iobuff.seek(0)
            res = remoting.decode(iobuff)

            if env and env.get('pywb.inputdata'):
                inputdata = env.get('pywb.inputdata')

                new_list = []

                for src, target in zip(inputdata.bodies, res.bodies):
                    #print(target[0] + ' = ' + src[0])

                    #print('messageId => corrId ' + target[1].body.correlationId + ' => ' + src[1].body[0].messageId)
                    target[1].body.correlationId = src[1].body[0].messageId

                    new_list.append((src[0], target[1]))

                res.bodies = new_list

            return BytesIO(remoting.encode(res).getvalue())

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
            return stream
