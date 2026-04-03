from __future__ import annotations

import ipaddress

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

UNKNOWN_IP = "0.0.0.0"
Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class StrictAccountAdapter(DefaultAccountAdapter):
    def _parse_ip(self, value: str | None) -> str | None:
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            return None

    def _trusted_proxy_networks(self) -> tuple[Network, ...]:
        networks: list[Network] = []
        for raw in getattr(settings, "ACCOUNT_TRUSTED_PROXY_CIDRS", ()):
            try:
                networks.append(ipaddress.ip_network(raw, strict=False))
            except ValueError:
                continue
        return tuple(networks)

    def _ip_in_networks(
        self,
        value: str | None,
        networks: tuple[Network, ...],
    ) -> bool:
        if not value or not networks:
            return False
        try:
            candidate = ipaddress.ip_address(value)
        except ValueError:
            return False
        return any(candidate in network for network in networks)

    def _remote_is_trusted_proxy(self, remote_ip: str | None) -> bool:
        if not remote_ip:
            return False
        if not getattr(settings, "ACCOUNT_TRUST_PROXY_HEADERS", False):
            return False
        try:
            remote_addr = ipaddress.ip_address(remote_ip)
        except ValueError:
            return False
        networks = self._trusted_proxy_networks()
        if networks:
            return any(remote_addr in network for network in networks)
        return False

    def _forwarded_client_ip(
        self,
        request,
        *,
        trusted_networks: tuple[Network, ...],
    ) -> str | None:
        real_ip = self._parse_ip(request.META.get("HTTP_X_REAL_IP"))
        if real_ip:
            return real_ip

        raw_value = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if not raw_value:
            return None

        parsed_chain = [
            parsed
            for part in raw_value.split(",")
            for parsed in [self._parse_ip(part)]
            if parsed
        ]
        if not parsed_chain:
            return None

        for candidate in reversed(parsed_chain):
            if not self._ip_in_networks(candidate, trusted_networks):
                return candidate
        return None

    def get_client_ip(self, request) -> str:
        remote_ip = self._parse_ip(request.META.get("REMOTE_ADDR"))
        trusted_networks = self._trusted_proxy_networks()
        if self._remote_is_trusted_proxy(remote_ip):
            forwarded_ip = self._forwarded_client_ip(
                request,
                trusted_networks=trusted_networks,
            )
            if forwarded_ip:
                return forwarded_ip
        return remote_ip or UNKNOWN_IP
