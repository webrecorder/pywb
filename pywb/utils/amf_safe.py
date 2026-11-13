"""Per-request PyAMF decoding without implicit class loading.

Only aliases already present in pyamf.CLASS_CACHE can instantiate classes.
Unknown aliases become pyamf.TypedObject instances. Decoder-local subclasses
retain each alias for re-encoding without modifying global registries/loaders.
"""

from io import BytesIO

import pyamf
from pyamf import amf0, amf3, remoting

# Make PyAMF's known Flex implementations available through their ordinary
# explicit registrations, never through input-driven class loaders/imports.
import pyamf.flex  # noqa: F401
import pyamf.flex.messaging  # noqa: F401
import pyamf.flex.data  # noqa: F401


class AliasPolicy:
    """Cache-only registered aliases and decoder-local generic aliases."""

    def __init__(self, strict=False):
        self.strict = strict
        self.generic = {}

    def get(self, alias):
        if isinstance(alias, bytes):
            alias = alias.decode("utf-8")

        try:
            # pyamf.get_class_alias() is unsafe here: it invokes custom class
            # loaders and imports arbitrary dotted module names from input.
            return pyamf.CLASS_CACHE[alias]
        except KeyError:
            pass

        if self.strict:
            raise pyamf.UnknownClassAlias("Unknown alias for %r" % (alias,))

        try:
            return self.generic[alias]
        except KeyError:
            pass

        # TypedObject itself loses its alias when encoded because PyAMF looks
        # up aliases by Python class. A local subclass carries the alias on
        # the class, allowing Safe*Context to restore it during encoding.
        klass = type("SafeTypedObject", (pyamf.TypedObject,), {
            "__amf_alias__": alias,
            "__module__": __name__,
        })
        class_alias = pyamf.TypedObjectClassAlias(alias)
        class_alias.klass = klass
        self.generic[alias] = class_alias
        return class_alias


def _generic_class_alias(klass):
    if not isinstance(klass, type) or not issubclass(klass, pyamf.TypedObject):
        return None

    alias = klass.__dict__.get("__amf_alias__")
    if alias is None:
        return None

    class_alias = pyamf.TypedObjectClassAlias(alias)
    class_alias.klass = klass
    return class_alias


class SafeAMF3Context(amf3.Context):
    def __init__(self, alias_policy=None, **kwargs):
        self.alias_policy = alias_policy or AliasPolicy()
        super().__init__(**kwargs)

    def getClassAlias(self, klass):
        if isinstance(klass, (str, bytes)):
            return self.alias_policy.get(klass)

        generic = _generic_class_alias(klass)
        return generic or super().getClassAlias(klass)


class SafeAMF3Decoder(amf3.Decoder):
    """AMF3 decoder with cache-only class alias resolution."""

    def __init__(self, *args, **kwargs):
        strict = kwargs.get("strict", False)
        super().__init__(*args, **kwargs)
        self.context.alias_policy.strict = strict

    def buildContext(self, **kwargs):
        return SafeAMF3Context(**kwargs)

    def _getClassDefinition(self, ref):
        # PyAMF 0.9.1 calls pyamf.get_class_alias() directly here, bypassing
        # codec.Context.getClassAlias(), so overriding only Context is unsafe.
        is_ref = ref & amf3.REFERENCE_BIT == 0
        ref >>= 1

        if is_ref:
            return self.context.getClassByReference(ref)

        name = self.readBytes()
        if name == "":
            name = pyamf.ASObject

        alias = self.context.getClassAlias(name)
        class_def = amf3.ClassDefinition(alias)
        class_def.encoding = ref & 0x03
        class_def.attr_len = ref >> 2
        class_def.static_properties = []

        for _ in range(class_def.attr_len):
            class_def.static_properties.append(self.readString())

        self.context.addClass(class_def, alias.klass)
        return class_def


class SafeAMF0Context(amf0.Context):
    """AMF0 context that also secures AMF3 decoder/encoder switching."""

    def __init__(self, alias_strict=False, **kwargs):
        self.alias_policy = AliasPolicy(strict=alias_strict)
        super().__init__(**kwargs)

    def getClassAlias(self, klass):
        if isinstance(klass, (str, bytes)):
            return self.alias_policy.get(klass)

        generic = _generic_class_alias(klass)
        return generic or super().getClassAlias(klass)

    def getAMF3Decoder(self, amf0_decoder):
        decoder = self.extra.get("amf3_decoder")
        if decoder is not None:
            return decoder

        decoder = SafeAMF3Decoder(
            stream=amf0_decoder.stream,
            timezone_offset=amf0_decoder.timezone_offset,
            strict=amf0_decoder.strict,
            context=SafeAMF3Context(alias_policy=self.alias_policy),
        )
        self.extra["amf3_decoder"] = decoder
        return decoder

    def getAMF3Encoder(self, amf0_encoder):
        encoder = self.extra.get("amf3_encoder")
        if encoder is not None:
            return encoder

        encoder = amf3.Encoder(
            stream=amf0_encoder.stream,
            timezone_offset=amf0_encoder.timezone_offset,
            context=SafeAMF3Context(alias_policy=self.alias_policy),
        )
        self.extra["amf3_encoder"] = encoder
        return encoder


def decode(stream, **kwargs):
    """Decode one remoting envelope with an isolated safe AMF0/AMF3 context."""
    if isinstance(stream, (bytes, bytearray)):
        stream = BytesIO(stream)

    # The safe subclasses are pure Python. Never allow cpyamf to bypass them.
    kwargs.pop("context", None)
    kwargs.pop("use_ext", None)
    return remoting.decode(
        stream,
        context=SafeAMF0Context(alias_strict=kwargs.get("strict", False)),
        use_ext=False,
        **kwargs,
    )


def encode(message, **kwargs):
    """Encode an envelope, retaining aliases of decoder-local TypedObjects."""
    kwargs.pop("context", None)
    kwargs.pop("use_ext", None)
    return remoting.encode(
        message,
        context=SafeAMF0Context(),
        use_ext=False,
        **kwargs,
    )
