"""Canonical attribute aliases used to normalize 1688 product data."""

from __future__ import annotations


ATTRIBUTE_ALIASES: dict[str, set[str]] = {
    "product_name": {
        "product_name",
        "title",
        "商品名称",
        "产品名称",
        "名称",
    },
    "brand": {
        "brand",
        "品牌",
        "牌子",
        "品牌名称",
        "thương hiệu",
        "thuong hieu",
        "hãng",
        "hang",
        "nhãn hiệu",
        "nhan hieu",
        "thæ°æ¡ng hiá»‡u",
    },
    "model": {
        "model",
        "型号",
        "产品型号",
        "款号",
        "số mặt hàng",
        "so mat hang",
        "mã model",
        "ma model",
        "mã sản phẩm",
        "ma san pham",
        "model number",
        "sá»‘ máº·t hÃ ng",
    },
    "color": {
        "color",
        "颜色",
        "颜色分类",
        "色号",
        "màu sắc",
        "mau sac",
        "màu",
        "mau",
        "mÃ u sáº¯c",
    },
    "size": {
        "size",
        "尺码",
        "尺寸",
        "kích thước",
        "kich thuoc",
        "kích thước sản phẩm",
        "kich thuoc san pham",
        "kích thước đóng gói",
        "kich thuoc dong goi",
        "product size",
        "product dimensions",
        "package size",
        "size option",
    },
    "material": {
        "material",
        "材质",
        "面料",
        "chất liệu",
        "chat lieu",
    },
    "ram": {
        "ram",
        "内存",
        "内存容量",
        "运行内存",
        "memory",
        "bộ nhớ",
        "bo nho",
        "dung lượng bộ nhớ",
        "dung luong bo nho",
        "dung lÆ°á»£ng bá»™ nhá»›",
    },
    "storage": {
        "storage",
        "硬盘容量",
        "存储",
        "存储容量",
        "disk capacity",
        "ổ cứng",
        "o cung",
        "dung lượng ổ cứng",
        "dung luong o cung",
        "ssd",
        "dung lÆ°á»£ng á»• cá»©ng",
    },
    "cpu": {
        "cpu",
        "处理器",
        "处理器型号",
        "processor",
        "loại cpu",
        "loai cpu",
        "bộ xử lý",
        "bo xu ly",
        "loáº¡i cpu",
        "bá»™ xá»­ lÃ½",
    },
    "screen_size": {
        "screen_size",
        "屏幕尺寸",
        "显示器尺寸",
        "screen size",
        "kích thước màn hình",
        "kich thuoc man hinh",
        "kÃ­ch thÆ°á»›c mÃ n hÃ¬nh",
    },
    "weight": {
        "weight",
        "重量",
        "净重",
        "trọng lượng",
        "trong luong",
        "cân nặng",
        "can nang",
        "cÃ¢n náº·ng",
        "trá»ng lÆ°á»£ng",
    },
}


def normalize_alias_key(value: object) -> str:
    """Normalize a raw attribute key before alias lookup."""
    text = str(value or "").strip().lower()
    return text.strip(" :.-_")


def build_alias_lookup() -> dict[str, str]:
    """Build a flat lookup of alias -> canonical field."""
    lookup: dict[str, str] = {}
    for canonical_field, aliases in ATTRIBUTE_ALIASES.items():
        lookup[normalize_alias_key(canonical_field)] = canonical_field
        for alias in aliases:
            lookup[normalize_alias_key(alias)] = canonical_field
    return lookup


ALIAS_LOOKUP = build_alias_lookup()
