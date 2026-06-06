# encoding:utf-8

"""
Minimal Chinese-only i18n stub. Always returns simplified Chinese text.
Kept as a drop-in replacement so existing t(zh, en) / _t(zh, en)
callsites continue to work without changes.
"""

ZH = "zh"
ZH_HANT = "zh-Hant"
EN = "en"
SUPPORTED = (ZH,)
DEFAULT_LANG = ZH


def detect_language():
    return ZH


def resolve_language(configured=None):
    return ZH


def set_language(lang):
    return ZH


def get_language():
    return ZH


def is_zh():
    return True


def t(zh_text, en_text):
    """Always return Chinese text, ignoring the English fallback."""
    return zh_text
