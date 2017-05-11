from io import BytesIO
from six.moves import zip


# ============================================================================
# Experimental: not fully tested
class RewriteAMF(object):  #pragma: no cover
    def __call__(self, rwinfo):
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
            inputdata = rwinfo.url_rewriter.rewrite_opts.get('pywb.inputdata')

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
