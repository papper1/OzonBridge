def clean_text(*args, **kwargs):
    from .clean_text import clean_text as impl

    return impl(*args, **kwargs)


def normalize_attributes(*args, **kwargs):
    from .normalize_attributes import normalize_attributes as impl

    return impl(*args, **kwargs)


def build_variants(*args, **kwargs):
    from .build_variants import build_variants as impl

    return impl(*args, **kwargs)


def translate_text(*args, **kwargs):
    from .translate import translate_text as impl

    return impl(*args, **kwargs)


__all__ = [
    "clean_text",
    "normalize_attributes",
    "build_variants",
    "translate_text",
]
