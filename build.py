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
from dataclasses import dataclass, field
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
CATEGORY_OUTPUT_ROOT = DIST_ROOT / "tipos"

DEFAULT_TRANSLATIONS = {
    "devocional": "NVI",
    "estudo_exegetico": "ACF",
    "estudo_tematico": "ACF",
    "pregacao": "",
}
REQUIRED_FIELDS = ("id", "tipo", "titulo", "passagem", "data", "resumo")
REQUIRED_FIELDS_BY_TYPE = {
    "devocional": REQUIRED_FIELDS,
    "estudo_exegetico": REQUIRED_FIELDS,
    "estudo_tematico": REQUIRED_FIELDS,
    "pregacao": ("id", "tipo", "titulo"),
}
STUDY_TYPE_ORDER = ("devocional", "estudo_exegetico", "estudo_tematico", "pregacao")
STUDY_TYPE_PRESENTATION = {
    "devocional": {
        "slug": "devocionais",
        "kicker": "Para meditar",
        "title": "Devocionais",
        "description": "Uma reflexão breve para meditar em uma passagem e conectá-la à vida.",
    },
    "estudo_exegetico": {
        "slug": "estudos-expositivos",
        "legacy_slugs": ("estudos-da-passagem",),
        "kicker": "Para compreender",
        "title": "Estudos expositivos",
        "description": "Uma passagem por vez, com contexto, explicação do texto e reflexão sobre sua mensagem.",
    },
    "estudo_tematico": {
        "slug": "estudos-tematicos",
        "kicker": "Para investigar",
        "title": "Estudos temáticos",
        "description": "Um tema bíblico examinado à luz de várias passagens.",
    },
    "pregacao": {
        "slug": "pregacoes",
        "kicker": "Para pregar",
        "title": "Pregações",
        "description": "Esboços e manuscritos de púlpito com anotações por seção e histórico de revisões.",
    },
}
GITHUB_REPO = "AlexSSCoelho/EstudosBiblicos"
GITHUB_BRANCH = "main"
SERMON_REVISION_FILE_RE = re.compile(r"^r([1-9]\d*)\.md$", re.IGNORECASE)
SERMON_REVISION_LABEL_RE = re.compile(r"^[rR]?([1-9]\d*)$")
DETAIL_BLOCK_RE = re.compile(
    r'<details\s+class="lex-drawer">\s*<summary>(?P<summary>.*?)</summary>'
    r'(?P<body>.*?)</details>',
    re.IGNORECASE | re.DOTALL,
)
VERSE_HEADING_RE = re.compile(
    r'(?m)^(?:v\.|vv\.|versículo|versículos)?\s*(\d+(?:[.:]\d+)?(?:[–—\-]\d+(?:[.:]\d+)?)?)\s*\n+(#{2,4}\s+(.+))$'
)
MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "toc", "smarty"]
SEMANTIC_SKIP_TAGS = frozenset({"pre", "code", "script", "style", "h1", "h2"})
BIBLICAL_ABBREV_AMBIGUOUS = "At|Am|Ed|Et|Ex|Na|Os"
BIBLICAL_ABBREV_SAFE = (
    "Gn|Êx|Lv|Nm|Dt|Js|Jz|Rt|Sm|Rs|Cr|Ne|Jó|Sl|Pv|Ec|Ct|Is|Jr|Lm|Ez|Dn|Jl|Ob|Jn|Mq|"
    "Hc|Sf|Ag|Zc|Ml|Mt|Mc|Lc|Jo|Rm|Co|Gl|Ef|Fp|Cl|Ts|Tm|Tt|Fm|Hb|Tg|Pe|Jd|Ap"
)
BIBLICAL_FULL_BOOKS = (
    "Gênesis|Êxodo|Levítico|Números|Deuteronômio|Josué|Juízes|Rute|Samuel|Reis|Crônicas|"
    "Esdras|Neemias|Ester|Jó|Salmos|Salmo|Provérbios|Eclesiastes|Cantares|Isaías|Jeremias|"
    "Lamentações|Ezequiel|Daniel|Oseias|Oséias|Joel|Amós|Obadias|Jonas|Miqueias|Miquéias|"
    "Naum|Habacuque|Sofonias|Ageu|Zacarias|Malaquias|Mateus|Marcos|Lucas|João|Atos|"
    "Romanos|Coríntios|Gálatas|Efésios|Filipenses|Colossenses|Tessalonicenses|Timóteo|Tito|"
    "Filemom|Hebreus|Tiago|Pedro|Judas|Apocalipse"
)
ATOMIC_UNIT_PATTERNS = (
    re.compile(
        rf"(?<![\wÀ-ÿ])(?:([1-3])\s+)?({BIBLICAL_FULL_BOOKS}|{BIBLICAL_ABBREV_SAFE})\s+"
        rf"(\d+(?:[.:]\d+)?(?:[–—\-]\d+(?:[.:]\d+)?)?)"
    ),
    re.compile(
        rf"(?<![\wÀ-ÿ])(?:([1-3])\s+)?({BIBLICAL_ABBREV_AMBIGUOUS})\s+"
        rf"(\d+[.:]\d+(?:[–—\-]\d+(?:[.:]\d+)?)?)"
    ),
    re.compile(
        r"(?<![\wÀ-ÿ])(vv?\.|caps?\.|capítulos?|versículos?|cf\.)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕ\d])"
    ),
    re.compile(r"(?<![\wÀ-ÿ])(\d+)\s+(a\.C\.|d\.C\.)"),
)
HTML_TAG_TOKEN_RE = re.compile(r"(<[^>]+>)")
HTML_TAG_NAME_RE = re.compile(r"^<\s*(/)?\s*([a-zA-Z0-9]+)")
PDF_DATE_RE = re.compile(
    rb"/(CreationDate|ModDate) \(D:\d{14}[+-]\d{2}'\d{2}'\)"
)
DATA_URI_RE = re.compile(r"\bdata:", re.IGNORECASE)
DATA_IMAGE_RE = re.compile(r"\bdata:image/", re.IGNORECASE)
ALLOWED_EXTERNAL_SCHEMES = {"http", "https"}
REVIEW_SUPPORTED_TYPES = frozenset({"estudo_exegetico", "estudo_tematico"})
REVIEW_ITEM_TYPES = ("quiz", "flashcard", "aberta")
REVIEW_DIFFICULTIES = ("facil", "intermediario", "dificil")


