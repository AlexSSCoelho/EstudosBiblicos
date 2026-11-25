from __future__ import annotations

import base64
import functools
import json
import socketserver
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import Page, Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build
import server as study_server


DIST_ROOT = ROOT / "dist"
VIEWPORTS = ((390, 844), (768, 900), (1440, 900))


def load_manifest_targets() -> tuple[list[str], list[tuple[str, int]]]:
    manifest = json.loads((DIST_ROOT / "manifest.json").read_text(encoding="utf-8"))
    studies = manifest.get("studies", [])
    study_paths = [f"/{entry['html']}" for entry in studies]
    counts = {
        "devocional": sum(1 for entry in studies if entry["tipo"] == "devocional"),
        "estudo_exegetico": sum(1 for entry in studies if entry["tipo"] == "estudo_exegetico"),
        "estudo_tematico": sum(1 for entry in studies if entry["tipo"] == "estudo_tematico"),
        "pregacao": sum(1 for entry in studies if entry["tipo"] == "pregacao"),
    }
    catalogs = [
        ("/tipos/devocionais.html", counts["devocional"]),
        ("/tipos/estudos-expositivos.html", counts["estudo_exegetico"]),
        ("/tipos/estudos-da-passagem.html", counts["estudo_exegetico"]),
        ("/tipos/estudos-tematicos.html", counts["estudo_tematico"]),
        ("/tipos/pregacoes.html", counts["pregacao"]),
        ("/tipos/todas.html", len(studies)),
    ]
    return study_paths, catalogs


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
    trigger = page.locator("#mobile-toc-trigger")
    if not trigger.is_visible():
        raise AssertionError(f"barra recolhível do índice mobile não está visível em {path}")
    trigger.click()
    page.wait_for_timeout(80)
    link = page.locator(".toc a").nth(link_index)
    href = link.get_attribute("href")
    if not href or not href.startswith("#"):
        raise AssertionError(f"link de TOC inválido em {path}: {href!r}")
    if not link.is_visible():
        raise AssertionError(f"lista vertical do índice mobile não abriu em {path}")
    link.click()
    page.wait_for_timeout(120)
    if page.locator(".toc.is-mobile-open").count() != 0:
        raise AssertionError(f"índice mobile não fechou após escolher seção em {path}")
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
    study_paths, catalogs = load_manifest_targets()
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
            if category_cards.count() != 4:
                raise AssertionError(
                    f"hub da biblioteca deveria ter 4 categorias: {category_cards.count()}"
                )
            for index in range(category_cards.count()):
                href = category_cards.nth(index).get_attribute("href")
                if not href or not href.startswith("tipos/"):
                    raise AssertionError(f"link de categoria inválido: {href!r}")
            expected_kickers = {"Para meditar", "Para compreender", "Para investigar", "Para pregar"}
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
                "Pregações",
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

            for catalog_path, expected_count in catalogs:
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

            for path in study_paths:
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
            assert_sermon_module_e2e(browser)
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    print("Frontend QA concluído: navegação, scroll, responsividade, cards, pregações e favicon OK.")
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


