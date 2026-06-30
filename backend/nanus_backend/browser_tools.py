from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse


@dataclass(frozen=True)
class BrowserSnapshot:
    url: str
    final_url: str
    title: str
    text: str
    engine: str
    char_count: int
    trace: dict[str, Any]


class BrowserSafetyError(RuntimeError):
    pass


def _blocked_ip(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise BrowserSafetyError("Browser target host cannot be resolved") from exc
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
    return False


def assert_safe_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise BrowserSafetyError("Only http(s) URLs can be browsed")
    host = parsed.hostname or ""
    if _blocked_ip(host):
        raise BrowserSafetyError("Local/private browser targets are blocked")
    return host


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _clean_html(raw: str) -> tuple[str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "Untitled page"
    cleaned = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", cleaned)
    text = re.sub(r"\s+", " ", text).strip()
    return title, text


def safe_urllib_snapshot(url: str, *, timeout: float = 12, max_redirects: int = 4, max_bytes: int = 1_000_000) -> BrowserSnapshot:
    current = url
    visited: list[str] = []
    opener = urllib.request.build_opener(_NoRedirect)
    for redirect_index in range(max_redirects + 1):
        host = assert_safe_url(current)
        request = urllib.request.Request(current, headers={"user-agent": "NanusBrowser/0.2"})
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(max_bytes).decode("utf-8", errors="replace")
                title, text = _clean_html(raw)
                return BrowserSnapshot(url=url, final_url=current, title=title, text=text[:8000], engine="safe-urllib", char_count=len(text[:8000]), trace={"visited": visited + [current], "allowedHost": host, "bytesReadLimit": max_bytes})
        except urllib.error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308} and exc.headers.get("Location"):
                visited.append(current)
                current = urljoin(current, exc.headers["Location"])
                continue
            raise
    raise BrowserSafetyError("Too many redirects")


async def playwright_snapshot(url: str, *, timeout_ms: int = 15_000) -> BrowserSnapshot:
    assert_safe_url(url)
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError("Playwright is not installed") from exc
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=False)
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        final_url = page.url
        assert_safe_url(final_url)
        title = await page.title()
        text = await page.locator("body").inner_text(timeout=timeout_ms)
        await browser.close()
        text = re.sub(r"\s+", " ", text).strip()[:8000]
        return BrowserSnapshot(url=url, final_url=final_url, title=title or final_url, text=text, engine="playwright", char_count=len(text), trace={"visited": [url, final_url], "timeoutMs": timeout_ms})


async def browser_snapshot(url: str, *, prefer_playwright: bool = True) -> BrowserSnapshot:
    if prefer_playwright:
        try:
            return await playwright_snapshot(url)
        except Exception:
            pass
    return await asyncio.to_thread(safe_urllib_snapshot, url)
