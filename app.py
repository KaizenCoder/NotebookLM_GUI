import customtkinter as ctk
import tkinter as tk
import subprocess
import threading
from tkinter import filedialog
import os
import json
import re

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def strip_ansi(text):
    """ Supprime toutes les séquences d'échappement ANSI (couleurs, positions de curseur) polluant stdout """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class NotebookLMApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NotebookLM Manager")
        self.geometry("1150x750") 
        self.minsize(1000, 600)

        self.paned_window = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bg="#444444")
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        self.notebooks_data = []
        self.selected_notebook_id = None
        self.combined_resources = []

        # ================== GAUCHE : CARNETS ==================
        self.left_panel = ctk.CTkFrame(self.paned_window, corner_radius=0)
        self.paned_window.add(self.left_panel, minsize=350, stretch="always")
        
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(3, weight=1) # ROW 3 pour que la scrollView prenne tout l'espace disponible

        self.lbl_notebooks = ctk.CTkLabel(self.left_panel, text="Vos Carnets", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_notebooks.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.en_filter_nb = ctk.CTkEntry(self.left_panel, placeholder_text="Rechercher un carnet...")
        self.en_filter_nb.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.en_filter_nb.bind("<KeyRelease>", self.render_notebooks)

        self.left_actions = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.left_actions.grid(row=2, column=0, padx=10, sticky="ew")
        self.left_actions.grid_columnconfigure(2, weight=1)
        
        self.btn_refresh_nb = ctk.CTkButton(self.left_actions, text="Actualiser", width=90, command=self.fetch_notebooks)
        self.btn_refresh_nb.grid(row=0, column=0, sticky="w")
        
        self.btn_login = ctk.CTkButton(self.left_actions, text="🔑 Login", width=80, command=self.login_notebooklm, fg_color="#d9534f", hover_color="#c9302c")
        self.btn_login.grid(row=0, column=1, padx=5, sticky="w")

        self.sort_var = ctk.StringVar(value="Alphabétique")
        self.combo_sort = ctk.CTkComboBox(self.left_actions, values=["Chronologique", "Alphabétique"], variable=self.sort_var, command=self.render_notebooks, width=130)
        self.combo_sort.grid(row=0, column=3, sticky="e")

        self.nb_scroll = ctk.CTkScrollableFrame(self.left_panel)
        self.nb_scroll.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        
        self.lbl_status_nb = ctk.CTkLabel(self.left_panel, text="Connexion en cours...", text_color="gray")
        self.lbl_status_nb.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        # ================== DROITE : RESSOURCES ==================
        self.right_panel = ctk.CTkFrame(self.paned_window, corner_radius=0)
        self.paned_window.add(self.right_panel, minsize=500, stretch="always")
        
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=1)

        self.lbl_resources = ctk.CTkLabel(self.right_panel, text="Aucun carnet sélectionné", font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_resources.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.right_actions = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.right_actions.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.right_actions.grid_columnconfigure(1, weight=1)

        self.en_filter_res = ctk.CTkEntry(self.right_actions, placeholder_text="Rechercher par nom...", width=160)
        self.en_filter_res.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.en_filter_res.bind("<KeyRelease>", self.render_resources)

        self.filter_types_frame = ctk.CTkScrollableFrame(self.right_actions, fg_color="transparent", orientation="horizontal", height=30)
        self.filter_types_frame.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.cb_filters = {}
        for idx, f_type in enumerate(["Sources", "Audio", "Vidéo", "Rapports", "Autres Artefacts"]):
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.filter_types_frame, text=f_type, variable=var, command=self.render_resources, width=80)
            cb.grid(row=0, column=idx, padx=5)
            self.cb_filters[f_type] = var

        self.cb_select_all = ctk.CTkCheckBox(self.right_actions, text="Tout sélectionner", command=self.toggle_select_all, width=120)
        self.cb_select_all.grid(row=0, column=2, padx=(5, 0), sticky="e")

        self.res_scroll = ctk.CTkScrollableFrame(self.right_panel)
        self.res_scroll.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        
        self.res_scroll.grid_columnconfigure(0, weight=0, minsize=40) 
        self.res_scroll.grid_columnconfigure(1, weight=1, minsize=140) 
        self.res_scroll.grid_columnconfigure(2, weight=4, minsize=300) 
        self.res_scroll.grid_columnconfigure(3, weight=1, minsize=100) 
        
        self.resource_checkboxes = []

        self.right_footer = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.right_footer.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.right_footer.grid_columnconfigure(1, weight=1)

        self.btn_dest = ctk.CTkButton(self.right_footer, text="Dossier...", command=self.choose_destination, width=100)
        self.btn_dest.grid(row=0, column=0, padx=5, pady=5)

        self.dest_var = ctk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.lbl_dest = ctk.CTkLabel(self.right_footer, textvariable=self.dest_var, text_color="gray")
        self.lbl_dest.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_download = ctk.CTkButton(self.right_footer, text="Télécharger", command=self.download_selected, fg_color="#28a745", hover_color="#218838")
        self.btn_download.grid(row=0, column=2, padx=5, pady=5)
        
        self.lbl_status_res = ctk.CTkLabel(self.right_panel, text="Sélectionnez un carnet à gauche", text_color="gray", justify="left", wraplength=450)
        self.lbl_status_res.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.after(100, lambda: self.paned_window.sash_place(0, 450, 0))
        
        # Démarrage automatique
        self.after(100, lambda: self.login_notebooklm(auto_fetch=True))

    def toggle_select_all(self):
        select_state = self.cb_select_all.get()
        for cb in self.resource_checkboxes:
            if select_state:
                cb.select()
            else:
                cb.deselect()

    def choose_destination(self):
        folder = filedialog.askdirectory(title="Choisir le dossier de sauvegarde", initialdir=self.dest_var.get())
        if folder:
            self.dest_var.set(folder)

    def login_notebooklm(self, auto_fetch=False):
        self.lbl_status_nb.configure(text="Authentification Chrome Google en cours...")
        self.btn_login.configure(state="disabled")
        self.btn_refresh_nb.configure(state="disabled")
        
        def run_login():
            try:
                env = os.environ.copy()
                env["CI"] = "1"
                p = subprocess.run("nlm login", env=env, shell=True, capture_output=True, text=True)
                if p.returncode == 0:
                    self.after(0, lambda: self.lbl_status_nb.configure(text="Connecté avec succès !"))
                    if auto_fetch:
                        self.after(0, self.fetch_notebooks)
                else:
                    self.after(0, lambda: self.lbl_status_nb.configure(text=f"Échec de connexion: {p.stderr[:50]}..."))
            except Exception as e:
                self.after(0, lambda: self.lbl_status_nb.configure(text=f"Erreur: {str(e)[:50]}"))
            finally:
                self.after(0, lambda: self.btn_login.configure(state="normal"))
                self.after(0, lambda: self.btn_refresh_nb.configure(state="normal"))

        threading.Thread(target=run_login, daemon=True).start()

    def run_cmd_json(self, cmd):
        env = os.environ.copy()
        env["CI"] = "1"
        env["NO_COLOR"] = "1"
        env["TERM"] = "dumb"
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, shell=True)
            output = strip_ansi(result.stdout).replace('\r', '\n')
            
            clean_lines = []
            for line in output.split("\n"):
                if not line.strip().startswith('━') and "╭─" not in line and "╰─" not in line:
                    clean_lines.append(line)
            output = "\n".join(clean_lines)

            start_idx = output.find('[')
            end_idx = output.rfind(']')
            if start_idx != -1 and end_idx != -1:
                return json.loads(output[start_idx:end_idx+1])
        except Exception as e:
            print(f"Erreur parsing JSON ({cmd}): {e}")
        return None

    def fetch_notebooks(self):
        self.lbl_status_nb.configure(text="Chargement...")
        self.btn_refresh_nb.configure(state="disabled")
        
        def run():
            data = self.run_cmd_json("nlm notebook list")
            if data:
                self.notebooks_data = data
                self.after(0, lambda: self.render_notebooks(None))
                self.after(0, lambda: self.lbl_status_nb.configure(text=f"{len(self.notebooks_data)} carnet(s) trouvé(s)"))
            else:
                self.notebooks_data = [
                    {"id": "abc-123", "title": "Audit et Contrôle 2026", "updated_at": "2026-03-20T10:00:00Z"},
                    {"id": "xyz-789", "title": "Rapport Annuel", "updated_at": "2026-03-19T10:00:00Z"}
                ]
                self.after(0, lambda: self.render_notebooks(None))
                self.after(0, lambda: self.lbl_status_nb.configure(text=f"Simulation activée (Erreur parsing CLI)"))
                
            self.after(0, lambda: self.btn_refresh_nb.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    def render_notebooks(self, _=None):
        for widget in self.nb_scroll.winfo_children():
            widget.destroy()
            
        sort_mode = self.sort_var.get()
        filter_text = self.en_filter_nb.get().lower()
        
        if sort_mode == "Alphabétique":
            sorted_nbs = sorted(self.notebooks_data, key=lambda x: str(x.get("title", "")).lower())
        else:
            sorted_nbs = sorted(self.notebooks_data, key=lambda x: x.get("updated_at", ""), reverse=True)
            
        for nb in sorted_nbs:
            nb_id = nb.get("id")
            raw_title = nb.get("title")
            nb_title = str(raw_title).strip() if raw_title else "Sans titre"
            
            if filter_text and filter_text not in nb_title.lower():
                continue
            
            btn = ctk.CTkButton(
                self.nb_scroll, 
                text=f"📄 {nb_title}", 
                fg_color="#3a3a3a", 
                hover_color="#4f4f4f",
                anchor="w", 
                command=lambda i=nb_id, t=nb_title: self.select_notebook(i, t)
            )
            btn.pack(fill="x", pady=2, padx=5)

    def select_notebook(self, nb_id, nb_title=""):
        self.selected_notebook_id = nb_id
        
        # Mettre à jour le titre dynamiquement
        titre_affichage = f'Carnet : "{nb_title}"' if nb_title else "Sources et Artefacts"
        self.lbl_resources.configure(text=titre_affichage)
        
        self.lbl_status_res.configure(text="Chargement des ressources...")
        self.btn_download.configure(state="disabled")
        
        self.en_filter_res.delete(0, 'end')
        for widget in self.res_scroll.winfo_children():
            widget.destroy()
        self.resource_checkboxes.clear()
        
        def run():
            self.combined_resources = []
            
            # 1. SOURCES ORIGINELLES UTILES
            sources_data = self.run_cmd_json(f'nlm source list {nb_id}')
            if isinstance(sources_data, list):
                for src in sources_data:
                    self.combined_resources.append({
                        "id": src.get("id"),
                        "title": src.get("title", ""),
                        "type": f"SOURCE ({src.get('type', 'texte')})",
                        "status": "Disponible",
                        "is_source": True
                    })
            
            # 2. ARTEFACTS GENERES (Audio, PDF, etc)
            artifacts_data = self.run_cmd_json(f'nlm studio status {nb_id} -a')
            if isinstance(artifacts_data, dict) and "artifacts" in artifacts_data:
                artifacts_list = artifacts_data["artifacts"]
            elif isinstance(artifacts_data, list):
                artifacts_list = artifacts_data
            else:
                artifacts_list = []
                
            for art in artifacts_list:
                art_id = art.get("id", art.get("artifact_id", ""))
                self.combined_resources.append({
                    "id": art_id,
                    "title": art.get("title", ""),
                    "type": f"ARTEFACT ({art.get('type', 'inconnu')})",
                    "status": art.get("status", "completed"),
                    "is_source": False,
                    "art_type": art.get("type", "unknown")
                })
                
            if not self.combined_resources:
                self.combined_resources = [
                    {"id": "doc-1", "title": "Bilan_Comptable_2025.pdf", "type": "SOURCE (pdf)", "status": "Simulation", "is_source": True},
                    {"id": "art-1", "title": "Podcast Synthèse", "type": "ARTEFACT (audio)", "status": "Simulation", "is_source": False, "art_type": "audio"}
                ]
                self.after(0, lambda: self.lbl_status_res.configure(text=f"Simulation activée pour les ressources."))
                
            self.after(0, self.render_resources)

        threading.Thread(target=run, daemon=True).start()

    def render_resources(self, event=None):
        filter_text = self.en_filter_res.get().lower()
        active_filters = [f_type for f_type, var in self.cb_filters.items() if var.get()]
        
        for widget in self.res_scroll.winfo_children():
            widget.destroy()
        self.resource_checkboxes.clear()
        
        if not self.combined_resources:
            self.lbl_status_res.configure(text="Ce carnet ne contient aucune ressource.")
            return

        ctk.CTkLabel(self.res_scroll, text="Sél.", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ctk.CTkLabel(self.res_scroll, text="Nature / Type", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ctk.CTkLabel(self.res_scroll, text="Nom Original ou Identifiant", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=2, sticky="w")
        ctk.CTkLabel(self.res_scroll, text="Statut", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=2, sticky="w")
            
        displayed_count = 0
        current_row = 1
        
        gen_names = {
            "audio": "Podcast Audio",
            "video": "Aperçu Vidéo",
            "report": "Rapport / Guide",
            "mind_map": "Carte Mentale",
            "slide_deck": "Diapositives",
            "quiz": "Quiz Interactif",
            "flashcards": "Flashcards",
            "data_table": "Tableau de Données"
        }
        
        for res in self.combined_resources:
            typ = res.get("type", "INCONNU").upper()
            title = res.get("title", "")
            res_id = res.get("id", "Sans ID")
            status = res.get("status", "N/A")
            is_source = res.get("is_source")
            art_type = res.get("art_type", "inconnu").lower()
            
            if is_source:
                display_name = title if (title and str(title).strip()) else f"Source ID: {res_id}"
            else:
                default_title = gen_names.get(art_type, f"Artefact généré")
                display_name = title if (title and str(title).strip()) else default_title

            if filter_text and filter_text not in display_name.lower() and filter_text not in typ.lower():
                continue
                
            allowed = False
            if is_source:
                if "Sources" in active_filters: allowed = True
            else:
                if art_type == "audio" and "Audio" in active_filters: allowed = True
                elif art_type == "video" and "Vidéo" in active_filters: allowed = True
                elif art_type in ["report", "slide_deck", "data_table", "mind_map"] and "Rapports" in active_filters: allowed = True
                elif art_type not in ["audio", "video", "report", "slide_deck", "data_table", "mind_map"] and "Autres Artefacts" in active_filters: allowed = True
                
            if not allowed:
                continue
                
            displayed_count += 1

            cb = ctk.CTkCheckBox(self.res_scroll, text="", width=20)
            cb.resource_data = res 
            cb.grid(row=current_row, column=0, padx=5, pady=5, sticky="w")
            self.resource_checkboxes.append(cb)
            
            ctk.CTkLabel(self.res_scroll, text=typ).grid(row=current_row, column=1, padx=5, sticky="w")
            ctk.CTkLabel(self.res_scroll, text=display_name, wraplength=400, justify="left").grid(row=current_row, column=2, padx=5, sticky="w")
            
            color_status = "white"
            if "completed" in status.lower() or "disponible" in status.lower(): color_status = "green"
            if "failed" in status.lower(): color_status = "red"
            
            ctk.CTkLabel(self.res_scroll, text=status, text_color=color_status).grid(row=current_row, column=3, padx=5, sticky="w")
            
            current_row += 1
            
        self.lbl_status_res.configure(text=f"{displayed_count} document(s) et artefact(s) affiché(s).")
        self.btn_download.configure(state="normal" if displayed_count > 0 else "disabled")

    def download_selected(self):
        dest = self.dest_var.get()
        selected = [cb for cb in self.resource_checkboxes if cb.get()]
        
        if not selected:
            self.lbl_status_res.configure(text="Sélectionnez au moins une ressource !")
            return

        self.lbl_status_res.configure(text=f"Téléchargement de {len(selected)} élément(s). Veuillez patienter...")
        self.btn_download.configure(state="disabled")

        def run_dl():
            import time
            success_count = 0
            errors = []
            env = os.environ.copy()
            env["CI"] = "1"
            env["NO_COLOR"] = "1"

            try:
                def sanitize_name(text):
                    import unicodedata
                    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
                    return "".join([c if c.isalnum() else "_" for c in text]).strip("_")

                for cb in selected:
                    res = cb.resource_data
                    res_id = res.get("id")
                    is_source = res.get("is_source")
                    
                    if not res_id: continue

                    if is_source:
                        raw_title = res.get("title")
                        if not raw_title: raw_title = "source_inconnue"
                        safe_title = sanitize_name(raw_title)
                        if not safe_title: safe_title = str(res_id)
                        
                        cmd = f'nlm source get {res_id}'
                        p = subprocess.run(cmd, env=env, shell=True, capture_output=True, text=True)
                        if p.returncode == 0:
                            clean_text = strip_ansi(p.stdout)
                            filepath = os.path.join(dest, f"{safe_title}.txt")
                            try:
                                with open(filepath, "w", encoding="utf-8") as f:
                                    f.write(clean_text)
                                success_count += 1
                            except Exception as e:
                                errors.append(f"Erreur d'écriture source: {str(e)[:50]}")
                        else:
                            err_out = strip_ansi(p.stderr).strip() or strip_ansi(p.stdout).strip()
                            errors.append(f"[{safe_title[:15]}] {err_out[:40]}")
                    else:
                        art_type = res.get("art_type", "unknown")
                        
                        exts = {
                            "audio": "m4a",
                            "video": "mp4",
                            "report": "md",
                            "slide_deck": "pdf",
                            "infographic": "png",
                            "data_table": "csv",
                            "mind_map": "json",
                            "quiz": "json",
                            "flashcards": "json"
                        }
                        ext = exts.get(art_type.lower(), "bin")
                        
                        raw_title = res.get("title")
                        if not raw_title: raw_title = f"Artefact_{art_type}"
                        safe_title = sanitize_name(raw_title)
                        if not safe_title: safe_title = str(res_id)
                        
                        out_path = os.path.join(dest, f"{safe_title}.{ext}")
                        
                        cmd = f'nlm download {art_type} "{self.selected_notebook_id}" --id "{res_id}" --output "{out_path}" --no-progress'
                        p = subprocess.run(cmd, env=env, shell=True, capture_output=True, text=True)
                        if p.returncode == 0:
                            success_count += 1
                        else:
                            err_out = strip_ansi(p.stderr).strip() or strip_ansi(p.stdout).strip()
                            errors.append(f"[{safe_title[:15]}] {err_out[:40]}")
                            
                    time.sleep(1)
                
                try:
                    nb_title_str = self.lbl_resources.cget("text").replace('Carnet : "', '').replace('"', '').strip()
                    if not nb_title_str or nb_title_str == "Sources et Artefacts": nb_title_str = "Notebook"
                    safe_nb_title = sanitize_name(nb_title_str)
                    url_path = os.path.join(dest, f"Acces_Direct_{safe_nb_title}.url")
                    
                    with open(url_path, "w", encoding="utf-8") as f:
                        f.write("[InternetShortcut]\n")
                        f.write(f"URL=https://notebooklm.google.com/notebook/{self.selected_notebook_id}\n")
                except Exception as e:
                    errors.append(f"Erreur création raccourci URL: {str(e)[:50]}")
                    
            except Exception as e:
                errors.append(f"Erreur critique: {str(e)[:100]}")
            
            if not errors:
                msg = f"Terminé : {success_count}/{len(selected)} fichier(s) sauvegardé(s) !"
            else:
                msg = f"{success_count}/{len(selected)} OK. Err: " + " | ".join(errors)
                
            self.after(0, lambda m=msg: self.lbl_status_res.configure(text=m[:200] + ("..." if len(m)>200 else "")))
            self.after(0, lambda: self.btn_download.configure(state="normal"))

        threading.Thread(target=run_dl, daemon=True).start()

if __name__ == "__main__":
    app = NotebookLMApp()
    app.mainloop()
