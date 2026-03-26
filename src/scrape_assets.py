"""
Scraper de assets (backgrounds + fontes) para o projeto Clip-Flow.

Usa Playwright (headless browser) para sites que bloqueiam requests simples,
e requests para APIs/sites que funcionam sem JS.

Fontes de backgrounds:
  - Imgflip (gandalf + wizard + mage templates) — requests + og:image
  - Pixabay (ilustracoes de wizard, mage) — Playwright
  - Lexica.art (imagens AI de wizards medievais) — Playwright
  - Pinterest (gandalf/wizard boards) — Playwright

Fontes tipograficas:
  - Google Fonts (fontes medievais/fantasy gratuitas) — requests

Uso:
  python -m src.scrape_assets
  python -m src.scrape_assets --source imgflip
  python -m src.scrape_assets --source pixabay
  python -m src.scrape_assets --source lexica
  python -m src.scrape_assets --source pinterest
  python -m src.scrape_assets --source fonts
  python -m src.scrape_assets --source all
"""

import argparse
import os
import re
import sys
import time
import unicodedata
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import BACKGROUNDS_DIR, FONTS_DIR

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

TIMEOUT = 15
DELAY_BETWEEN_DOWNLOADS = 1.0
MAX_RETRIES = 2


def _safe_filename(name: str, prefix: str) -> str:
    """Gera nome de arquivo seguro sem acentos ou caracteres especiais."""
    slug = name.lower().strip()
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return f"{prefix}_{slug[:50]}.png"


def _download_image(url: str, dest: Path) -> Path | None:
    """Baixa imagem, converte para PNG e salva no destino."""
    if dest.exists():
        print(f"  [pular] Ja existe: {dest.name}")
        return dest

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()

            img = Image.open(BytesIO(resp.content))

            # Filtrar imagens muito pequenas (icones)
            if img.width < 100 or img.height < 100:
                print(f"  [pular] Muito pequena ({img.width}x{img.height}): {url[:60]}")
                return None

            img.convert("RGB").save(str(dest), "PNG", quality=95)
            print(f"  [ok] {dest.name} ({img.width}x{img.height})")
            return dest

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            print(f"  [erro] Falha ao baixar {url[:60]}: {e}")
            return None

    return None


def _launch_browser():
    """Inicia Playwright com stealth settings e retorna (playwright, browser).

    Caller deve fechar com browser.close() e playwright.stop().
    """
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    return pw, browser


def _new_stealth_page(browser):
    """Cria uma page com headers e settings anti-deteccao."""
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="pt-BR",
    )
    page = context.new_page()
    # Remover flag de webdriver
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    return page


# ============================================================
# Imgflip — requests (funciona sem JS)
# ============================================================

def scrape_imgflip(query: str) -> list[dict]:
    """Extrai URLs de templates do Imgflip direto das <img> tags da busca."""
    url = f"https://imgflip.com/memesearch?q={query}"
    print(f"\n[Imgflip] Buscando: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [erro] Falha ao acessar Imgflip: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Pegar <img> direto — src contem URLs do CDN imgflip
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "")
        if "i.imgflip.com" not in src:
            continue

        if src.startswith("//"):
            src = "https:" + src

        title = img_tag.get("alt", "") or img_tag.get("title", "")
        if not title:
            parent = img_tag.find_parent("a")
            if parent:
                title = parent.get("title", "") or parent.text.strip()
        if not title:
            title = query

        title = re.sub(r"\s*Meme\s*Template\s*$", "", title, flags=re.IGNORECASE).strip()

        results.append({
            "url": src,
            "title": title,
            "filename": _safe_filename(title, f"imgflip_{query}"),
        })

    # Deduplicar por URL
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    print(f"  Encontrados: {len(unique)} templates")
    return unique


# ============================================================
# Pixabay — Playwright (bloqueia requests simples com 403)
# ============================================================

def scrape_pixabay(query: str, browser=None) -> list[dict]:
    """Busca ilustracoes no Pixabay usando Playwright com stealth."""
    search_url = (
        f"https://pixabay.com/illustrations/search/{query.replace(' ', '%20')}/"
    )
    print(f"\n[Pixabay] Buscando: {search_url}")

    own_browser = browser is None
    pw = None
    if own_browser:
        pw, browser = _launch_browser()

    try:
        page = _new_stealth_page(browser)
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Scroll para carregar mais imagens (lazy loading)
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1500)

        # Extrair URLs das imagens
        images = page.evaluate("""
            () => {
                const results = [];
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {
                    const srcset = img.getAttribute('srcset') || img.getAttribute('data-lazy-srcset') || '';
                    const src = img.getAttribute('src') || '';
                    const alt = img.getAttribute('alt') || '';

                    const combined = srcset + ' ' + src;
                    if (!combined.includes('pixabay.com') && !combined.includes('cdn.pixabay.com')) continue;

                    let bestUrl = src;
                    if (srcset) {
                        const parts = srcset.split(',').map(s => s.trim());
                        const last = parts[parts.length - 1];
                        if (last) bestUrl = last.split(' ')[0];
                    }

                    if (bestUrl && bestUrl.startsWith('http')) {
                        results.push({ url: bestUrl, alt: alt });
                    }
                }
                return results;
            }
        """)

        page.context.close()

        results = []
        seen = set()
        for item in images:
            url = item["url"]
            if url in seen:
                continue
            seen.add(url)
            alt = item.get("alt", f"pixabay_{len(results)}")
            results.append({
                "url": url,
                "title": alt,
                "filename": _safe_filename(alt, "pixabay"),
            })

        print(f"  Encontrados: {len(results)} ilustracoes")
        return results

    except Exception as e:
        print(f"  [erro] Falha no Pixabay via Playwright: {e}")
        return []
    finally:
        if own_browser:
            browser.close()
            pw.stop()


