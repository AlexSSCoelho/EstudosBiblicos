"""Build the canonical Bible-study sources into HTML, PDF and a library index.

The repository deliberately keeps the build entry point small and explicit:
Markdown plus YAML front matter is the editorial source, while everything in
dist/ is a reproducible artifact.
"""

from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

try:
    import markdown
except ImportError as exc:  # pragma: no cover - exercised by the CLI guard
    raise SystemExit(
        "Dependência ausente: Markdown. Execute 'py -m pip install -r requirements.txt'."
    ) from exc

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by the CLI guard
    raise SystemExit(
        "Dependência ausente: PyYAML. Execute 'py -m pip install -r requirements.txt'."
    ) from exc

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
except ImportError as exc:  # pragma: no cover - exercised by the CLI guard
    raise SystemExit(
        "Dependência ausente: Jinja2. Execute 'py -m pip install -r requirements.txt'."
    ) from exc


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "Pregações"
TEMPLATE_ROOT = ROOT / "templates"
ASSET_ROOT = ROOT / "assets"
DIST_ROOT = ROOT / "dist"
STUDY_OUTPUT_ROOT = DIST_ROOT / "estudos"

DEFAULT_TRANSLATIONS = {
    "devocional": "NVI",
    "estudo_exegetico": "ACF",
    "estudo_tematico": "ACF",
}
REQUIRED_FIELDS = ("id", "tipo", "titulo", "passagem", "data", "resumo")
DETAIL_BLOCK_RE = re.compile(
    r'<details\s+class="lex-drawer">\s*<summary>(?P<summary>.*?)</summary>'
    r'(?P<body>.*?)</details>',
    re.IGNORECASE | re.DOTALL,
)
VERSE_HEADING_RE = re.compile(
    r'(?m)^(?:v\.|vv\.|versículo|versículos)?\s*(\d+(?:[.:]\d+)?(?:[–—\-]\d+(?:[.:]\d+)?)?)\s*\n+(#{2,4}\s+(.+))$'
)
MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "toc", "smarty"]
PDF_DATE_RE = re.compile(
    rb"/(CreationDate|ModDate) \(D:\d{14}[+-]\d{2}'\d{2}'\)"
)
DATA_URI_RE = re.compile(r"\bdata:", re.IGNORECASE)
DATA_IMAGE_RE = re.compile(r"\bdata:image/", re.IGNORECASE)
ALLOWED_EXTERNAL_SCHEMES = {"http", "https"}


class BuildError(RuntimeError):
    """An actionable build failure."""


