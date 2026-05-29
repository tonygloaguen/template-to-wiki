# Convertisseur ODT Hatlab vers DokuWiki

Cet outil convertit un tutoriel Hatlab rempli dans LibreOffice Writer au format .odt en fichier .txt compatible DokuWiki. Il utilise uniquement la bibliothèque standard Python.

## Installation Ubuntu / Debian

    sudo apt update
    sudo apt install -y python3-tk
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    python -c "import tkinter; print('Tkinter OK')"

## Lancement CLI

Commande type :

    python convert_odt_tuto_hatlab.py examples/install_party_linux_example.odt sortie_test.txt --media-namespace projets:divers --force

Avec extraction des images intégrées :

    python convert_odt_tuto_hatlab.py modele_tutoriel_hatlab_opendocument.odt sortie_test.txt --media-namespace projets:divers --page-id install_party_linux --extract-media-dir /chemin/local/data/media/projets/divers --force

Le script refuse d'écraser un fichier de sortie existant sans --force.

## Lancement GUI

Lancer l'interface locale :

    python hatlab_odt_converter_gui.py

L'interface permet de choisir le fichier ODT, le fichier TXT de sortie, le namespace média DokuWiki, l'identifiant de page optionnel, l'extraction des images intégrées et l'écrasement volontaire du fichier de sortie.

## Procédure contributeur

1. Ouvrir le modèle .odt dans LibreOffice Writer.
2. Remplir les champs : titre, auteur, catégories, mots-clés, licence, résumé, introduction, listes, étapes, notes.
3. Pour les images de V1, ajouter dans chaque étape une ligne : Image : nom_image.png.
4. Envoyer le .odt et les images associées à l'admin wiki.

## Procédure admin

1. Lancer le GUI ou la commande CLI.
2. Générer un .txt local et relire la sortie.
3. Copier le .txt généré dans data/pages/... du DokuWiki.
4. Copier les images dans data/media/... ou utiliser l'option d'extraction vers un dossier local correspondant.

## Structure attendue

    Titre du tutoriel
    Auteur : Nom
    Catégories : Divers, Électronique
    Mots-clés : linux, usb, installation
    Licence : Attribution (CC BY)

    Résumé court
    Texte du résumé.

    Introduction
    Texte d'introduction.

    Liste des matériaux
    - Clé USB 8 Go minimum

    Liste des outils
    - LibreOffice

    Etape n°1 - Télécharger l'image ISO
    Texte de l'étape.
    Image : iso_linux.png

    Notes et références
    - https://example.org

## Limites connues

- La conversion préserve les paragraphes et listes simples, pas toute la mise en forme LibreOffice.
- Les images intégrées peuvent être extraites, mais l'association automatique image/étape n'est pas déduite depuis la mise en page ODT.
- L'outil génère un fichier local et ne modifie pas directement un wiki de production.

## Vérification

    python -m py_compile convert_odt_tuto_hatlab.py hatlab_odt_converter_gui.py
    python -m unittest discover -s tests
    python convert_odt_tuto_hatlab.py --self-test
    python convert_odt_tuto_hatlab.py examples/install_party_linux_example.odt sortie_test.txt --media-namespace projets:divers --force
