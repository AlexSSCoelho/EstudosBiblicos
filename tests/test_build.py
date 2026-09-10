import os
import tempfile
import unittest
from pathlib import Path

import build


class BuildMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path("tests/fixture-estudo.md")
        self.base = {
            "id": "material-de-teste",
            "tipo": "devocional",
            "titulo": "Material de teste",
            "passagem": "João 1:1",
            "data": "2026-09-09",
            "resumo": "Resumo de teste.",
        }

    def test_devotional_defaults_to_nvi(self) -> None:
        metadata = build.normalize_metadata(self.base, self.path)
        self.assertEqual(metadata["traducao"], "NVI")
        self.assertTrue(metadata["traducao_inferida"])

    def test_exegetical_defaults_to_acf(self) -> None:
        metadata = build.normalize_metadata(
            {**self.base, "id": "estudo-de-teste", "tipo": "estudo_exegetico"},
            self.path,
        )
        self.assertEqual(metadata["traducao"], "ACF")
        self.assertTrue(metadata["traducao_inferida"])

    def test_explicit_translation_wins(self) -> None:
        metadata = build.normalize_metadata(
            {**self.base, "traducao": "ARA"},
            self.path,
        )
        self.assertEqual(metadata["traducao"], "ARA")
        self.assertFalse(metadata["traducao_inferida"])

    def test_null_translation_uses_default_and_optional_fields_are_safe(self) -> None:
        for translation in (None, "", "   "):
            metadata = build.normalize_metadata(
                {**self.base, "traducao": translation, "tema": None, "autor": None},
                self.path,
            )
            self.assertEqual(metadata["traducao"], "NVI")
            self.assertTrue(metadata["traducao_inferida"])
            self.assertEqual(metadata["tema"], "")
            self.assertEqual(metadata["autor"], "")
            self.assertEqual(metadata["tese"], "")


class BuildRenderingTests(unittest.TestCase):
    def test_lexical_drawer_renders_markdown_inside_details(self) -> None:
        html, toc = build.render_markdown(
            """## Unidade\n\n<details class=\"lex-drawer\">\n<summary>Gramática</summary>\n\n**Lema**\n\nTexto consultável.\n</details>\n"""
        )
        self.assertIn('<details class="lex-drawer">', html)
        self.assertIn("<strong>Lema</strong>", html)
        self.assertNotIn("**Lema**", html)
        self.assertEqual(toc[0]["name"], "Unidade")

    def test_minimal_devotional_and_exegetical_render_without_optional_fields(self) -> None:
        cases = (
            ("devocional", "devocional-minimo", "NVI"),
            ("estudo_exegetico", "estudo-minimo", "ACF"),
        )
        old_output_root = build.STUDY_OUTPUT_ROOT
        try:
            with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
                root = Path(temp_dir)
                build.STUDY_OUTPUT_ROOT = root / "dist" / "estudos"
                for study_type, study_id, translation in cases:
                    source = root / f"{study_id}.md"
                    source.write_text(
                        f"""---\nid: {study_id}\ntipo: {study_type}\ntitulo: Material mínimo\npassagem: Salmo 1\ndata: 2026-09-09\ntraducao: null\nresumo: Exposição organizada por unidade.\nhomiletica: false\n---\n\n## Unidade literária\n\nO conteúdo define a estrutura.\n""",
                        encoding="utf-8",
                    )
                    study = build.load_study(source)
                    card = build.render_study(study, build.environment(), skip_pdf=True)
                    html = (build.STUDY_OUTPUT_ROOT / study_id / f"{study_id}.html").read_text(
                        encoding="utf-8"
                    )
                    self.assertEqual(study.metadata["traducao"], translation)
                    self.assertEqual(card["traducao"], translation)
                    self.assertNotIn("None", html)
                    self.assertIn("Unidade literária", html)
        finally:
            build.STUDY_OUTPUT_ROOT = old_output_root

    def test_image_without_optional_fields_renders_for_string_and_mapping(self) -> None:
        old_output_root = build.STUDY_OUTPUT_ROOT
        try:
            with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
                root = Path(temp_dir)
                build.STUDY_OUTPUT_ROOT = root / "dist" / "estudos"
                (root / "figura.png").write_bytes(b"not-a-real-image")
                cases = (
                    ("imagem-string", '  - "./figura.png"'),
                    ("imagem-mapping", '  - src: "./figura.png"'),
                )
                for study_id, image_yaml in cases:
                    source = root / f"{study_id}.md"
                    source.write_text(
                        f"""---\nid: {study_id}\ntipo: devocional\ntitulo: Material com imagem\npassagem: Salmo 1\ndata: 2026-09-09\nresumo: Renderização de imagem sem campos opcionais.\nimagens:\n{image_yaml}\n---\n\n## Unidade\n\nTexto do estudo.\n""",
                        encoding="utf-8",
                    )
                    study = build.load_study(source)
                    build.render_study(study, build.environment(), skip_pdf=True)
                    html = (
                        build.STUDY_OUTPUT_ROOT / study_id / f"{study_id}.html"
                    ).read_text(encoding="utf-8")
                    self.assertIn('src="./figura.png"', html)
                    self.assertIn('alt="Imagem de apoio ao estudo"', html)
                    self.assertNotIn("None", html)
        finally:
            build.STUDY_OUTPUT_ROOT = old_output_root


