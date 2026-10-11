# -*- coding: utf-8 -*-
"""
SOFASCORE ORTAK OTURUM

Sofascore API'si bazi IP'lere Cloudflare/Turnstile dogrulamasi koyuyor
(403 {"reason": "challenge"}). Bu durumda curl_cffi hangi parmak iziyle
gelirse gelsin engelleniyor; sadece dogrulamayi gecmis gercek bir Chrome
istek atabiliyor.

Akis:
  1. Once hizli yol: curl_cffi (safari parmak izi).
  2. 403 challenge gelirse gercek Chrome acilir (Playwright, kalici profil),
     dogrulama kendiliginden gecilir ve kalan tum istekler Chrome icinden
     fetch() ile yapilir.

Kullanim requests.Session ile ayni: session.get(url, timeout=15)
-> .status_code, .text, .content, .json()
"""
import atexit
import base64
import json
import os
import time
from datetime import date

try:
    from curl_cffi import requests as curl_requests
    USE_CURL = True
except ImportError:
    import requests as std_requests
    USE_CURL = False

SITE_URL = "https://www.sofascore.com/"
API_BASE = "https://www.sofascore.com/api/v1"

# Dogrulama cookie'si bu profilde saklanir, sonraki calismalarda tekrar sorulmaz
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.sofa_browser_profile')

DEFAULT_HEADERS = {
    # NOT: User-Agent eklenmemeli, impersonate parmak iziyle celisip 403 aldiriyor
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
    'Origin': 'https://www.sofascore.com',
    'Referer': 'https://www.sofascore.com/',
}


# Chrome icinde calisan fetch; govdeyi base64 olarak doner (resimler icin de calisir)
FETCH_JS = """async ([url, timeoutMs]) => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    const headers = {};
    const m = document.cookie.match(/(?:^|; )sofa_captcha=([^;]+)/);
    if (m) headers['x-captcha'] = decodeURIComponent(m[1]);
    try {
        const r = await fetch(url, {signal: ctrl.signal, credentials: 'include', headers});
        const buf = new Uint8Array(await r.arrayBuffer());
        let bin = '';
        for (let i = 0; i < buf.length; i += 0x8000) {
            bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
        }
        return {status: r.status, body: btoa(bin)};
    } catch (e) {
        return {status: 0, body: ''};
    } finally {
        clearTimeout(timer);
    }
}"""


class BrowserResponse:
    """Chrome icinden yapilan fetch sonucunu requests Response gibi gosterir"""

    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

    @property
    def text(self):
        return self.content.decode('utf-8', errors='replace')

    def json(self):
        return json.loads(self.content)


def _is_challenge(response):
    if response.status_code != 403:
        return False
    try:
        return 'challenge' in response.text
    except Exception:
        return True


class SofaSession:
    def __init__(self):
        self.headers = dict(DEFAULT_HEADERS)
        if USE_CURL:
            self._http = curl_requests.Session(impersonate="safari")
        else:
            self._http = std_requests.Session()
        self._http.headers.update(self.headers)

        self._playwright = None
        self._context = None
        self._page = None
        self.browser_mode = False

    # --- Hizli yol ---------------------------------------------------------
    def _http_get(self, url, timeout):
        return self._http.get(url, timeout=timeout)

    # --- Gercek Chrome -----------------------------------------------------
    def _start_browser(self):
        from playwright.sync_api import sync_playwright

        print("[INFO] Sofascore dogrulama istiyor, Chrome uzerinden devam ediliyor...")
        self._playwright = sync_playwright().start()
        atexit.register(self.close)
        launch_args = dict(
            headless=False,  # headless Chrome dogrulamayi gecemiyor
            ignore_default_args=["--enable-automation"],
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-position=-2400,-2400",  # pencere ekran disinda, kullaniciyi rahatsiz etmesin
                "--window-size=1000,800",
            ],
        )
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                PROFILE_DIR, channel="chrome", **launch_args)
        except Exception:
            # Sistemde Chrome yoksa Playwright'in kendi Chromium'u
            self._context = self._playwright.chromium.launch_persistent_context(
                PROFILE_DIR, **launch_args)

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

        if self._refresh_token():
            print("[OK] Chrome dogrulamayi gecti.")
            self.browser_mode = True
            return True

        print("[HATA] Chrome dogrulamayi gecemedi.")
        return False

    def _refresh_token(self):
        """Futbol sayfasini ac: site kendi istegi 403 alinca /token/captcha ile
        yeni token uretip sofa_captcha cookie'sine yaziyor. Token gecerli olana kadar bekle."""
        probe = f"{API_BASE}/sport/football/scheduled-tournaments/{date.today().isoformat()}/page/1"
        for attempt in range(3):
            self._page.goto(SITE_URL + "football", timeout=60000)
            for _ in range(15):
                time.sleep(2)
                if self._browser_fetch(probe, 15).status_code == 200:
                    return True
        return False

    def _browser_fetch(self, url, timeout):
        # Site her API isteginde sofa_captcha token'ini x-captcha header'i olarak gonderiyor;
        # bu header olmadan korunan endpoint'ler 403 challenge donuyor
        result = None
        for attempt in range(5):
            try:
                result = self._page.evaluate(FETCH_JS, [url, int(timeout * 1000)])
                break
            except Exception:
                # Sayfa o sirada yenileniyor (site token alinca reload edebiliyor), yuklenmesini bekle
                time.sleep(2)
                try:
                    self._page.wait_for_load_state("domcontentloaded", timeout=30000)
                except Exception:
                    pass
        if result is None:
            return BrowserResponse(0, b'')
        return BrowserResponse(result['status'], base64.b64decode(result['body']))

    # --- Ortak arayuz ------------------------------------------------------
    def get(self, url, timeout=15):
        if self.browser_mode:
            response = self._browser_fetch(url, timeout)
            if _is_challenge(response):
                # Token suresi dolmus (~1 saat), yenile ve bir kez tekrar dene
                print("\n[INFO] Sofascore token yenileniyor...")
                if self._refresh_token():
                    response = self._browser_fetch(url, timeout)
            if response.status_code == 0:
                raise TimeoutError(f"Chrome fetch basarisiz: {url}")
            return response

        response = self._http_get(url, timeout)
        if _is_challenge(response) and '/api/' in url:
            if self._context is None and self._start_browser():
                return self.get(url, timeout)
        return response

    def close(self):
        try:
            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._context = None
        self._playwright = None
        self.browser_mode = False