class BuildError(RuntimeError):
    """An actionable build failure."""


@dataclass
class Study:
    metadata: dict[str, Any]
    body: str
    body_html: str
    toc: list[dict[str, Any]]
    source_path: Path
    review: dict[str, Any] | None = None
    revisions: list[dict[str, Any]] = field(default_factory=list)

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
        is_range = any(sep in verse for sep in ("–", "-", "—"))
        prefix = "Versículos" if is_range else "Versículo"
        return (
            f'<div class="verse-marker" id="{anchor_id}">'
            f'<span class="verse-tag"><span class="verse-tag-prefix">{prefix}</span> {verse}</span>'
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
            # Não tratar livros bíblicos numerados (ex: 1 Samuel, 2 Reis, 1 João) como versículos
            is_numbered_book = bool(re.match(r"^[123]\s+(?:samuel|reis|crônicas|cronicas|coríntios|corintios|tessalonicenses|timóteo|timoteo|pedro|joão|joao)\b", name, re.IGNORECASE))
            if not is_numbered_book:
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
    if normalized in {
        "pregacao",
        "pregação",
        "sermao",
        "sermão",
        "esboco",
        "esboço",
        "mensagem",
    }:
        return "pregacao"
    raise BuildError(
        f"{path}: tipo inválido: {value!r}. Use devocional, estudo_exegetico, estudo_tematico ou pregacao."
    )


def normalize_revision(value: Any, path: Path) -> tuple[str, int]:
    if value is None or not str(value).strip():
        return "R1", 1
    raw = str(value).strip()
    match = SERMON_REVISION_LABEL_RE.fullmatch(raw)
    if not match:
        raise BuildError(
            f"{path}: revisão inválida: {value!r}. Use R1, R2, R3... (ou número inteiro positivo)."
        )
    number = int(match.group(1))
    return f"R{number}", number


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
    if not metadata.get("tipo"):
        missing_base = [field for field in REQUIRED_FIELDS if not metadata.get(field)]
        raise BuildError(f"{path}: campos obrigatórios ausentes: {', '.join(missing_base)}.")

    study_type = normalize_type(metadata["tipo"], path)
    required_fields = REQUIRED_FIELDS_BY_TYPE[study_type]
    missing = [field for field in required_fields if not metadata.get(field)]
    if missing:
        raise BuildError(f"{path}: campos obrigatórios ausentes: {', '.join(missing)}.")

    study_id = str(metadata["id"]).strip()
    if study_id != slugify(study_id) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", study_id):
        raise BuildError(f"{path}: id inválido: {study_id!r}. Use slug minúsculo com hífens.")

    normalized = dict(metadata)
    normalized["id"] = study_id
    normalized["tipo"] = study_type
    normalized["titulo"] = str(metadata["titulo"]).strip()
    normalized["passagem"] = str(metadata.get("passagem") or "").strip()
    normalized["resumo"] = str(metadata.get("resumo") or "").strip()
    normalized["data"] = str(metadata.get("data") or "").strip()
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
    default_translation = DEFAULT_TRANSLATIONS[normalized["tipo"]]
    normalized["traducao_inferida"] = (not bool(translation_text)) and bool(default_translation)
    normalized["traducao"] = translation_text or default_translation
    normalized["homiletica"] = bool(metadata.get("homiletica", False))
    if normalized["tipo"] == "estudo_tematico" and normalized["homiletica"]:
        raise BuildError(f"{path}: estudos temáticos não incluem proposição ou movimentos homiléticos.")
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
    for field_name in ("autor", "tese", "destinatarios", "nota_revisao", "estudo_origem"):
        value = metadata.get(field_name)
        normalized[field_name] = "" if value is None else str(value).strip()
    igreja_value = metadata.get("igreja")
    if igreja_value is None or not str(igreja_value).strip():
        igreja_value = metadata.get("local")
    normalized["igreja"] = "" if igreja_value is None else str(igreja_value).strip()

    if normalized["tipo"] == "pregacao":
        revisao_label, revisao_numero = normalize_revision(metadata.get("revisao"), path)
        normalized["revisao"] = revisao_label
        normalized["revisao_numero"] = revisao_numero
        raw_sermao_id = str(metadata.get("sermao_id") or "").strip() or study_id
        if raw_sermao_id != slugify(raw_sermao_id) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]*", raw_sermao_id
        ):
            raise BuildError(
                f"{path}: sermao_id inválido: {raw_sermao_id!r}. Use slug minúsculo com hífens."
            )
        normalized["sermao_id"] = raw_sermao_id
    else:
        normalized["revisao"] = ""
        normalized["revisao_numero"] = 0
        normalized["sermao_id"] = ""

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