# ============================================================
# Lexica.art — Playwright (API retorna 500, usar pagina web)
# ============================================================

def scrape_lexica(query: str, browser=None) -> list[dict]:
    """Busca imagens AI no Lexica.art usando Playwright."""
    search_url = f"https://lexica.art/?q={query.replace(' ', '+')}"
    print(f"\n[Lexica] Buscando: {search_url}")

    own_browser = browser is None
    pw = None
    if own_browser:
        pw, browser = _launch_browser()

    try:
        page = _new_stealth_page(browser)
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        # Scroll para carregar mais
        for _ in range(3):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1500)

        # Extrair URLs das imagens do grid
        images = page.evaluate("""
            () => {
                const results = [];
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {
                    const src = img.getAttribute('src') || '';
                    const alt = img.getAttribute('alt') || '';

                    if (src.includes('lexica.art') || src.includes('image.lexica')
                        || src.includes('lexica-serve') || src.includes('lxc')) {
                        results.push({ url: src, alt: alt });
                    }
                }
                return results;
            }
        """)

        page.context.close()

        results = []
        seen = set()
        for item in images:
            url = item["url"]
            if url in seen or not url.startswith("http"):
                continue
            seen.add(url)
            alt = item.get("alt", "")
            title = alt[:50] if alt else f"lexica_{len(results)}"
            results.append({
                "url": url,
                "title": title,
                "filename": _safe_filename(f"lexica_{len(results)}_{title[:20]}", "lexica"),
            })

        print(f"  Encontrados: {len(results)} imagens AI")
        return results

    except Exception as e:
        print(f"  [erro] Falha no Lexica via Playwright: {e}")
        return []
    finally:
        if own_browser:
            browser.close()
            pw.stop()


# ============================================================
# Pinterest — Playwright (requer JS para renderizar imagens)
# ============================================================

def scrape_pinterest(search_query: str, browser=None) -> list[dict]:
    """Busca imagens no Pinterest via busca web usando Playwright."""
    search_url = f"https://br.pinterest.com/search/pins/?q={search_query.replace(' ', '%20')}"
    print(f"\n[Pinterest] Buscando: {search_url}")

    own_browser = browser is None
    pw = None
    if own_browser:
        pw, browser = _launch_browser()

    try:
        page = _new_stealth_page(browser)
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        # Scroll para carregar mais pins
        for _ in range(4):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(2000)

        # Extrair URLs das imagens
        images = page.evaluate("""
            () => {
                const results = [];
                const imgs = document.querySelectorAll('img[src*="pinimg.com"]');
                for (const img of imgs) {
                    let src = img.getAttribute('src') || '';
                    const alt = img.getAttribute('alt') || '';

                    if (!src.includes('pinimg.com')) continue;

                    src = src.replace('/236x/', '/736x/').replace('/170x/', '/736x/');
                    results.push({ url: src, alt: alt });
                }
                return results;
            }
        """)

        page.context.close()

        results = []
        seen = set()
        for item in images:
            url = item["url"]
            if url in seen or not url.startswith("http"):
                continue
            seen.add(url)
            alt = item.get("alt", f"pinterest_{len(results)}")
            results.append({
                "url": url,
                "title": alt,
                "filename": _safe_filename(alt, "pinterest"),
            })

        print(f"  Encontrados: {len(results)} imagens")
        return results

    except Exception as e:
        print(f"  [erro] Falha no Pinterest via Playwright: {e}")
        return []
    finally:
        if own_browser:
            browser.close()
            pw.stop()


# ============================================================
# Google Fonts — requests (API funciona sem JS)
# ============================================================

FONT_FAMILIES = [
    "MedievalSharp",
    "UnifrakturMaguntia",
    "Cinzel",
    "Cinzel Decorative",
    "IM Fell English",
    "Pirata One",
]


