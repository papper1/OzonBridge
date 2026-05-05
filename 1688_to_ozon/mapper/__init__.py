def map_attributes_to_ozon(*args, **kwargs):
    from .attribute_mapper import map_attributes_to_ozon as impl

    return impl(*args, **kwargs)


def map_category_to_ozon(*args, **kwargs):
    from .category_mapper import map_category_to_ozon as impl

    return impl(*args, **kwargs)


def map_product_to_ozon(*args, **kwargs):
    from .product_mapper import map_product_to_ozon as impl

    return impl(*args, **kwargs)


__all__ = [
    "map_attributes_to_ozon",
    "map_category_to_ozon",
    "map_product_to_ozon",
]
