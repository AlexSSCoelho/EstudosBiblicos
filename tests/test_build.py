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


class BuildRenderingTests(unittest.TestCase):
    def test_lexical_drawer_renders_markdown_inside_details(self) -> None:
        html, toc = build.render_markdown(
            """## Unidade\n\n<details class=\"lex-drawer\">\n<summary>Gramática</summary>\n\n**Lema**\n\nTexto consultável.\n</details>\n"""
        )
        self.assertIn('<details class="lex-drawer">', html)
        self.assertIn("<strong>Lema</strong>", html)
        self.assertNotIn("**Lema**", html)
        self.assertEqual(toc[0]["name"], "Unidade")

    def test_study_without_homiletics_can_render(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "estudo.md"
            source.write_text(
                """---\nid: estudo-sem-homiletica\ntipo: estudo_exegetico\ntitulo: Estudo sem homilética\npassagem: Salmo 1\ndata: 2026-09-09\nresumo: Exposição organizada por unidade.\nhomiletica: false\n---\n\n## Unidade literária\n\nO conteúdo define a estrutura.\n""",
                encoding="utf-8",
            )
            study = build.load_study(source)
            self.assertFalse(study.metadata["homiletica"])
            self.assertIn("Unidade literária", study.body_html)


class BuildValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
