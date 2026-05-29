#!/usr/bin/env python3
"""Interface graphique locale pour le convertisseur ODT Hatlab vers DokuWiki."""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from convert_odt_tuto_hatlab import ConversionError, convert_odt_to_dokuwiki


DEFAULT_MEDIA_NAMESPACE = "projets:divers"


class HatlabOdtConverterGui(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Convertisseur ODT Hatlab vers DokuWiki")
        self.minsize(760, 560)

        self.input_odt = tk.StringVar()
        self.output_txt = tk.StringVar()
        self.media_namespace = tk.StringVar(value=DEFAULT_MEDIA_NAMESPACE)
        self.page_id = tk.StringVar()
        self.extract_images = tk.BooleanVar(value=False)
        self.extract_media_dir = tk.StringVar()
        self.force = tk.BooleanVar(value=False)
        self.last_output_txt = ""

        self._build_ui()
        self._update_extract_state()

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(8, weight=1)

        title = ttk.Label(root, text="Convertisseur ODT Hatlab vers DokuWiki", font=("TkDefaultFont", 13, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(root, text="Fichier ODT source").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.input_odt).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(root, text="Choisir un fichier .odt", command=self.choose_input).grid(row=1, column=2, sticky="ew", pady=4)

        ttk.Label(root, text="Fichier TXT de sortie").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.output_txt).grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(root, text="Choisir l'emplacement de sortie", command=self.choose_output).grid(row=2, column=2, sticky="ew", pady=4)

        ttk.Label(root, text="Namespace média DokuWiki").grid(row=3, column=0, sticky="w", pady=4)
        namespace_frame = ttk.Frame(root)
        namespace_frame.grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        namespace_frame.columnconfigure(0, weight=1)
        ttk.Entry(namespace_frame, textvariable=self.media_namespace).grid(row=0, column=0, sticky="ew")
        ttk.Label(namespace_frame, text="Exemples : projets:electronique, projets:maison").grid(row=1, column=0, sticky="w", pady=(2, 0))

        ttk.Label(root, text="Identifiant de page").grid(row=4, column=0, sticky="w", pady=4)
        page_frame = ttk.Frame(root)
        page_frame.grid(row=4, column=1, sticky="ew", padx=8, pady=4)
        page_frame.columnconfigure(0, weight=1)
        ttk.Entry(page_frame, textvariable=self.page_id).grid(row=0, column=0, sticky="ew")
        ttk.Label(page_frame, text="Exemple : install_party_linux").grid(row=1, column=0, sticky="w", pady=(2, 0))

        ttk.Checkbutton(root, text="Extraire les images intégrées", variable=self.extract_images, command=self._update_extract_state).grid(row=5, column=0, sticky="w", pady=4)
        self.extract_entry = ttk.Entry(root, textvariable=self.extract_media_dir)
        self.extract_entry.grid(row=5, column=1, sticky="ew", padx=8, pady=4)
        self.extract_button = ttk.Button(root, text="Choisir le dossier média", command=self.choose_media_dir)
        self.extract_button.grid(row=5, column=2, sticky="ew", pady=4)

        ttk.Checkbutton(root, text="Écraser le fichier de sortie s'il existe", variable=self.force).grid(row=6, column=0, columnspan=3, sticky="w", pady=6)

        button_frame = ttk.Frame(root)
        button_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        button_frame.columnconfigure(0, weight=1)
        ttk.Button(button_frame, text="Convertir", command=self.convert).grid(row=0, column=0, sticky="w")
        ttk.Button(button_frame, text="Ouvrir le dossier de sortie", command=self.open_output_folder).grid(row=0, column=1, sticky="e")

        ttk.Label(root, text="Logs").grid(row=8, column=0, sticky="nw", pady=(6, 0))
        log_frame = ttk.Frame(root)
        log_frame.grid(row=8, column=1, columnspan=2, sticky="nsew", padx=8, pady=(6, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=14, wrap="word")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def choose_input(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier ODT",
            filetypes=(("Documents OpenDocument", "*.odt"), ("Tous les fichiers", "*.*")),
        )
        if not path:
            return
        self.input_odt.set(path)
        if not self.output_txt.get().strip():
            base, _extension = os.path.splitext(path)
            self.output_txt.set(base + ".txt")
        self.log("Fichier source sélectionné : %s" % path)

    def choose_output(self):
        initialdir = os.path.dirname(self.input_odt.get()) or os.getcwd()
        initialfile = "sortie_dokuwiki.txt"
        if self.input_odt.get().strip():
            initialfile = os.path.splitext(os.path.basename(self.input_odt.get().strip()))[0] + ".txt"
        path = filedialog.asksaveasfilename(
            title="Choisir l'emplacement du fichier TXT",
            defaultextension=".txt",
            initialdir=initialdir,
            initialfile=initialfile,
            filetypes=(("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")),
        )
        if path:
            self.output_txt.set(path)
            self.log("Fichier de sortie sélectionné : %s" % path)

    def choose_media_dir(self):
        path = filedialog.askdirectory(title="Choisir le dossier média de sortie")
        if path:
            self.extract_media_dir.set(path)
            self.log("Dossier média sélectionné : %s" % path)

    def _update_extract_state(self):
        state = "normal" if self.extract_images.get() else "disabled"
        self.extract_entry.configure(state=state)
        self.extract_button.configure(state=state)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def _validate_form(self):
        input_odt = self.input_odt.get().strip()
        output_txt = self.output_txt.get().strip()
        media_namespace = self.media_namespace.get().strip() or DEFAULT_MEDIA_NAMESPACE
        page_id = self.page_id.get().strip() or None
        extract_media_dir = None

        if not input_odt:
            raise ConversionError("Choisissez un fichier .odt source.")
        if not output_txt:
            raise ConversionError("Choisissez un fichier .txt de sortie.")
        if self.extract_images.get():
            extract_media_dir = self.extract_media_dir.get().strip()
            if not extract_media_dir:
                raise ConversionError("Choisissez un dossier média pour extraire les images intégrées.")

        return input_odt, output_txt, media_namespace, page_id, extract_media_dir

    def convert(self):
        try:
            input_odt, output_txt, media_namespace, page_id, extract_media_dir = self._validate_form()
            self.log("--- Conversion ---")
            self.log("Fichier source : %s" % input_odt)
            self.log("Fichier de sortie : %s" % output_txt)
            self.log("Namespace média : %s" % media_namespace)
            if page_id:
                self.log("Identifiant de page : %s" % page_id)
            if extract_media_dir:
                self.log("Extraction images : %s" % extract_media_dir)
            self.log("Fonction appelée : convert_odt_to_dokuwiki")

            report = convert_odt_to_dokuwiki(
                input_odt=input_odt,
                output_txt=output_txt,
                media_namespace=media_namespace,
                page_id=page_id,
                extract_media_dir=extract_media_dir,
                force=self.force.get(),
            )
            self.last_output_txt = report["output_txt"]
            for warning in report["warnings"]:
                self.log("Avertissement : %s" % warning)
            if report["images_extracted"]:
                self.log("Images extraites :")
                for image_path in report["images_extracted"]:
                    self.log("  - %s" % image_path)
            self.log("Succès : fichier généré : %s" % report["output_txt"])
            messagebox.showinfo("Conversion terminée", "Fichier généré :\n%s" % report["output_txt"])
        except Exception as exc:
            self.log("Erreur : %s" % exc)
            messagebox.showerror("Erreur de conversion", str(exc))

    def open_output_folder(self):
        output_txt = self.last_output_txt or self.output_txt.get().strip()
        if not output_txt:
            messagebox.showwarning("Aucun fichier", "Aucun fichier de sortie n'est défini.")
            return
        folder = os.path.dirname(os.path.abspath(output_txt))
        if not os.path.isdir(folder):
            messagebox.showerror("Dossier introuvable", "Le dossier n'existe pas :\n%s" % folder)
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", folder])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            self.log("Ouverture du dossier : %s" % folder)
        except Exception as exc:
            self.log("Impossible d'ouvrir le dossier : %s" % exc)
            messagebox.showerror("Ouverture impossible", str(exc))


def main():
    app = HatlabOdtConverterGui()
    app.mainloop()


if __name__ == "__main__":
    main()
