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
    "/estudos/mateus-24-3-14/",
    "/estudos/daniel-3-16-18/",
    "/estudos/filipenses-4-6-9/",
    "/estudos/romanos-12-2-devocional/",
    "/estudos/a-imutabilidade-de-deus/",
)
CATALOGS = (
    ("/tipos/devocionais.html", 1),
    ("/tipos/estudos-expositivos.html", 3),
    ("/tipos/estudos-da-passagem.html", 3),
    ("/tipos/estudos-tematicos.html", 1),
    ("/tipos/todas.html", 5),
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

            category_cards = page.locator(".category-card")
            if category_cards.count() != 3:
                raise AssertionError(
                    f"hub da biblioteca deveria ter 3 categorias: {category_cards.count()}"
                )
            for index in range(category_cards.count()):
                href = category_cards.nth(index).get_attribute("href")
                if not href or not href.startswith("tipos/"):
                    raise AssertionError(f"link de categoria inválido: {href!r}")
            expected_kickers = {"Para meditar", "Para compreender", "Para investigar"}
            actual_kickers = set(
                page.locator(".category-card-kicker").all_text_contents()
            )
            if actual_kickers != expected_kickers:
                raise AssertionError(
                    f"rótulos de propósito dos cards divergentes: {actual_kickers}"
                )
            expected_titles = {
                "Devocionais",
                "Estudos expositivos",
                "Estudos temáticos",
            }
            actual_titles = set(page.locator(".category-card h3").all_text_contents())
            if actual_titles != expected_titles:
                raise AssertionError(
                    f"títulos das categorias divergentes: {actual_titles}"
                )
            category_text = " ".join(category_cards.all_text_contents())
            if page.locator(".category-card-action").count() or "Ver " in category_text:
                raise AssertionError(
                    "a home ainda exibe uma ação redundante dentro dos cards"
                )
            if page.locator(".study-card").count() != 0:
                raise AssertionError("a biblioteca inicial ainda expõe cards individuais")
            all_readings = page.locator(".library-all-link a")
            if all_readings.get_attribute("href") != "tipos/todas.html":
                raise AssertionError("link para todas as leituras não foi renderizado")

            page.goto(f"{base_url}/tipos/todas.html", wait_until="domcontentloaded")
            page.wait_for_timeout(150)
            if page_errors:
                raise AssertionError(f"erros JS no catálogo completo: {page_errors}")
            card = page.locator(".study-card").first
            card_transition = card.evaluate(
                "element => getComputedStyle(element).transitionProperty"
            )
            if "transform" not in card_transition or "box-shadow" not in card_transition:
                raise AssertionError(
                    f"card não possui transição de clicabilidade: {card_transition}"
                )
            card.hover()
            hover_transform = card.evaluate(
                "element => getComputedStyle(element).transform"
            )
            if hover_transform == "none":
                raise AssertionError("card não reage visualmente ao hover")
            card_box = card.bounding_box()
            if card_box is None:
                raise AssertionError("card do catálogo completo não foi renderizado")
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
            if not hit or "estudos/" not in hit or not hit.endswith("/"):
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
            if page.locator(".card-read-link").count() != 0:
                raise AssertionError("o catálogo ainda exibe o link redundante 'Ler estudo'")
            title_link = card.locator("h3 a")
            title_link.hover()
            title_decoration = title_link.evaluate(
                "element => getComputedStyle(element).textDecorationLine"
            )
            if "underline" in title_decoration:
                raise AssertionError("o título do estudo ainda fica sublinhado no hover")

            for catalog_path, expected_count in CATALOGS:
                page_errors.clear()
                page.goto(f"{base_url}{catalog_path}", wait_until="domcontentloaded")
                page.wait_for_timeout(100)
                if page_errors:
                    raise AssertionError(
                        f"erros JS no catálogo {catalog_path}: {page_errors}"
                    )
                actual_count = page.locator(".study-card").count()
                if actual_count != expected_count:
                    raise AssertionError(
                        f"catálogo {catalog_path} deveria ter {expected_count} cards, "
                        f"mas renderizou {actual_count}"
                    )
                if page.locator(".library-back-link").get_attribute("href") != "../":
                    raise AssertionError(
                        f"retorno à biblioteca inválido em {catalog_path}"
                    )
                if page.locator(".library-footer a").count() != 0:
                    raise AssertionError(
                        f"o catálogo {catalog_path} ainda exibe retorno duplicado no rodapé"
                    )

            page_errors.clear()
            romanos = "/estudos/romanos-12-2-devocional/"
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
                        numeric_indices = [
                            index
                            for index, href in enumerate(hrefs)
                            if href and len(href) > 1 and href[1].isdigit()
                        ]
                        target_index = (
                            numeric_indices[0]
                            if numeric_indices
                            else min(2, len(hrefs) - 1)
                        )
                        assert_mobile_anchor_clear(page, target_index, path)

            assert_review_pilot_desktop(page, base_url)
            assert_remaining_reviews_desktop(page, base_url)
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    print("Frontend QA concluído: navegação, scroll, responsividade, cards e favicon OK.")
    return 0


def assert_review_pilot_desktop(page: Page, base_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(f"{base_url}/estudos/filipenses-4-6-9/", wait_until="domcontentloaded")
    page.wait_for_timeout(200)
    if page_errors:
        raise AssertionError(f"erros JS no piloto de revisão: {page_errors}")

    assert_no_horizontal_overflow(page, "/estudos/filipenses-4-6-9/", 1440)
    if not page.locator("#study-rail").is_visible():
        raise AssertionError("trilha direita deveria estar visível em 1440px")
    if page.locator(".rail-review-btn").count() != 5:
        raise AssertionError("deveria renderizar 5 botões h2 em Filipenses")
    if page.locator(".rail-reading-prompt").count() != 7:
        raise AssertionError("deveria renderizar 7 perguntas de leitura ativa h3 em Filipenses")

    # Alinhamento direito entre a trilha marginal e o bloco de tese + toggle do índice lateral
    right_diff = page.evaluate(
        """() => {
            const rail = document.getElementById('study-rail').getBoundingClientRect().right;
            const thesis = document.querySelector('.thesis').getBoundingClientRect().right;
            return Math.abs(rail - thesis);
        }"""
    )
    if right_diff > 2.0:
        raise AssertionError(f"trilha direita desalinhada com a tese: diff={right_diff}")

    prose_before = page.locator(".prose").bounding_box()["width"]
    page.locator("#toc-toggle-btn").click()
    page.wait_for_timeout(120)
    if page.locator(".toc").is_visible():
        raise AssertionError("índice lateral deveria recolher ao clicar no ícone do header")
    prose_after = page.locator(".prose").bounding_box()["width"]
    if prose_after <= prose_before or prose_after > 920:
        raise AssertionError(
            f"largura de leitura após recolher TOC fora da faixa esperada: before={prose_before}, after={prose_after}"
        )
    page.locator("#toc-toggle-btn").click()
    page.wait_for_timeout(120)
    if not page.locator(".toc").is_visible():
        raise AssertionError("índice lateral deveria expandir ao clicar novamente no ícone")

    # Abrir primeira gaveta lexical e verificar zero sobreposição na trilha
    page.locator("details.lex-drawer summary").first.click()
    page.wait_for_timeout(120)
    overlap = page.evaluate(
        """() => {
            const cards = Array.from(document.querySelectorAll('#study-rail .rail-card'));
            const rects = cards.map((c) => c.getBoundingClientRect());
            for (let i = 1; i < rects.length; i += 1) {
                if (rects[i - 1].bottom > rects[i].top + 1) {
                    return { index: i, prevBottom: rects[i - 1].bottom, top: rects[i].top };
                }
            }
            return null;
        }"""
    )
    if overlap:
        raise AssertionError(f"colisão vertical na trilha direita após abrir léxico: {overlap}")

    # Abrir slide-over da primeira seção e responder todos os 6 itens
    page.locator(".rail-review-btn").first.click()
    page.wait_for_timeout(120)
    if not page.locator("#review-drawer").is_visible():
        raise AssertionError("slide-over não abriu ao clicar no botão da seção")

    for step in range(6):
        card_text = page.locator("#review-drawer-body").inner_text().casefold()
        for forbidden in ("nível:", "fácil", "intermediário", "difícil", "dificuldade"):
            if forbidden in card_text:
                raise AssertionError(f"dificuldade exposta na UI: {forbidden}")

        if page.locator(".review-option").count() == 4:
            page.locator(".review-option").first.click()
            page.locator(".review-submit-btn").click()
        elif page.locator(".review-input").count() == 1:
            page.locator(".review-input").fill("ius italicum")
            page.locator(".review-submit-btn").click()
        elif page.locator(".review-textarea").count() == 1:
            page.locator(".review-textarea").fill(
                "A colônia romana tinha orgulho cívico e lealdade a Roma, mas a identidade cristã em Cristo relativiza esse prestígio."
            )
            page.locator(".review-submit-btn").click()
            self_confirm = page.locator(".review-self-confirm-btn")
            if self_confirm.count() == 1:
                self_confirm.click()
        else:
            raise AssertionError(f"formato de questão desconhecido no passo {step}")

        page.wait_for_timeout(60)
        page.locator("#review-next-btn").click()
        page.wait_for_timeout(80)

    summary_score = page.locator(".review-summary-score").inner_text()
    if "/ 10" not in summary_score:
        raise AssertionError(f"nota final não exibida no resumo: {summary_score!r}")

    page.keyboard.press("Escape")
    page.wait_for_timeout(100)
    if page.locator("#review-drawer").is_visible():
        raise AssertionError("slide-over não fechou com Escape")

    badge_after = page.locator(".rail-review-btn").first.inner_text()
    if "Nota " not in badge_after:
        raise AssertionError(f"botão da seção não atualizou com a nota: {badge_after!r}")

    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(150)
    badge_reloaded = page.locator(".rail-review-btn").first.inner_text()
    if "Nota " not in badge_reloaded:
        raise AssertionError(f"progresso não persistiu em localStorage: {badge_reloaded!r}")

    # Garantir ocultação em tablet e mobile
    for width, height in ((768, 900), (390, 844)):
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(100)
        if page.locator("#study-rail").is_visible() or page.locator("#review-drawer").is_visible():
            raise AssertionError(f"revisão ativa deveria estar oculta em {width}px")
        assert_no_horizontal_overflow(page, "/estudos/filipenses-4-6-9/", width)


def assert_remaining_reviews_desktop(page: Page, base_url: str) -> None:
    targets = [
        ("/estudos/daniel-3-16-18/", 4, 6),
        ("/estudos/mateus-24-3-14/", 4, 14),
        ("/estudos/a-imutabilidade-de-deus/", 7, 7),
    ]
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    for path, expected_buttons, expected_prompts in targets:
        page_errors.clear()
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
        page.wait_for_timeout(200)
        if page_errors:
            raise AssertionError(f"erros JS em {path}: {page_errors}")

        assert_no_horizontal_overflow(page, path, 1440)
        if not page.locator("#study-rail").is_visible():
            raise AssertionError(f"trilha direita deveria estar visível em {path}")
        if page.locator(".rail-review-btn").count() != expected_buttons:
            raise AssertionError(
                f"{path}: esperado {expected_buttons} botões h2, obtido {page.locator('.rail-review-btn').count()}"
            )
        if page.locator(".rail-reading-prompt").count() != expected_prompts:
            raise AssertionError(
                f"{path}: esperado {expected_prompts} perguntas de leitura ativa, obtido {page.locator('.rail-reading-prompt').count()}"
            )

        overlap = page.evaluate(
            """() => {
                const cards = Array.from(document.querySelectorAll('#study-rail .rail-card'));
                const rects = cards.map((c) => c.getBoundingClientRect());
                for (let i = 1; i < rects.length; i += 1) {
                    if (rects[i - 1].bottom > rects[i].top + 1) {
                        return { index: i, prevBottom: rects[i - 1].bottom, top: rects[i].top };
                    }
                }
                return null;
            }"""
        )
        if overlap:
            raise AssertionError(f"{path}: colisão vertical na trilha direita: {overlap}")

        page.locator(".rail-review-btn").first.click()
        page.wait_for_timeout(120)
        if not page.locator("#review-drawer").is_visible():
            raise AssertionError(f"{path}: slide-over não abriu")
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        if page.locator("#review-drawer").is_visible():
            raise AssertionError(f"{path}: slide-over não fechou com Escape")

        for width, height in ((768, 900), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(80)
            if page.locator("#study-rail").is_visible() or page.locator("#review-drawer").is_visible():
                raise AssertionError(f"{path}: revisão ativa deveria estar oculta em {width}px")
            assert_no_horizontal_overflow(page, path, width)


if __name__ == "__main__":
    raise SystemExit(main())
