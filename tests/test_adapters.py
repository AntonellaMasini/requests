import requests.adapters


def test_request_url_trims_leading_path_separators():
    """See also https://github.com/psf/requests/issues/6643."""
    a = requests.adapters.HTTPAdapter()
    p = requests.Request(method="GET", url="http://127.0.0.1:10000//v:h").prepare()
    assert "/v:h" == a.request_url(p, {})


class TestRequestUrlPreservesDoubleSlash:
    """Paths with leading double slashes should be preserved when they don't
    look like a network authority (host:port). Stripping them breaks AWS S3
    presigned URLs for keys that start with '/'.

    See also https://github.com/psf/requests/issues/6711.
    """

    def test_preserves_double_slash_in_path(self):
        """A path like //key should not be collapsed to /key."""
        a = requests.adapters.HTTPAdapter()
        p = requests.Request(
            method="GET",
            url="https://bucket.s3.amazonaws.com//key_with_leading_slash.txt",
        ).prepare()
        assert "//key_with_leading_slash.txt" == a.request_url(p, {})

    def test_preserves_double_slash_with_query_string(self):
        """Presigned URLs have query params that must not be affected."""
        a = requests.adapters.HTTPAdapter()
        p = requests.Request(
            method="GET",
            url="https://bucket.s3.amazonaws.com//key?X-Amz-Signature=abc123",
        ).prepare()
        assert "//key?X-Amz-Signature=abc123" == a.request_url(p, {})

    def test_still_collapses_authority_like_path(self):
        """Paths like //host:port should still be collapsed (issue #6643)."""
        a = requests.adapters.HTTPAdapter()
        p = requests.Request(
            method="GET", url="http://127.0.0.1:10000//v:h"
        ).prepare()
        assert "/v:h" == a.request_url(p, {})

    def test_preserves_triple_slash_path(self):
        """A path like ///key should be preserved when no colon in segment."""
        a = requests.adapters.HTTPAdapter()
        p = requests.Request(
            method="GET",
            url="https://example.com///deep/path",
        ).prepare()
        assert "///deep/path" == a.request_url(p, {})
