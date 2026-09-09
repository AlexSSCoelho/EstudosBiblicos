"""Build the canonical Bible-study sources into HTML, PDF and a library index.

The repository deliberately keeps the build entry point small and explicit:
Markdown plus YAML front matter is the editorial source, while everything in
dist/ is a reproducible artifact.
"""

from __future__ import annotations

import argparse
from html import escape
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
from pathlib import Path
from typing import Any, Iterable

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
}
REQUIRED_FIELDS = ("id", "tipo", "titulo", "passagem", "data", "resumo")
LOCAL_REF_RE = re.compile(r"(?P<ref>\./[A-Za-z0-9À-ÿ0-9_./ -]+)")
DETAIL_BLOCK_RE = re.compile(
    r'<details\s+class="lex-drawer">\s*<summary>(?P<summary>.*?)</summary>'
    r'(?P<body>.*?)</details>',
    re.IGNORECASE | re.DOTALL,
)
MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "toc", "smarty"]
PDF_DATE_RE = re.compile(
    rb"/(CreationDate|ModDate) \(D:\d{14}[+-]\d{2}'\d{2}'\)"
)


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
    raise BuildError(f"{path}: tipo inválido: {value!r}. Use devocional ou estudo_exegetico.")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


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
    normalized["traducao_inferida"] = not bool(str(metadata.get("traducao", "")).strip())
    normalized["traducao"] = (
        str(metadata.get("traducao")).strip()
        if str(metadata.get("traducao", "")).strip()
        else DEFAULT_TRANSLATIONS[normalized["tipo"]]
    )
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
    normalized["igreja"] = metadata.get("igreja")
    normalized["status"] = str(metadata.get("status", "rascunho"))
    return normalized


def local_references(study: Study) -> set[str]:
    references = set(LOCAL_REF_RE.findall(study.body))
    for image in study.metadata.get("imagens", []):
        if isinstance(image, dict) and str(image.get("src", "")).startswith("./"):
            references.add(str(image["src"]))
        elif isinstance(image, str) and image.startswith("./"):
            references.add(image)
    return references


def validate_source(study: Study) -> None:
    if "data:image/" in study.body.lower() or "data:image/" in study.body_html.lower():
        raise BuildError(
            f"{study.source_path}: imagens Base64 não são permitidas; use um asset local ou URL perene."
        )

    for reference in local_references(study):
        relative = reference[2:]
        if not relative or relative.startswith("../") or "/../" in relative:
            raise BuildError(f"{study.source_path}: caminho de asset inválido: {reference}")
        candidate = (study.source_dir / relative).resolve()
        if not candidate.is_file():
            raise BuildError(f"{study.source_path}: asset local não encontrado: {reference}")


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
            f"<summary>{summary}</summary>\n"
            f"{inner_html}\n"
            "</details>"
        )

    body_with_drawers = DETAIL_BLOCK_RE.sub(render_lexical_drawer, body)
    parser = markdown_parser()
    body_html = parser.convert(body_with_drawers)
    return body_html, flatten_toc(parser.toc_tokens)


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
        return dict(image)
    return {"src": str(image)}


def hero_image(study: Study) -> dict[str, Any] | None:
    images = [image_dict(item) for item in study.metadata.get("imagens", [])]
    for image in images:
        if image.get("hero"):
            return image
    return images[0] if images else None


def copy_study_assets(study: Study) -> None:
    for reference in local_references(study):
        relative = Path(reference[2:])
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

    with tempfile.TemporaryDirectory(prefix="estudos-pdf-") as profile:
        command = [
            str(candidates[0]),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise BuildError(f"Chromium não conseguiu gerar {pdf_path}: {detail}")


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
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_ROOT)),
        undefined=StrictUndefined,
        autoescape=select_autoescape(["html", "xml"]),
    )


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
        "passagem": study.metadata["passagem"],
        "traducao": study.metadata["traducao"],
        "traducao_inferida": study.metadata["traducao_inferida"],
        "data": study.metadata["data"],
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


def render_study(study: Study, templates: Environment, skip_pdf: bool) -> dict[str, Any]:
    study.output_dir.mkdir(parents=True, exist_ok=True)
    copy_study_assets(study)

    entries = [entry for entry in study.toc if entry["level"] <= 3]
    context = {
        "metadata": study.metadata,
        "body_html": study.body_html,
        "toc": entries,
        "hero_image": hero_image(study),
        "credits": credits_context(study.metadata),
        "asset_prefix": "../../",
        "source_path": study.source_path.as_posix(),
    }
    template_name = (
        "devotional.html.j2"
        if study.metadata["tipo"] == "devocional"
        else "exegetical.html.j2"
    )
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