def download_google_fonts() -> int:
    """Baixa fontes medievais/fantasy do Google Fonts."""
    print(f"\n[Google Fonts] Baixando fontes para {FONTS_DIR}/")
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for family in FONT_FAMILIES:
        filename = family.replace(" ", "") + ".ttf"
        dest = FONTS_DIR / filename

        if dest.exists():
            print(f"  [pular] Ja existe: {filename}")
            downloaded += 1
            continue

        css_url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}"
        try:
            css_resp = requests.get(
                css_url,
                headers={**HEADERS, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=TIMEOUT,
            )
            css_resp.raise_for_status()
        except Exception as e:
            print(f"  [erro] Falha ao buscar CSS de {family}: {e}")
            continue

        urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css_resp.text)
        if not urls:
            urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css_resp.text)

        if not urls:
            print(f"  [aviso] Nenhum TTF encontrado para {family}")
            continue

        font_url = urls[0]
        try:
            font_resp = requests.get(font_url, timeout=TIMEOUT)
            font_resp.raise_for_status()

            if font_url.endswith(".woff2"):
                print(f"  [aviso] {family} so disponivel em woff2, pulando")
                continue

            dest.write_bytes(font_resp.content)
            print(f"  [ok] {filename} ({len(font_resp.content) // 1024} KB)")
            downloaded += 1

        except Exception as e:
            print(f"  [erro] Falha ao baixar fonte {family}: {e}")

        time.sleep(0.5)

    print(f"  Total fontes baixadas: {downloaded}/{len(FONT_FAMILIES)}")
    return downloaded


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Scraper de assets (backgrounds + fontes) para clip-flow"
    )
    parser.add_argument(
        "--source",
        choices=["imgflip", "pixabay", "lexica", "pinterest", "fonts", "all"],
        default="all",
        help="Fonte para buscar (padrao: all)",
    )
    args = parser.parse_args()

    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)

    # === Fontes tipograficas ===
    if args.source in ("all", "fonts"):
        download_google_fonts()
        if args.source == "fonts":
            return

    # === Backgrounds ===
    all_images = []
    downloaded = 0
    source = args.source

    # Fontes que usam Playwright compartilham o browser
    needs_browser = source in ("all", "pixabay", "lexica", "pinterest")
    pw, browser = (None, None)
    if needs_browser:
        print("\n[Browser] Iniciando Playwright (headless Chromium)...")
        pw, browser = _launch_browser()

    try:
        # Imgflip — requests
        if source in ("all", "imgflip"):
            for query in ["gandalf", "wizard", "wizard meme", "mage"]:
                templates = scrape_imgflip(query)
                all_images.extend(templates)
                time.sleep(1)

        # Pixabay — Playwright
        if source in ("all", "pixabay"):
            for query in [
                "wizard fantasy illustration",
                "sorcerer dark fantasy",
                "mystical wizard cartoon",
            ]:
                templates = scrape_pixabay(query, browser)
                all_images.extend(templates)
                time.sleep(1)

        # Lexica — Playwright
        if source in ("all", "lexica"):
            for query in [
                "mystical wizard cartoon dark fantasy",
                "old wizard staff medieval illustration",
                "gandalf style wizard dark moody portrait",
            ]:
                templates = scrape_lexica(query, browser)
                all_images.extend(templates)
                time.sleep(1)

        # Pinterest — Playwright
        if source in ("all", "pinterest"):
            for query in [
                "wizard meme cartoon medieval",
                "gandalf meme funny",
            ]:
                templates = scrape_pinterest(query, browser)
                all_images.extend(templates)
                time.sleep(1)

    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()
            print("[Browser] Playwright encerrado.")

    if not all_images:
        print("\nNenhuma imagem encontrada em nenhuma fonte.")
        print("Dica: tente rodar com --source especifico para isolar o problema.")
        sys.exit(1)

    # Deduplicar global por URL
    seen_urls = set()
    unique_images = []
    for item in all_images:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique_images.append(item)

    # Download
    print(f"\n{'='*50}")
    print(f"Baixando {len(unique_images)} imagens para {BACKGROUNDS_DIR}/")
    print(f"{'='*50}")

    for item in unique_images:
        dest = BACKGROUNDS_DIR / item["filename"]
        result = _download_image(item["url"], dest)
        if result:
            downloaded += 1
        time.sleep(DELAY_BETWEEN_DOWNLOADS)

    # Relatorio final
    print(f"\n{'='*50}")
    print(f"Concluido!")
    print(f"  Total encontrado:  {len(unique_images)}")
    print(f"  Total baixado:     {downloaded}")
    print(f"  Destino:           {BACKGROUNDS_DIR}/")
    print(f"{'='*50}")

    backgrounds = list(BACKGROUNDS_DIR.glob("*.png")) + list(BACKGROUNDS_DIR.glob("*.jpg"))
    print(f"\nBackgrounds disponiveis: {len(backgrounds)}")
    for bg in sorted(backgrounds):
        print(f"  - {bg.name}")

    fonts = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
    if fonts:
        print(f"\nFontes disponiveis: {len(fonts)}")
        for f in sorted(fonts):
            print(f"  - {f.name}")


if __name__ == "__main__":
    main()
