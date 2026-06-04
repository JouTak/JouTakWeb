from __future__ import annotations

from accounts.adapters import StrictAccountAdapter
from django.test import RequestFactory, SimpleTestCase, override_settings


class StrictAccountAdapterClientIpTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.factory = RequestFactory()
        self.adapter = StrictAccountAdapter()

    def _request(
        self,
        *,
        remote_addr: str | None = None,
        forwarded_for: str | None = None,
        real_ip: str | None = None,
    ):
        request = self.factory.get("/")
        if remote_addr is not None:
            request.META["REMOTE_ADDR"] = remote_addr
        else:
            request.META.pop("REMOTE_ADDR", None)
        if forwarded_for is not None:
            request.META["HTTP_X_FORWARDED_FOR"] = forwarded_for
        if real_ip is not None:
            request.META["HTTP_X_REAL_IP"] = real_ip
        return request

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=False,
        ACCOUNT_TRUSTED_PROXY_CIDRS=(),
    )
    def test_ignores_forwarded_headers_without_trusted_proxy(self):
        request = self._request(
            remote_addr="203.0.113.9",
            forwarded_for="1.2.3.4",
            real_ip="5.6.7.8",
        )

        self.assertEqual(self.adapter.get_client_ip(request), "203.0.113.9")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_uses_real_ip_when_remote_is_trusted(self):
        request = self._request(
            remote_addr="10.0.0.5",
            real_ip="198.51.100.42",
            forwarded_for="1.2.3.4, 5.6.7.8",
        )

        # X-Real-IP wins over X-Forwarded-For when both are present.
        self.assertEqual(self.adapter.get_client_ip(request), "198.51.100.42")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_picks_last_untrusted_ip_in_forwarded_chain(self):
        request = self._request(
            remote_addr="10.0.0.5",
            forwarded_for="1.2.3.4, 10.0.0.99, 10.0.0.5",
        )

        # Chain is [client, proxy-a, proxy-b]; all trailing trusted
        # proxies are skipped and the untrusted 1.2.3.4 is returned.
        self.assertEqual(self.adapter.get_client_ip(request), "1.2.3.4")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_falls_back_to_remote_addr_for_fully_trusted_chain(self):
        request = self._request(
            remote_addr="10.0.0.5",
            forwarded_for="10.0.0.7, 10.0.0.8",
        )

        self.assertEqual(self.adapter.get_client_ip(request), "10.0.0.5")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_ignores_garbage_in_forwarded_chain(self):
        request = self._request(
            remote_addr="10.0.0.5",
            forwarded_for="garbage, not-an-ip, 203.0.113.7",
        )

        self.assertEqual(self.adapter.get_client_ip(request), "203.0.113.7")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_rejects_forwarded_headers_from_untrusted_remote(self):
        request = self._request(
            remote_addr="203.0.113.10",
            forwarded_for="1.2.3.4",
            real_ip="5.6.7.8",
        )

        # Remote is not in a trusted CIDR → we do not trust headers.
        self.assertEqual(self.adapter.get_client_ip(request), "203.0.113.10")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("2001:db8::/48",),
    )
    def test_supports_ipv6_trusted_cidrs(self):
        # Only ``2001:db8:0::/48`` is trusted, so the inner proxy
        # (``2001:db8::beef``) is skipped but the outer hop
        # (``2001:db8:1::2``) is the untrusted client we want.
        request = self._request(
            remote_addr="2001:db8::1",
            forwarded_for="2001:db8:1::2, 2001:db8::beef",
        )

        self.assertEqual(self.adapter.get_client_ip(request), "2001:db8:1::2")

    @override_settings(
        ACCOUNT_TRUST_PROXY_HEADERS=True,
        ACCOUNT_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",),
    )
    def test_missing_remote_addr_returns_unknown_ip(self):
        request = self._request()

        self.assertEqual(self.adapter.get_client_ip(request), "0.0.0.0")
