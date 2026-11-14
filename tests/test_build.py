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

    def test_thematic_defaults_to_acf_and_requires_tema(self) -> None:
        # Sem tema deve falhar
        with self.assertRaises(build.BuildError):
            build.normalize_metadata(
                {**self.base, "id": "estudo-tematico-teste", "tipo": "estudo_tematico"},
                self.path,
            )
        # Com tema deve passar e assumir ACF
        metadata = build.normalize_metadata(
            {**self.base, "id": "estudo-tematico-teste", "tipo": "estudo_tematico", "tema": "Teologia Própria"},
            self.path,
        )
        self.assertEqual(metadata["traducao"], "ACF")
        self.assertTrue(metadata["traducao_inferida"])
        self.assertEqual(metadata["tema"], "Teologia Própria")
        self.assertFalse(metadata["homiletica"])

        with self.assertRaisesRegex(build.BuildError, "estudos temáticos não incluem"):
            build.normalize_metadata(
                {
                    **self.base,
                    "id": "estudo-tematico-teste",
                    "tipo": "estudo_tematico",
                    "tema": "Teologia Própria",
                    "homiletica": True,
                },
                self.path,
            )

    def test_thematic_aliases_and_unknown_type_rejection(self) -> None:
        for alias in ("tematico", "estudo_doutrinario"):
            metadata = build.normalize_metadata(
                {**self.base, "tipo": alias, "tema": "Atributos"},
                self.path,
            )
            self.assertEqual(metadata["tipo"], "estudo_tematico")

        with self.assertRaises(build.BuildError):
            build.normalize_metadata(
                {**self.base, "tipo": "tipo_desconhecido"},
                self.path,
            )

    def test_passagens_chave_validation_and_normalization(self) -> None:
        valid_yaml = {
            **self.base,
            "tipo": "estudo_tematico",
            "tema": "Doutrina",
            "passagens_chave": {
                "antigo_testamento": [{"ref": "Ml 3.6", "texto": "Eu não mudo"}],
                "novo_testamento": [{"ref": "Tg 1.17"}],
            },
        }
        meta = build.normalize_metadata(valid_yaml, self.path)
        self.assertEqual(len(meta["passagens_chave"]["antigo_testamento"]), 1)
        self.assertEqual(meta["passagens_chave"]["antigo_testamento"][0]["texto"], "Eu não mudo")
        self.assertNotIn("texto", meta["passagens_chave"]["novo_testamento"][0])

        # Seção inesperada deve falhar
        invalid_yaml = {
            **self.base,
            "tipo": "estudo_tematico",
            "tema": "Doutrina",
            "passagens_chave": {"apocrifos": [{"ref": "Tobias 1.1"}]},
        }
        with self.assertRaises(build.BuildError):
            build.normalize_metadata(invalid_yaml, self.path)

        # Item sem ref deve falhar
        invalid_ref = {
            **self.base,
            "tipo": "estudo_tematico",
            "tema": "Doutrina",
            "passagens_chave": {"novo_testamento": [{"texto": "sem ref"}]},
        }
        with self.assertRaises(build.BuildError):
            build.normalize_metadata(invalid_ref, self.path)

    def test_external_links_open_in_new_tab(self) -> None:
        md = "Visite o [Logeion](https://logeion.uchicago.edu/) e veja o [mapa local](./mapa.png) e a [seção](#sec)."
        html, _ = build.render_markdown(md)
        self.assertIn('href="https://logeion.uchicago.edu/" target="_blank" rel="noopener noreferrer"', html)
        self.assertNotIn('href="./mapa.png" target="_blank"', html)
        self.assertNotIn('href="#sec" target="_blank"', html)

    def test_semantic_units_preserve_non_breaking_spaces_in_prose_and_tables(self) -> None:
        md = (
            "## Mateus 24.3–14\n\n"
            "| Unidade e Paralelos | Movimento |\n"
            "| :--- | :--- |\n"
            "| **vv. 4–5** (Mc 13.5–6; Lc 21.8) | Confira 1 Co 15.1–4 em 70 d.C. |\n\n"
            "Código `Lc 21.8` não é alterado.\n"
        )
        html, _ = build.render_markdown(md)
        self.assertIn("<strong>vv.\u00a04–5</strong> (Mc\u00a013.5–6; Lc\u00a021.8)", html)
        self.assertIn("1\u00a0Co\u00a015.1–4 em 70\u00a0d.C.", html)
        self.assertIn("<code>Lc 21.8</code>", html)
        self.assertIn(">Mateus 24.3–14</h2>", html)

    def test_explicit_translation_wins(self) -> None:
        metadata = build.normalize_metadata(
            {**self.base, "traducao": "ARA"},
            self.path,
        )
        self.assertEqual(metadata["traducao"], "ARA")
        self.assertFalse(metadata["traducao_inferida"])

    def test_format_date_br(self) -> None:
        self.assertEqual(build.format_date_br("2026-09-10"), "10/09/2026")
        self.assertEqual(build.format_date_br("2026-07-19"), "19/07/2026")
        self.assertEqual(build.format_date_br("data-invalida"), "data-invalida")
        metadata = build.normalize_metadata(self.base, self.path)
        self.assertEqual(metadata["data_formatada"], "09/09/2026")

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
        self.assertIn('class="lex-drawer-body"', html)
        self.assertIn('class="lex-toggle-badge"', html)
        self.assertEqual(toc[0]["name"], "Unidade")

    def test_verse_detection_and_badges_in_toc_and_body(self) -> None:
        md = "## Contexto\n\nVisão geral.\n\n4.6\n\n### Oração e gratidão\n\nTexto de exposição.\n\n4.6–7\n\n### Oração e paz\n\nTexto da unidade.\n"
        html, toc = build.render_markdown(md)
        self.assertIn('class="verse-marker"', html)
        self.assertIn('>Versículo</span> 4.6', html)
        self.assertIn('>Versículos</span> 4.6–7', html)
        self.assertEqual(len(toc), 3)
        self.assertEqual(toc[0]["badge"], "01")
        self.assertEqual(toc[0]["badge_type"], "number")
        self.assertEqual(toc[1]["badge"], "v. 6")
        self.assertEqual(toc[1]["badge_type"], "verse")
        self.assertTrue(toc[1]["is_verse"])
        self.assertEqual(toc[2]["badge"], "·")
        self.assertEqual(toc[2]["verse_range"], "4.6–7")

    def test_numbered_biblical_books_are_not_mistaken_for_verses_in_toc(self) -> None:
        md = "## 1 Samuel 15.10–31: O mistério das antropopatias\n\nTexto de exposição.\n"
        _html, toc = build.render_markdown(md)
        self.assertEqual(len(toc), 1)
        self.assertEqual(toc[0]["badge"], "01")
        self.assertEqual(toc[0]["badge_type"], "number")
        self.assertFalse(toc[0]["is_verse"])

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
    def test_mobile_toc_centers_inside_bar_without_scrolling_page(self) -> None:
        source_script = Path("assets/study.js").read_text(encoding="utf-8")
        generated_script = Path("dist/assets/study.js").read_text(encoding="utf-8")
        self.assertEqual(source_script, generated_script)
        self.assertIn('tocNav.scrollTo({ left, behavior: "auto" });', source_script)
        self.assertNotIn('link.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" })', source_script)

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