def protect_semantic_units_in_text(text: str) -> str:
    """Bind atomic biblical and editorial units with NBSP to avoid orphan breaks."""
    for pattern in ATOMIC_UNIT_PATTERNS[:2]:
        text = pattern.sub(
            lambda m: (
                f"{m.group(1)}\u00a0{m.group(2)}\u00a0{m.group(3)}"
                if m.group(1)
                else f"{m.group(2)}\u00a0{m.group(3)}"
            ),
            text,
        )
    text = ATOMIC_UNIT_PATTERNS[2].sub(lambda m: f"{m.group(1)}\u00a0", text)
    text = ATOMIC_UNIT_PATTERNS[3].sub(lambda m: f"{m.group(1)}\u00a0{m.group(2)}", text)
    return text


def protect_semantic_units(html: str) -> str:
    """Apply atomic line-break protection only to prose text nodes."""
    tokens = HTML_TAG_TOKEN_RE.split(html)
    skip_stack: list[str] = []
    output: list[str] = []

    for token in tokens:
        if not token:
            continue
        if token.startswith("<"):
            tag_match = HTML_TAG_NAME_RE.match(token)
            if tag_match:
                is_closing = bool(tag_match.group(1))
                tag_name = tag_match.group(2).lower()
                if tag_name in SEMANTIC_SKIP_TAGS:
                    if is_closing:
                        if tag_name in skip_stack:
                            while skip_stack:
                                popped = skip_stack.pop()
                                if popped == tag_name:
                                    break
                    elif not token.rstrip().endswith("/>"):
                        skip_stack.append(tag_name)
            output.append(token)
        else:
            output.append(token if skip_stack else protect_semantic_units_in_text(token))

    return "".join(output)


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
    body_html = protect_semantic_units(body_html)
    return body_html, enrich_toc(flatten_toc(parser.toc_tokens), verse_map)


