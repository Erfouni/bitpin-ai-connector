import httpx


async def test_public_ip_probe_is_credential_free_and_validates_families():
    from bitpin_connector.network import public_ips

    calls = []

    async def endpoint(request):
        calls.append(request)
        assert request.url.scheme == "https"
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        return httpx.Response(
            200, text="8.8.8.8" if request.url.host == "api.ipify.org" else "2606:4700:4700::1111"
        )

    result = await public_ips(transport=httpx.MockTransport(endpoint))
    assert result == {"ipv4": "8.8.8.8", "ipv6": "2606:4700:4700::1111"}
    assert len(calls) == 2


async def test_public_ip_probe_does_not_print_html_or_guess_missing_ipv6():
    from bitpin_connector.network import public_ips

    async def endpoint(request):
        if request.url.host == "api6.ipify.org":
            raise httpx.ConnectError("No IPv6 route")
        return httpx.Response(200, text="<script>not-an-IP</script>")

    assert await public_ips(transport=httpx.MockTransport(endpoint)) == {"ipv4": None, "ipv6": None}


async def test_ip_probe_rejects_redirects_and_private_addresses():
    from bitpin_connector.network import public_ips

    async def endpoint(request):
        if request.url.host == "api6.ipify.org":
            return httpx.Response(302, headers={"Location": "https://untrusted.example/"})
        return httpx.Response(200, text="192.168.1.1")

    assert await public_ips(transport=httpx.MockTransport(endpoint)) == {"ipv4": None, "ipv6": None}
