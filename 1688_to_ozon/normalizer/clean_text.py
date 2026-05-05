import re


MOJIBAKE_HINTS = (
    "\u00c3",
    "\u00c2",
    "\u00c4",
    "\u00c5",
    "\u00e6",
    "\u00e7",
    "\u00e8",
    "\u00e9",
    "\u00ea",
    "\u00f4",
    "\u00f5",
    "\u00f0",
)

MOJIBAKE_TIMES = "\u00c3\u2014"


def _encode_mojibake_bytes(text: str) -> bytes:
    """Reconstruct original bytes from mixed latin1/cp1252 mojibake text."""
    chunks = bytearray()
    for char in str(text):
        codepoint = ord(char)
        if codepoint <= 255:
            chunks.append(codepoint)
            continue
        chunks.extend(char.encode("cp1252"))
    return bytes(chunks)


def repair_mojibake(text: str) -> str:
    """Repair common UTF-8 text that was decoded as latin1/cp1252."""
    if not text:
        return ""

    repaired = str(text)
    for _ in range(2):
        if not any(hint in repaired for hint in MOJIBAKE_HINTS):
            break
        try:
            candidate = _encode_mojibake_bytes(repaired).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if candidate == repaired:
            break
        repaired = candidate
    return repaired


def normalize_resolution(text: str) -> str:
    """Normalize screen resolution values like 1920 x 1080."""
    if not text:
        return ""

    text = text.replace(MOJIBAKE_TIMES, "x").replace("*", "x")
    text = re.sub(r"(\d)\s*[xX]\s*(\d)", r"\1x\2", text)
    return text.strip()


def normalize_weight(text: str) -> str:
    """Normalize weight text like 1,8kg -> 1.8 kg."""
    if not text:
        return ""

    text = re.sub(r"(\d),(\d)\s*(kg|g|lb)\b", r"\1.\2 \3", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d(?:\.\d+)?)\s*(kg|g|lb)\b", r"\1 \2", text, flags=re.IGNORECASE)
    return text.strip()


def normalize_dimension(text: str) -> str:
    """Normalize dimension strings like 30 x20 x 2cm."""
    if not text:
        return ""

    text = text.replace(MOJIBAKE_TIMES, "x").replace("*", "x")
    text = re.sub(r"(\d)\s*[xX]\s*(\d)", r"\1 x \2", text)
    text = re.sub(r"(\d(?:\.\d+)?)\s*(cm|mm|m|inch|in)\b", r"\1 \2", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def extract_numeric_dimension_values(text: str) -> str:
    """Extract only numeric parts from dimension-like text."""
    normalized = normalize_dimension(text)
    if not normalized:
        return ""

    numbers = re.findall(r"\d+(?:\.\d+)?", normalized.replace(",", "."))
    return " ".join(numbers)


def normalize_storage_text(text: str) -> str:
    """Normalize storage strings like 512 gb ssd -> 512GB SSD."""
    if not text:
        return ""

    text = re.sub(r"(\d+)\s*(tb|gb|mb)\b", lambda m: f"{m.group(1)}{m.group(2).upper()}", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(ssd|hdd|emmc|nvme)\b", lambda m: m.group(1).upper(), text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    """Clean raw text crawled from 1688."""
    if not text:
        return ""

    text = repair_mojibake(str(text))
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = text.replace(MOJIBAKE_TIMES, "x")
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"(\d),(\d)\s*(kg|g|lb|cm|mm|m)\b", r"\1.\2 \3", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d(?:\.\d+)?)\s*(kg|g|lb|cm|mm|m|inch|in)\b", r"\1 \2", text, flags=re.IGNORECASE)

    text = normalize_resolution(text)
    text = normalize_weight(text)
    text = normalize_dimension(text)
    text = normalize_storage_text(text)

    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