def _require_non_empty_str(value: Any, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise BuildError(f"{label} não pode ficar vazio.")
    return text


def _require_str_list(value: Any, label: str, *, min_items: int = 1) -> list[str]:
    if not isinstance(value, list):
        raise BuildError(f"{label} deve ser uma lista.")
    cleaned = [str(item).strip() for item in value if item is not None and str(item).strip()]
    if len(cleaned) < min_items:
        raise BuildError(f"{label} exige ao menos {min_items} item(ns) válido(s).")
    return cleaned


def _validate_active_reading(
    raw_items: Any, toc_by_id: dict[str, dict[str, Any]], review_path: Path
) -> list[dict[str, Any]]:
    """Validate and normalize active-reading marginalia anchored to h2/h3 headings."""
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise BuildError(f"{review_path}: 'leitura_ativa' deve ser uma lista.")

    seen_targets: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_items):
        label = f"{review_path}: leitura_ativa[{index}]"
        if not isinstance(entry, dict):
            raise BuildError(f"{label} deve ser um objeto.")
        target_id = _require_non_empty_str(entry.get("target_id"), f"{label}.target_id")
        toc_entry = toc_by_id.get(target_id)
        if toc_entry is None or toc_entry.get("level") not in (2, 3):
            raise BuildError(
                f"{label}.target_id ({target_id!r}) não corresponde a um título h2 ou h3 do estudo."
            )
        if target_id in seen_targets:
            raise BuildError(f"{label}.target_id duplicado: {target_id!r}.")
        seen_targets.add(target_id)
        perguntas = _require_str_list(entry.get("perguntas"), f"{label}.perguntas", min_items=1)
        normalized.append(
            {
                "target_id": target_id,
                "target_level": int(toc_entry["level"]),
                "target_title": toc_entry.get("name", ""),
                "perguntas": perguntas,
            }
        )
    return normalized


def _validate_quiz_item(item: dict[str, Any], label: str) -> dict[str, Any]:
    enunciado = _require_non_empty_str(item.get("enunciado"), f"{label}.enunciado")
    justificativa = _require_non_empty_str(item.get("justificativa"), f"{label}.justificativa")
    raw_options = item.get("alternativas")
    if not isinstance(raw_options, list) or len(raw_options) != 4:
        raise BuildError(f"{label}.alternativas deve conter exatamente 4 opções.")

    alternativas: list[dict[str, Any]] = []
    correct_count = 0
    for opt_index, opt in enumerate(raw_options):
        opt_label = f"{label}.alternativas[{opt_index}]"
        if not isinstance(opt, dict):
            raise BuildError(f"{opt_label} deve ser um objeto com 'texto' e 'correta'.")
        texto = _require_non_empty_str(opt.get("texto"), f"{opt_label}.texto")
        if not isinstance(opt.get("correta"), bool):
            raise BuildError(f"{opt_label}.correta deve ser booleano (true/false).")
        is_correct = bool(opt["correta"])
        if is_correct:
            correct_count += 1
        alternativas.append({"texto": texto, "correta": is_correct})

    if correct_count != 1:
        raise BuildError(f"{label}.alternativas deve ter exatamente 1 alternativa correta.")

    return {
        "enunciado": enunciado,
        "alternativas": alternativas,
        "justificativa": justificativa,
    }


def _validate_flashcard_item(item: dict[str, Any], label: str) -> dict[str, Any]:
    frente = _require_non_empty_str(item.get("frente"), f"{label}.frente")
    resposta_principal = _require_non_empty_str(
        item.get("resposta_principal"), f"{label}.resposta_principal"
    )
    aceitas = _require_str_list(item.get("aceitas"), f"{label}.aceitas", min_items=1)
    raw_parciais = item.get("parciais")
    parciais = (
        _require_str_list(raw_parciais, f"{label}.parciais", min_items=0)
        if raw_parciais is not None
        else []
    )
    nota_explicativa = _require_non_empty_str(
        item.get("nota_explicativa"), f"{label}.nota_explicativa"
    )
    return {
        "frente": frente,
        "resposta_principal": resposta_principal,
        "aceitas": aceitas,
        "parciais": parciais,
        "nota_explicativa": nota_explicativa,
    }


