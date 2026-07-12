"""
Euroton B2B katalog scraper.

Poverilnice iz okoljskih spremenljivk (NE v kodi):
    EUROTON_USER      – uporabniško ime (npr. 103757)
    EUROTON_PASSWORD  – geslo

Odkrita arhitektura (iz HAR analize):
  - Prijava:  https://www.euroton.si/avtodeli/signin.aspx?B2B=1  (ASP.NET postback)
  - Iskanje:  https://katalog.euroton.si/b2b/redesign/?prikaz=artikli
              &searchproizv=on&searchprod=on&search=KODA&tmpl=ajax
              → vrne JSON {"html_res": "<article_box-i...>"}
  - Cene:     https://katalog.euroton.si/b2b/redesign/getStock.php?id=ARTIKEL_ID
              → vrne JSON s HTML cenami (Vaša cena brez DDV ipd.)

Uporaba:
    from euroton_scraper import EurotonClient
    c = EurotonClient()
    rez = c.isci("6000633302")
    # rez = {"ok": True, "rezultati": [{"znamka":..., "koda":..., "naziv":..., "cena":...}], ...}
"""

import os
import re
import json
import time
import logging

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("euroton")

SIGNIN_URL = "https://www.euroton.si/avtodeli/signin.aspx?B2B=1&ReturnURL=tdcatalogue.aspx"
KATALOG_BASE = "https://katalog.euroton.si/b2b/redesign/"
STOCK_URL = "https://katalog.euroton.si/b2b/redesign/getStock.php"

F_USER = "ctl00$PageContent$ctl00$ctrlLogin$UserName"
F_PASS = "ctl00$PageContent$ctl00$ctrlLogin$Password"
F_REMEMBER = "ctl00$PageContent$ctl00$ctrlLogin$RememberMe"
F_LOGIN_BTN = "ctl00$PageContent$ctl00$ctrlLogin$LoginButton"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DELAY = 1.0  # spoštljiv zamik med zahtevami (sekunde)


