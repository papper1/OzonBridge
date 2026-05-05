def get_product_links(*args, **kwargs):
    from .search import get_product_links as impl

    return impl(*args, **kwargs)


def crawl_product(*args, **kwargs):
    from .product import crawl_product as impl

    return impl(*args, **kwargs)


def save_session(*args, **kwargs):
    from .session import save_session as impl

    return impl(*args, **kwargs)


def check_session_valid(*args, **kwargs):
    from .session import check_session_valid as impl

    return impl(*args, **kwargs)


def open_login_browser(*args, **kwargs):
    from .session import open_login_browser as impl

    return impl(*args, **kwargs)


def wait_for_manual_login(*args, **kwargs):
    from .session import wait_for_manual_login as impl

    return impl(*args, **kwargs)


def save_context_session(*args, **kwargs):
    from .session import save_context_session as impl

    return impl(*args, **kwargs)


__all__ = [
    "get_product_links",
    "crawl_product",
    "save_session",
    "check_session_valid",
    "open_login_browser",
    "wait_for_manual_login",
    "save_context_session",
]
