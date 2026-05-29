import os
import tempfile
import unittest
import zipfile

from convert_odt_tuto_hatlab import (
    convert_odt_to_dokuwiki,
    extract_odt_images,
    normalize_image_name,
    parse_tutorial,
    read_odt_text,
    render_dokuwiki,
    validate_tutorial,
)


MINIMAL_ODT_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body>
    <office:text>
      <text:p>Titre test</text:p>
      <text:p>Auteur : Alice</text:p>
      <text:p>Catégories : Divers, Électronique</text:p>
      <text:p>Mots-clés : linux, usb</text:p>
      <text:p>Licence : Attribution (CC BY)</text:p>
      <text:p>Résumé court</text:p>
      <text:p>Un résumé.</text:p>
      <text:p>Liste des matériaux</text:p>
      <text:list>
        <text:list-item><text:p>Clé USB</text:p></text:list-item>
        <text:list-item><text:p>PC Windows</text:p></text:list-item>
      </text:list>
    </office:text>
  </office:body>
</office:document-content>
"""


def write_minimal_odt(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml", MINIMAL_ODT_CONTENT)
        archive.writestr("Pictures/Image Test.PNG", b"fake-image")


class ConvertOdtTutoHatlabTests(unittest.TestCase):
    def test_normalize_image_name_keeps_only_safe_filename(self):
        self.assertEqual(
            normalize_image_name("../Mes Images/ISO Linux été.PNG"),
            "iso_linux_ete.png",
        )

    def test_parse_and_render_step_with_wrap_image(self):
        lines = [
            "Installer Linux",
            "Auteur : Alice",
            "Catégories : Divers, Électronique",
            "Mots-clés : linux, usb",
            "Licence : Attribution (CC BY)",
            "Résumé court",
            "Un résumé court.",
            "Introduction",
            "Intro.",
            "Etape n°1 - Télécharger l'image ISO",
            "Texte de l'étape.",
            "Image : Images/ISO Linux.PNG",
        ]

        data = parse_tutorial(lines)
        errors, warnings = validate_tutorial(data, strict=True)
        rendered = render_dokuwiki(data, "projets:divers")

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertIn("<WRAP group>", rendered)
        self.assertIn(
            "{{projets:divers:iso_linux.png|Télécharger l'image ISO}}", rendered
        )
        self.assertIn("==== Etape n°1 - Télécharger l'image ISO ====", rendered)

    def test_read_odt_text_preserves_simple_lists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            odt_path = os.path.join(temp_dir, "sample.odt")
            write_minimal_odt(odt_path)

            lines = read_odt_text(odt_path)

        self.assertIn("Titre test", lines)
        self.assertIn("- Clé USB", lines)
        self.assertIn("- PC Windows", lines)

    def test_extract_odt_images_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            odt_path = os.path.join(temp_dir, "sample.odt")
            media_dir = os.path.join(temp_dir, "media")
            write_minimal_odt(odt_path)

            first = extract_odt_images(odt_path, media_dir, "Page Test")
            second = extract_odt_images(odt_path, media_dir, "Page Test")

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertNotEqual(first[0], second[0])
            self.assertTrue(os.path.exists(first[0]))
            self.assertTrue(os.path.exists(second[0]))

    def test_convert_odt_to_dokuwiki_writes_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            odt_path = os.path.join(temp_dir, "sample.odt")
            output_path = os.path.join(temp_dir, "sample.txt")
            media_dir = os.path.join(temp_dir, "media")
            write_minimal_odt(odt_path)

            report = convert_odt_to_dokuwiki(
                odt_path,
                output_path,
                "projets:divers",
                page_id="Page Test",
                extract_media_dir=media_dir,
                force=False,
            )

            self.assertEqual(report["output_txt"], output_path)
            self.assertEqual(len(report["images_extracted"]), 1)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, encoding="utf-8") as output_file:
                content = output_file.read()
            self.assertIn("====== Titre test ======", content)

    def test_convert_example_odt_outputs_expected_dokuwiki_blocks(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        odt_path = os.path.join(root_dir, "examples", "install_party_linux_example.odt")
        self.assertTrue(os.path.exists(odt_path))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "install_party_linux.txt")
            convert_odt_to_dokuwiki(
                odt_path,
                output_path,
                "projets:divers",
                force=False,
            )

            with open(output_path, encoding="utf-8") as output_file:
                content = output_file.read()

        self.assertIn("Install-party Linux", content)
        self.assertIn("<WRAP group>", content)
        self.assertIn("<WRAP half column>", content)
        self.assertIn("{{projets:divers:iso_linux.png|", content)
        self.assertIn("==== Etape n°1 - Télécharger l’image ISO Linux ====", content)


if __name__ == "__main__":
    unittest.main()