def _validate_open_item(item: dict[str, Any], label: str) -> dict[str, Any]:
    enunciado = _require_non_empty_str(item.get("enunciado"), f"{label}.enunciado")
    resposta_modelo = _require_non_empty_str(
        item.get("resposta_modelo"), f"{label}.resposta_modelo"
    )
    trecho_ancora = str(item.get("trecho_ancora") or "").strip()

    rubrica = item.get("rubrica")
    if not isinstance(rubrica, dict):
        raise BuildError(f"{label}.rubrica deve ser um objeto.")
    raw_nucleos = rubrica.get("nucleos")
    if not isinstance(raw_nucleos, list) or len(raw_nucleos) < 2:
        raise BuildError(f"{label}.rubrica.nucleos exige ao menos 2 núcleos de sentido.")

    nucleos: list[dict[str, Any]] = []
    for n_index, nucleo in enumerate(raw_nucleos):
        n_label = f"{label}.rubrica.nucleos[{n_index}]"
        if not isinstance(nucleo, dict):
            raise BuildError(f"{n_label} deve ser um objeto.")
        rotulo = _require_non_empty_str(nucleo.get("rotulo"), f"{n_label}.rotulo")
        termos = (
            _require_str_list(nucleo.get("termos"), f"{n_label}.termos", min_items=0)
            if nucleo.get("termos") is not None
            else []
        )
        expressoes = (
            _require_str_list(nucleo.get("expressoes"), f"{n_label}.expressoes", min_items=0)
            if nucleo.get("expressoes") is not None
            else []
        )
        if not termos and not expressoes:
            raise BuildError(f"{n_label} precisa definir 'termos' ou 'expressoes'.")
        nucleos.append({"rotulo": rotulo, "termos": termos, "expressoes": expressoes})

    raw_sinais = rubrica.get("sinais_erro")
    sinais_erro: list[list[str]] = []
    if raw_sinais is not None:
        if not isinstance(raw_sinais, list):
            raise BuildError(f"{label}.rubrica.sinais_erro deve ser uma lista.")
        for s_index, sinal in enumerate(raw_sinais):
            if isinstance(sinal, str) and sinal.strip():
                sinais_erro.append([sinal.strip()])
            elif isinstance(sinal, list):
                sinais_erro.append(
                    _require_str_list(
                        sinal, f"{label}.rubrica.sinais_erro[{s_index}]", min_items=1
                    )
                )
            else:
                raise BuildError(
                    f"{label}.rubrica.sinais_erro[{s_index}] deve ser texto ou lista de termos."
                )

    return {
        "enunciado": enunciado,
        "resposta_modelo": resposta_modelo,
        "trecho_ancora": trecho_ancora,
        "rubrica": {
            "nucleos": nucleos,
            "sinais_erro": sinais_erro,
        },
    }


def _validate_review_sections(
    raw_sections: Any, h2_by_id: dict[str, dict[str, Any]], review_path: Path
) -> list[dict[str, Any]]:
    """Validate and normalize per-h2 review batteries (quiz, flashcard, open)."""
    if raw_sections is None:
        return []
    if not isinstance(raw_sections, list):
        raise BuildError(f"{review_path}: 'revisao_secoes' deve ser uma lista.")

    seen_sections: set[str] = set()
    seen_item_ids: set[str] = set()
    normalized_sections: list[dict[str, Any]] = []

    for sec_index, section in enumerate(raw_sections):
        sec_label = f"{review_path}: revisao_secoes[{sec_index}]"
        if not isinstance(section, dict):
            raise BuildError(f"{sec_label} deve ser um objeto.")
        section_id = _require_non_empty_str(section.get("section_id"), f"{sec_label}.section_id")
        h2_entry = h2_by_id.get(section_id)
        if h2_entry is None:
            raise BuildError(
                f"{sec_label}.section_id ({section_id!r}) não corresponde a um título h2 do estudo."
            )
        if section_id in seen_sections:
            raise BuildError(f"{sec_label}.section_id duplicado: {section_id!r}.")
        seen_sections.add(section_id)

        raw_items = section.get("itens")
        if not isinstance(raw_items, list) or len(raw_items) < 6:
            raise BuildError(f"{sec_label}.itens exige no mínimo 6 questões.")

        type_counts = {item_type: 0 for item_type in REVIEW_ITEM_TYPES}
        difficulties_present: set[str] = set()
        normalized_items: list[dict[str, Any]] = []

        for item_index, item in enumerate(raw_items):
            item_label = f"{sec_label}.itens[{item_index}]"
            if not isinstance(item, dict):
                raise BuildError(f"{item_label} deve ser um objeto.")
            item_id = _require_non_empty_str(item.get("id"), f"{item_label}.id")
            if item_id in seen_item_ids:
                raise BuildError(f"{item_label}.id duplicado: {item_id!r}.")
            seen_item_ids.add(item_id)

            item_type = _require_non_empty_str(item.get("tipo"), f"{item_label}.tipo").casefold()
            if item_type not in REVIEW_ITEM_TYPES:
                raise BuildError(
                    f"{item_label}.tipo inválido: {item_type!r}. Use quiz, flashcard ou aberta."
                )

            difficulty = _require_non_empty_str(
                item.get("dificuldade"), f"{item_label}.dificuldade"
            ).casefold()
            if difficulty not in REVIEW_DIFFICULTIES:
                raise BuildError(
                    f"{item_label}.dificuldade inválida: {difficulty!r}. Use facil, intermediario ou dificil."
                )

            type_counts[item_type] += 1
            difficulties_present.add(difficulty)

            if item_type == "quiz":
                payload = _validate_quiz_item(item, item_label)
            elif item_type == "flashcard":
                payload = _validate_flashcard_item(item, item_label)
            else:
                payload = _validate_open_item(item, item_label)

            normalized_items.append(
                {
                    "id": item_id,
                    "tipo": item_type,
                    "dificuldade": difficulty,
                    **payload,
                }
            )

        missing_types = [t for t, count in type_counts.items() if count < 2]
        if missing_types:
            raise BuildError(
                f"{sec_label}: cada h2 exige ao menos 2 itens de cada tipo; faltando em {', '.join(missing_types)}."
            )
        missing_difficulties = [d for d in REVIEW_DIFFICULTIES if d not in difficulties_present]
        if missing_difficulties:
            raise BuildError(
                f"{sec_label}: cada h2 deve contemplar os 3 níveis de dificuldade; ausente(s): {', '.join(missing_difficulties)}."
            )

        normalized_sections.append(
            {
                "section_id": section_id,
                "section_title": h2_entry.get("name", ""),
                "itens": normalized_items,
            }
        )

    return normalized_sections


