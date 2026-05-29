#!/usr/bin/env python3
"""Generate the example Hatlab ODT without external dependencies."""

import os
import zipfile
from xml.sax.saxutils import escape


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(ROOT_DIR, "examples", "install_party_linux_example.odt")

LINES = [
    "Install-party Linux",
    "Auteur : Hatlab",
    "Catégories : Divers, Logiciel & Programmation",
    "Mots-clés : linux, usb, installation, windows",
    "Licence : Attribution (CC BY)",
    "Résumé court",
    "Préparer et accompagner l'installation de Linux sur un ordinateur personnel pendant un atelier collectif.",
    "Introduction",
    "Ce tutoriel sert de support de test pour une install-party Linux organisée au Hatlab.",
    "Il décrit les étapes principales pour télécharger une image ISO, créer une clé USB bootable, démarrer un PC dessus puis installer Linux.",
    "Liste des matériaux",
    "- Une clé USB de 8 Go minimum",
    "- Un ordinateur compatible avec Linux",
    "- Une connexion Internet stable",
    "- Une sauvegarde récente des données importantes",
    "Liste des outils",
    "- Un navigateur web",
    "- Un outil de création de clé USB bootable",
    "- Le menu de démarrage ou le BIOS/UEFI du PC",
    "Etape n°1 - Télécharger l’image ISO Linux",
    "Choisir une distribution Linux adaptée au public de l'atelier, par exemple Ubuntu ou Linux Mint.",
    "Télécharger l'image ISO depuis le site officiel de la distribution.",
    "Vérifier si possible la somme de contrôle fournie par le site.",
    "Image : iso_linux.png",
    "Etape n°2 - Préparer la clé USB bootable",
    "Brancher la clé USB puis ouvrir l'outil de création de support bootable.",
    "Sélectionner l'image ISO téléchargée et la clé USB cible.",
    "Lancer l'écriture puis attendre la fin de l'opération avant de retirer la clé.",
    "Image : cle_usb_bootable.png",
    "Etape n°3 - Démarrer le PC sur la clé USB",
    "Redémarrer l'ordinateur avec la clé USB branchée.",
    "Ouvrir le menu de démarrage avec la touche indiquée par le constructeur, souvent F12, F10, Échap ou Suppr.",
    "Choisir la clé USB dans la liste des périphériques de démarrage.",
    "Image : bios_boot_menu.png",
    "Etape n°4 - Installer Linux",
    "Tester le système en mode live avant de lancer l'installation.",
    "Choisir la langue, le clavier, le fuseau horaire et le type d'installation.",
    "Relire les choix de partitionnement avant de valider l'écriture sur le disque.",
    "Image : installation_linux.png",
    "Notes et références",
    "- Sauvegarder les données Windows avant toute modification du disque.",
    "- Utiliser les pages officielles de la distribution choisie pour télécharger l'ISO.",
    "- Prévoir du temps pour les mises à jour après l'installation.",
]


def paragraph(text):
    return "      <text:p>%s</text:p>" % escape(text)


def build_content_xml():
    body = "\n".join(paragraph(line) for line in LINES)
    return (
        """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body>
    <office:text>
%s
    </office:text>
  </office:body>
</office:document-content>
"""
        % body
    )


STYLES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0">
</office:document-styles>
"""

META_XML = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0">
  <office:meta>
    <meta:generator>tools/create_example_odt.py</meta:generator>
  </office:meta>
</office:document-meta>
"""

MANIFEST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
  xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
  manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""


def create_odt(output_path=OUTPUT_PATH):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(output_path, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/vnd.oasis.opendocument.text",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr(
            "content.xml", build_content_xml(), compress_type=zipfile.ZIP_DEFLATED
        )
        archive.writestr("styles.xml", STYLES_XML, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("meta.xml", META_XML, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr(
            "META-INF/manifest.xml", MANIFEST_XML, compress_type=zipfile.ZIP_DEFLATED
        )
    return output_path


def main():
    path = create_odt()
    print("Example ODT generated: %s" % path)


if __name__ == "__main__":
    main()
