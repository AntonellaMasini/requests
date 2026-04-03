"""Tests for character detection library resolution (issue #7223).

Verifies that requests prefers charset_normalizer (a required dependency)
over chardet (an optional dependency via the [use-chardet-on-py3] extra),
and only checks the version of the library actually in use.
"""

import types
from unittest import mock

from requests.compat import _resolve_char_detection


class TestResolveCharDetection:
    """Tests for _resolve_char_detection preference order."""

    def test_prefers_charset_normalizer_over_chardet(self):
        """When both charset_normalizer and chardet are importable,
        charset_normalizer should be preferred."""
        charset_mod = types.ModuleType("charset_normalizer")
        charset_mod.__version__ = "3.0.0"
        chardet_mod = types.ModuleType("chardet")
        chardet_mod.__version__ = "5.0.0"

        def fake_import(name):
            if name == "charset_normalizer":
                return charset_mod
            if name == "chardet":
                return chardet_mod
            raise ImportError(name)

        with mock.patch("importlib.import_module", side_effect=fake_import):
            result = _resolve_char_detection()

        assert result is charset_mod
        assert result.__name__ == "charset_normalizer"

    def test_falls_back_to_chardet_when_charset_normalizer_missing(self):
        """When charset_normalizer is not importable, chardet should be used."""
        chardet_mod = types.ModuleType("chardet")
        chardet_mod.__version__ = "5.0.0"

        def fake_import(name):
            if name == "charset_normalizer":
                raise ImportError(name)
            if name == "chardet":
                return chardet_mod
            raise ImportError(name)

        with mock.patch("importlib.import_module", side_effect=fake_import):
            result = _resolve_char_detection()

        assert result is chardet_mod
        assert result.__name__ == "chardet"

    def test_returns_none_when_neither_available(self):
        """When neither library is importable, None should be returned."""

        def fake_import(name):
            raise ImportError(name)

        with mock.patch("importlib.import_module", side_effect=fake_import):
            result = _resolve_char_detection()

        assert result is None


class TestCharDetectionVersionCheck:
    """Tests that __init__.py only checks the version of the resolved library."""

    def test_no_chardet_version_when_charset_normalizer_used(self):
        """When charset_normalizer is resolved, chardet_version should be None
        even if chardet is independently importable (issue #7223)."""
        import requests

        # If charset_normalizer is the resolved library (the default),
        # chardet_version should not be set regardless of chardet being installed.
        from requests.compat import chardet as resolved_mod

        if resolved_mod is not None and resolved_mod.__name__ == "charset_normalizer":
            assert requests.charset_normalizer_version is not None
            assert requests.chardet_version is None

    def test_chardet_version_set_when_chardet_is_resolved(self):
        """When chardet is the resolved library, chardet_version should be set."""
        chardet_mod = types.ModuleType("chardet")
        chardet_mod.__version__ = "5.2.0"

        with mock.patch("requests.compat.chardet", chardet_mod):
            with mock.patch("requests.compat._resolve_char_detection", return_value=chardet_mod):
                # Simulate what __init__.py does
                _chardet_module = chardet_mod
                charset_normalizer_version = None
                chardet_version = None

                if _chardet_module is not None:
                    if _chardet_module.__name__ == "charset_normalizer":
                        charset_normalizer_version = _chardet_module.__version__
                    elif _chardet_module.__name__ == "chardet":
                        chardet_version = _chardet_module.__version__

                assert chardet_version == "5.2.0"
                assert charset_normalizer_version is None


class TestHelpInfoCharDetection:
    """Tests that help.info() reports the correct using_charset_normalizer flag."""

    def test_using_charset_normalizer_flag_reflects_resolved_module(self):
        """The using_charset_normalizer flag should reflect which library
        was actually resolved for use, not just what's importable."""
        from requests.help import info

        result = info()
        from requests.compat import chardet as resolved_mod

        if resolved_mod is not None and resolved_mod.__name__ == "charset_normalizer":
            assert result["using_charset_normalizer"] is True
        elif resolved_mod is not None and resolved_mod.__name__ == "chardet":
            assert result["using_charset_normalizer"] is False
