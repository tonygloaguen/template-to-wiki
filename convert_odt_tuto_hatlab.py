#!/usr/bin/env python3
"""Convertit un modele ODT de tutoriel Hatlab en syntaxe DokuWiki.

Le script utilise uniquement la bibliotheque standard : un fichier .odt est un
zip contenant notamment content.xml, qui est parse pour extraire les paragraphes
et listes utiles.
"""

import argparse
import os
import posixpath
import re
import shutil
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree


TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"

TAG_P = "{%s}p" % TEXT_NS
TAG_H = "{%s}h" % TEXT_NS
TAG_LIST = "{%s}list" % TEXT_NS
TAG_LIST_ITEM = "{%s}list-item" % TEXT_NS
TAG_S = "{%s}s" % TEXT_NS
TAG_TAB = "{%s}tab" % TEXT_NS
TAG_LINE_BREAK = "{%s}line-break" % TEXT_NS
ATTR_C = "{%s}c" % TEXT_NS

FIELD_LABELS = {
    "auteur": "author",
    "categories": "categories",
    "mots-cles": "keywords",
    "mots cles": "keywords",
    "licence": "license",
}

SECTION_LABELS = {
    "resume court": "summary",
    "resume": "summary",
    "introduction": "introduction",
    "liste des materiaux": "materials",
    "materiaux": "materials",
    "liste des outils": "tools",
    "outils": "tools",
    "notes et references": "notes",
    "notes": "notes",
    "references": "notes",
}


class ConversionError(Exception):
    """Erreur lisible pour l'utilisateur final."""