def load_review(
    study_dir: Path, study_id: str, study_type: str, toc: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Load and validate optional active-reading and review sidecar (revisao.yml)."""
    review_path = study_dir / "revisao.yml"
    if not review_path.exists():
        return None
    if study_type not in REVIEW_SUPPORTED_TYPES:
        raise BuildError(
            f"{review_path}: revisão ativa é suportada apenas em estudos expositivos e temáticos."
        )

    raw_data = yaml.safe_load(review_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise BuildError(f"{review_path}: a raiz do arquivo deve ser um objeto YAML.")
    if raw_data.get("version") != 1:
        raise BuildError(f"{review_path}: campo obrigatório 'version: 1' ausente ou inválido.")

    toc_by_id = {entry["id"]: entry for entry in toc if entry.get("id")}
    h2_by_id = {
        entry["id"]: entry for entry in toc if entry.get("id") and entry.get("level") == 2
    }

    leitura_ativa = _validate_active_reading(raw_data.get("leitura_ativa"), toc_by_id, review_path)
    revisao_secoes = _validate_review_sections(
        raw_data.get("revisao_secoes"), h2_by_id, review_path
    )
    if not leitura_ativa and not revisao_secoes:
        raise BuildError(
            f"{review_path}: informe ao menos 'leitura_ativa' ou 'revisao_secoes'."
        )

    return {
        "version": 1,
        "study_id": study_id,
        "leitura_ativa": leitura_ativa,
        "revisao_secoes": revisao_secoes,
    }


def load_study(path: Path) -> Study:
    metadata, body = parse_source(path)
    metadata = normalize_metadata(metadata, path)
    body_html, toc = render_markdown(body)
    review = load_review(path.parent, str(metadata["id"]), str(metadata["tipo"]), toc)
    study = Study(
        metadata=metadata,
        body=body,
        body_html=body_html,
        toc=toc,
        source_path=path,
        review=review,
    )
    validate_source(study)
    return study


def relative_repo_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def revision_summary_for(study: Study) -> dict[str, Any]:
    return {
        "id": study.study_id,
        "revisao": study.metadata["revisao"],
        "revisao_numero": study.metadata["revisao_numero"],
        "titulo": study.metadata["titulo"],
        "data": study.metadata["data"],
        "data_formatada": study.metadata["data_formatada"],
        "igreja": study.metadata["igreja"],
        "nota_revisao": study.metadata.get("nota_revisao", ""),
        "href": f"../{study.study_id}/",
        "html": f"estudos/{study.study_id}/",
        "pdf": f"estudos/{study.study_id}/{study.study_id}.pdf",
        "source_path": relative_repo_posix(study.source_path),
    }


def attach_sermon_revisions(studies: list[Study]) -> None:
    grouped: dict[str, list[Study]] = {}
    for study in studies:
        if study.metadata.get("tipo") == "pregacao":
            grouped.setdefault(study.metadata["sermao_id"], []).append(study)

    for sermao_id, group in grouped.items():
        group.sort(key=lambda item: (item.metadata["revisao_numero"], item.study_id))
        seen_numbers: set[int] = set()
        for item in group:
            rev_num = int(item.metadata["revisao_numero"])
            if rev_num in seen_numbers:
                raise BuildError(
                    f"Revisão duplicada R{rev_num} para a pregação {sermao_id!r}."
                )
            seen_numbers.add(rev_num)

        summaries = [revision_summary_for(item) for item in group]
        for item in group:
            item.revisions = [
                {**summary, "is_current": summary["id"] == item.study_id}
                for summary in summaries
            ]


def is_study_source_file(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name
    return name.casefold() == "estudo.md" or bool(SERMON_REVISION_FILE_RE.fullmatch(name))


def find_studies() -> list[Study]:
    if not SOURCE_ROOT.exists():
        return []
    sources = sorted(path for path in SOURCE_ROOT.rglob("*.md") if is_study_source_file(path))
    studies = [load_study(path) for path in sources]
    ids = [study.study_id for study in studies]
    duplicates = sorted({study_id for study_id in ids if ids.count(study_id) > 1})
    if duplicates:
        raise BuildError(f"ids de estudos duplicados: {', '.join(duplicates)}.")
    attach_sermon_revisions(studies)
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
    for path in (DIST_ROOT / "assets", STUDY_OUTPUT_ROOT, CATEGORY_OUTPUT_ROOT):
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
    revisions = study.revisions or (
        [{**revision_summary_for(study), "is_current": True}]
        if study.metadata["tipo"] == "pregacao"
        else []
    )
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
        "igreja": study.metadata.get("igreja", ""),
        "resumo": study.metadata["resumo"],
        "status": study.metadata["status"],
        "tags": study.metadata["tags"],
        "homiletica": study.metadata["homiletica"],
        "revisao": study.metadata.get("revisao", ""),
        "revisao_numero": study.metadata.get("revisao_numero", 0),
        "sermao_id": study.metadata.get("sermao_id", ""),
        "revisoes_total": len(revisions) if study.metadata["tipo"] == "pregacao" else 0,
        "revisoes": [
            {
                "id": rev["id"],
                "revisao": rev["revisao"],
                "data_formatada": rev["data_formatada"],
                "igreja": rev["igreja"],
                "html": rev["html"],
                "pdf": rev["pdf"],
            }
            for rev in revisions
        ],
        "html": f"estudos/{study.study_id}/",
        "pdf": f"estudos/{study.study_id}/{study.study_id}.pdf",
        "fonte": relative_repo_posix(study.source_path),
    }


def normalize_generated_text(text: str) -> str:
    """Keep generated text stable and free of whitespace-only line noise."""
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


TEMPLATE_BY_TYPE = {
    "devocional": "devotional.html.j2",
    "estudo_exegetico": "exegetical.html.j2",
    "estudo_tematico": "thematic.html.j2",
    "pregacao": "sermon.html.j2",
}


def sermon_editor_payload(study: Study, revisions: list[dict[str, Any]]) -> dict[str, Any]:
    max_revision = max((int(rev["revisao_numero"]) for rev in revisions), default=1)
    rel_source = relative_repo_posix(study.source_path)
    rel_dir = relative_repo_posix(study.source_dir)
    return {
        "id": study.study_id,
        "sermao_id": study.metadata["sermao_id"],
        "revisao": study.metadata["revisao"],
        "revisao_numero": study.metadata["revisao_numero"],
        "next_revisao_numero": max_revision + 1,
        "source_path": rel_source,
        "source_dir": rel_dir,
        "github_repo": GITHUB_REPO,
        "github_branch": GITHUB_BRANCH,
        "metadata": {
            "titulo": study.metadata["titulo"],
            "passagem": study.metadata["passagem"],
            "tema": study.metadata["tema"],
            "data": study.metadata["data"],
            "igreja": study.metadata["igreja"],
            "traducao": study.metadata["traducao"],
            "resumo": study.metadata["resumo"],
            "nota_revisao": study.metadata.get("nota_revisao", ""),
            "estudo_origem": study.metadata.get("estudo_origem", ""),
        },
        "body": study.body,
        "revisions": [
            {
                "id": rev["id"],
                "revisao": rev["revisao"],
                "revisao_numero": rev["revisao_numero"],
                "data_formatada": rev["data_formatada"],
                "igreja": rev["igreja"],
                "nota_revisao": rev["nota_revisao"],
                "href": rev["href"],
                "source_path": rev["source_path"],
                "is_current": rev["is_current"],
            }
            for rev in revisions
        ],
    }


def render_study(study: Study, templates: Environment, skip_pdf: bool) -> dict[str, Any]:
    study.output_dir.mkdir(parents=True, exist_ok=True)
    copy_study_assets(study)

    entries = [entry for entry in study.toc if entry["level"] <= 4]
    review_json = (
        json.dumps(study.review, ensure_ascii=False).replace("</", "<\\/")
        if study.review is not None
        else ""
    )
    study_type = study.metadata["tipo"]
    revisions: list[dict[str, Any]] = []
    sermon_editor_json = ""
    if study_type == "pregacao":
        revisions = study.revisions or [{**revision_summary_for(study), "is_current": True}]
        sermon_editor_json = json.dumps(
            sermon_editor_payload(study, revisions), ensure_ascii=False
        ).replace("</", "<\\/")

    context = {
        "metadata": study.metadata,
        "body_html": study.body_html,
        "toc": entries,
        "hero_image": hero_image(study),
        "credits": credits_context(study.metadata),
        "asset_prefix": "../../",
        "source_path": study.source_path.as_posix(),
        "review_data": study.review,
        "review_json": review_json,
        "revisions": revisions,
        "sermon_editor_json": sermon_editor_json,
    }
    if study_type not in TEMPLATE_BY_TYPE:
        raise BuildError(f"Tipo de estudo sem template mapeado: {study_type!r}")

    template_name = TEMPLATE_BY_TYPE[study_type]
    html_content = normalize_generated_text(
        templates.get_template(template_name).render(**context)
    )
    html_path = study.output_dir / "index.html"
    html_path.write_text(html_content, encoding="utf-8")
    # Mantém o endereço antigo funcionando para favoritos e links já compartilhados.
    legacy_html_path = study.output_dir / f"{study.study_id}.html"
    legacy_html_path.write_text(html_content, encoding="utf-8")

    pdf_path = study.output_dir / f"{study.study_id}.pdf"
    if not skip_pdf:
        render_pdf(html_path, pdf_path)

    return card_for(study)


def deduplicate_sermon_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the latest revision card per sermon family in catalog views."""
    non_sermons: list[dict[str, Any]] = []
    latest_by_sermon: dict[str, dict[str, Any]] = {}
    for card in cards:
        if card["tipo"] != "pregacao":
            non_sermons.append(card)
            continue
        sermao_id = card.get("sermao_id") or card["id"]
        current = latest_by_sermon.get(sermao_id)
        if current is None or int(card.get("revisao_numero", 0)) > int(
            current.get("revisao_numero", 0)
        ):
            latest_by_sermon[sermao_id] = card
    return non_sermons + list(latest_by_sermon.values())


def sort_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated = [card for card in cards if card.get("data")]
    undated = [card for card in cards if not card.get("data")]
    dated.sort(key=lambda card: (card["data"], card["titulo"].casefold()), reverse=True)
    undated.sort(key=lambda card: card["titulo"].casefold())
    return dated + undated


def study_count_label(count: int) -> str:
    if count == 0:
        return "Nenhuma leitura disponível"
    if count == 1:
        return "1 leitura disponível"
    return f"{count} leituras disponíveis"


def category_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    categories: list[dict[str, Any]] = []
    for study_type in STUDY_TYPE_ORDER:
        presentation = STUDY_TYPE_PRESENTATION[study_type]
        count = sum(1 for card in cards if card["tipo"] == study_type)
        categories.append(
            {
                "type": study_type,
                "slug": presentation["slug"],
                "legacy_slugs": presentation.get("legacy_slugs", ()),
                "kicker": presentation["kicker"],
                "title": presentation["title"],
                "description": presentation["description"],
                "count": count,
                "count_label": study_count_label(count),
                "href": f"tipos/{presentation['slug']}.html",
            }
        )
    return categories


def render_catalog_page(
    cards: list[dict[str, Any]],
    templates: Environment,
    *,
    title: str,
    description: str,
    output_path: Path,
) -> None:
    catalog = normalize_generated_text(
        templates.get_template("catalog.html.j2").render(
            title=title,
            description=description,
            cards=sort_cards(cards),
            count_label=study_count_label(len(cards)),
            asset_prefix="../",
            root_prefix="../",
            study_prefix="../",
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(catalog, encoding="utf-8")


def render_catalog_pages(cards: list[dict[str, Any]], templates: Environment) -> None:
    CATEGORY_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for category in category_cards(cards):
        category_studies = [
            card for card in cards if card["tipo"] == category["type"]
        ]
        for slug in (category["slug"], *category["legacy_slugs"]):
            render_catalog_page(
                category_studies,
                templates,
                title=category["title"],
                description=category["description"],
                output_path=CATEGORY_OUTPUT_ROOT / f"{slug}.html",
            )
    render_catalog_page(
        cards,
        templates,
        title="Todas as leituras",
        description="Veja todos os estudos, devocionais, leituras temáticas e pregações em um só lugar.",
        output_path=CATEGORY_OUTPUT_ROOT / "todas.html",
    )


def render_index(cards: list[dict[str, Any]], templates: Environment) -> None:
    catalog = sort_cards(deduplicate_sermon_cards(cards))
    index = normalize_generated_text(
        templates.get_template("index.html.j2").render(
            categories=category_cards(catalog),
            total_count=len(catalog),
            asset_prefix="./",
        )
    )
    (DIST_ROOT / "index.html").write_text(index, encoding="utf-8")
    (DIST_ROOT / "manifest.json").write_text(
        json.dumps({"version": 1, "studies": catalog}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    render_catalog_pages(catalog, templates)


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
