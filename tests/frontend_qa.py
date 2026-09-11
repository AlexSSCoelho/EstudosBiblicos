from __future__ import annotations

import functools
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server as study_server


DIST_ROOT = ROOT / "dist"
STUDIES = (
    "/estudos/filipenses-4-6-9/filipenses-4-6-9.html",
    "/estudos/romanos-12-2-devocional/romanos-12-2-devocional.html",
    "/estudos/a-imutabilidade-de-deus/a-imutabilidade-de-deus.html",
)
VIEWPORTS = ((390, 844), (768, 900), (1440, 900))


class QuietHandler(study_server.UTF8HttpRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


class ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def assert_no_horizontal_overflow(page: Page, path: str, width: int) -> None:
    dimensions = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth
        })"""
    )
    if dimensions["scrollWidth"] != dimensions["clientWidth"]:
        raise AssertionError(
            f"overflow horizontal em {path} @ {width}px: {dimensions}"
        )


def assert_toc_targets_exist(page: Page, path: str) -> list[str]:
    hrefs = page.locator(".toc a").evaluate_all(
        "els => els.map((el) => el.getAttribute('href')).filter(Boolean)"
    )
    missing = page.evaluate(
        """(items) => items.filter((href) => {
            if (!href.startsWith('#')) return true;
            return !document.getElementById(href.slice(1));
        })""",
        hrefs,
    )
    if missing:
        raise AssertionError(f"TOC com alvos inexistentes em {path}: {missing}")
    return hrefs


def assert_mobile_anchor_clear(page: Page, link_index: int, path: str) -> None:
    page.add_style_tag(content="html { scroll-behavior: auto !important; }")
    link = page.locator(".toc a").nth(link_index)
    href = link.get_attribute("href")
    if not href or not href.startswith("#"):
        raise AssertionError(f"link de TOC inválido em {path}: {href!r}")
    link.click()
    page.wait_for_timeout(100)
    geometry = page.evaluate(
        """(id) => {
            const target = document.getElementById(id);
            const topbar = document.querySelector('.topbar');
            const toc = document.querySelector('.toc');
            return {
                targetTop: target.getBoundingClientRect().top,
                obstructionBottom: Math.max(
                    topbar ? topbar.getBoundingClientRect().bottom : 0,
                    toc ? toc.getBoundingClientRect().bottom : 0
                )
            };
        }""",
        href[1:],
    )
    if geometry["targetTop"] < geometry["obstructionBottom"] + 5:
        raise AssertionError(
            f"título encoberto pelo cabeçalho/TOC em {path}: {geometry}"
        )


def main() -> int:
    handler = functools.partial(QuietHandler, directory=str(DIST_ROOT))
    httpd = ThreadingServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{httpd.server_address[1]}"

    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception:
                browser = playwright.chromium.launch(headless=True, channel="msedge")
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))

            page.goto(f"{base_url}/", wait_until="domcontentloaded")
            page.wait_for_timeout(150)
            if page_errors:
                raise AssertionError(f"erros JS na biblioteca: {page_errors}")
            if page.locator('link[rel="icon"][href="./assets/favicon.svg"]').count() != 1:
                raise AssertionError("favicon SVG não está ligado na biblioteca")
            favicon_response = page.request.get(f"{base_url}/assets/favicon.svg")
            if favicon_response.status != 200:
                raise AssertionError(
                    f"favicon SVG não foi servido: HTTP {favicon_response.status}"
                )

            card = page.locator(".study-card").first
            card_box = card.bounding_box()
            if card_box is None:
                raise AssertionError("card da biblioteca não foi renderizado")
            hit = page.evaluate(
                """([x, y]) => {
                    const element = document.elementFromPoint(x, y);
                    const anchor = element ? element.closest('a') : null;
                    return anchor ? anchor.getAttribute('href') : null;
                }""",
                [
                    card_box["x"] + card_box["width"] - 36,
                    card_box["y"] + card_box["height"] / 2,
                ],
            )
            if not hit or not hit.endswith(".html"):
                raise AssertionError(
                    f"área interna do card não aponta para o estudo: {hit!r}"
                )
            pdf_link = card.locator(".card-meta a").first
            pdf_box = pdf_link.bounding_box()
            if pdf_box is None:
                raise AssertionError("link PDF do card não foi renderizado")
            pdf_hit = page.evaluate(
                """([x, y]) => {
                    const element = document.elementFromPoint(x, y);
                    const anchor = element ? element.closest('a') : null;
                    return anchor ? anchor.getAttribute('href') : null;
                }""",
                [
                    pdf_box["x"] + pdf_box["width"] / 2,
                    pdf_box["y"] + pdf_box["height"] / 2,
                ],
            )
            if pdf_hit != pdf_link.get_attribute("href"):
                raise AssertionError("link PDF deixou de ser alvo independente no card")

            page_errors.clear()
            romanos = STUDIES[1]
            page.goto(f"{base_url}{romanos}", wait_until="domcontentloaded")
            page.wait_for_timeout(150)
            if page_errors:
                raise AssertionError(f"erros JS em Romanos desktop: {page_errors}")
            toc_position = page.locator(".toc").evaluate(
                "element => getComputedStyle(element).position"
            )
            if toc_position != "sticky":
                raise AssertionError(
                    f"TOC devocional desktop não está fixada na barra lateral: {toc_position}"
                )

            for path in STUDIES:
                for width, height in VIEWPORTS:
                    page.set_viewport_size({"width": width, "height": height})
                    page_errors.clear()
                    page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
                    page.wait_for_timeout(200)
                    if page_errors:
                        raise AssertionError(
                            f"erros JS em {path} @ {width}px: {page_errors}"
                        )
                    assert_no_horizontal_overflow(page, path, width)
                    hrefs = assert_toc_targets_exist(page, path)
                    if not hrefs:
                        raise AssertionError(f"TOC vazio em {path}")
                    if page.locator(".toc a.active").count() != 1:
                        raise AssertionError(
                            f"scroll spy não ativou exatamente um item em {path} @ {width}px"
                        )
                    if width <= 860 and page.evaluate("window.scrollY") != 0:
                        raise AssertionError(
                            f"página iniciou deslocada em {path} @ {width}px"
                        )

                    if width == 390:
                        if "filipenses" in path:
                            numeric_indices = [
                                index
                                for index, href in enumerate(hrefs)
                                if href and len(href) > 1 and href[1].isdigit()
                            ]
                            if not numeric_indices:
                                raise AssertionError(
                                    "Filipenses não expôs o caso de regressão com id numérico"
                                )
                            assert_mobile_anchor_clear(
                                page, numeric_indices[0], path
                            )
                        else:
                            assert_mobile_anchor_clear(
                                page, min(2, len(hrefs) - 1), path
                            )

            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    print("Frontend QA concluído: navegação, scroll, responsividade, cards e favicon OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