def strip_accents(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def compact_spaces(value):
    return re.sub(r"[ \t\r\f\v]+", " ", value).strip()


def label_key(value):
    value = strip_accents(value).lower()
    value = value.replace("'", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" :")


def split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def _text_content(element):
    parts = []
    if element.text:
        parts.append(element.text)

    for child in list(element):
        if child.tag == TAG_S:
            count = child.attrib.get(ATTR_C, "1")
            try:
                count_int = int(count)
            except ValueError:
                count_int = 1
            parts.append(" " * max(count_int, 1))
        elif child.tag == TAG_TAB:
            parts.append("\t")
        elif child.tag == TAG_LINE_BREAK:
            parts.append("\n")
        else:
            parts.append(_text_content(child))

        if child.tail:
            parts.append(child.tail)

    return "".join(parts)


def _clean_xml_text(value):
    cleaned_lines = [compact_spaces(line) for line in value.splitlines()]
    return "\n".join(line for line in cleaned_lines if line).strip()


def _extract_list_lines(list_element, level):
    lines = []
    indent = "  " * level

    for item in list_element.findall(TAG_LIST_ITEM):
        item_paragraphs = []
        nested_lists = []

        for child in list(item):
            if child.tag in (TAG_P, TAG_H):
                text = _clean_xml_text(_text_content(child))
                if text:
                    item_paragraphs.extend(text.splitlines())
            elif child.tag == TAG_LIST:
                nested_lists.extend(_extract_list_lines(child, level + 1))

        if item_paragraphs:
            lines.append("%s- %s" % (indent, item_paragraphs[0]))
            for paragraph in item_paragraphs[1:]:
                lines.append("%s  %s" % (indent, paragraph))

        lines.extend(nested_lists)

    return lines


def _extract_blocks(element):
    lines = []
    for child in list(element):
        if child.tag in (TAG_P, TAG_H):
            text = _clean_xml_text(_text_content(child))
            if text:
                lines.extend(text.splitlines())
        elif child.tag == TAG_LIST:
            lines.extend(_extract_list_lines(child, 0))
        else:
            lines.extend(_extract_blocks(child))
    return lines


def read_odt_text(path):
    """Retourne les lignes utiles extraites de content.xml dans un .odt."""
    if not os.path.exists(path):
        raise ConversionError("Fichier introuvable : %s" % path)
    if not zipfile.is_zipfile(path):
        raise ConversionError("Le fichier n'est pas un ODT valide ou lisible : %s" % path)

    try:
        with zipfile.ZipFile(path) as archive:
            try:
                content = archive.read("content.xml")
            except KeyError:
                raise ConversionError("ODT invalide : content.xml est absent.")
    except zipfile.BadZipFile:
        raise ConversionError("ODT invalide : archive zip corrompue.")

    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise ConversionError("ODT invalide : content.xml est mal forme (%s)." % exc)

    body = root.find(".//{%s}body/{%s}text" % (OFFICE_NS, OFFICE_NS))
    if body is None:
        raise ConversionError("ODT invalide : impossible de trouver office:body/office:text.")

    return _extract_blocks(body)


def normalize_image_name(name):
    """Nettoie un nom d'image pour DokuWiki sans conserver de chemin."""
    raw_name = name.strip().replace("\\", "/")
    base_name = posixpath.basename(raw_name)
    base_name = strip_accents(base_name).lower()
    base_name = base_name.replace(" ", "_")
    base_name = re.sub(r"[^a-z0-9._-]+", "_", base_name)
    base_name = re.sub(r"_+", "_", base_name)
    base_name = base_name.strip("._-")
    return base_name or "image"


def normalize_page_id(page_id):
    if not page_id:
        return ""
    value = strip_accents(page_id).lower()
    value = value.replace(":", "_").replace("/", "_").replace("\\", "_")
    value = re.sub(r"[^a-z0-9._-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("._-")


def _parse_metadata_line(line):
    if ":" not in line:
        return None, None
    label, value = line.split(":", 1)
    field = FIELD_LABELS.get(label_key(label))
    if not field:
        return None, None
    return field, value.strip()


def _parse_step_heading(line):
    match = re.match(
        r"^\s*(?:etape|étape)\s*n\s*[°oº]?\s*(\d+)\s*[-:–]\s*(.+?)\s*$",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None
    return {
        "number": int(match.group(1)),
        "title": compact_spaces(match.group(2)),
        "lines": [],
        "image": "",
    }


def _section_for_line(line):
    return SECTION_LABELS.get(label_key(line))


def empty_tutorial():
    return {
        "title": "",
        "author": "",
        "categories": [],
        "keywords": [],
        "license": "",
        "summary": [],
        "introduction": [],
        "materials": [],
        "tools": [],
        "steps": [],
        "notes": [],
        "warnings": [],
    }


def parse_tutorial(lines):
    """Parse les lignes extraites de l'ODT en structure de tutoriel."""
    data = empty_tutorial()
    useful_lines = [line.strip() for line in lines if line and line.strip()]
    if not useful_lines:
        raise ConversionError("Aucun texte utile n'a ete trouve dans le document.")

    data["title"] = useful_lines[0]
    current_section = None
    current_step = None
    metadata_open = True

    for line in useful_lines[1:]:
        field, value = _parse_metadata_line(line)
        if field and metadata_open:
            if field in ("categories", "keywords"):
                data[field] = split_csv(value)
            else:
                data[field] = value
            continue

        step = _parse_step_heading(line)
        if step:
            data["steps"].append(step)
            current_step = step
            current_section = "step"
            metadata_open = False
            continue

        section = _section_for_line(line)
        if section:
            current_section = section
            current_step = None
            metadata_open = False
            continue

        image_match = re.match(r"^\s*image\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if image_match:
            image_name = normalize_image_name(image_match.group(1))
            if current_step is not None:
                current_step["image"] = image_name
            else:
                data["warnings"].append(
                    "Image ignoree hors etape : %s" % image_match.group(1).strip()
                )
            continue

        metadata_open = False
        if current_section == "step" and current_step is not None:
            current_step["lines"].append(line)
        elif current_section in ("summary", "introduction", "materials", "tools", "notes"):
            data[current_section].append(line)
        else:
            data["warnings"].append("Ligne ignoree hors section : %s" % line)

    return data


def validate_tutorial(data, strict):
    errors = []
    warnings = list(data.get("warnings", []))

    required = [
        ("title", "titre du tutoriel"),
        ("author", "Auteur"),
        ("categories", "Catégories"),
        ("keywords", "Mots-clés"),
        ("license", "Licence"),
        ("summary", "Résumé court"),
        ("introduction", "Introduction"),
    ]
    for key, label in required:
        if not data.get(key):
            message = "Champ manquant : %s" % label
            if strict:
                errors.append(message)
            else:
                warnings.append(message)

    if not data.get("steps"):
        message = "Aucune etape detectee."
        if strict:
            errors.append(message)
        else:
            warnings.append(message)

    return errors, warnings


def _render_value(value):
    if isinstance(value, list):
        return ", ".join(value)
    return value or ""


def _render_dokuwiki_lines(lines):
    rendered = []
    for line in lines:
        stripped = line.strip()
        bullet = re.match(r"^\s*[-*]\s+(.+)$", stripped)
        if bullet:
            rendered.append("  * %s" % bullet.group(1).strip())
        else:
            rendered.append(stripped)
    return rendered


def _escape_table_cell(value):
    return _render_value(value).replace("|", "/").strip()


def _escape_media_title(value):
    return value.replace("|", "-").strip()


def _media_link(media_namespace, image_name, title):
    namespace = (media_namespace or "").strip(": ")
    if namespace:
        target = "%s:%s" % (namespace, image_name)
    else:
        target = image_name
    return "{{%s|%s}}" % (target, _escape_media_title(title))


def _append_section(output, title, lines):
    if not lines:
        return
    output.append("==== %s ====" % title)
    output.extend(_render_dokuwiki_lines(lines))
    output.append("")


def render_dokuwiki(data, media_namespace):
    """Genere une page DokuWiki lisible depuis la structure parse."""
    output = []
    output.append("====== %s ======" % data.get("title", "").strip())
    output.append("")
    output.append("^ Champ ^ Valeur ^")
    output.append("| Auteur | %s |" % _escape_table_cell(data.get("author", "")))
    output.append("| Catégories | %s |" % _escape_table_cell(data.get("categories", [])))
    output.append("")

    if data.get("summary"):
        output.append("==== Résumé ====")
        output.extend(_render_dokuwiki_lines(data["summary"]))
        output.append("")

    if data.get("license"):
        output.append("**Licence :** %s" % data["license"])
        output.append("")

    if data.get("keywords"):
        output.append("**Mots-clés :** %s" % ", ".join(data["keywords"]))
        output.append("")

    _append_section(output, "Introduction", data.get("introduction", []))
    _append_section(output, "Liste des matériaux", data.get("materials", []))
    _append_section(output, "Liste des outils", data.get("tools", []))

    for step in data.get("steps", []):
        title = "Etape n°%s - %s" % (step["number"], step["title"])
        output.append("==== %s ====" % title)
        if step.get("image"):
            output.append("<WRAP group>")
            output.append("")
            output.append("<WRAP half column>")
            output.extend(_render_dokuwiki_lines(step.get("lines", [])))
            output.append("</WRAP>")
            output.append("")
            output.append("<WRAP half column>")
            output.append(_media_link(media_namespace, step["image"], step["title"]))
            output.append("</WRAP>")
            output.append("")
            output.append("</WRAP>")
            output.append("<WRAP clear />")
        else:
            output.extend(_render_dokuwiki_lines(step.get("lines", [])))
        output.append("")

    _append_section(output, "Notes et références", data.get("notes", []))

    text = "\n".join(output).rstrip() + "\n"
    return text


def _unique_path(path):
    if not os.path.exists(path):
        return path

    directory, filename = os.path.split(path)
    stem, extension = os.path.splitext(filename)
    index = 2
    while True:
        candidate = os.path.join(directory, "%s_%s%s" % (stem, index, extension))
        if not os.path.exists(candidate):
            return candidate
        index += 1


def extract_odt_images(path, target_dir, page_id=None):
    """Extrait Pictures/* de l'ODT vers target_dir sans ecraser l'existant."""
    if not os.path.exists(path):
        raise ConversionError("Fichier introuvable : %s" % path)
    if not zipfile.is_zipfile(path):
        raise ConversionError("Le fichier n'est pas un ODT valide ou lisible : %s" % path)

    prefix = normalize_page_id(page_id)
    extracted = []

    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    try:
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir() or not member.filename.startswith("Pictures/"):
                    continue
                original_name = posixpath.basename(member.filename)
                if not original_name:
                    continue
                clean_name = normalize_image_name(original_name)
                if prefix:
                    clean_name = normalize_image_name("%s_%s" % (prefix, clean_name))
                destination = _unique_path(os.path.join(target_dir, clean_name))
                with archive.open(member) as source, open(destination, "wb") as target:
                    shutil.copyfileobj(source, target)
                extracted.append(destination)
    except zipfile.BadZipFile:
        raise ConversionError("ODT invalide : archive zip corrompue.")

    return extracted


def convert_odt_to_dokuwiki(
    input_odt,
    output_txt,
    media_namespace,
    page_id=None,
    extract_media_dir=None,
    force=False,
    strict=False,
):
    """Convertit un ODT en fichier DokuWiki et retourne un rapport simple."""
    if os.path.exists(output_txt) and not force:
        raise ConversionError(
            "Le fichier de sortie existe deja : %s. Utilisez --force pour l'ecraser."
            % output_txt
        )

    lines = read_odt_text(input_odt)
    data = parse_tutorial(lines)
    errors, warnings = validate_tutorial(data, strict)
    if errors:
        raise ConversionError("; ".join(errors))

    images_extracted = []
    if extract_media_dir:
        images_extracted = extract_odt_images(input_odt, extract_media_dir, page_id)

    output_dir = os.path.dirname(os.path.abspath(output_txt))
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    rendered = render_dokuwiki(data, media_namespace)
    with open(output_txt, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(rendered)

    return {
        "output_txt": output_txt,
        "images_extracted": images_extracted,
        "warnings": warnings,
    }


def run_self_test():
    sample = [
        "Installer Linux",
        "Auteur : Alice",
        "Categories : Divers, Electronique",
        "Mots-cles : linux, usb",
        "Licence : Attribution (CC BY)",
        "Resume court",
        "Un resume court.",
        "Introduction",
        "Texte d'introduction.",
        "Liste des matériaux",
        "- Cle USB",
        "Liste des outils",
        "- LibreOffice",
        "Etape n°1 - Telecharger l'image ISO",
        "Texte de l'etape.",
        "Image : Mes Images/ISO Linux.PNG",
        "Notes et références",
        "- https://example.org",
    ]
    data = parse_tutorial(sample)
    errors, warnings = validate_tutorial(data, strict=True)
    if errors:
        raise ConversionError("; ".join(errors))
    rendered = render_dokuwiki(data, "projets:divers")
    checks = [
        "====== Installer Linux ======",
        "{{projets:divers:iso_linux.png|Telecharger l'image ISO}}",
        "<WRAP half column>",
        "==== Liste des matériaux ====",
    ]
    missing = [check for check in checks if check not in rendered]
    if missing:
        raise ConversionError("Self-test echoue, sortie inattendue : %s" % missing)
    if warnings:
        print("Self-test OK avec avertissements : %s" % "; ".join(warnings))
    else:
        print("Self-test OK")


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Convertit un modele tutoriel Hatlab .odt en fichier .txt DokuWiki "
            "sans modifier directement un wiki de production."
        )
    )
    parser.add_argument("input_odt", nargs="?", help="Chemin du fichier .odt source.")
    parser.add_argument("output_txt", nargs="?", help="Chemin du fichier .txt DokuWiki a generer.")
    parser.add_argument(
        "--media-namespace",
        default="projets:divers",
        help="Namespace media DokuWiki pour les images (defaut: projets:divers).",
    )
    parser.add_argument(
        "--page-id",
        default="",
        help="Identifiant de page optionnel, utilise comme prefixe pour les images extraites.",
    )
    parser.add_argument(
        "--extract-media-dir",
        default="",
        help="Dossier cible optionnel pour extraire les images integrees dans l'ODT.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Echoue si des champs importants sont absents.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Autorise l'ecrasement du fichier de sortie s'il existe deja.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Execute un test interne minimal sans lire de fichier ODT.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        run_self_test()
        return 0

    if not args.input_odt or not args.output_txt:
        parser.error("input_odt et output_txt sont requis sauf avec --self-test.")

    report = convert_odt_to_dokuwiki(
        args.input_odt,
        args.output_txt,
        args.media_namespace,
        page_id=args.page_id,
        extract_media_dir=args.extract_media_dir or None,
        force=args.force,
        strict=args.strict,
    )

    if report["images_extracted"]:
        print(
            "%s image(s) extraite(s) vers %s"
            % (len(report["images_extracted"]), args.extract_media_dir)
        )
    for warning in report["warnings"]:
        print("Avertissement : %s" % warning, file=sys.stderr)
    print("Fichier DokuWiki genere : %s" % report["output_txt"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConversionError as exc:
        print("Erreur : %s" % exc, file=sys.stderr)
        sys.exit(1)
