from io import BytesIO
from six.moves import zip

from pywb.rewrite.content_rewriter import BufferedRewriter


# ============================================================================
# Experimental: not fully tested
class RewriteAMF(BufferedRewriter):  #pragma: no cover
    def rewrite_stream(self, stream):
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

            # TODO: revisit this
            inputdata = url_rewriter.rewrite_opts.get('pywb.inputdata')

            if inputdata:
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


