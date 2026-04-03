"""Tests for character detection library resolution (issue #7223).

Verifies that ``charset_normalizer`` (the required dependency) is preferred
over ``chardet`` (the optional ``[use_chardet_on_py3]`` extra), and that
``chardet`` is only used as a fallback when ``charset_normalizer`` is not
available.
"""

import warnings
from unittest import mock

import pytest

from requests.compat import _resolve_char_detection
from requests.exceptions import RequestsDependencyWarning

# ---------------------------------------------------------------------------
# compat._resolve_char_detection tests
# ---------------------------------------------------------------------------


class TestResolveCharDetection:
    def test_prefers_charset_normalizer_over_chardet(self):
        """When both libraries are importable, charset_normalizer wins."""
        result = _resolve_char_detection()
        # charset_normalizer is a hard dependency, so it should always be
        # available in the test environment.
        assert result is not None
        assert result.__name__ == "charset_normalizer"

    def test_falls_back_to_chardet_when_charset_normalizer_missing(self):
        """When charset_normalizer is not importable, chardet is used."""
        import importlib

        real_import_module = importlib.import_module

        def _mock_import_module(name):
            if name == "charset_normalizer":
                raise ImportError("mocked")
            return real_import_module(name)

        with mock.patch("importlib.import_module", side_effect=_mock_import_module):
            result = _resolve_char_detection()

        if result is not None:
            assert result.__name__ == "chardet"

    def test_returns_none_when_neither_available(self):
        """When no detection library is importable, None is returned."""
        import importlib

        real_import_module = importlib.import_module

        def _mock_import_module(name):
            if name in ("charset_normalizer", "chardet"):
                raise ImportError("mocked")
            return real_import_module(name)

        with mock.patch("importlib.import_module", side_effect=_mock_import_module):
            result = _resolve_char_detection()

        assert result is None


# ---------------------------------------------------------------------------
# check_compatibility tests
# ---------------------------------------------------------------------------


class TestCheckCompatibility:
    """Verify that check_compatibility respects the new priority order."""

    def test_charset_normalizer_checked_first(self):
        """When both versions are provided, charset_normalizer is validated
        (not chardet), so an out-of-range chardet version does NOT raise."""
        from requests import check_compatibility

        # Valid charset_normalizer, invalid chardet — should NOT warn/assert.
        # (chardet_version is ignored when charset_normalizer_version is set)
        check_compatibility("2.0.0", "0.0.1", "3.0.0")

    def test_chardet_checked_when_charset_normalizer_missing(self):
        """When charset_normalizer_version is None, chardet is validated."""
        from requests import check_compatibility

        # Valid chardet, no charset_normalizer.
        check_compatibility("2.0.0", "5.0.0", None)

    def test_chardet_invalid_when_charset_normalizer_missing(self):
        """Invalid chardet with no charset_normalizer raises AssertionError."""
        from requests import check_compatibility

        with pytest.raises(AssertionError):
            check_compatibility("2.0.0", "0.0.1", None)

    def test_warns_when_neither_available(self):
        """A warning is issued when both versions are None."""
        from requests import check_compatibility

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_compatibility("2.0.0", None, None)
            dep_warnings = [
                x for x in w if issubclass(x.category, RequestsDependencyWarning)
            ]
            assert len(dep_warnings) == 1
            assert "character detection" in str(dep_warnings[0].message).lower()


# ---------------------------------------------------------------------------
# __init__ module-level gating tests
# ---------------------------------------------------------------------------


class TestInitChardetGating:
    """Verify that the __init__ module does not import chardet when
    charset_normalizer is available."""

    def test_chardet_version_is_none_when_charset_normalizer_available(self):
        """chardet_version should be None at module level because
        charset_normalizer is the installed hard dependency."""
        import requests

        # charset_normalizer is a required dep, so it should be detected.
        assert requests.charset_normalizer_version is not None
        # chardet_version must be None — chardet should be ignored.
        assert requests.chardet_version is None


# ---------------------------------------------------------------------------
# help.info() tests
# ---------------------------------------------------------------------------


class TestHelpChardetGating:
    def test_help_reports_charset_normalizer_not_chardet(self):
        """help.info() should report charset_normalizer as the active library
        when it is available, regardless of whether chardet is importable."""
        from requests.help import info

        result = info()
        assert result["charset_normalizer"]["version"] is not None
        assert result["chardet"]["version"] is None
        assert result["using_charset_normalizer"] is True
