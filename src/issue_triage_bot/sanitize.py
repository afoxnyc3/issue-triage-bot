"""Render model strings as bounded plain text, never active GitHub markup."""

import html
import re
import unicodedata
from html.parser import HTMLParser


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def sanitize(value: str, *, limit: int = 600) -> str:
    # Decode before stripping tags, so encoded HTML cannot become active afterward.
    for _ in range(3):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    parser = _TextOnly()
    parser.feed(value)
    parser.close()
    value = " ".join(parser.parts)
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", value)
    value = re.sub(r"(?i)\b(?:https?://|www\.|mailto:)[^\s<>]+", "", value)
    # The final character transform is the security boundary even for malformed or
    # nested markdown that the cosmetic substitutions above do not recognize.
    replacements: dict[str, str | int | None] = {
        "@": "＠",
        "#": "＃",
        "<": "＜",
        ">": "＞",
        "&": "＆",
        "[": "［",
        "]": "］",
        "*": "＊",
        "_": "＿",
        "`": "｀",
        chr(92): "＼",
        ":": "：",
        "/": "／",
        "!": "！",
    }
    value = value.translate(str.maketrans(replacements))
    value = "".join(c for c in value if not unicodedata.category(c).startswith("C") or c.isspace())
    return " ".join(value.split())[:limit]