class EurotonClient:
    def __init__(self, username=None, password=None):
        self.username = username or os.environ.get("EUROTON_USER", "")
        self.password = password or os.environ.get("EUROTON_PASSWORD", "")
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "sl-SI,sl;q=0.9,en;q=0.8",
        })
        self._logged_in = False

    # ── ASP.NET prijava ─────────────────────────────────────────────────
    @staticmethod
    def _aspnet_fields(html):
        soup = BeautifulSoup(html, "html.parser")
        out = {}
        for n in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
            el = soup.find("input", {"name": n})
            out[n] = el["value"] if (el and el.has_attr("value")) else ""
        return out

    def login(self):
        if not self.username or not self.password:
            return {"ok": False, "napaka": "Manjkajo poverilnice (EUROTON_USER/EUROTON_PASSWORD)."}
        try:
            r = self.s.get(SIGNIN_URL, timeout=20)
            r.raise_for_status()
        except Exception as e:
            return {"ok": False, "napaka": f"GET signin: {e}"}

        payload = self._aspnet_fields(r.text)
        payload[F_USER] = self.username
        payload[F_PASS] = self.password
        payload[F_REMEMBER] = "on"
        payload[F_LOGIN_BTN] = "Prijava"
        payload["__EVENTTARGET"] = ""
        payload["__EVENTARGUMENT"] = ""

        time.sleep(DELAY)
        try:
            r2 = self.s.post(SIGNIN_URL, data=payload, timeout=20,
                             headers={"Referer": SIGNIN_URL})
            r2.raise_for_status()
        except Exception as e:
            return {"ok": False, "napaka": f"POST prijava: {e}"}

        low = r2.text.lower()
        if ("ctrllogin$password" in r2.text.lower().replace("_", "$")
                and "odjav" not in low and "signout" not in low):
            return {"ok": False, "napaka": "Prijava zavrnjena – preveri uporabniško ime/geslo."}

        self._logged_in = True
        return {"ok": True}

    # ── Iskanje ─────────────────────────────────────────────────────────
    def isci(self, koda, limit=30):
        koda = str(koda).strip()
        if not koda:
            return {"ok": False, "napaka": "Prazna koda", "rezultati": []}

        if not self._logged_in:
            lg = self.login()
            if not lg["ok"]:
                return {"ok": False, "napaka": lg["napaka"], "rezultati": []}

        params = {
            "prikaz": "artikli",
            "searchproizv": "on",
            "searchprod": "on",
            "search": koda + " ",
            "start": "0",
            "limit": str(limit),
            "tmpl": "ajax",
        }
        time.sleep(DELAY)
        try:
            r = self.s.get(KATALOG_BASE, params=params, timeout=25,
                           headers={"Referer": KATALOG_BASE,
                                    "X-Requested-With": "XMLHttpRequest"})
            r.raise_for_status()
        except Exception as e:
            return {"ok": False, "napaka": f"Iskanje: {e}", "rezultati": []}

        # Odgovor je JSON {"html_res": "..."} ali čist HTML
        html = ""
        try:
            data = json.loads(r.text)
            html = data.get("html_res", "")
        except Exception:
            html = r.text

        if not html:
            return {"ok": True, "napaka": None, "rezultati": [],
                    "sporocilo": "Ni rezultatov za to kodo."}

        rezultati = self._parse(html)

        # Dopolni cene (getStock) za artikle ki imajo ID
        for art in rezultati:
            if art.get("stock_id"):
                cena = self._cena(art["stock_id"])
                if cena:
                    art["cena"] = cena
                time.sleep(0.4)  # blaga zadrška med stock klici

        return {"ok": True, "napaka": None, "rezultati": rezultati}

    # ── Parsiranje artiklov ─────────────────────────────────────────────
    @staticmethod
    def _parse(html):
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for box in soup.select(".article_box"):
            # articleGroup: "grupa|naziv|brandID"
            ag = box.select_one(".articleGroup")
            ag_txt = ag.get_text(strip=True) if ag else ""
            deli = ag_txt.split("|")
            naziv = deli[1].strip() if len(deli) >= 2 else ag_txt

            ab = box.select_one(".articleBrand")
            znamka = ab.get_text(strip=True) if ab else ""

            # Koda artikla – iz info- elementa ali prve krepke kode
            koda_art = ""
            info = box.find(id=re.compile(r"^info-"))
            if info:
                m = re.search(r"([A-Z0-9][A-Z0-9/.\-]{3,})", info.get_text(" ", strip=True))
                if m:
                    koda_art = m.group(1)

            # stock_id – iz id-jev oblike "stockImg-123" ali price-123
            stock_id = None
            for el in box.find_all(id=re.compile(r"-(\d+)$")):
                m = re.search(r"-(\d+)$", el.get("id", ""))
                if m:
                    stock_id = m.group(1)
                    break

            if znamka or naziv:
                out.append({
                    "znamka": znamka,
                    "naziv": naziv,
                    "koda": koda_art,
                    "stock_id": stock_id,
                    "cena": None,
                })
        return out

    # ── Cena posameznega artikla ────────────────────────────────────────
    def _cena(self, stock_id):
        try:
            r = self.s.get(STOCK_URL, params={"id": stock_id, "ima_naso_zalogo": "1"},
                           timeout=15, headers={"Referer": KATALOG_BASE})
            r.raise_for_status()
            data = json.loads(r.text)
        except Exception:
            return None
        # data = { "<hash>": { "price": "<html>", ... } }
        for _k, v in data.items():
            if isinstance(v, dict) and v.get("price"):
                soup = BeautifulSoup(v["price"], "html.parser")
                cene = {}
                for div in soup.select("div"):
                    t = div.get_text(" ", strip=True)
                    m = re.search(r"(Va[šs]a cena brez DDV|Redna cena z DDV|Redna cena brez DDV)\s*:?\s*([\d.,]+)\s*€", t)
                    if m:
                        cene[m.group(1)] = m.group(2)
                if cene:
                    # Prioriteta: Vaša cena
                    for kljuc in ("Vaša cena brez DDV", "Redna cena z DDV", "Redna cena brez DDV"):
                        if kljuc in cene:
                            return f"{cene[kljuc]} € ({kljuc})"
        return None