def assert_sermon_module_e2e(browser: object) -> None:
    """Validate sermon reading, revisions, GitHub-backed section notes, and R3 editor."""
    old_source = build.SOURCE_ROOT
    old_dist = build.DIST_ROOT
    old_study = build.STUDY_OUTPUT_ROOT
    old_cat = build.CATEGORY_OUTPUT_ROOT

    with tempfile.TemporaryDirectory(dir=ROOT, ignore_cleanup_errors=True) as temp_dir:
        tmp_root = Path(temp_dir)
        build.SOURCE_ROOT = tmp_root / "Pregações"
        build.DIST_ROOT = tmp_root / "dist"
        build.STUDY_OUTPUT_ROOT = build.DIST_ROOT / "estudos"
        build.CATEGORY_OUTPUT_ROOT = build.DIST_ROOT / "tipos"

        try:
            sermon_dir = build.SOURCE_ROOT / "Pregação - O Bom Pastor"
            sermon_dir.mkdir(parents=True)
            (sermon_dir / "estudo.md").write_text(
                """---
id: o-bom-pastor
tipo: pregacao
titulo: O Bom Pastor
---

## A voz do Pastor

Esboço inicial sem data, local ou tema.

## O cuidado no vale

Aplicação final para a igreja.
""",
                encoding="utf-8",
            )
            (sermon_dir / "r2.md").write_text(
                """---
id: o-bom-pastor-r2
sermao_id: o-bom-pastor
revisao: R2
tipo: pregacao
titulo: O Bom Pastor
passagem: Salmo 23.1–6
data: 2026-11-22
igreja: IPR Paranaíba-MS
nota_revisao: Ajustado ritmo da introdução.
---

## A voz do Pastor

Texto revisado em R2.

## O cuidado no vale

Conclusão revisada.
""",
                encoding="utf-8",
            )
            build.build(skip_pdf=True)
        finally:
            build.SOURCE_ROOT = old_source
            build.DIST_ROOT = old_dist
            build.STUDY_OUTPUT_ROOT = old_study
            build.CATEGORY_OUTPUT_ROOT = old_cat

        handler = functools.partial(QuietHandler, directory=str(tmp_root / "dist"))
        httpd = ThreadingServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        sermon_base = f"http://127.0.0.1:{httpd.server_address[1]}"

        github_store: dict[str, dict[str, str]] = {}
        put_calls: list[tuple[str, str]] = []

        def handle_github(route: Route) -> None:
            req = route.request
            url = req.url
            method = req.method.upper()
            auth = req.headers.get("authorization", "")
            if auth != "Bearer test-token-123":
                route.fulfill(
                    status=401,
                    content_type="application/json",
                    body=json.dumps({"message": "Bad credentials"}),
                )
                return

            if "/contents/" not in url:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"full_name": "AlexSSCoelho/EstudosBiblicos", "permissions": {"push": True}}),
                )
                return

            raw_path = url.split("/contents/", 1)[1].split("?", 1)[0]
            repo_path = unquote(raw_path)

            if method == "GET":
                if repo_path in github_store:
                    entry = github_store[repo_path]
                    encoded = base64.b64encode(entry["content"].encode("utf-8")).decode("ascii")
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps({"sha": entry["sha"], "content": encoded}),
                    )
                    return
                if not repo_path.endswith(".json") and not repo_path.endswith(".md"):
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps([{"name": "estudo.md"}, {"name": "r2.md"}]),
                    )
                    return
                route.fulfill(
                    status=404,
                    content_type="application/json",
                    body=json.dumps({"message": "Not Found"}),
                )
                return

            if method == "PUT":
                payload = json.loads(req.post_data or "{}")
                decoded = base64.b64decode(payload["content"]).decode("utf-8")
                sha = f"sha-{len(put_calls) + 1}"
                github_store[repo_path] = {"sha": sha, "content": decoded}
                put_calls.append((repo_path, decoded))
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "content": {"sha": sha},
                            "commit": {"html_url": "https://github.com/AlexSSCoelho/EstudosBiblicos/commit/abc123"},
                        }
                    ),
                )
                return

            route.abort()

        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route("https://api.github.com/**", handle_github)

        try:
            # 1. Modo visitante: leitura limpa sem controles de autor nem notas
            page.goto(f"{sermon_base}/estudos/o-bom-pastor/", wait_until="domcontentloaded")
            page.wait_for_timeout(150)
            if page_errors:
                raise AssertionError(f"erros JS na pregação visitante: {page_errors}")
            assert_no_horizontal_overflow(page, "/estudos/o-bom-pastor/", 1440)
            if page.locator("#sermon-author-bar").is_visible():
                raise AssertionError("barra do autor deveria estar oculta para visitantes sem token")
            if page.locator(".sermon-note-anchor").count() != 0:
                raise AssertionError("âncoras de anotação não devem existir sem token")
            if page.locator(".sermon-rev-link").count() != 2:
                raise AssertionError("seletor de revisões deveria listar R1 e R2")

            # Navegar para R2 e voltar para R1
            page.locator(".sermon-rev-link", has_text="R2").click()
            page.wait_for_timeout(120)
            if "o-bom-pastor-r2" not in page.url:
                raise AssertionError(f"seletor não navegou para R2: {page.url}")
            page.locator(".sermon-rev-link", has_text="R1").click()
            page.wait_for_timeout(120)

            # 2. Ativar Modo Autor via modal
            page.locator("#sermon-auth-btn").click()
            page.wait_for_timeout(100)
            page.locator("#sermon-gh-token").fill("test-token-123")
            page.locator("#sermon-auth-save").click()
            page.wait_for_timeout(200)
            if not page.locator("#sermon-author-bar").is_visible():
                raise AssertionError("barra do autor não apareceu após conectar token")
            if page.locator(".sermon-note-anchor").count() != 2:
                raise AssertionError("deveria renderizar 2 âncoras de anotação por seção")

            # 3. Salvar nota separada na primeira seção
            page.locator(".sermon-note-trigger").first.click()
            page.locator(".sermon-note-textarea").fill("Trazer ilustração da ovelha — reduzir introdução.")
            page.locator(".sermon-note-form .sermon-btn--primary").click()
            page.wait_for_timeout(200)
            if page.locator("#sermon-notes-count").inner_text().strip() != "1":
                raise AssertionError("contador de notas não atualizou para 1")
            if "Trazer ilustração da ovelha" not in page.locator(".sermon-note-card").first.inner_text():
                raise AssertionError("cartão de nota salva não exibiu o texto gravado")

            # Abrir drawer "Todas as notas"
            page.locator("#sermon-all-notes-btn").click()
            page.wait_for_timeout(100)
            if not page.locator("#sermon-notes-drawer").is_visible():
                raise AssertionError("drawer de todas as notas não abriu")
            page.keyboard.press("Escape")
            page.wait_for_timeout(80)

            # 4. Criar revisão R3 no navegador vendo a nota da R1 como referência
            page.locator("#sermon-new-revision-btn").click()
            page.wait_for_timeout(200)
            if not page.locator("#sermon-editor-modal").is_visible():
                raise AssertionError("modal do editor de revisão não abriu")
            if "Trazer ilustração da ovelha" not in page.locator("#ed-ref-notes-list").inner_text():
                raise AssertionError("notas da R1 não apareceram na barra lateral do editor R3")
            page.locator("#ed-meta-drawer summary").click()
            page.locator("#ed-nota-revisao").fill("Versão R3 criada direto no navegador.")
            page.locator("#ed-tab-preview").click()
            page.wait_for_timeout(80)
            if not page.locator("#ed-preview").is_visible():
                raise AssertionError("aba de pré-visualização não exibiu preview")
            page.locator("#ed-tab-write").click()
            page.locator("#ed-save-btn").click()
            page.wait_for_timeout(120)
            if not page.locator("#sermon-confirm-modal").is_visible():
                raise AssertionError("modal de confirmação para criar R3 não abriu")
            page.locator("#sermon-confirm-ok").click()
            page.wait_for_timeout(250)
            if not page.locator(".sermon-save-banner").is_visible():
                raise AssertionError("banner de confirmação do salvamento R3 não apareceu")

            r3_puts = [content for path, content in put_calls if path.endswith("/r3.md")]
            if not r3_puts:
                raise AssertionError(f"commit de r3.md não foi enviado ao GitHub: {put_calls}")
            if "revisao: R3" not in r3_puts[0] or "tipo: pregacao" not in r3_puts[0]:
                raise AssertionError(f"front matter gerado para R3 inválido:\n{r3_puts[0]}")
            if "\ndata:" in r3_puts[0] or "\nigreja:" in r3_puts[0]:
                raise AssertionError("campos opcionais vazios não deveriam ser emitidos no front matter")

            page.keyboard.press("Escape")
            page.wait_for_timeout(80)

            # Responsividade mobile em modo autor
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(120)
            assert_no_horizontal_overflow(page, "/estudos/o-bom-pastor/", 390)

            # 5. Desconectar e confirmar retorno ao modo visitante limpo
            page.locator("#sermon-auth-btn").click()
            page.wait_for_timeout(80)
            page.locator("#sermon-auth-disconnect").click()
            page.wait_for_timeout(120)
            if page.locator("#sermon-author-bar").is_visible():
                raise AssertionError("barra do autor deveria ocultar após desconectar")
            if page.locator(".sermon-note-anchor").count() != 0:
                raise AssertionError("âncoras de nota deveriam ser removidas após desconectar")
            if page_errors:
                raise AssertionError(f"erros JS durante fluxo de pregações: {page_errors}")
        finally:
            context.close()
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