@dataclass
class Study:
    metadata: dict[str, Any]
    body: str
    body_html: str
    toc: list[dict[str, Any]]
    source_path: Path

    @property
    def source_dir(self) -> Path:
        return self.source_path.parent

    @property
    def study_id(self) -> str:
        return str(self.metadata["id"])

    @property
    def output_dir(self) -> Path:
        return STUDY_OUTPUT_ROOT / self.study_id


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def flatten_toc(tokens: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for token in tokens:
        flattened.append(
            {
                "id": token.get("id", ""),
                "name": token.get("name", ""),
                "level": int(token.get("level", 1)),
            }
        )
        flattened.extend(flatten_toc(token.get("children", [])))
    return flattened


def extract_and_inject_verse_markers(text: str) -> tuple[str, dict[str, str]]:
    verse_map: dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        verse = m.group(1).strip()
        heading_line = m.group(2).strip()
        heading_title = m.group(3).strip()
        verse_map[slugify(heading_title)] = verse
        anchor_id = f"v-{slugify(verse)}"
        return (
            f'<div class="verse-marker" id="{anchor_id}">'
            f'<span class="verse-tag"><span class="verse-tag-prefix">Versículo</span> {verse}</span>'
            f"</div>\n\n{heading_line}"
        )

    processed = VERSE_HEADING_RE.sub(repl, text)
    return processed, verse_map


def format_verse_badge(verse: str) -> str:
    if "." in verse and not ("–" in verse or "-" in verse or "—" in verse):
        return f"v. {verse.split('.')[-1]}"
    if re.fullmatch(r"\d+", verse):
        return f"v. {verse}"
    return verse


def enrich_toc(raw_toc: list[dict[str, Any]], verse_map: dict[str, str]) -> list[dict[str, Any]]:
    eligible = [e for e in raw_toc if e.get("level", 1) in (2, 3, 4)]
    if not eligible:
        return []

    enriched: list[dict[str, Any]] = []
    section_counter = 1

    for entry in eligible:
        slug = entry.get("id", "")
        name = entry.get("name", "")
        level = int(entry.get("level", 2))

        verse = verse_map.get(slug)
        if not verse:
            v_match = re.match(
                r"^(?:v\.|vv\.|versículo\s*)?(\d+(?:[.:]\d+)?(?:[–—\-]\d+(?:[.:]\d+)?)?)(?:\s*[·:–\-]\s*|\s+)(.*)$",
                name,
                re.IGNORECASE,
            )
            if v_match:
                verse = v_match.group(1).strip()

        is_verse = bool(verse)
        item = dict(entry)
        item["is_verse"] = is_verse
        item["verse"] = verse

        if is_verse and ("." in str(verse) or re.fullmatch(r"\d+", str(verse))) and not ("–" in str(verse) or "-" in str(verse) or "—" in str(verse)):
            item["badge_type"] = "verse"
            item["badge"] = format_verse_badge(str(verse))
            item["is_subitem"] = False
        elif level == 2:
            item["badge_type"] = "number"
            item["badge"] = f"{section_counter:02d}"
            item["is_subitem"] = False
            section_counter += 1
        else:
            item["badge_type"] = "bullet"
            item["badge"] = "·"
            item["is_subitem"] = True
            if verse:
                item["verse_range"] = verse

        enriched.append(item)

    return enriched


def parse_source(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise BuildError(f"{path}: a fonte precisa começar com front matter YAML.")

    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)\Z", text, re.DOTALL)
    if not match:
        raise BuildError(f"{path}: front matter YAML não foi fechado corretamente.")

    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise BuildError(f"{path}: o front matter precisa resultar em um objeto YAML.")
    return metadata, match.group(2).lstrip()


def normalize_type(value: Any, path: Path) -> str:
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if normalized in {"devocional", "devocional_estudo_rapido"}:
        return "devocional"
    if normalized in {
        "estudo",
        "estudo_exegetico",
        "exegetico",
        "exegese",
        "estudo_exegetico_completo",
    }:
        return "estudo_exegetico"
    if normalized in {
        "estudo_tematico",
        "tematico",
        "estudo_doutrinario",
    }:
        return "estudo_tematico"
    raise BuildError(
        f"{path}: tipo inválido: {value!r}. Use devocional, estudo_exegetico ou estudo_tematico."
    )


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_passagens_chave(value: Any, path: Path) -> dict[str, list[dict[str, str]]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BuildError(
            f"{path}: 'passagens_chave' deve ser um objeto contendo 'antigo_testamento' e/ou 'novo_testamento'."
        )

    allowed_sections = {"antigo_testamento", "novo_testamento"}
    unexpected_sections = set(value.keys()) - allowed_sections
    if unexpected_sections:
        raise BuildError(
            f"{path}: seções inesperadas em 'passagens_chave': {', '.join(sorted(unexpected_sections))}."
        )

    normalized: dict[str, list[dict[str, str]]] = {}
    for section in ("antigo_testamento", "novo_testamento"):
        if section not in value or value[section] is None:
            continue
        items = value[section]
        if not isinstance(items, list):
            raise BuildError(f"{path}: 'passagens_chave.{section}' deve ser uma lista de passagens.")

        section_items: list[dict[str, str]] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise BuildError(
                    f"{path}: 'passagens_chave.{section}[{index}]' deve ser um objeto com campo 'ref'."
                )
            ref = str(item.get("ref") or "").strip()
            if not ref:
                raise BuildError(
                    f"{path}: 'passagens_chave.{section}[{index}]' exige o campo obrigatório 'ref'."
                )
            entry = {"ref": ref}
            if "texto" in item and item["texto"] is not None:
                entry["texto"] = str(item["texto"]).strip()
            section_items.append(entry)

        if section_items:
            normalized[section] = section_items

    return normalized


def format_date_br(value: Any) -> str:
    val_str = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", val_str)
    if match:
        year, month, day = match.groups()
        return f"{day}/{month}/{year}"
    return val_str


def normalize_metadata(metadata: dict[str, Any], path: Path) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if not metadata.get(field)]
    if missing:
        raise BuildError(f"{path}: campos obrigatórios ausentes: {', '.join(missing)}.")

    study_id = str(metadata["id"]).strip()
    if study_id != slugify(study_id) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", study_id):
        raise BuildError(f"{path}: id inválido: {study_id!r}. Use slug minúsculo com hífens.")

    normalized = dict(metadata)
    normalized["id"] = study_id
    normalized["tipo"] = normalize_type(metadata["tipo"], path)
    normalized["titulo"] = str(metadata["titulo"]).strip()
    normalized["passagem"] = str(metadata["passagem"]).strip()
    normalized["resumo"] = str(metadata["resumo"]).strip()
    normalized["data"] = str(metadata["data"]).strip()
    normalized["data_formatada"] = format_date_br(normalized["data"])

    if normalized["tipo"] == "estudo_tematico":
        tema = str(metadata.get("tema") or "").strip()
        if not tema:
            raise BuildError(f"{path}: o campo 'tema' é obrigatório para estudos temáticos.")
        normalized["tema"] = tema
    else:
        normalized["tema"] = str(metadata.get("tema") or "").strip()

    normalized["passagens_chave"] = normalize_passagens_chave(metadata.get("passagens_chave"), path)

    translation = metadata.get("traducao")
    translation_text = "" if translation is None else str(translation).strip()
    normalized["traducao_inferida"] = not bool(translation_text)
    normalized["traducao"] = translation_text or DEFAULT_TRANSLATIONS[normalized["tipo"]]
    normalized["homiletica"] = bool(metadata.get("homiletica", False))
    normalized["tags"] = [str(item) for item in as_list(metadata.get("tags"))]
    normalized["fontes_textuais"] = [
        str(item) if not isinstance(item, dict) else item
        for item in as_list(metadata.get("fontes_textuais"))
    ]
    normalized["lexicos"] = [
        str(item) if not isinstance(item, dict) else item
        for item in as_list(metadata.get("lexicos"))
    ]
    normalized["imagens"] = as_list(metadata.get("imagens"))
    for field in ("autor", "tese", "destinatarios", "igreja"):
        value = metadata.get(field)
        normalized[field] = "" if value is None else str(value).strip()
    status = metadata.get("status")
    normalized["status"] = str(status).strip() if status is not None else "rascunho"
    return normalized


class ReferenceParser(HTMLParser):
    """Collect resource links emitted by Markdown or written as raw HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.casefold() in {"src", "href"} and value is not None:
                self.references.append(value)


def body_references(study: Study) -> list[str]:
    parser = ReferenceParser()
    parser.feed(study.body_html)
    parser.close()
    return parser.references


def image_references(study: Study) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for index, item in enumerate(study.metadata.get("imagens", [])):
        image = image_dict(item)
        source = image.get("src")
        if source is None or not str(source).strip():
            raise BuildError(
                f"{study.source_path}: imagens[{index}].src precisa ser informado."
            )
        references.append((f"imagens[{index}].src", str(source).strip()))
    return references


def local_reference_path(reference: str) -> Path | None:
    """Return a safe local path, ignore approved URLs/anchors, or raise."""
    value = str(reference).strip()
    if not value:
        raise BuildError("referência vazia")
    if DATA_URI_RE.match(value):
        raise BuildError("data URI não é permitida")

    parsed = urlsplit(value)
    scheme = parsed.scheme.casefold()
    if scheme:
        if scheme in ALLOWED_EXTERNAL_SCHEMES:
            return None
        raise BuildError(f"esquema de URL não permitido: {scheme}")
    if parsed.netloc:
        raise BuildError("referência de rede sem esquema não é permitida")
    if value.startswith("#"):
        return None

    path_text = unquote(parsed.path).replace("\\", "/")
    if "\x00" in path_text:
        raise BuildError("caminho contém byte nulo")
    if not path_text.startswith("./"):
        raise BuildError("caminho local precisa começar com ./")

    parts = PurePosixPath(path_text[2:]).parts
    if not parts or any(part == ".." for part in parts):
        raise BuildError("travessia de diretório não é permitida")
    return Path(*parts)


def validate_reference(study: Study, reference: str, label: str) -> Path | None:
    try:
        relative = local_reference_path(reference)
    except BuildError as exc:
        raise BuildError(f"{study.source_path}: {label} ({reference!r}): {exc}") from exc

    if relative is None:
        return None

    source_root = study.source_dir.resolve()
    candidate = (source_root / relative).resolve(strict=False)
    try:
        candidate.relative_to(source_root)
    except ValueError as exc:
        raise BuildError(
            f"{study.source_path}: {label} ({reference!r}) aponta para fora da pasta do estudo."
        ) from exc
    if not candidate.is_file():
        raise BuildError(f"{study.source_path}: asset local não encontrado: {reference}")
    return relative


def local_references(study: Study) -> set[str]:
    references = [reference for _label, reference in image_references(study)]
    references.extend(body_references(study))
    local: set[str] = set()
    for reference in references:
        if local_reference_path(reference) is not None:
            local.add(reference)
    return local


def validate_source(study: Study) -> None:
    if DATA_IMAGE_RE.search(study.body) or DATA_IMAGE_RE.search(study.body_html):
        raise BuildError(
            f"{study.source_path}: imagens Base64 não são permitidas; use um asset local ou URL perene."
        )

    for label, reference in image_references(study):
        validate_reference(study, reference, label)
    for index, reference in enumerate(body_references(study)):
        validate_reference(study, reference, f"referência HTML/Markdown[{index}]")


def markdown_parser() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=MARKDOWN_EXTENSIONS,
        output_format="html5",
    )


def render_markdown(body: str) -> tuple[str, list[dict[str, Any]]]:
    def render_lexical_drawer(match: re.Match[str]) -> str:
        inner_parser = markdown_parser()
        inner_html = inner_parser.convert(match.group("body").strip())
        summary = escape(" ".join(match.group("summary").split()))
        return (
            '<details class="lex-drawer">\n'
            '<summary class="lex-drawer-summary">\n'
            f'  <span class="lex-summary-title">{summary}</span>\n'
            '  <span class="lex-toggle-badge" aria-hidden="true">\n'
            '    <span class="lex-toggle-text lex-toggle-text--closed">Consultar léxico</span>\n'
            '    <span class="lex-toggle-text lex-toggle-text--open">Recolher</span>\n'
            '    <svg class="lex-toggle-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>\n'
            '  </span>\n'
            '</summary>\n'
            '<div class="lex-drawer-body">\n'
            f'{inner_html}\n'
            '</div>\n'
            '</details>'
        )

    body_with_verses, verse_map = extract_and_inject_verse_markers(body)
    body_with_drawers = DETAIL_BLOCK_RE.sub(render_lexical_drawer, body_with_verses)
    parser = markdown_parser()
    raw_html = parser.convert(body_with_drawers)

    def external_link_replacer(match: re.Match[str]) -> str:
        tag_content = match.group(1)
        href_match = re.search(r'href=["\'](https?://[^"\']+)["\']', tag_content, re.IGNORECASE)
        if href_match:
            if 'target=' not in tag_content:
                tag_content = f'{tag_content} target="_blank"'
            if 'rel=' not in tag_content:
                tag_content = f'{tag_content} rel="noopener noreferrer"'
        return f'<a {tag_content.strip()}>'

    body_html = re.sub(r'<a\s+([^>]+)>', external_link_replacer, raw_html)
    return body_html, enrich_toc(flatten_toc(parser.toc_tokens), verse_map)


def load_study(path: Path) -> Study:
    metadata, body = parse_source(path)
    metadata = normalize_metadata(metadata, path)
    body_html, toc = render_markdown(body)
    study = Study(
        metadata=metadata,
        body=body,
        body_html=body_html,
        toc=toc,
        source_path=path,
    )
    validate_source(study)
    return study


def find_studies() -> list[Study]:
    if not SOURCE_ROOT.exists():
        return []
    sources = sorted(SOURCE_ROOT.rglob("estudo.md"))
    studies = [load_study(path) for path in sources]
    ids = [study.study_id for study in studies]
    duplicates = sorted({study_id for study_id in ids if ids.count(study_id) > 1})
    if duplicates:
        raise BuildError(f"ids de estudos duplicados: {', '.join(duplicates)}.")
    return studies


def image_dict(image: Any) -> dict[str, Any]:
    if isinstance(image, dict):
        normalized = dict(image)
    else:
        normalized = {"src": str(image)}

    for field in ("src", "alt", "legenda", "credito", "credit"):
        value = normalized.get(field)
        normalized[field] = "" if value is None else str(value)
    normalized["hero"] = bool(normalized.get("hero"))
    return normalized


def hero_image(study: Study) -> dict[str, Any] | None:
    images = [image_dict(item) for item in study.metadata.get("imagens", [])]
    for image in images:
        if image.get("hero"):
            return image
    return images[0] if images else None


def copy_study_assets(study: Study) -> None:
    for reference in local_references(study):
        relative = validate_reference(study, reference, "asset local")
        if relative is None:
            continue
        source = study.source_dir / relative
        target = study.output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def remove_generated_tree(path: Path) -> None:
    """Remove uma saída gerada mesmo quando o OneDrive marca a pasta como somente leitura."""
    if not path.exists():
        return

    def handle_readonly(func: Any, failing_path: str, _exc_info: Any) -> None:
        os.chmod(failing_path, stat.S_IWRITE)
        func(failing_path)

    shutil.rmtree(path, onerror=handle_readonly)


def clean_generated_outputs() -> None:
    for path in (DIST_ROOT / "assets", STUDY_OUTPUT_ROOT):
        remove_generated_tree(path)
    for path in (DIST_ROOT / "index.html", DIST_ROOT / "manifest.json"):
        if path.exists():
            path.unlink()
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ASSET_ROOT, DIST_ROOT / "assets")


def browser_candidates() -> list[Path]:
    candidates: list[Path] = []
    for command in ("google-chrome", "chrome", "msedge", "chromium", "chromium-browser"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))
    candidates.extend(
        [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", ""))
            / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", ""))
            / "Microsoft/Edge/Application/msedge.exe",
        ]
    )
    return [path for path in candidates if path.is_file()]


def verify_pdf(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 100:
        raise BuildError(f"PDF não foi produzido: {path}")
    if path.read_bytes()[:5] != b"%PDF-":
        raise BuildError(f"arquivo produzido não é um PDF válido: {path}")


def render_pdf_with_playwright(html_path: Path, pdf_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.emulate_media(media="print")
            page.goto(html_path.as_uri(), wait_until="load", timeout=60_000)
            page.wait_for_timeout(500)
            page.evaluate(
                """() => {
                    document.querySelectorAll("details.lex-drawer").forEach((drawer) => {
                        drawer.open = true;
                    });
                }"""
            )
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
        return True
    except Exception:
        if pdf_path.exists():
            pdf_path.unlink()
        return False


def render_pdf_with_chromium(html_path: Path, pdf_path: Path) -> None:
    candidates = browser_candidates()
    if not candidates:
        raise BuildError(
            "Nenhum Chromium/Chrome/Edge foi encontrado para gerar PDF. "
            "Instale as dependências e execute 'python -m playwright install chromium'."
        )

    print_html_path: Path | None = None
    try:
        print_html = html_path.read_text(encoding="utf-8").replace(
            '<details class="lex-drawer">',
            '<details class="lex-drawer" open>',
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".html",
            prefix=f".{html_path.stem}-print-",
            dir=html_path.parent,
            delete=False,
        ) as print_file:
            print_file.write(print_html)
            print_html_path = Path(print_file.name)

        with tempfile.TemporaryDirectory(prefix="estudos-pdf-") as profile:
            command = [
                str(candidates[0]),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={pdf_path.resolve()}",
                print_html_path.as_uri(),
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise BuildError(f"Chromium não conseguiu gerar {pdf_path}: {detail}")
    finally:
        if print_html_path is not None:
            print_html_path.unlink(missing_ok=True)


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    if not render_pdf_with_playwright(html_path, pdf_path):
        render_pdf_with_chromium(html_path, pdf_path)
    normalize_pdf_metadata(pdf_path)
    verify_pdf(pdf_path)


def normalize_pdf_metadata(pdf_path: Path) -> None:
    """Remove timestamps emitted by Chromium so repeated builds are byte-stable."""
    data = pdf_path.read_bytes()
    fixed_date = b"D:20000101000000+00'00'"
    normalized = PDF_DATE_RE.sub(
        lambda match: b"/" + match.group(1) + b" (" + fixed_date + b")",
        data,
    )
    if normalized != data:
        pdf_path.write_bytes(normalized)


def environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["date_br"] = format_date_br
    return env


def credits_context(metadata: dict[str, Any]) -> dict[str, list[Any]]:
    images = [image_dict(item) for item in metadata.get("imagens", [])]
    return {
        "textual": metadata.get("fontes_textuais", []),
        "lexicons": metadata.get("lexicos", []),
        "images": images,
    }


def card_for(study: Study) -> dict[str, Any]:
    return {
        "id": study.study_id,
        "tipo": study.metadata["tipo"],
        "titulo": study.metadata["titulo"],
        "tema": study.metadata.get("tema", ""),
        "passagem": study.metadata["passagem"],
        "traducao": study.metadata["traducao"],
        "traducao_inferida": study.metadata["traducao_inferida"],
        "data": study.metadata["data"],
        "data_formatada": format_date_br(study.metadata["data"]),
        "resumo": study.metadata["resumo"],
        "status": study.metadata["status"],
        "tags": study.metadata["tags"],
        "homiletica": study.metadata["homiletica"],
        "html": f"estudos/{study.study_id}/{study.study_id}.html",
        "pdf": f"estudos/{study.study_id}/{study.study_id}.pdf",
        "fonte": study.source_path.relative_to(ROOT).as_posix(),
    }


def normalize_generated_text(text: str) -> str:
    """Keep generated text stable and free of whitespace-only line noise."""
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


TEMPLATE_BY_TYPE = {
    "devocional": "devotional.html.j2",
    "estudo_exegetico": "exegetical.html.j2",
    "estudo_tematico": "thematic.html.j2",
}


def render_study(study: Study, templates: Environment, skip_pdf: bool) -> dict[str, Any]:
    study.output_dir.mkdir(parents=True, exist_ok=True)
    copy_study_assets(study)

    entries = [entry for entry in study.toc if entry["level"] <= 4]
    context = {
        "metadata": study.metadata,
        "body_html": study.body_html,
        "toc": entries,
        "hero_image": hero_image(study),
        "credits": credits_context(study.metadata),
        "asset_prefix": "../../",
        "source_path": study.source_path.as_posix(),
    }
    study_type = study.metadata["tipo"]
    if study_type not in TEMPLATE_BY_TYPE:
        raise BuildError(f"Tipo de estudo sem template mapeado: {study_type!r}")

    template_name = TEMPLATE_BY_TYPE[study_type]
    html_content = normalize_generated_text(
        templates.get_template(template_name).render(**context)
    )
    html_path = study.output_dir / f"{study.study_id}.html"
    html_path.write_text(html_content, encoding="utf-8")

    pdf_path = study.output_dir / f"{study.study_id}.pdf"
    if not skip_pdf:
        render_pdf(html_path, pdf_path)

    return card_for(study)


def render_index(cards: list[dict[str, Any]], templates: Environment) -> None:
    cards = sorted(cards, key=lambda card: (card["data"], card["titulo"]), reverse=True)
    index = normalize_generated_text(
        templates.get_template("index.html.j2").render(cards=cards, asset_prefix="./")
    )
    (DIST_ROOT / "index.html").write_text(index, encoding="utf-8")
    (DIST_ROOT / "manifest.json").write_text(
        json.dumps({"version": 1, "studies": cards}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def select_study(studies: list[Study], selector: str | None) -> Study | None:
    if selector is None:
        return None
    normalized = selector.casefold()
    for study in studies:
        if study.study_id.casefold() == normalized:
            return study
        if study.source_path.parent.name.casefold() == normalized:
            return study
    raise BuildError(f"estudo não encontrado: {selector}")


def build(selector: str | None = None, skip_pdf: bool = False) -> list[dict[str, Any]]:
    studies = find_studies()
    if not studies:
        raise BuildError("nenhuma fonte Pregações/**/estudo.md foi encontrada.")

    selected = select_study(studies, selector)
    templates = environment()

    if selected is None:
        clean_generated_outputs()
        cards = [render_study(study, templates, skip_pdf) for study in studies]
    else:
        DIST_ROOT.mkdir(parents=True, exist_ok=True)
        (DIST_ROOT / "assets").mkdir(parents=True, exist_ok=True)
        for asset in ASSET_ROOT.iterdir():
            target = DIST_ROOT / "assets" / asset.name
            if asset.is_dir():
                shutil.copytree(asset, target, dirs_exist_ok=True)
            else:
                shutil.copy2(asset, target)
        if selected.output_dir.exists():
            remove_generated_tree(selected.output_dir)
        render_study(selected, templates, skip_pdf)
        cards = [card_for(study) for study in studies if study.output_dir.exists()]

    render_index(cards, templates)
    return cards


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", nargs="?", help="id ou pasta de um estudo específico")
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="gera HTML e índice sem executar o gerador de PDF",
    )
    args = parser.parse_args()

    try:
        cards = build(args.study, skip_pdf=args.skip_pdf)
    except BuildError as exc:
        print(f"ERRO DE BUILD: {exc}", file=sys.stderr)
        return 1

    pdf_note = " (PDF ignorado)" if args.skip_pdf else ""
    print(f"Build concluído: {len(cards)} estudo(s){pdf_note}. Saída: {DIST_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