class BuildValidationTests(unittest.TestCase):
    def test_mobile_toc_does_not_scroll_page_on_initial_activation(self) -> None:
        source_script = Path("assets/study.js").read_text(encoding="utf-8")
        generated_script = Path("dist/assets/study.js").read_text(encoding="utf-8")
        for script in (source_script, generated_script):
            self.assertIn('const isInitialActivation = activeId === "";', script)
            self.assertIn(
                'active && !isInitialActivation && window.matchMedia("(max-width: 860px)")',
                script,
            )

    def test_workflow_rebuilds_when_any_study_file_changes(self) -> None:
        workflow = Path(".github/workflows/build-estudos.yml").read_text(encoding="utf-8")
        self.assertIn('      - "Pregações/**"', workflow)
        self.assertNotIn('      - "Pregações/**/estudo.md"', workflow)

    def test_base64_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            source = source_dir / "estudo.md"
            source.write_text("---\n---\n", encoding="utf-8")
            study = build.Study(
                metadata={},
                body="![mapa](data:image/png;base64,abc)",
                body_html="<img src=\"data:image/png;base64,abc\">",
                toc=[],
                source_path=source,
            )
            with self.assertRaises(build.BuildError):
                build.validate_source(study)

    def test_front_matter_base64_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "estudo.md"
            study = build.Study(
                metadata={"imagens": [{"src": "data:image/png;base64,abc"}]},
                body="",
                body_html="",
                toc=[],
                source_path=source,
            )
            with self.assertRaises(build.BuildError):
                build.validate_source(study)

    def test_traversal_in_front_matter_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "estudo.md"
            study = build.Study(
                metadata={"imagens": [{"src": "../segredo.png"}]},
                body="",
                body_html="",
                toc=[],
                source_path=source,
            )
            with self.assertRaises(build.BuildError):
                build.validate_source(study)

    def test_html_image_reference_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            source = source_dir / "estudo.md"
            study = build.Study(
                metadata={},
                body="",
                body_html='<img src="./figura.png">',
                toc=[],
                source_path=source,
            )
            with self.assertRaises(build.BuildError):
                build.validate_source(study)

    def test_traversal_in_html_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "estudo.md"
            study = build.Study(
                metadata={},
                body="",
                body_html='<img src="../segredo.png">',
                toc=[],
                source_path=source,
            )
            with self.assertRaises(build.BuildError):
                build.validate_source(study)

    def test_local_html_reference_with_query_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            source = source_dir / "estudo.md"
            (source_dir / "figura.png").write_bytes(b"not-a-real-image")
            study = build.Study(
                metadata={},
                body="",
                body_html=(
                    '<img src="./figura.png?versao=1#top">'
                    '<a href="https://example.com">Fonte</a>'
                ),
                toc=[],
                source_path=source,
            )
            build.validate_source(study)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink não disponível")
    def test_symlink_outside_study_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "estudo"
            source_dir.mkdir()
            outside = root / "segredo.png"
            outside.write_bytes(b"secret")
            link = source_dir / "atalho.png"
            try:
                os.symlink(outside, link)
            except OSError as exc:
                self.skipTest(f"criação de symlink não autorizada: {exc}")
            study = build.Study(
                metadata={"imagens": [{"src": "./atalho.png"}]},
                body="",
                body_html="",
                toc=[],
                source_path=source_dir / "estudo.md",
            )
            with self.assertRaises(build.BuildError):
                build.validate_source(study)


if __name__ == "__main__":
    unittest.main()
