"""Public egress discovery: no Bitpin credentials are sent to the IP service."""

import asyncio
import ipaddress

import httpx


async def public_ips(*, transport=None) -> dict[str, str | None]:
    async with httpx.AsyncClient(
        timeout=6, trust_env=False, follow_redirects=False, transport=transport
    ) as http:

        async def probe(url, family):
            try:
                response = await asyncio.wait_for(http.get(url), timeout=7)
                response.raise_for_status()
                if len(response.content) > 64:
                    return None
                value = ipaddress.ip_address(response.text.strip())
                return str(value) if value.is_global and value.version == family else None
            except (httpx.HTTPError, TimeoutError, ValueError):
                return None

        ipv4, ipv6 = await asyncio.gather(
            probe("https://api.ipify.org", 4), probe("https://api6.ipify.org", 6)
        )
        return {"ipv4": ipv4, "ipv6": ipv6}


def print_public_ips(values: dict[str, str | None]):
    print("\nSERVER PUBLIC OUTBOUND IP · IP مجاز بیت‌پین")
    for label, value in values.items():
        print(f"  {label.upper()}: {value or 'Not detected (unavailable or probe failed)'}")
    print("Add the outbound IP to your Bitpin API key's allowed IP list BEFORE continuing.")
    print("در تنظیمات API بیت‌پین، IP عمومی خروجی سرور را در فهرست IPهای مجاز ثبت کنید.")
    print("If both families are available, account for both routes. Do not enter a Docker/private IP.")
    print("Observed via ipify without proxies. Destination-specific routing/NAT can differ.")
    if not any(values.values()):
        print("Automatic lookup failed. Check the outbound public IP with your server provider.")
    print()
