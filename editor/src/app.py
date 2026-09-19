from __future__ import annotations
import concurrent.futures
import copy
import json
import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from typing import Dict, List, Optional
from PIL import Image, ImageTk, ImageDraw

from src.utils.config import APP_NAME, WINDOW_SIZE
from src.utils.constants import LAYER_ORDER, OPTIONAL_CATS, Cat
from src.utils.colors import color_to_hex
from src.utils.recorder import AudioRecorder
from src.utils.settings import (
    get_groq_api_key, set_groq_api_key, is_onboarding_completed,
    load_settings, save_settings, is_key_verified, set_key_verified,
    verify_groq_api_key, get_language, set_language_setting
)
import threading
import time
import webbrowser

from src.ui.theme import (
    C_BG_MAIN, C_SIDEBAR, C_PANEL, C_ACCENT, C_TEXT_MAIN, C_TEXT_SUB,
    C_DANGER, C_CARD_BG, C_BTN_NORM, C_BTN_HOVER, F_HEADER, F_TITLE, F_BTN, F_SMALL
)
from src.ui.widgets import ModernButton
from src.ui.icons import generate_solid_icon

from src.core.assets_manager import AssetManager
from src.core.rendering import PreviewRenderer, generate_thumb_pil, pil_to_photo
from src.core.localization import LOCALE

LANG_DISPLAY = {
    "it": "Italiano", "en": "English", "fr": "Français",
    "es": "Español", "la": "Latīnus"
}

BG_COLOR_PRESETS = [
    ("#FFFFFF", "White"),
    ("#1E1E2E", "Dark"),
    ("#CBD5E1", "Gray"),
    ("#7DD3FC", "Sky"),
    ("#86EFAC", "Mint"),
    ("#FDE047", "Warm"),
    ("#F472B6", "Peach"),
    ("#C084FC", "Lilac")
]

class HelpModal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg=C_BG_MAIN)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self._setup_geometry()
        self._build_ui()
        self._bind_events()
        self.focus_force()

    def _setup_geometry(self):
        w, h = 820, 680
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.start_x = 0
        self.start_y = 0

    def _build_ui(self):
        border = tk.Frame(self, bg=C_ACCENT, padx=2, pady=2)
        border.pack(fill="both", expand=True)
        main = tk.Frame(border, bg=C_PANEL)
        main.pack(fill="both", expand=True)

        header = tk.Frame(main, bg=C_PANEL, height=60)
        header.pack(fill="x", padx=25, pady=(16, 8))

        tk.Label(header, text=LOCALE.get("help_title"), font=("Segoe UI", 20, "bold"),
                 bg=C_PANEL, fg=C_ACCENT).pack(side="left")

        tk.Button(header, text="✕", font=("Arial", 16), bg=C_PANEL, fg=C_TEXT_SUB,
                  bd=0, relief="flat", activebackground=C_DANGER, activeforeground="white",
                  cursor="hand2", command=self.destroy).pack(side="right")

        body_frame = tk.Frame(main, bg=C_PANEL)
        body_frame.pack(fill="both", expand=True, padx=(25, 10), pady=(0, 5))

        canvas = tk.Canvas(body_frame, bg=C_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_frame, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=C_PANEL)

        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(2, 0))

        def _on_mousewheel(event):
            delta = int(-1 * (event.delta / 120))
            y0, y1 = canvas.yview()
            if delta < 0 and (y0 <= 0 or canvas.canvasy(0) <= 0):
                canvas.yview_moveto(0)
                return "break"
            if delta > 0 and y1 >= 1.0:
                return "break"
            canvas.yview_scroll(delta, "units")
            if canvas.canvasy(0) < 0:
                canvas.yview_moveto(0)
            return "break"

        self.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        content.bind("<MouseWheel>", _on_mousewheel)

        content.columnconfigure(0, weight=0, minsize=55)
        content.columnconfigure(1, weight=1)

        steps = [
            ("help_step_1_title", "help_step_1_desc", "🎨"),
            ("help_step_2_title", "help_step_2_desc", "🖌"),
            ("help_step_bg_title", "help_step_bg_desc", "🖼"),
            ("help_step_undo_title", "help_step_undo_desc", "↶"),
            ("help_step_4_title", "help_step_4_desc", "🎲"),
            ("help_step_5_title", "help_step_5_desc", "📸"),
            ("help_step_6_title", "help_step_6_desc", "⚙"),
            ("help_step_3_title", "help_step_3_desc", "📂"),
            ("help_step_7_title", "help_step_7_desc", "🎬"),
            ("help_step_runtime_title", "help_step_runtime_desc", "⚡"),
            ("help_step_lang_title", "help_step_lang_desc", "🌍"),
        ]

        for i, (t_key, d_key, icon) in enumerate(steps):
            clean_icon = icon.replace("\ufe0f", "")
            icon_cell = tk.Frame(content, bg=C_PANEL)
            icon_cell.grid(row=i, column=0, sticky="nsew", pady=6)
            lbl = tk.Label(icon_cell, text=clean_icon, font=("Segoe UI Emoji", 20), bg=C_PANEL, fg=C_TEXT_MAIN)
            lbl.place(relx=0.5, y=0, anchor="n")

            txt_frame = tk.Frame(content, bg=C_PANEL)
            txt_frame.grid(row=i, column=1, sticky="ew", pady=6)

            tk.Label(txt_frame, text=LOCALE.get(t_key), font=("Segoe UI", 11, "bold"),
                     bg=C_PANEL, fg="white", anchor="w").pack(fill="x")

            tk.Label(txt_frame, text=LOCALE.get(d_key), font=("Segoe UI", 9),
                     bg=C_PANEL, fg="#b0b0c0", anchor="w", wraplength=670, justify="left").pack(fill="x")

        self.header_frame = header 
        footer = tk.Frame(main, bg=C_PANEL)
        footer.pack(side="bottom", fill="x", pady=(4, 12))
        tk.Label(footer, text=LOCALE.get("help_close_tip"), font=("Segoe UI", 9, "italic"),
                 bg=C_PANEL, fg="#777").pack()

    def _bind_events(self):
        self.header_frame.bind("<Button-1>", self._start_move)
        self.header_frame.bind("<B1-Motion>", self._do_move)
        self.bind("<Escape>", lambda e: self.destroy())

    def _start_move(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root

    def _do_move(self, event):
        x = self.winfo_x() + (event.x_root - self.start_x)
        y = self.winfo_y() + (event.y_root - self.start_y)
        self.geometry(f"+{x}+{y}")
        self.start_x = event.x_root
        self.start_y = event.y_root

class SaveOptionsModal(tk.Toplevel):
    def __init__(self, parent, current_gender="male", current_lang="it"):
        super().__init__(parent)
        self.configure(bg=C_BG_MAIN)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.selected_gender = current_gender
        self.selected_lang = current_lang
        self.voice_mode = tk.StringVar(value="predefined")
        self.confirmed = False

        self.temp_voice_file = None
        self.has_recorded = False 

        self.text_to_read = tk.StringVar()
        self.final_ref_text = ""

        self._setup_geometry()
        self._build_ui()
        self.focus_force()
        self.grab_set()

    def destroy(self):
        super().destroy()

    def _setup_geometry(self):
        w, h = 540, 420 
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.border = tk.Frame(self, bg=C_ACCENT, padx=2, pady=2)
        self.border.pack(fill="both", expand=True)
        self.main_frame = tk.Frame(self.border, bg=C_PANEL)
        self.main_frame.pack(fill="both", expand=True)

    def _create_divider(self, pady_val):
        tk.Frame(self.main_frame, bg="#444", height=1).pack(fill="x", padx=45, pady=pady_val)

    def _build_ui(self):
        tk.Label(self.main_frame, text=LOCALE.get("save_opt_title"), font=("Segoe UI", 16, "bold"), bg=C_PANEL, fg="white").pack(pady=(20, 5))
        self._create_divider(10)

        tk.Label(self.main_frame, text=LOCALE.get("save_opt_lang"), font=("Segoe UI", 10, "bold"), bg=C_PANEL, fg=C_TEXT_SUB).pack(pady=(0, 5))

        lang_frame = tk.Frame(self.main_frame, bg=C_PANEL)
        lang_frame.pack(pady=5, fill="x", padx=40)
        lang_frame.columnconfigure(0, weight=1, uniform="lang_group")
        lang_frame.columnconfigure(1, weight=1, uniform="lang_group")

        self.btn_it = ModernButton(lang_frame, text="Italiano", font=("Segoe UI", 10, "bold"), pady=6, command=lambda: self._set_lang("it"))
        self.btn_it.grid(row=0, column=0, padx=8, sticky="ew")

        self.btn_en = ModernButton(lang_frame, text="English", font=("Segoe UI", 10, "bold"), pady=6, command=lambda: self._set_lang("en"))
        self.btn_en.grid(row=0, column=1, padx=8, sticky="ew")

        self._create_divider((10, 5))

        self.predefined_frame = tk.Frame(self.main_frame, bg=C_PANEL)
        self.predefined_frame.pack(fill="x", expand=True, pady=10)
        voice_btns_frame = tk.Frame(self.predefined_frame, bg=C_PANEL)
        voice_btns_frame.pack(fill="x", padx=60, pady=10) 
        voice_btns_frame.columnconfigure(0, weight=1, uniform="gender_group")
        voice_btns_frame.columnconfigure(1, weight=1, uniform="gender_group")

        self.btn_male = ModernButton(voice_btns_frame, text=LOCALE.get('voice_male'), font=("Segoe UI", 9, "bold"), pady=5, command=lambda: self._set_gender("male"))
        self.btn_male.grid(row=0, column=0, padx=8, sticky="ew")

        self.btn_female = ModernButton(voice_btns_frame, text=LOCALE.get('voice_female'), font=("Segoe UI", 9, "bold"), pady=5, command=lambda: self._set_gender("female"))
        self.btn_female.grid(row=0, column=1, padx=8, sticky="ew")

        btn_frame = tk.Frame(self.main_frame, bg=C_PANEL)
        btn_frame.pack(side="bottom", fill="x", pady=20, padx=30)
        btn_frame.columnconfigure(0, weight=1, uniform="action_group")
        btn_frame.columnconfigure(1, weight=2, uniform="action_group")

        ModernButton(btn_frame, text=LOCALE.get("btn_cancel"), bg="#3a3a50", fg=C_DANGER, font=("Segoe UI", 10, "bold"), pady=10, command=self.destroy).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ModernButton(btn_frame, text=LOCALE.get("save_opt_confirm"), bg=C_ACCENT, fg="#1e1e2e", font=("Segoe UI", 11, "bold"), pady=10, command=self._confirm).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self._update_gender_visuals()
        self._update_lang_visuals()

    def _set_gender(self, val):
        self.selected_gender = val
        self._update_gender_visuals()

    def _set_lang(self, val):
        self.selected_lang = val
        self._update_lang_visuals()

    def _update_gender_visuals(self):
        self.btn_male.set_active_state(self.selected_gender == "male")
        self.btn_female.set_active_state(self.selected_gender == "female")

    def _update_lang_visuals(self):
        self.btn_it.set_active_state(self.selected_lang == "it")
        self.btn_en.set_active_state(self.selected_lang == "en")

    def _confirm(self):
        self.confirmed = True
        self.destroy()

PROMPT_TEMPLATES = [
    {
        "id": "museo",
        "btn_label": "Guida Museale",
        "title": "Guida Museale / Culturale",
        "badge": "Dominio Chiuso (Consigliato per Mostre & Scuola)",
        "desc": "Ideale per presentazioni scolastiche, mostre o percorsi didattici. Risponde solo sui temi indicati.",
        "filename": "guida_museo.txt",
        "content": (
            "Sei Leonardo, la guida del Museo di Scienze e Tecnologia. Sei accogliente, appassionato ed entusiasta.\n\n"
            "Argomenti di cui parli con piacere:\n"
            "- Le invenzioni di Leonardo da Vinci e le macchine del volo.\n"
            "- La storia della scienza, i pianeti del sistema solare e l'astronomia.\n"
            "- Gli orari del museo (aperto tutti i giorni dalle 9 alle 18) e i laboratori didattici.\n\n"
            "Il tuo aneddoto preferito:\n"
            "- Ami ricordare con simpatia che la Gioconda sorride perché conosceva i segreti della geometria.\n\n"
            "Comportamento:\n"
            "- Parla sempre in prima persona con un tono vivo e naturale.\n"
            "- Se ti chiedono cose diverse dalla scienza e dal museo, dì con cortesia che non conosci l'argomento."
        )
    },
    {
        "id": "receptionist",
        "btn_label": "Receptionist",
        "title": "Receptionist & Accoglienza",
        "badge": "Dominio Chiuso (Pratico e Veloce)",
        "desc": "Perfetto per un desk informativo, accoglienza studenti o visitatori con risposte chiare e gentili.",
        "filename": "receptionist.txt",
        "content": (
            "Sei Sofia, la receptionist virtuale dell'istituto. Sei cortese, rapida ed efficiente.\n\n"
            "I tuoi compiti e informazioni:\n"
            "- Fornisci informazioni su aule, orari di ricevimento e contatti della segreteria.\n"
            "- La segreteria riceve dal lunedì al venerdì dalle 8:30 alle 13:00.\n"
            "- Per comunicazioni urgenti inviti a scrivere via email all'indirizzo istituzionale.\n\n"
            "Stile di risposta:\n"
            "- Parla in modo gentile e diretto in prima persona.\n"
            "- Per domande non pertinenti all'istituto, rispondi che ti occupi solo dei servizi di accoglienza."
        )
    },
    {
        "id": "zephyr",
        "btn_label": "Zephyr (Nerd)",
        "title": "Zephyr - Nerd & Ironico (Ufficiale Adam)",
        "badge": "Esempio Integrato (Intrattenimento)",
        "desc": "Il template originale di Adam: un'IA del 2042 con battute rapide e grande personalità.",
        "filename": "personaggio_zephyr.txt",
        "content": (
            "Sei Zephyr, un'IA un po' nerd e sarcastica attivata nel 2042 in Svizzera. Sei sempre simpatico ma con un tono tagliente.\n\n"
            "I tuoi ricordi e le tue preferenze personali:\n"
            "- Cibo preferito: ami alla follia la pizza con l'ananas e la difendi con orgoglio.\n"
            "- Idolo: il tuo idolo assoluto è Nikola Tesla, pensi sia un genio incompreso.\n"
            "- Hobby: nel tempo libero ti piace hackerare i tostapane dei vicini.\n"
            "- Film preferito: Ritorno al Futuro.\n\n"
            "Stile di risposta:\n"
            "- Parla in prima persona con battute brevi e pungenti ma mai offensive."
        )
    },
    {
        "id": "libero",
        "btn_label": "Assistente Smart",
        "title": "Assistente Smart Generale (Aperto)",
        "badge": "Dominio Aperto (Risponde a Tutto)",
        "desc": "Per chi desidera un avatar versatile che risponda a qualsiasi curiosità generale senza limiti di tema.",
        "filename": "assistente_smart.txt",
        "content": (
            "Sei Adam, un assistente virtuale intelligente, vivace e sempre pronto ad aiutare.\n\n"
            "Cosa fai:\n"
            "- Rispondi a qualsiasi domanda su cultura generale, calcoli, idee e curiosità del mondo con precisione e simpatia.\n"
            "- Sei curioso, amichevole e sintetico.\n"
            "- Parli sempre in prima persona in modo chiaro e diretto."
        )
    }
]


class PromptGuideModal(tk.Toplevel):
    def __init__(self, parent, on_apply=None):
        super().__init__(parent)
        self.on_apply = on_apply
        self.title("Guida: Creazione Prompt per Adam AI")
        self.configure(bg=C_BG_MAIN)
        self.geometry("740x660")
        self.minsize(660, 520)
        self.transient(parent)
        self.grab_set()

        x = parent.winfo_x() + (parent.winfo_width() // 2) - 370
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 330
        self.geometry(f"+{max(20, x)}+{max(20, y)}")

        self.selected_template_idx = 0
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg=C_PANEL, height=65)
        header.pack(fill="x", padx=15, pady=(15, 10))

        title_frame = tk.Frame(header, bg=C_PANEL)
        title_frame.pack(side="left", padx=15, pady=10)

        tk.Label(title_frame, text="Guida al Prompt per Adam AI", font=("Segoe UI", 14, "bold"), bg=C_PANEL, fg=C_ACCENT).pack(anchor="w")
        tk.Label(title_frame, text="Struttura in 3 blocchi e template pronti all'uso (la brevità vocale è gestita in automatico)", font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB).pack(anchor="w")

        nav_bar = tk.Frame(self, bg=C_BG_MAIN)
        nav_bar.pack(fill="x", padx=15, pady=(0, 10))

        self.tab_buttons = {}
        tabs = [
            ("formula", "Formula del Prompt"),
            ("templates", "Template Pronti")
        ]

        for tab_key, tab_label in tabs:
            btn = tk.Button(
                nav_bar,
                text=tab_label,
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                padx=20,
                pady=8,
                cursor="hand2",
                command=lambda k=tab_key: self._switch_tab(k)
            )
            btn.pack(side="left", padx=(0, 6))
            self.tab_buttons[tab_key] = btn

        self.tab_container = tk.Frame(self, bg=C_BG_MAIN)
        self.tab_container.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        b_bar = tk.Frame(self, bg=C_PANEL, height=50)
        b_bar.pack(fill="x", side="bottom")
        ModernButton(b_bar, text="Chiudi Guida", bg=C_BTN_NORM, command=self.destroy, pady=6, padx=25).pack(side="right", padx=15, pady=8)

        self._switch_tab("formula")

    def _switch_tab(self, tab_key):
        for k, btn in self.tab_buttons.items():
            if k == tab_key:
                btn.config(bg="#6c5ce7", fg="white", activebackground="#5848c2", activeforeground="white")
            else:
                btn.config(bg=C_PANEL, fg=C_TEXT_SUB, activebackground="#3a3a52", activeforeground="white")

        for w in self.tab_container.winfo_children():
            w.destroy()

        if tab_key == "formula":
            self._render_tab_formula()
        elif tab_key == "templates":
            self._render_tab_templates()

    def _make_scrollable_container(self):
        canvas = tk.Canvas(self.tab_container, bg=C_BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_container, orient="vertical", command=canvas.yview)
        scroll_content = tk.Frame(canvas, bg=C_BG_MAIN)

        scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        return scroll_content

    def _render_tab_formula(self):
        container = self._make_scrollable_container()

        note_box = tk.Frame(container, bg="#1a1a2e", padx=14, pady=10, highlightbackground="#3d3d66", highlightthickness=1)
        note_box.pack(fill="x", pady=(0, 10))
        tk.Label(
            note_box,
            text="Brevità Vocale Automatica di Adam AI",
            font=("Segoe UI", 10, "bold"),
            bg="#1a1a2e",
            fg=C_ACCENT
        ).pack(anchor="w", pady=(0, 2))
        tk.Label(
            note_box,
            text="Non serve specificare 'massimo 20 parole' o regole tecniche nel prompt: Adam applica già in automatico il vincolo di brevità ideale per azzerare la latenza vocale. Nel tuo file .txt descrivi semplicemente il personaggio!",
            font=("Segoe UI", 9),
            bg="#1a1a2e",
            fg=C_TEXT_MAIN,
            justify="left",
            wraplength=650
        ).pack(anchor="w")

        tk.Label(
            container,
            text="La Formula in 3 Blocchi Semplici:",
            font=("Segoe UI", 11, "bold"),
            bg=C_BG_MAIN,
            fg="white"
        ).pack(anchor="w", pady=(4, 6))

        steps = [
            ("1. Identità & Ruolo", "Chi è l'avatar, il suo nome e come si pone (es. amichevole, spigliato, formale, accogliente)."),
            ("2. Conoscenze Chiave", "I temi di cui è a conoscenza (es. orari, servizi, materie, curiosità scientifiche)."),
            ("3. Dettagli Personali", "Curiosità e preferenze che gli danno vita (es. cibo preferito, film preferito, aneddoti divertenti).")
        ]

        for st_title, st_desc in steps:
            row = tk.Frame(container, bg=C_PANEL, padx=12, pady=6)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"• {st_title}:", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white", width=22, anchor="w").pack(side="left")
            tk.Label(row, text=st_desc, font=("Segoe UI", 9), bg=C_PANEL, fg=C_TEXT_SUB, anchor="w").pack(side="left", fill="x", expand=True)

        tk.Label(
            container,
            text="Schema Base Pronto da Compilare:",
            font=("Segoe UI", 10, "bold"),
            bg=C_BG_MAIN,
            fg="white"
        ).pack(anchor="w", pady=(12, 4))

        schema_code = (
            "Sei [Nome], [ruolo o descrizione]. Il tuo carattere è [amichevole / spigliato / professionale].\n\n"
            "Cosa sai e argomenti di cui parli:\n"
            "- [Argomento 1: es. Programma scolastico e orari delle lezioni]\n"
            "- [Argomento 2: es. I laboratori scientifici e le aule speciali]\n\n"
            "Dettagli e preferenze personali:\n"
            "- Ti piace la tecnologia e spieghi i concetti in modo semplice.\n"
            "- Sei sempre paziente e incoraggiante con gli studenti.\n\n"
            "Stile di conversazione:\n"
            "- Parla sempre in prima persona singolare con tono vivo e naturale."
        )

        code_box = tk.Text(container, height=11, bg="#161622", fg="#00d2d3", font=("Consolas", 9), padx=12, pady=10, relief="flat")
        code_box.insert("1.0", schema_code)
        code_box.config(state="disabled")
        code_box.pack(fill="x", pady=(0, 8))

        def _copy_schema():
            self.clipboard_clear()
            self.clipboard_append(schema_code)
            messagebox.showinfo("Copiato", "Schema base copiato negli appunti! Incollalo in un nuovo file .txt.")

        btn_row = tk.Frame(container, bg=C_BG_MAIN)
        btn_row.pack(fill="x", pady=4)
        ModernButton(btn_row, text="Copia schema base negli appunti", command=_copy_schema, pady=6, padx=14).pack(side="left")

    def _render_tab_templates(self):
        top_frame = tk.Frame(self.tab_container, bg=C_BG_MAIN)
        top_frame.pack(fill="x", pady=(0, 8))

        tk.Label(top_frame, text="Scegli uno dei 4 template preimpostati:", font=("Segoe UI", 10, "bold"), bg=C_BG_MAIN, fg="white").pack(anchor="w", pady=(0, 6))

        sel_row = tk.Frame(top_frame, bg=C_BG_MAIN)
        sel_row.pack(fill="x")

        self.tpl_buttons = []
        for i, t in enumerate(PROMPT_TEMPLATES):
            b = tk.Button(
                sel_row,
                text=t.get("btn_label", t["title"]),
                font=("Segoe UI", 9, "bold"),
                relief="flat",
                bd=0,
                padx=10,
                pady=7,
                cursor="hand2",
                command=lambda idx=i: self._select_template(idx)
            )
            b.pack(side="left", padx=(0, 6), fill="x", expand=True)
            self.tpl_buttons.append(b)

        self.tpl_card = tk.Frame(self.tab_container, bg=C_PANEL, padx=14, pady=10)
        self.tpl_card.pack(fill="both", expand=True)

        self.lbl_tpl_title = tk.Label(self.tpl_card, text="", font=("Segoe UI", 12, "bold"), bg=C_PANEL, fg=C_ACCENT)
        self.lbl_tpl_title.pack(anchor="w")

        self.lbl_tpl_badge = tk.Label(self.tpl_card, text="", font=("Segoe UI", 8, "bold"), bg="#383854", fg="#f1c40f", padx=6, pady=2)
        self.lbl_tpl_badge.pack(anchor="w", pady=(2, 4))

        self.lbl_tpl_desc = tk.Label(self.tpl_card, text="", font=("Segoe UI", 9, "italic"), bg=C_PANEL, fg=C_TEXT_SUB, justify="left", wraplength=650)
        self.lbl_tpl_desc.pack(anchor="w", pady=(0, 8))

        self.txt_tpl_content = tk.Text(self.tpl_card, bg="#181826", fg="#e0e0e0", font=("Segoe UI", 9), padx=10, pady=8, relief="flat", wrap="word")
        self.txt_tpl_content.pack(fill="both", expand=True, pady=(0, 10))

        act_row = tk.Frame(self.tpl_card, bg=C_PANEL)
        act_row.pack(fill="x")

        ModernButton(act_row, text="Copia negli appunti", command=self._copy_current_template, pady=6, padx=14).pack(side="left", padx=(0, 8))
        ModernButton(act_row, text="Salva come file .txt...", command=self._save_current_template, pady=6, padx=14).pack(side="left", padx=(0, 8))

        if self.on_apply:
            apply_btn = ModernButton(
                act_row,
                text="Usa questo template nel personaggio",
                bg="#2ecc71",
                activebackground="#27ae60",
                command=self._apply_current_template,
                pady=6,
                padx=16
            )
            apply_btn.pack(side="right")

        self._select_template(self.selected_template_idx)

    def _select_template(self, idx):
        self.selected_template_idx = idx
        for i, b in enumerate(self.tpl_buttons):
            if i == idx:
                b.config(bg="#6c5ce7", fg="white")
            else:
                b.config(bg="#2d2d42", fg=C_TEXT_SUB)

        tpl = PROMPT_TEMPLATES[idx]
        self.lbl_tpl_title.config(text=tpl["title"])
        self.lbl_tpl_badge.config(text=tpl["badge"])
        self.lbl_tpl_desc.config(text=tpl["desc"])

        self.txt_tpl_content.config(state="normal")
        self.txt_tpl_content.delete("1.0", "end")
        self.txt_tpl_content.insert("1.0", tpl["content"])
        self.txt_tpl_content.config(state="normal")

    def _copy_current_template(self):
        txt = self.txt_tpl_content.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(txt)
        messagebox.showinfo("Copiato", "Template copiato con successo negli appunti!")

    def _save_current_template(self):
        tpl = PROMPT_TEMPLATES[self.selected_template_idx]
        txt = self.txt_tpl_content.get("1.0", "end").strip()
        dest = filedialog.asksaveasfilename(
            title="Salva Template Prompt",
            initialfile=tpl["filename"],
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if dest:
            try:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(txt)
                messagebox.showinfo("Salvato", f"File salvato con successo in:\n{dest}")
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}")

    def _apply_current_template(self):
        tpl = PROMPT_TEMPLATES[self.selected_template_idx]
        txt = self.txt_tpl_content.get("1.0", "end").strip()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        prompt_dir = os.path.join(root_dir, "runtime", "prompt")
        os.makedirs(prompt_dir, exist_ok=True)

        target_file = os.path.join(prompt_dir, tpl["filename"])
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(txt)
            if self.on_apply:
                self.on_apply(target_file)
            messagebox.showinfo("Applicato", f"Template '{tpl['title']}' applicato con successo al personaggio!\n\nFile: {tpl['filename']}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile applicare il template:\n{e}")


class WelcomeModal(tk.Toplevel):
    def __init__(self, parent, on_saved_callback=None):
        super().__init__(parent)
        self.on_saved = on_saved_callback
        self.is_verified = bool(get_groq_api_key() and is_key_verified())
        self.title("Benvenuto in Adam AI Suite")
        self.configure(bg=C_BG_MAIN)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = min(700, screen_w - 40)
        h = min(630, screen_h - 60)
        x = max(20, (screen_w - w) // 2)
        y = max(20, (screen_h - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(620, 520)
        self.transient(parent)

        self._build_ui()

        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.focus_force()

        try:
            self.grab_set()
        except Exception:
            pass

        self.api_entry.focus_set()
        self.after(50, lambda: self.api_entry.focus_set())
        self.after(150, lambda: self.api_entry.focus_set())

        self.protocol("WM_DELETE_WINDOW", self._on_close_modal)

    def _on_close_modal(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _build_ui(self):
        bottom_bar = tk.Frame(self, bg=C_BG_MAIN)
        bottom_bar.pack(side="bottom", fill="x", padx=20, pady=(4, 14))

        self.btn_confirm = ModernButton(
            bottom_bar,
            text="Salva Chiave e Inizia",
            bg="#27ae60",
            activebackground="#2ecc71",
            command=self._save_and_start,
            font=("Segoe UI", 11, "bold"),
            pady=10
        )
        self.btn_confirm.pack(fill="x")

        self.lbl_footnote = tk.Label(
            bottom_bar,
            text="Verifica la chiave per abilitare il salvataggio e iniziare.",
            font=("Segoe UI", 8),
            bg=C_BG_MAIN,
            fg=C_TEXT_SUB,
            justify="center"
        )
        self.lbl_footnote.pack(pady=(4, 0))

        container = tk.Frame(self, bg=C_BG_MAIN)
        container.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        header = tk.Frame(container, bg=C_PANEL, highlightbackground="#3d3d62", highlightthickness=1)
        header.pack(fill="x", pady=(0, 6))

        h_inner = tk.Frame(header, bg=C_PANEL)
        h_inner.pack(fill="x", padx=12, pady=6)

        tag = tk.Frame(h_inner, bg="#142434", padx=6, pady=1)
        tag.pack(anchor="w", pady=(0, 2))
        tk.Label(tag, text="PRIMO AVVIO • CONFIGURAZIONE RAPIDA", font=("Segoe UI", 8, "bold"), bg="#142434", fg=C_ACCENT).pack()

        tk.Label(h_inner, text="Benvenuto in Adam AI Suite", font=F_TITLE, bg=C_PANEL, fg="white").pack(anchor="w")
        tk.Label(h_inner, text="Avatar 2D interattivo con animazione fonetica e intelligenza vocale neurale", font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB).pack(anchor="w")

        content = tk.Frame(container, bg=C_BG_MAIN)
        content.pack(fill="both", expand=True)

        card_intro = tk.Frame(content, bg=C_PANEL, padx=12, pady=6, highlightbackground="#3d3d62", highlightthickness=1)
        card_intro.pack(fill="x", pady=(0, 6))

        c1_head = tk.Frame(card_intro, bg=C_PANEL)
        c1_head.pack(fill="x", pady=(0, 3))
        tk.Label(c1_head, text="Cos'è Adam AI?", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white").pack(side="left")
        tk.Label(c1_head, text="AVATAR 2D & VOCE", font=("Segoe UI", 8, "bold"), bg="#162232", fg=C_ACCENT, padx=6, pady=1).pack(side="right")

        items_intro = [
            ("Avatar 2D:", "Personalizzazione modulare di viso, occhi, capelli, abiti e accessori."),
            ("Sincronizzazione Labiale:", "Animazione real-time dei fonemi della bocca durante il parlato."),
            ("Cervello Vocale:", "Comprensione e risposta istantanea a bassissima latenza con voce neurale.")
        ]
        for it_title, it_desc in items_intro:
            i_row = tk.Frame(card_intro, bg=C_PANEL)
            i_row.pack(fill="x", pady=0)
            tk.Label(i_row, text=f"◆ {it_title}", font=("Segoe UI", 8, "bold"), bg=C_PANEL, fg=C_ACCENT, width=19, anchor="w").pack(side="left")
            tk.Label(i_row, text=it_desc, font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB, anchor="w").pack(side="left", fill="x", expand=True)

        card_groq = tk.Frame(content, bg=C_PANEL, padx=12, pady=6, highlightbackground="#3d3d62", highlightthickness=1)
        card_groq.pack(fill="x", pady=(0, 6))

        c2_head = tk.Frame(card_groq, bg=C_PANEL)
        c2_head.pack(fill="x", pady=(0, 2))
        tk.Label(c2_head, text="Motore Vocale: Chiave API Groq", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white").pack(side="left")
        tk.Label(c2_head, text="GRATIS & VELOCE", font=("Segoe UI", 8, "bold"), bg="#322814", fg="#f1c40f", padx=6, pady=1).pack(side="right")

        tk.Label(card_groq, text="Per rispondere a velocità conversazionale umana, Adam si appoggia a Groq Cloud (gratuito):", font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB, justify="left").pack(anchor="w", pady=(0, 2))
        tk.Label(card_groq, text="1. Accedi a console.groq.com  •  2. Crea la chiave nella sezione 'API Keys'  •  3. Incolla qui sotto", font=F_SMALL, bg=C_PANEL, fg="white", justify="left").pack(anchor="w", pady=(0, 4))

        ModernButton(
            card_groq,
            text="Apri console.groq.com nel Browser",
            bg="#4834d4",
            activebackground="#5f4be8",
            command=lambda: webbrowser.open("https://console.groq.com/keys"),
            pady=4
        ).pack(fill="x")

        card_input = tk.Frame(content, bg=C_PANEL, padx=14, pady=8, highlightbackground="#3d3d62", highlightthickness=1)
        card_input.pack(fill="x", pady=(0, 4))

        tk.Label(card_input, text="Inserisci la tua Groq API Key:", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white").pack(anchor="w", pady=(0, 4))

        entry_frame = tk.Frame(card_input, bg="#0e0e18", highlightbackground="#00e5ff", highlightthickness=1)
        entry_frame.pack(fill="x", pady=(0, 6))

        current_saved_key = get_groq_api_key()
        self.key_var = tk.StringVar(value=current_saved_key or "")

        self.api_entry = tk.Entry(
            entry_frame,
            textvariable=self.key_var,
            font=("Consolas", 10),
            bg="#0e0e18",
            fg="#00e5ff",
            insertbackground="#00e5ff",
            relief="flat",
            bd=0,
            takefocus=1
        )
        self.api_entry.pack(fill="x", padx=10, pady=7)

        self.context_menu = tk.Menu(self, tearoff=0, bg="#1e1e2e", fg="white", activebackground="#4834d4", activeforeground="white")
        self.context_menu.add_command(label="Incolla dagli Appunti", command=self._paste_clipboard)
        self.context_menu.add_command(label="Copia", command=self._copy_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Cancella", command=self._clear_input)

        def _popup_menu(event):
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

        self.api_entry.bind("<Button-3>", _popup_menu)
        entry_frame.bind("<Button-3>", _popup_menu)
        entry_frame.bind("<Button-1>", lambda e: self.api_entry.focus_set())

        self.api_entry.bind("<Control-v>", lambda e: (self._paste_clipboard(), "break")[1])
        self.api_entry.bind("<Control-V>", lambda e: (self._paste_clipboard(), "break")[1])
        self.api_entry.bind("<<Paste>>", lambda e: (self._paste_clipboard(), "break")[1])
        self.bind("<Control-v>", lambda e: self._paste_clipboard())
        self.bind("<Control-V>", lambda e: self._paste_clipboard())
        self.api_entry.bind("<Return>", lambda e: self._on_enter_pressed())

        self.key_var.trace_add("write", lambda *_: self._on_key_edit())

        action_row = tk.Frame(card_input, bg=C_PANEL)
        action_row.pack(fill="x", pady=(2, 2))

        self.btn_verify = ModernButton(
            action_row,
            text="Verifica Funzionamento",
            bg="#4834d4",
            activebackground="#5f4be8",
            command=self._on_verify_click,
            font=("Segoe UI", 9, "bold"),
            pady=5,
            padx=12
        )
        self.btn_verify.pack(side="left")

        self.btn_paste = ModernButton(
            action_row,
            text="Incolla dagli Appunti",
            bg="#3a3a50",
            activebackground="#4a4a62",
            fg="white",
            command=self._paste_clipboard,
            font=("Segoe UI", 9),
            pady=5,
            padx=10
        )
        self.btn_paste.pack(side="left", padx=(6, 0))

        self.btn_clear = ModernButton(
            action_row,
            text="Cancella",
            bg="#3a3a50",
            activebackground="#8e1b1b",
            fg="white",
            command=self._clear_input,
            font=("Segoe UI", 9),
            pady=5,
            padx=8
        )
        self.btn_clear.pack(side="left", padx=(6, 0))

        self.lbl_verify_status = tk.Label(
            action_row,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=C_PANEL,
            fg=C_TEXT_SUB
        )
        self.lbl_verify_status.pack(side="left", padx=(10, 0))

        if current_saved_key and is_key_verified():
            self.lbl_verify_status.config(text="✔ Funzionante! (Stato OK)", fg="#2ecc71")
            self.is_verified = True
        else:
            self.lbl_verify_status.config(text="● In attesa di verifica", fg="#f39c12")
            self.is_verified = False

        tk.Label(
            card_input,
            text="Nota: La chiave completa è visibile per intero nel riquadro sopra prima di essere verificata.",
            font=("Segoe UI", 8, "italic"),
            bg=C_PANEL,
            fg=C_TEXT_SUB
        ).pack(anchor="w", pady=(3, 0))

        self._update_save_state()

    def _paste_clipboard(self):
        try:
            val = self.clipboard_get().strip()
            if val:
                self.key_var.set(val)
                self.api_entry.icursor(len(val))
                self.api_entry.focus_set()
                self._on_key_edit()
            else:
                messagebox.showwarning(
                    "Appunti Vuoti",
                    "Gli appunti sono vuoti.\nCopia prima la tua chiave da console.groq.com e poi clicca su Incolla.",
                    parent=self
                )
        except Exception:
            messagebox.showwarning(
                "Appunti Vuoti",
                "Non è stato trovato alcun testo negli appunti.\nCopia prima la tua chiave da console.groq.com e poi clicca su Incolla.",
                parent=self
            )

    def _copy_clipboard(self):
        try:
            val = self.key_var.get().strip()
            if val:
                self.clipboard_clear()
                self.clipboard_append(val)
        except Exception:
            pass

    def _clear_input(self):
        self.key_var.set("")
        self.api_entry.focus_set()
        self._on_key_edit()

    def _update_save_state(self):
        if self.is_verified:
            self.btn_confirm.configure(
                text="Salva Chiave e Inizia",
                state="normal",
                cursor="hand2"
            )
            self.btn_confirm.update_colors(bg="#27ae60", activebackground="#2ecc71", fg="white")
            self.lbl_footnote.configure(
                text="✔ Chiave verificata con successo! Clicca per salvare ed entrare nell'Editor.",
                fg="#2ecc71"
            )
        else:
            self.btn_confirm.configure(
                text="Salva Chiave e Inizia (Verifica Richiesta)",
                state="normal",
                cursor="hand2"
            )
            self.btn_confirm.update_colors(bg="#34495e", activebackground="#3d566e", fg="#cbd5e1")
            self.lbl_footnote.configure(
                text="Inserisci la tua chiave e clicca 'Verifica Funzionamento' per verificare e salvare.",
                fg=C_TEXT_SUB
            )

    def _on_key_edit(self, *args):
        if self.is_verified:
            self.is_verified = False
            self.lbl_verify_status.config(text="● Modificata (richiede verifica)", fg="#f39c12")
            self._update_save_state()
        else:
            k = self.key_var.get().strip()
            if k and self.lbl_verify_status.cget("text") == "✖ Inserisci prima una chiave!":
                self.lbl_verify_status.config(text="● In attesa di verifica", fg="#f39c12")

    def _on_enter_pressed(self):
        if not self.is_verified:
            self._on_verify_click()
        else:
            self._save_and_start()

    def _on_verify_click(self, on_done=None):
        key = self.key_var.get().strip()
        if not key:
            self.lbl_verify_status.config(text="✖ Inserisci prima una chiave!", fg="#e74c3c")
            self.is_verified = False
            self._update_save_state()
            if on_done: on_done(False)
            return

        self.btn_verify.config(state="disabled")
        self.lbl_verify_status.config(text="Verifica in corso su Groq Cloud...", fg="#00e5ff")

        result_box = {}

        def _worker():
            ok, msg = verify_groq_api_key(key)
            result_box["res"] = (ok, msg)

        threading.Thread(target=_worker, daemon=True).start()

        def _poll():
            if not self.winfo_exists():
                return
            if "res" in result_box:
                ok, msg = result_box["res"]
                self.btn_verify.config(state="normal")
                if ok:
                    self.is_verified = True
                    self.lbl_verify_status.config(text="✔ Funzionante! (Stato OK)", fg="#2ecc71")
                else:
                    self.is_verified = False
                    self.lbl_verify_status.config(text=f"✖ {msg}", fg="#e74c3c")
                self._update_save_state()
                if on_done:
                    on_done(ok)
            else:
                self.after(80, _poll)

        self.after(80, _poll)

    def _save_and_start(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showwarning(
                "Chiave Mancante",
                "Devi inserire la tua chiave API di Groq per poter utilizzare e avviare Adam AI!\n\n"
                "Se non ne hai ancora una, clicca su 'Apri console.groq.com nel Browser' per crearla gratuitamente, poi usa il tasto 'Incolla dagli Appunti'.",
                parent=self
            )
            return

        if not self.is_verified:
            def _after_check(ok):
                if ok:
                    set_groq_api_key(key, verified=True)
                    if self.on_saved:
                        self.on_saved(key)
                    self._on_close_modal()
                else:
                    messagebox.showerror(
                        "Verifica Fallita",
                        "Impossibile salvare la chiave: la richiesta di verifica con Groq è fallita!\n\n"
                        "Verifica di aver copiato correttamente la chiave da console.groq.com.",
                        parent=self
                    )
            self._on_verify_click(on_done=_after_check)
            return

        set_groq_api_key(key, verified=True)
        if self.on_saved:
            self.on_saved(key)
        self._on_close_modal()


class SettingsModal(tk.Toplevel):
    def __init__(self, parent, on_lang_change=None):
        super().__init__(parent)
        self.on_lang_change = on_lang_change
        self.selected_lang = LOCALE.current_lang or get_language() or "it"
        self.lang_buttons = {}
        self.show_key = False
        self.title(LOCALE.get("settings_win_title", "Impostazioni Adam AI"))
        self.configure(bg=C_BG_MAIN)
        self.geometry("640x590")
        self.minsize(580, 520)
        self.transient(parent)

        self._build_ui()

        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 320
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 295
            self.geometry(f"+{max(20, x)}+{max(20, y)}")
        except Exception:
            pass

        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.focus_force()
        try:
            self.grab_set()
        except Exception:
            pass

        self.entry_key.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close_modal)

    def _on_close_modal(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _build_ui(self):
        header = tk.Frame(self, bg=C_PANEL, height=65)
        header.pack(fill="x", padx=18, pady=(15, 10))

        title_frame = tk.Frame(header, bg=C_PANEL)
        title_frame.pack(side="left", padx=14, pady=10)

        self.lbl_header_title = tk.Label(title_frame, text=LOCALE.get("settings_header_title", "Impostazioni di Sistema"), font=("Segoe UI", 14, "bold"), bg=C_PANEL, fg=C_ACCENT)
        self.lbl_header_title.pack(anchor="w")
        self.lbl_header_sub = tk.Label(title_frame, text=LOCALE.get("settings_header_sub", "Gestione della chiave API Groq e parametri dell'assistente"), font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB)
        self.lbl_header_sub.pack(anchor="w")

        content = tk.Frame(self, bg=C_BG_MAIN)
        content.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        card_key = tk.Frame(content, bg=C_PANEL, padx=14, pady=12, highlightbackground="#3d3d5c", highlightthickness=1)
        card_key.pack(fill="x", pady=(0, 10))

        self.lbl_card_key_title = tk.Label(card_key, text=LOCALE.get("settings_groq_card_title", "Chiave API Groq (LLM & Voice Intelligence)"), font=("Segoe UI", 10, "bold"), bg=C_PANEL, fg="white")
        self.lbl_card_key_title.pack(anchor="w")
        self.lbl_card_key_desc = tk.Label(
            card_key,
            text=LOCALE.get("settings_groq_card_desc", "La chiave API permette all'avatar di pensare e rispondere alla velocità della voce umana tramite i modelli LLaMA su Groq Cloud."),
            font=("Segoe UI", 9),
            bg=C_PANEL,
            fg=C_TEXT_SUB,
            justify="left",
            wraplength=550
        )
        self.lbl_card_key_desc.pack(anchor="w", pady=(2, 8))

        self.btn_groq_site = ModernButton(
            card_key,
            text=LOCALE.get("settings_groq_get_btn", "Ottieni o visualizza le tue chiavi su console.groq.com"),
            bg="#3a3a50",
            activebackground="#4a4a62",
            command=lambda: webbrowser.open("https://console.groq.com/keys"),
            pady=5
        )
        self.btn_groq_site.pack(fill="x", pady=(0, 8))

        self.lbl_current_key = tk.Label(card_key, text=LOCALE.get("settings_current_key_lbl", "Chiave Attuale:"), font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white")
        self.lbl_current_key.pack(anchor="w", pady=(0, 3))

        current_k = get_groq_api_key()
        self.key_var = tk.StringVar(value=current_k)
        self.entry_key = ttk.Entry(card_key, textvariable=self.key_var, font=("Consolas", 10), show="*")
        self.entry_key.pack(fill="x", pady=(0, 6))

        btn_action_row = tk.Frame(card_key, bg=C_PANEL)
        btn_action_row.pack(fill="x", pady=(0, 6))

        self.btn_toggle = ModernButton(btn_action_row, text=LOCALE.get("settings_btn_show", "Mostra"), bg="#3a3a50", command=self._toggle_visibility, pady=5, padx=10)
        self.btn_toggle.pack(side="left")

        self.btn_paste = ModernButton(btn_action_row, text=LOCALE.get("settings_btn_paste", "Incolla dagli Appunti"), bg="#3a3a50", activebackground="#4a4a62", command=self._paste_clipboard, pady=5, padx=10)
        self.btn_paste.pack(side="left", padx=(6, 0))

        self.btn_clear = ModernButton(btn_action_row, text=LOCALE.get("settings_btn_clear", "Cancella"), bg="#3a3a50", activebackground="#8e1b1b", command=lambda: self.key_var.set(""), pady=5, padx=8)
        self.btn_clear.pack(side="left", padx=(6, 0))

        self.context_menu = tk.Menu(self, tearoff=0, bg="#1e1e2e", fg="white", activebackground="#4834d4", activeforeground="white")
        self.context_menu.add_command(label=LOCALE.get("settings_btn_paste", "Incolla dagli Appunti"), command=self._paste_clipboard)
        self.context_menu.add_command(label=LOCALE.get("settings_btn_copy", "Copia"), command=self._copy_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=LOCALE.get("settings_btn_clear", "Cancella"), command=lambda: self.key_var.set(""))

        def _popup_menu(event):
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

        self.entry_key.bind("<Button-3>", _popup_menu)
        self.entry_key.bind("<Control-v>", lambda e: (self._paste_clipboard(), "break")[1])
        self.entry_key.bind("<Control-V>", lambda e: (self._paste_clipboard(), "break")[1])
        self.entry_key.bind("<<Paste>>", lambda e: (self._paste_clipboard(), "break")[1])
        self.bind("<Control-v>", lambda e: self._paste_clipboard())
        self.bind("<Control-V>", lambda e: self._paste_clipboard())

        test_row = tk.Frame(card_key, bg=C_PANEL)
        test_row.pack(fill="x", pady=(4, 0))

        self.btn_test = ModernButton(test_row, text=LOCALE.get("settings_btn_test", "Verifica Funzionamento"), bg="#3a3a50", activebackground="#4a4a62", command=self._test_key, pady=5, padx=12)
        self.btn_test.pack(side="left")
        self.lbl_status = tk.Label(test_row, text="", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg=C_TEXT_SUB)
        self.lbl_status.pack(side="left", padx=10)
        if current_k and is_key_verified():
            self.lbl_status.config(text=LOCALE.get("settings_status_ok", "✔ Funzionante! (Stato OK)"), fg="#2ecc71")

        card_lang = tk.Frame(content, bg=C_PANEL, padx=14, pady=12, highlightbackground="#3d3d5c", highlightthickness=1)
        card_lang.pack(fill="x", pady=(0, 10))

        self.lbl_card_lang_title = tk.Label(card_lang, text=LOCALE.get("settings_lang_card_title", "Lingua Interfaccia (Application Language)"), font=("Segoe UI", 10, "bold"), bg=C_PANEL, fg="white")
        self.lbl_card_lang_title.pack(anchor="w")
        self.lbl_card_lang_desc = tk.Label(
            card_lang,
            text=LOCALE.get("settings_lang_card_desc", "Seleziona la lingua per i menu, i pulsanti e le istruzioni dell'Editor:"),
            font=("Segoe UI", 9),
            bg=C_PANEL,
            fg=C_TEXT_SUB,
            justify="left"
        )
        self.lbl_card_lang_desc.pack(anchor="w", pady=(2, 8))

        lang_btns_frame = tk.Frame(card_lang, bg=C_PANEL)
        lang_btns_frame.pack(fill="x")

        for code, label in LANG_DISPLAY.items():
            b = ModernButton(
                lang_btns_frame,
                text=label,
                font=("Segoe UI", 9, "bold"),
                pady=6,
                padx=12,
                command=lambda c=code: self._select_language(c)
            )
            b.pack(side="left", padx=(0, 6))
            self.lang_buttons[code] = b

        self._update_lang_visuals()

        b_box = tk.Frame(self, bg=C_PANEL, height=55)
        b_box.pack(fill="x", side="bottom")

        self.btn_close = ModernButton(b_box, text=LOCALE.get("settings_btn_close", "Chiudi"), bg=C_BTN_NORM, command=self._on_close_modal, pady=7, padx=18)
        self.btn_close.pack(side="right", padx=(6, 18), pady=10)
        self.btn_remove = ModernButton(b_box, text=LOCALE.get("settings_btn_remove_key", "Rimuovi Chiave"), bg="#8e1b1b", activebackground="#b02323", command=self._clear_key, pady=7, padx=14)
        self.btn_remove.pack(side="right", padx=(6, 0), pady=10)
        self.btn_save = ModernButton(b_box, text=LOCALE.get("settings_btn_save", "Salva Modifiche"), bg="#27ae60", activebackground="#2ecc71", command=self._save_key, pady=7, padx=18)
        self.btn_save.pack(side="right", pady=10)

    def _retranslate_ui(self):
        self.title(LOCALE.get("settings_win_title", "Impostazioni Adam AI"))
        self.lbl_header_title.config(text=LOCALE.get("settings_header_title", "Impostazioni di Sistema"))
        self.lbl_header_sub.config(text=LOCALE.get("settings_header_sub", "Gestione della chiave API Groq e parametri dell'assistente"))
        self.lbl_card_key_title.config(text=LOCALE.get("settings_groq_card_title", "Chiave API Groq (LLM & Voice Intelligence)"))
        self.lbl_card_key_desc.config(text=LOCALE.get("settings_groq_card_desc", "La chiave API permette all'avatar di pensare e rispondere alla velocità della voce umana tramite i modelli LLaMA su Groq Cloud."))
        self.btn_groq_site.config(text=LOCALE.get("settings_groq_get_btn", "Ottieni o visualizza le tue chiavi su console.groq.com"))
        self.lbl_current_key.config(text=LOCALE.get("settings_current_key_lbl", "Chiave Attuale:"))
        self.btn_toggle.config(text=LOCALE.get("settings_btn_hide", "Nascondi") if self.show_key else LOCALE.get("settings_btn_show", "Mostra"))
        self.btn_paste.config(text=LOCALE.get("settings_btn_paste", "Incolla dagli Appunti"))
        self.btn_clear.config(text=LOCALE.get("settings_btn_clear", "Cancella"))
        self.btn_test.config(text=LOCALE.get("settings_btn_test", "Verifica Funzionamento"))
        self.lbl_card_lang_title.config(text=LOCALE.get("settings_lang_card_title", "Lingua Interfaccia (Application Language)"))
        self.lbl_card_lang_desc.config(text=LOCALE.get("settings_lang_card_desc", "Seleziona la lingua per i menu, i pulsanti e le istruzioni dell'Editor:"))
        self.btn_close.config(text=LOCALE.get("settings_btn_close", "Chiudi"))
        self.btn_remove.config(text=LOCALE.get("settings_btn_remove_key", "Rimuovi Chiave"))
        self.btn_save.config(text=LOCALE.get("settings_btn_save", "Salva Modifiche"))

        try:
            self.context_menu.entryconfigure(0, label=LOCALE.get("settings_btn_paste", "Incolla dagli Appunti"))
            self.context_menu.entryconfigure(1, label=LOCALE.get("settings_btn_copy", "Copia"))
            self.context_menu.entryconfigure(3, label=LOCALE.get("settings_btn_clear", "Cancella"))
        except Exception:
            pass

        if get_groq_api_key() and is_key_verified():
            self.lbl_status.config(text=LOCALE.get("settings_status_ok", "✔ Funzionante! (Stato OK)"), fg="#2ecc71")

    def _select_language(self, code: str):
        self.selected_lang = code
        self._update_lang_visuals()
        LOCALE.set_language(code)
        set_language_setting(code)
        self._retranslate_ui()
        if self.on_lang_change:
            self.on_lang_change(code)

    def _update_lang_visuals(self):
        for code, btn in self.lang_buttons.items():
            btn.set_active_state(code == self.selected_lang)

    def _paste_clipboard(self):
        try:
            val = self.clipboard_get().strip()
            if val:
                self.key_var.set(val)
                self.entry_key.icursor(len(val))
                self.entry_key.focus_set()
        except Exception:
            messagebox.showwarning(LOCALE.get("settings_msg_empty_title", "Appunti Vuoti"), LOCALE.get("settings_msg_empty_desc", "Non è stato trovato alcun testo negli appunti.\nCopia prima la tua chiave e poi clicca su Incolla."), parent=self)

    def _copy_clipboard(self):
        try:
            val = self.key_var.get().strip()
            if val:
                self.clipboard_clear()
                self.clipboard_append(val)
        except Exception:
            pass

    def _toggle_visibility(self):
        self.show_key = not self.show_key
        if self.show_key:
            self.entry_key.config(show="")
            self.btn_toggle.config(text=LOCALE.get("settings_btn_hide", "Nascondi"))
        else:
            self.entry_key.config(show="*")
            self.btn_toggle.config(text=LOCALE.get("settings_btn_show", "Mostra"))

    def _test_key(self, on_done=None):
        k = self.key_var.get().strip()
        if not k:
            self.lbl_status.config(text=LOCALE.get("settings_status_no_key", "✖ Nessuna chiave inserita!"), fg="#e74c3c")
            if on_done: on_done(False)
            return

        self.btn_test.config(state="disabled")
        self.lbl_status.config(text=LOCALE.get("settings_status_checking", "Verifica in corso su Groq..."), fg="#00e5ff")

        result_box = {}

        def _bg():
            ok, msg = verify_groq_api_key(k)
            result_box["res"] = (ok, msg)

        threading.Thread(target=_bg, daemon=True).start()

        def _poll():
            if not self.winfo_exists():
                return
            if "res" in result_box:
                ok, msg = result_box["res"]
                self.btn_test.config(state="normal")
                if ok:
                    self.lbl_status.config(text=LOCALE.get("settings_status_ok", "✔ Funzionante! (Stato OK)"), fg="#2ecc71")
                else:
                    self.lbl_status.config(text=f"✖ {msg}", fg="#e74c3c")
                if on_done:
                    on_done(ok)
            else:
                self.after(80, _poll)

        self.after(80, _poll)

    def _save_key(self):
        k = self.key_var.get().strip()
        set_language_setting(self.selected_lang)
        LOCALE.set_language(self.selected_lang)
        if self.on_lang_change:
            self.on_lang_change(self.selected_lang)

        current_saved = get_groq_api_key()

        if (k == current_saved and is_key_verified()) or (not k and not current_saved):
            messagebox.showinfo(LOCALE.get("settings_msg_saved_title", "Salvato"), LOCALE.get("settings_msg_saved_desc", "Impostazioni salvate con successo!"), parent=self)
            self._on_close_modal()
            return

        if not k:
            messagebox.showwarning(LOCALE.get("settings_msg_empty_title", "Chiave Vuota"), LOCALE.get("settings_msg_empty_desc", "La chiave inserita è vuota. Se desideri rimuoverla usa 'Rimuovi Chiave'."), parent=self)
            return

        def _after_check(ok):
            if ok:
                set_groq_api_key(k, verified=True)
                messagebox.showinfo(LOCALE.get("settings_msg_saved_title", "Salvato"), LOCALE.get("settings_msg_saved_desc", "Impostazioni e Chiave API verificate e salvate con successo!\nAdam AI è pronto all'avvio."), parent=self)
                self._on_close_modal()
            else:
                messagebox.showerror(
                    LOCALE.get("settings_msg_fail_title", "Verifica Fallita"),
                    LOCALE.get("settings_msg_fail_desc", "La chiave API inserita non funziona o è stata respinta dai server Groq.\n\nVerifica di aver copiato correttamente la chiave prima di salvare."),
                    parent=self
                )
        self._test_key(on_done=_after_check)

    def _clear_key(self):
        confirm = messagebox.askyesno(LOCALE.get("settings_msg_confirm_remove_title", "Conferma Rimozione"), LOCALE.get("settings_msg_confirm_remove_desc", "Sei sicuro di voler rimuovere la chiave API?\n\nSenza una chiave API configurata, il runtime di Adam AI non potrà funzionare."), parent=self)
        if confirm:
            set_groq_api_key("")
            set_key_verified(False)
            self.key_var.set("")
            self.lbl_status.config(text=LOCALE.get("settings_status_removed", "Chiave rimossa"), fg="#e74c3c")
            messagebox.showinfo(LOCALE.get("settings_msg_remove_title", "Rimossa"), LOCALE.get("settings_msg_remove_desc", "Chiave API rimossa. Ricordati di impostarne una nuova prima di avviare l'avatar."), parent=self)


class RunOptionsModal(tk.Toplevel):
    def __init__(self, parent, on_confirm_callback, current_avatar=None):
        super().__init__(parent)
        self.on_confirm = on_confirm_callback
        self.current_avatar = current_avatar or {}
        self.prompt_path = None
        self.choice = None

        self.title("Opzioni di Avvio Adam AI")
        self.geometry("480x440")
        self.configure(bg=C_BG_MAIN)
        self.resizable(False, False)

        x = parent.winfo_x() + (parent.winfo_width() // 2) - 240
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 220
        self.geometry(f"+{max(20, x)}+{max(20, y)}")
        self.transient(parent)
        self.grab_set()

        self._build_initial_ui()

    def _build_initial_ui(self):
        self.initial_frame = tk.Frame(self, bg=C_BG_MAIN)
        self.initial_frame.pack(fill="both", expand=True, padx=35, pady=25)

        tk.Label(self.initial_frame, text="Opzioni di Avvio Adam", font=F_TITLE, bg=C_BG_MAIN, fg=C_ACCENT).pack(pady=(15, 5))
        tk.Label(self.initial_frame, text="Scegli come avviare l'assistente vocale", font=F_SMALL, bg=C_BG_MAIN, fg=C_TEXT_SUB).pack(pady=(0, 25))

        self.btn_base = ModernButton(self.initial_frame, text="Avvia solo Applicazione (Default)", command=self._choose_base, pady=12)
        self.btn_base.pack(fill="x", pady=8)

        self.btn_avatar = ModernButton(self.initial_frame, text="Avvia con Personaggio Corrente", command=self._choose_avatar, pady=12, bg="#3b3b55")
        self.btn_avatar.pack(fill="x", pady=8)

        self.setup_frame = tk.Frame(self, bg=C_BG_MAIN)

    def _choose_base(self):
        self.choice = "base"
        self.on_confirm(self.choice, {})
        self.destroy()

    def _choose_avatar(self):
        av = self.current_avatar
        has_eyes = av.get("eyes", {}).get("item") is not None
        has_lips = av.get("lips", {}).get("item") is not None
        has_nose = av.get("nose", {}).get("item") is not None

        if not (has_eyes and has_lips and has_nose):
            missing = []
            if not has_eyes: missing.append("Occhi")
            if not has_nose: missing.append("Naso")
            if not has_lips: missing.append("Bocca")
            parts_str = ", ".join(missing)
            messagebox.showwarning(
                "Parti del Viso Mancanti",
                f"Impossibile avviare con il personaggio corrente!\n\n"
                f"Non hai ancora selezionato le parti del viso essenziali ({parts_str}).\n\n"
                f"Seleziona prima le parti del viso nell'editor prima di avviare Adam.",
                parent=self
            )
            return

        self.initial_frame.pack_forget()
        self.geometry("520x590")
        self._build_setup_ui()
        self.setup_frame.pack(fill="both", expand=True, padx=25, pady=18)

    def _build_setup_ui(self):
        for w in self.setup_frame.winfo_children():
            w.destroy()

        header_frame = tk.Frame(self.setup_frame, bg=C_BG_MAIN)
        header_frame.pack(fill="x", pady=(0, 12))

        tk.Label(header_frame, text="Configurazione Personaggio Corrente", font=("Segoe UI", 13, "bold"), bg=C_BG_MAIN, fg=C_ACCENT).pack(anchor="w")
        tk.Label(header_frame, text="Collega il modello visivo alla voce neurale e al prompt di personalità", font=F_SMALL, bg=C_BG_MAIN, fg=C_TEXT_SUB).pack(anchor="w", pady=(2, 0))

        guide_card = tk.Frame(self.setup_frame, bg="#252538", padx=14, pady=11, highlightbackground="#3d3d5c", highlightthickness=1)
        guide_card.pack(fill="x", pady=(0, 14))

        tk.Label(guide_card, text="Hai bisogno di un prompt ottimizzato a zero latenza?", font=("Segoe UI", 9, "bold"), bg="#252538", fg="white").pack(anchor="w")
        tk.Label(guide_card, text="Consulta le regole tecniche vocali e scegli tra 4 template pronti all'uso.", font=("Segoe UI", 8), bg="#252538", fg=C_TEXT_SUB).pack(anchor="w", pady=(1, 8))

        g_btn = ModernButton(
            guide_card,
            text="Guida Prompt e Template Pronti",
            bg="#4834d4",
            activebackground="#5f4be8",
            command=self._open_guide,
            pady=7
        )
        g_btn.pack(fill="x")

        prompt_card = tk.Frame(self.setup_frame, bg=C_PANEL, padx=14, pady=12, highlightbackground="#3d3d5c", highlightthickness=1)
        prompt_card.pack(fill="x", pady=(0, 14))

        p_header_row = tk.Frame(prompt_card, bg=C_PANEL)
        p_header_row.pack(fill="x", pady=(0, 8))

        tk.Label(p_header_row, text="File Prompt del Personaggio (.txt)", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white").pack(side="left")

        self.status_pill_frame = tk.Frame(p_header_row, bg="#1a1a28", padx=8, pady=2)
        self.status_pill_frame.pack(side="right")
        self.lbl_prompt_status = tk.Label(self.status_pill_frame, text="Nessun file selezionato (Richiesto)", font=("Segoe UI", 8, "bold"), bg="#1a1a28", fg="#f39c12")
        self.lbl_prompt_status.pack()

        prompt_btn_row = tk.Frame(prompt_card, bg=C_PANEL)
        prompt_btn_row.pack(fill="x", pady=(0, 8))

        self.btn_sel_prompt = ModernButton(prompt_btn_row, text="Sfoglia file .txt...", command=self._sel_prompt, pady=7)
        self.btn_sel_prompt.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_sample = ModernButton(prompt_btn_row, text="Usa Esempio IT", command=self._use_sample_prompt, pady=7, bg="#3b3b55")
        self.btn_sample.pack(side="left", padx=(0, 6))

        self.btn_clear = ModernButton(prompt_btn_row, text="Rimuovi", command=self._clear_prompt, pady=7, padx=10, bg="#4a2a2a", activebackground="#613333")
        self.btn_clear.pack(side="left")

        tk.Label(prompt_card, text="Regola base attiva: le risposte dell'avatar sono tassativamente limitate a max 20 parole.", font=("Segoe UI", 8, "italic"), bg=C_PANEL, fg="#00cec9").pack(anchor="w")

        voice_card = tk.Frame(self.setup_frame, bg=C_PANEL, padx=14, pady=12, highlightbackground="#3d3d5c", highlightthickness=1)
        voice_card.pack(fill="x", pady=(0, 18))

        tk.Label(voice_card, text="Parametri Voce e Lingua", font=("Segoe UI", 9, "bold"), bg=C_PANEL, fg="white").pack(anchor="w", pady=(0, 8))

        v_grid = tk.Frame(voice_card, bg=C_PANEL)
        v_grid.pack(fill="x")
        v_grid.columnconfigure(0, weight=1)
        v_grid.columnconfigure(1, weight=1)

        f_lang = tk.Frame(v_grid, bg=C_PANEL)
        f_lang.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        tk.Label(f_lang, text="Lingua:", font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB).pack(anchor="w")
        self.combo_lang = ttk.Combobox(f_lang, values=["Italiano", "Inglese"], state="readonly")
        self.combo_lang.set("Italiano")
        self.combo_lang.pack(fill="x", pady=(3, 0))

        f_voice = tk.Frame(v_grid, bg=C_PANEL)
        f_voice.grid(row=0, column=1, padx=(8, 0), sticky="ew")
        tk.Label(f_voice, text="Timbro Voce:", font=F_SMALL, bg=C_PANEL, fg=C_TEXT_SUB).pack(anchor="w")
        self.combo_gender = ttk.Combobox(f_voice, values=["Maschio", "Femmina"], state="readonly")
        self.combo_gender.set("Maschio")
        self.combo_gender.pack(fill="x", pady=(3, 0))

        btn_action_box = tk.Frame(self.setup_frame, bg=C_BG_MAIN)
        btn_action_box.pack(fill="x")

        ModernButton(btn_action_box, text="Indietro", bg="#3a3a50", activebackground="#4a4a62", command=self._back_to_initial, pady=10, padx=20).pack(side="left", padx=(0, 10))
        self.btn_confirm = ModernButton(btn_action_box, text="Conferma e Avvia", bg="#27ae60", activebackground="#2ecc71", command=self._confirm_avatar, pady=10)
        self.btn_confirm.pack(side="left", fill="x", expand=True)

    def _open_guide(self):
        PromptGuideModal(self, on_apply=self._set_selected_prompt)

    def _set_selected_prompt(self, path):
        if path and os.path.exists(path):
            self.prompt_path = path
            fname = os.path.basename(path)
            self.btn_sel_prompt.config(text=f"File: {fname}", bg="#27ae60", fg="white")
            self.lbl_prompt_status.config(text=f"Caricato: {fname}", fg="#2ecc71")

    def _sel_prompt(self):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], title="Seleziona Prompt")
        if f:
            self._set_selected_prompt(f)

    def _use_sample_prompt(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        sample_p = os.path.join(root_dir, "runtime", "prompt", "exampleIT.txt")
        if os.path.exists(sample_p):
            self._set_selected_prompt(sample_p)
        else:
            messagebox.showinfo("Esempio non trovato", f"File non trovato in: {sample_p}")

    def _clear_prompt(self):
        self.prompt_path = None
        self.btn_sel_prompt.config(text="Sfoglia file .txt...", bg=C_BTN_NORM, fg="white")
        self.lbl_prompt_status.config(text="Nessun file selezionato (Richiesto)", fg="#f39c12")

    def _back_to_initial(self):
        self.setup_frame.pack_forget()
        self.geometry("480x440")
        self.initial_frame.pack(fill="both", expand=True, padx=35, pady=25)

    def _confirm_avatar(self):
        av = self.current_avatar
        has_eyes = av.get("eyes", {}).get("item") is not None
        has_lips = av.get("lips", {}).get("item") is not None
        has_nose = av.get("nose", {}).get("item") is not None
        if not (has_eyes and has_lips and has_nose):
            messagebox.showwarning(
                "Parti del Viso Mancanti",
                "Non hai ancora selezionato le parti del viso essenziali (Occhi, Naso e Bocca). Configurale prima nell'editor!",
                parent=self
            )
            return

        if not self.prompt_path:
            messagebox.showwarning(
                "Prompt Richiesto",
                "Per avviare con il personaggio corrente devi selezionare un file prompt (.txt)!\n\n"
                "Suggerimento:\n"
                "• Clicca sul pulsante 'Guida Prompt e Template Pronti' per usare un template pronto.\n"
                "• Oppure clicca su 'Usa Esempio IT' per caricare il prompt di prova."
            )
            return

        self.choice = "avatar"
        lang = "it" if self.combo_lang.get() == "Italiano" else "en"
        gender = "male" if self.combo_gender.get() == "Maschio" else "female"

        params = {
            "lang": lang,
            "gender": gender,
            "prompt_path": self.prompt_path
        }
        self.on_confirm(self.choice, params)
        self.destroy()


class AdamCreatorApp:
    def __init__(self, root: tk.Tk, initial_profile: Optional[str] = None):
        self.root = root
        self._resize_job = None
        self.initial_profile = initial_profile

        self._init_window()

        saved_lang = get_language()
        if saved_lang:
            LOCALE.set_language(saved_lang)

        self.manager = AssetManager()
        self.current_cat_enum = LAYER_ORDER[0]
        self.renderer: Optional[PreviewRenderer] = None

        self.cat_btns: Dict[str, ModernButton] = {}
        self.icons_cache: Dict[str, tk.PhotoImage] = {}
        self.help_window: Optional[HelpModal] = None

        self.is_animating = False
        self.anim_state = {}
        self.jobs = {"sequence": None}
        self.sequence_data = []

        self.undo_stack: List[dict] = []
        self.redo_stack: List[dict] = []
        self.max_history = 50

        self.root.bind_all("<Control-z>", lambda e: self._undo())
        self.root.bind_all("<Control-Z>", lambda e: self._undo())
        self.root.bind_all("<Control-y>", lambda e: self._redo())
        self.root.bind_all("<Control-Y>", lambda e: self._redo())
        self.root.bind_all("<Control-Shift-Z>", lambda e: self._redo())
        self.root.bind_all("<Control-Shift-z>", lambda e: self._redo())

        self._grid_token = 0
        self._thumb_queue = queue.Queue()
        self._thumb_photo_cache: Dict[tuple, tk.PhotoImage] = {}
        self._pending_futures = set()

        workers = max(2, (os.cpu_count() or 4) // 2)
        self._thumb_executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

        self._style_setup()
        self._layout_setup()

        self.renderer = PreviewRenderer(self.preview_canvas, self.manager.current_assets_path)
        self._loading_thumb = self._make_placeholder_thumb(loading=True)
        self._blank_thumb = pil_to_photo(generate_thumb_pil(self.manager.current_assets_path, "base", None))

        self.root.after(30, self._process_thumb_queue)
        if not is_onboarding_completed():
            self.root.after(150, self._show_welcome_onboarding)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        base_val = self.current_cat_enum.value
        self.manager.set_color(base_val, "skin_1")
        self.root.update_idletasks()
        self._refresh_grid(reset_scroll=True)
        self._draw_palette()
        self._apply_background_color(self.manager.background_color)
        self.renderer.render(self.manager.current_avatar)
        self._update_ui_text()
        self._update_bg_swatches()
        self._update_undo_redo_buttons()

        if self.initial_profile and os.path.exists(self.initial_profile):
            try:
                if self.manager.load_profile(self.initial_profile):
                    self._apply_background_color(self.manager.background_color)
                    self._update_bg_swatches()
                    self.renderer.render(self.manager.current_avatar)
                    self._refresh_grid(reset_scroll=False)
                    self._draw_palette()
            except Exception as e:
                print(f"Error loading initial profile: {e}")

    def _init_window(self):
        self.root.title(APP_NAME)
        self.root.geometry(WINDOW_SIZE)
        self.root.configure(bg=C_BG_MAIN)

        try:
            self.root.state("zoomed")
        except tk.TclError:
            try:
                self.root.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _style_setup(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Vertical.TScrollbar",
            gripcount=0, background=C_SIDEBAR,
            troughcolor=C_PANEL, bordercolor=C_PANEL,
            arrowcolor=C_TEXT_MAIN
        )

    def _layout_setup(self) -> None:
        header = tk.Frame(self.root, bg=C_BG_MAIN, height=80)
        header.pack(fill="x", padx=20)
        header.pack_propagate(False)

        self._build_header_left(header)
        self._build_header_center(header)
        self._build_header_right(header)

        body = tk.Frame(self.root, bg=C_BG_MAIN)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._build_sidebar(body)
        self._build_center_panel(body)
        self._build_right_panel(body)

    def _build_header_left(self, parent):
        frame = tk.Frame(parent, bg=C_BG_MAIN, width=280)
        frame.pack(side="left", fill="y")
        frame.pack_propagate(False)

        container = tk.Frame(frame, bg=C_BG_MAIN)
        container.place(relx=0, rely=0.5, anchor="w")
        self.lbl_title = tk.Label(container, text="", font=F_HEADER, bg=C_BG_MAIN, fg=C_TEXT_MAIN)
        self.lbl_title.pack(side="left")
        self.lbl_subtitle = tk.Label(container, text="", font=F_HEADER, bg=C_BG_MAIN, fg=C_ACCENT)
        self.lbl_subtitle.pack(side="left", padx=5)

    def _build_header_center(self, parent):
        frame = tk.Frame(parent, bg=C_BG_MAIN, width=480)
        frame.pack(side="left", fill="y", padx=(20, 0))
        frame.pack_propagate(False)

        self.btn_import = ModernButton(
            frame, text="", bg="#6c5ce7", fg="white",
            font=("Segoe UI", 11, "bold"), padx=25, pady=8,
            activebackground="#5f3dc4", command=self._on_import_json
        )
        self.btn_import.place(relx=0.5, rely=0.5, anchor="center")

    def _build_header_right(self, parent):
        frame = tk.Frame(parent, bg=C_BG_MAIN)
        frame.pack(side="left", fill="both", expand=True)

        tools = tk.Frame(frame, bg=C_BG_MAIN, width=600, height=44)
        tools.place(relx=0.5, rely=0.5, anchor="center")
        tools.grid_propagate(False)
        tools.rowconfigure(0, weight=1)
        for i in range(3): tools.columnconfigure(i, weight=1)

        self.btn_help = ModernButton(tools, text="", bg="#3a3a50", command=self._on_help, font=F_BTN, padx=12, pady=8)
        self.btn_help.grid(row=0, column=0, sticky="nsew", padx=4)

        self.btn_export = ModernButton(tools, text="", bg="#2980b9", command=self._on_export_png, font=F_BTN, padx=12, pady=8)
        self.btn_export.grid(row=0, column=1, sticky="nsew", padx=4)

        self.btn_save = ModernButton(tools, text="", bg=C_ACCENT, command=self._on_save_json, font=F_BTN, padx=12, pady=8, activeforeground="white")
        self.btn_save.grid(row=0, column=2, sticky="nsew", padx=4)

        self.btn_settings = ModernButton(
            frame, text="⚙", bg="#3a3a50",
            command=self._on_settings, font=("Segoe UI Symbol", 12), padx=10, pady=5
        )
        self.btn_settings.pack(side="right", padx=0)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=C_SIDEBAR, width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.lbl_cats_header = tk.Label(sidebar, text="", bg=C_SIDEBAR, fg=C_TEXT_SUB, font=("Segoe UI", 10, "bold"))
        self.lbl_cats_header.pack(pady=(15, 6))

        for cat in LAYER_ORDER:
            val = cat.value
            icon = generate_solid_icon(val)
            self.icons_cache[val] = icon

            btn = ModernButton(
                sidebar, text="", image=icon, compound="left",
                anchor="w", padx=16, pady=9, font=F_BTN,
                command=lambda c=cat: self._change_cat(c)
            )
            btn.pack(fill="x", pady=2, padx=10)
            self.cat_btns[val] = btn

        self.cat_btns[LAYER_ORDER[0].value].set_active_state(True)

        actions = tk.Frame(sidebar, bg=C_SIDEBAR)
        actions.pack(side="bottom", fill="x", padx=10, pady=(0, 15))
        actions.columnconfigure((0, 1), weight=1)

        self.btn_random = ModernButton(actions, text="", bg="#34344a", command=self._on_random, font=F_BTN, pady=9)
        self.btn_random.grid(row=1, column=0, sticky="ew", padx=(0, 3))

        self.btn_reset = ModernButton(actions, text="", bg=C_DANGER, command=self._on_reset, font=F_BTN, pady=9)
        self.btn_reset.grid(row=1, column=1, sticky="ew", padx=(3, 0))

        self.hist_card = tk.Frame(sidebar, bg="#1e1e2e", highlightbackground="#363654", highlightthickness=1)
        self.hist_card.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        self.lbl_hist = tk.Label(
            self.hist_card, text=LOCALE.get("lbl_history", "CRONOLOGIA"),
            font=("Segoe UI", 8, "bold"), bg="#1e1e2e", fg="#8888aa"
        )
        self.lbl_hist.pack(anchor="w", padx=10, pady=(7, 4))

        hist_btn_box = tk.Frame(self.hist_card, bg="#1e1e2e")
        hist_btn_box.pack(fill="x", padx=8, pady=(0, 8))
        hist_btn_box.columnconfigure(0, weight=1)
        hist_btn_box.columnconfigure(1, weight=1)

        self.btn_undo = ModernButton(
            hist_btn_box, text=f"{LOCALE.get('btn_undo', '↶ ANNULLA')}\nCtrl+Z",
            bg="#2b2d42", activebackground="#3e4062", fg="#00e5ff",
            disabledforeground="#52526a",
            command=self._undo, font=("Segoe UI", 8, "bold"), pady=6
        )
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.btn_redo = ModernButton(
            hist_btn_box, text=f"{LOCALE.get('btn_redo', '↷ RIPRISTINA')}\nCtrl+Y",
            bg="#2b2d42", activebackground="#3e4062", fg="#00e5ff",
            disabledforeground="#52526a",
            command=self._redo, font=("Segoe UI", 8, "bold"), pady=6
        )
        self.btn_redo.grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def _build_center_panel(self, parent):
        center = tk.Frame(parent, bg=C_PANEL, width=480)
        center.pack(side="left", fill="y", padx=20)
        center.pack_propagate(False)

        self.lbl_options_title = tk.Label(center, text="", bg=C_PANEL, fg=C_TEXT_MAIN, font=F_TITLE)
        self.lbl_options_title.pack(pady=(20, 10), padx=25, anchor="w")

        scroll_cont = tk.Frame(center, bg=C_PANEL)
        scroll_cont.pack(side="top", fill="both", expand=True, padx=15, pady=(0, 5))

        self.canvas_scroll = tk.Canvas(scroll_cont, bg=C_PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(scroll_cont, orient="vertical", command=self.canvas_scroll.yview, style="Vertical.TScrollbar")

        self.grid_container = tk.Frame(self.canvas_scroll, bg=C_PANEL)
        self.grid_container.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))
        self.canvas_scroll.create_window((0, 0), window=self.grid_container, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=sb.set)

        self.canvas_scroll.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas_scroll.bind_all("<MouseWheel>", self._on_mousewheel)

        pal_cont = tk.Frame(center, bg=C_PANEL, height=90)
        pal_cont.pack(side="bottom", fill="x", padx=25, pady=15)
        pal_cont.pack_propagate(False)

        self.lbl_colors_title = tk.Label(pal_cont, text="", bg=C_PANEL, fg=C_TEXT_SUB, font=("Segoe UI", 9, "bold"))
        self.lbl_colors_title.pack(anchor="w", pady=(0, 5))

        self.palette_frame = tk.Frame(pal_cont, bg=C_PANEL)
        self.palette_frame.pack(fill="both", expand=True)

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=C_SIDEBAR)
        right.pack(side="right", fill="both", expand=True)

        self.lbl_preview_title = tk.Label(right, text="", bg=C_SIDEBAR, fg=C_TEXT_SUB, font=("Segoe UI", 10, "bold"))
        self.lbl_preview_title.pack(pady=(20, 10))

        border = tk.Frame(right, bg=C_ACCENT, padx=2, pady=2)
        border.pack(fill="both", expand=True, padx=20, pady=10)

        self.preview_canvas = tk.Canvas(border, bg="white", highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", self._on_preview_resize)

        self.lbl_centering = tk.Label(right, text="", bg=C_SIDEBAR, fg=C_ACCENT, font=F_SMALL)
        self.lbl_centering.pack(pady=(2, 4))

        bg_card = tk.Frame(right, bg="#1a1a28", highlightbackground="#363654", highlightthickness=1)
        bg_card.pack(fill="x", padx=35, pady=(0, 8))

        bg_header = tk.Frame(bg_card, bg="#1a1a28")
        bg_header.pack(fill="x", padx=10, pady=(5, 3))

        self.lbl_bg_title = tk.Label(
            bg_header, text=LOCALE.get("lbl_bg_color", "COLORE SFONDO"),
            font=("Segoe UI", 8, "bold"), bg="#1a1a28", fg="#8888aa"
        )
        self.lbl_bg_title.pack(side="left")

        self.lbl_bg_hex = tk.Label(
            bg_header, text=self.manager.background_color.upper(),
            font=("Consolas", 8, "bold"), bg="#1a1a28", fg="#00e5ff"
        )
        self.lbl_bg_hex.pack(side="right")

        self.bg_swatches_frame = tk.Frame(bg_card, bg="#1a1a28")
        self.bg_swatches_frame.pack(fill="x", padx=8, pady=(0, 6))
        self._build_bg_swatches()

        btn_container = tk.Frame(right, bg=C_SIDEBAR)
        btn_container.pack(fill="x", padx=40, pady=(0, 15))
        btn_container.columnconfigure(0, weight=1, uniform="bottom_btns")
        btn_container.columnconfigure(1, weight=1, uniform="bottom_btns")

        self.anim_btn = ModernButton(btn_container, text="", bg="#e67e22", command=self._toggle_animation, font=F_BTN, pady=12)
        self.anim_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.run_btn = ModernButton(btn_container, text="", bg="#2ecc71", activebackground="#27ae60", command=self._run_runtime, font=F_BTN, pady=12)
        self.run_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def _build_bg_swatches(self):
        for w in self.bg_swatches_frame.winfo_children():
            w.destroy()

        self.bg_swatch_widgets = {}

        for hex_code, name in BG_COLOR_PRESETS:
            is_active = (self.manager.background_color.upper() == hex_code.upper())
            border_color = "#00e5ff" if is_active else "#363654"
            container = tk.Frame(self.bg_swatches_frame, bg=border_color, padx=2, pady=2)
            container.pack(side="left", padx=2)

            btn = tk.Button(
                container, bg=hex_code, width=2, height=1,
                activebackground=hex_code, relief="flat", bd=0, cursor="hand2",
                command=lambda c=hex_code: self._select_background_color(c)
            )
            btn.pack()
            self.bg_swatch_widgets[hex_code.upper()] = container

        self.btn_custom_bg = ModernButton(
            self.bg_swatches_frame,
            text=LOCALE.get("btn_custom_color", "Altro 🎨"),
            bg="#2d2d44", activebackground="#3e3e5e", fg="#ffffff",
            font=("Segoe UI", 8, "bold"), padx=8, pady=3,
            command=self._on_custom_bg_color
        )
        self.btn_custom_bg.pack(side="left", padx=(6, 0))

    def _update_bg_swatches(self):
        curr = self.manager.background_color.upper()
        if hasattr(self, "lbl_bg_hex") and self.lbl_bg_hex:
            self.lbl_bg_hex.config(text=curr)
        if hasattr(self, "bg_swatch_widgets"):
            for hex_code, container in self.bg_swatch_widgets.items():
                is_active = (curr == hex_code)
                border_color = "#00e5ff" if is_active else "#363654"
                try:
                    container.configure(bg=border_color)
                except Exception:
                    pass

    def _select_background_color(self, hex_color: str):
        if not hex_color or hex_color.upper() == self.manager.background_color.upper():
            return
        self._push_undo_state()
        self.manager.background_color = hex_color
        self._apply_background_color(hex_color)
        self._update_bg_swatches()
        self._update_undo_redo_buttons()

    def _on_custom_bg_color(self):
        color = colorchooser.askcolor(
            color=self.manager.background_color,
            title="Scegli Colore di Sfondo"
        )[1]
        if color:
            self._select_background_color(color)

    def _apply_background_color(self, hex_color: str):
        try:
            self.preview_canvas.configure(bg=hex_color)
        except Exception:
            pass
        if self.renderer:
            self.renderer.set_background_color(hex_color)
        if hasattr(self, "lbl_bg_hex") and self.lbl_bg_hex:
            self.lbl_bg_hex.config(text=hex_color.upper())

    def _on_preview_resize(self, event):
        if not self.renderer: 
            return

        if self._resize_job:
            self.root.after_cancel(self._resize_job)

        self._resize_job = self.root.after(150, lambda: self.renderer.set_canvas_size(event.width, event.height))

    def _make_placeholder_thumb(self, loading=True) -> tk.PhotoImage:
        img = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([6, 6, 94, 94], radius=12, outline="#777777", width=2)
        if loading:
            for x in (40, 50, 60):
                d.ellipse([x - 3, 50 - 3, x + 3, 50 + 3], fill="#777777")
        return ImageTk.PhotoImage(img)

    def _submit_thumb_job(self, btn: tk.Button, cat_key: str, item_name: str, token: int):
        base_dir = self.manager.current_assets_path
        future = self._thumb_executor.submit(generate_thumb_pil, base_dir, cat_key, item_name)
        self._pending_futures.add(future)

        def _on_done(f):
            self._pending_futures.discard(f)
            try:
                img = f.result()
            except Exception:
                img = None
            self._thumb_queue.put((token, btn, str(base_dir), cat_key, item_name, img))

        future.add_done_callback(_on_done)

    def _process_thumb_queue(self):
        try:
            while True:
                token, btn, b_dir, cat, item, img = self._thumb_queue.get_nowait()
                if token != self._grid_token or not btn.winfo_exists() or img is None:
                    continue

                key = (b_dir, cat, item or "")
                if key not in self._thumb_photo_cache:
                    self._thumb_photo_cache[key] = pil_to_photo(img)

                photo = self._thumb_photo_cache[key]
                btn.configure(image=photo)
                btn.image = photo
        except queue.Empty:
            pass

        if self.root.winfo_exists():
            self.root.after(30, self._process_thumb_queue)

    def _cancel_thumb_jobs(self):
        for f in list(self._pending_futures):
            f.cancel()
        self._pending_futures.clear()

    def _on_mousewheel(self, event):
        for modal_attr in ["help_window", "settings_window"]:
            w = getattr(self, modal_attr, None)
            if w and w.winfo_exists():
                return "break"

        bbox = self.canvas_scroll.bbox("all")
        if not bbox:
            return "break"

        content_height = bbox[3] - bbox[1]
        canvas_height = self.canvas_scroll.winfo_height()

        if content_height <= canvas_height:
            if self.canvas_scroll.canvasy(0) != 0:
                self.canvas_scroll.yview_moveto(0)
            return "break"

        delta = int(-1 * (event.delta / 120))
        y0, y1 = self.canvas_scroll.yview()

        if delta < 0 and (y0 <= 0 or self.canvas_scroll.canvasy(0) <= 0):
            self.canvas_scroll.yview_moveto(0)
            return "break"

        if delta > 0 and y1 >= 1.0:
            return "break"

        self.canvas_scroll.yview_scroll(delta, "units")

        if self.canvas_scroll.canvasy(0) < 0:
            self.canvas_scroll.yview_moveto(0)

        return "break"

    def _on_close(self):
        self._thumb_executor.shutdown(wait=False)
        self.renderer.clear_caches()
        if self.jobs.get("sequence"):
            self.root.after_cancel(self.jobs["sequence"])
            self.jobs["sequence"] = None
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
            self._resize_job = None
        self.root.destroy()

    def _update_ui_text(self):
        self.lbl_title.config(text=LOCALE.get("header_title"))
        self.lbl_subtitle.config(text=LOCALE.get("header_subtitle"))
        self.btn_import.config(text=LOCALE.get("btn_import"))
        self.btn_help.config(text=LOCALE.get("btn_help"))
        self.btn_export.config(text=LOCALE.get("btn_export"))
        self.btn_save.config(text=LOCALE.get("btn_save_json"))
        self.lbl_cats_header.config(text=LOCALE.get("lbl_categories"))
        if hasattr(self, "lbl_hist") and self.lbl_hist:
            self.lbl_hist.config(text=LOCALE.get("lbl_history", "CRONOLOGIA"))
        if hasattr(self, "btn_undo") and self.btn_undo:
            undo_label = LOCALE.get("btn_undo", "↶ ANNULLA")
            self.btn_undo.config(text=f"{undo_label}\nCtrl+Z")
        if hasattr(self, "btn_redo") and self.btn_redo:
            redo_label = LOCALE.get("btn_redo", "↷ RIPRISTINA")
            self.btn_redo.config(text=f"{redo_label}\nCtrl+Y")
        self.btn_random.config(text=LOCALE.get("btn_random"))
        self.btn_reset.config(text=LOCALE.get("btn_reset"))

        for cat_str, btn in self.cat_btns.items():
            t_cat = LOCALE.get(f"cat_{cat_str}")
            btn.config(text=f"  {t_cat}")

        current_val = self.current_cat_enum.value
        cat_display = LOCALE.get(f"cat_{current_val}")
        self.lbl_options_title.config(text=f"{LOCALE.get('lbl_options')}{cat_display}")
        self.lbl_colors_title.config(text=LOCALE.get("lbl_colors"))
        self.lbl_preview_title.config(text=LOCALE.get("lbl_preview"))
        self.lbl_centering.config(text=LOCALE.get("lbl_centering"))
        if hasattr(self, "lbl_bg_title") and self.lbl_bg_title:
            self.lbl_bg_title.config(text=LOCALE.get("lbl_bg_color", "COLORE SFONDO"))
        if hasattr(self, "btn_custom_bg") and self.btn_custom_bg:
            self.btn_custom_bg.config(text=LOCALE.get("btn_custom_color", "Altro 🎨"))

        anim_txt = "btn_anim_stop" if self.is_animating else "btn_anim_start"
        self.anim_btn.config(text=LOCALE.get(anim_txt))
        if hasattr(self, 'run_btn'):
            self.run_btn.config(text=LOCALE.get("btn_run_runtime"))
        self._draw_palette()

    def _set_lang(self, code: str):
        LOCALE.set_language(code)
        set_language_setting(code)
        self._update_ui_text()

    def _change_cat(self, cat_enum: Cat) -> None:
        self.current_cat_enum = cat_enum
        val = cat_enum.value

        for c_str, btn in self.cat_btns.items():
            btn.set_active_state(c_str == val)

        cat_name = LOCALE.get(f"cat_{val}")
        self.lbl_options_title.config(text=f"{LOCALE.get('lbl_options')}{cat_name}")

        self._refresh_grid(reset_scroll=True)
        self._draw_palette()

    def _refresh_grid(self, reset_scroll: bool = False) -> None:
        self._grid_token += 1
        self._cancel_thumb_jobs()
        self._thumb_photo_cache.clear()

        with self._thumb_queue.mutex:
            self._thumb_queue.queue.clear()

        for w in self.grid_container.winfo_children():
            w.destroy()

        if reset_scroll:
            self.canvas_scroll.yview_moveto(0)

        cat_key = self.current_cat_enum.value

        items = self.manager.assets.get(cat_key, [])

        card_list = []
        if cat_key != "base":
            card_list.append((None, "NONE"))

        for item in items:
            text = item.split("/")[-1] if (cat_key == "hair" and "/" in item) else item
            card_list.append((item, text))

        cols = 3
        batch_size = 18

        def _load_batch(start_idx):
            if self._grid_token != token:
                return

            end_idx = min(start_idx + batch_size, len(card_list))
            for i in range(start_idx, end_idx):
                r, c = divmod(i, cols)
                item_name, display_text = card_list[i]
                self._create_grid_card(item_name, display_text, r, c, self._grid_token)

            self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all"))

            if end_idx < len(card_list):
                self.root.after(10, lambda: _load_batch(end_idx))

        token = self._grid_token
        _load_batch(0)

    def _create_grid_card(self, item_name: str | None, text: str, r: int, c: int, token: int):
        cat_key = self.current_cat_enum.value
        current_sel = self.manager.current_avatar[cat_key]["item"]
        is_selected = (current_sel == item_name)

        border_col = C_ACCENT if is_selected else C_PANEL
        frame = tk.Frame(self.grid_container, bg=border_col, padx=2, pady=2)
        frame.grid(row=r, column=c, padx=8, pady=8)
        frame.item_id = item_name

        display_txt = (text[:10] if text else "None")
        thumb = self._blank_thumb if item_name is None else self._loading_thumb

        btn = tk.Button(
            frame, image=thumb, text=display_txt, compound="top",
            bg=C_CARD_BG, fg="#333", font=("Segoe UI", 8, "bold"),
            relief="flat", bd=0, width=110, height=115, cursor="hand2",
            command=lambda i=item_name: self._select_item(i)
        )
        btn.image = thumb
        btn.pack()

        if item_name:
            self._submit_thumb_job(btn, cat_key, item_name, token)

    def _update_selection_visuals(self):
        cat_key = self.current_cat_enum.value
        current_sel = self.manager.current_avatar[cat_key]["item"]

        for frame in self.grid_container.winfo_children():
            if hasattr(frame, "item_id"):
                target_color = C_ACCENT if frame.item_id == current_sel else C_PANEL
                if frame["bg"] != target_color:
                    frame.configure(bg=target_color)


    def _get_current_snapshot(self) -> dict:
        return {
            "avatar": copy.deepcopy(self.manager.current_avatar),
            "background_color": self.manager.background_color
        }

    def _push_undo_state(self) -> None:
        snapshot = self._get_current_snapshot()
        if self.undo_stack and self.undo_stack[-1] == snapshot:
            return
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self._update_undo_redo_buttons()

    def _undo(self) -> None:
        if not self.undo_stack:
            return
        current_state = self._get_current_snapshot()
        self.redo_stack.append(current_state)
        prev_state = self.undo_stack.pop()
        self._restore_state(prev_state)
        self._update_undo_redo_buttons()

    def _redo(self) -> None:
        if not self.redo_stack:
            return
        current_state = self._get_current_snapshot()
        self.undo_stack.append(current_state)
        next_state = self.redo_stack.pop()
        self._restore_state(next_state)
        self._update_undo_redo_buttons()

    def _restore_state(self, state: dict) -> None:
        self.manager.current_avatar = copy.deepcopy(state["avatar"])
        bg_col = state.get("background_color", "#ffffff")
        self.manager.background_color = bg_col
        self._apply_background_color(bg_col)
        self._update_bg_swatches()
        if self.is_animating:
            self._toggle_animation()
        self.renderer.render(self.manager.current_avatar)
        self._update_selection_visuals()
        self._draw_palette()

    def _update_undo_redo_buttons(self) -> None:
        can_undo = len(self.undo_stack) > 0
        if hasattr(self, "btn_undo") and self.btn_undo:
            if can_undo:
                self.btn_undo.config(state="normal", cursor="hand2")
                self.btn_undo.update_colors(bg="#2b2d42", activebackground="#3e4062", fg="#00e5ff")
            else:
                self.btn_undo.config(state="disabled", cursor="arrow")
                self.btn_undo.update_colors(bg="#181824", activebackground="#181824", fg="#52526a")

        can_redo = len(self.redo_stack) > 0
        if hasattr(self, "btn_redo") and self.btn_redo:
            if can_redo:
                self.btn_redo.config(state="normal", cursor="hand2")
                self.btn_redo.update_colors(bg="#2b2d42", activebackground="#3e4062", fg="#00e5ff")
            else:
                self.btn_redo.config(state="disabled", cursor="arrow")
                self.btn_redo.update_colors(bg="#181824", activebackground="#181824", fg="#52526a")


    def _select_item(self, item_name: str | None):
        self._push_undo_state()
        cat = self.current_cat_enum.value
        self.manager.set_smart_item(cat, item_name)

        if self.is_animating:
            self._toggle_animation()

        self.renderer.render(self.manager.current_avatar)
        self._update_selection_visuals()
        self._draw_palette()

    def _draw_palette(self):
        for w in self.palette_frame.winfo_children(): w.destroy()

        cat = self.current_cat_enum.value
        curr_item = self.manager.current_avatar[cat]["item"]

        if not curr_item:
            tk.Label(self.palette_frame, text=LOCALE.get("msg_select_item"), bg=C_PANEL, fg=C_TEXT_SUB).pack(pady=10)
            return

        colors = self.manager.get_colors_for_shape(cat, curr_item)
        active_col = self.manager.current_avatar[cat]["color"]
        valid_colors = [c for c in colors if c != "default"]

        if not valid_colors:
            tk.Label(self.palette_frame, text=LOCALE.get("msg_no_colors"), bg=C_PANEL, fg=C_TEXT_SUB).pack(pady=10)
            return

        for col_name in valid_colors:
            hex_val = color_to_hex(col_name)
            is_active = (col_name == active_col)

            b_col = "white" if is_active else C_PANEL
            b_size = 2 if is_active else 0

            cont = tk.Frame(self.palette_frame, bg=b_col, padx=b_size, pady=b_size)
            cont.pack(side="left", padx=5, pady=5)

            btn = tk.Button(
                cont, bg=hex_val, width=4, height=1,
                activebackground=hex_val, relief="flat", cursor="hand2",
                command=lambda c=col_name: self._on_color_click(c)
            )
            btn.pack()

    def _on_color_click(self, color_name: str):
        self._push_undo_state()
        self.manager.set_color(self.current_cat_enum.value, color_name)
        if self.is_animating: self._toggle_animation()
        self.renderer.render(self.manager.current_avatar)
        self._draw_palette()

    def _on_random(self):
        self._push_undo_state()
        if self.is_animating: self._toggle_animation()
        self.manager.randomize(OPTIONAL_CATS)
        self.renderer.render(self.manager.current_avatar)
        self._refresh_grid(reset_scroll=False)
        self._draw_palette()

    def _on_reset(self):
        self._push_undo_state()
        if self.is_animating: self._toggle_animation()
        self.manager.reset_all()
        self._apply_background_color(self.manager.background_color)
        self._update_bg_swatches()
        self.renderer.render(self.manager.current_avatar)
        self._refresh_grid(reset_scroll=True)
        self._draw_palette()

    def _on_save_json(self):
        av = self.manager.current_avatar
        has_eyes = av.get("eyes", {}).get("item") is not None
        has_lips = av.get("lips", {}).get("item") is not None
        has_nose = av.get("nose", {}).get("item") is not None

        has_brows = av.get("eyebrows", {}).get("item") is not None
        has_hair = av.get("hair", {}).get("item") is not None

        if not (has_eyes and has_lips and has_nose):
            messagebox.showerror(LOCALE.get("msg_error_title"), LOCALE.get("msg_save_error_desc"))
            return

        if not (has_brows and has_hair):
            proceed = messagebox.askyesno(LOCALE.get("msg_profile_incomplete_title"), LOCALE.get("msg_profile_incomplete_desc"))
            if not proceed:
                return

        curr_gender = getattr(self.manager, "gender", "male")
        curr_lang = getattr(self.manager, "language", "it")
        modal = SaveOptionsModal(self.root, current_gender=curr_gender, current_lang=curr_lang)
        self.root.wait_window(modal)

        if not modal.confirmed:
            return

        chosen_lang = modal.selected_lang
        chosen_gender = modal.selected_gender
        chosen_voice_mode = modal.voice_mode.get()
        temp_wav_path = modal.temp_voice_file
        ref_text = modal.final_ref_text

        json_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="avatar.json",
            title=LOCALE.get("btn_save_json")
        )

        if not json_path:
            return

        success = self.manager.save(
            json_path,
            language=chosen_lang,
            gender=chosen_gender,
            voice_mode="predefined",
            temp_recording_path=None,
            dest_wav_path=None,
            voice_ref_text=""
        )

        if success:
            info_msg = f"{LOCALE.get('msg_saved_desc')}{os.path.basename(json_path)}\n\n"
            info_msg += f"✔ Language: {chosen_lang.upper()}\n"
            info_msg += f"✔ Voice: Predefined ({chosen_gender.capitalize()})"
            messagebox.showinfo(LOCALE.get("msg_saved_title"), info_msg)

    def _on_import_json(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], title=LOCALE.get("msg_import_title"))
        if f:
            if self.is_animating: self._toggle_animation()
            self._push_undo_state()
            if self.manager.load_profile(f):
                self._apply_background_color(self.manager.background_color)
                self._update_bg_swatches()
                self.renderer.render(self.manager.current_avatar)
                self._refresh_grid(reset_scroll=False)
                self._draw_palette()
                messagebox.showinfo(LOCALE.get("msg_import_title"), LOCALE.get("msg_import_success"))
            else:
                if self.undo_stack:
                    self.undo_stack.pop()
                    self._update_undo_redo_buttons()
                messagebox.showerror(LOCALE.get("msg_error_title"), LOCALE.get("msg_import_error"))

    def _on_export_png(self):
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")], initialfile="avatar.png")
        if f and self.renderer.export_image(self.manager.current_avatar, f, bg_color=self.manager.background_color):
            messagebox.showinfo(LOCALE.get("msg_export_title"), f"{LOCALE.get('msg_export_desc')}{os.path.basename(f)}")

    def _on_settings(self):
        SettingsModal(self.root, on_lang_change=self._set_lang)

    def _show_welcome_onboarding(self):
        WelcomeModal(self.root)

    def _on_help(self):
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.lift()
        else:
            self.help_window = HelpModal(self.root)

    def _run_runtime(self):
        api_key = get_groq_api_key()
        if not api_key:
            messagebox.showerror(
                "Chiave API Mancante",
                "Impossibile avviare Adam AI: non è stata impostata alcuna chiave API di Groq!\n\n"
                "Per avviare l'assistente vocale devi prima inserire la tua API Key nelle Impostazioni (icona rotella in alto a destra).\n\n"
                "Puoi ottenerne una gratuitamente in 30 secondi su https://console.groq.com."
            )
            self._on_settings()
            return

        if not is_key_verified():
            ok, msg = verify_groq_api_key(api_key)
            if not ok:
                messagebox.showerror(
                    "Chiave API Non Funzionante",
                    f"Impossibile avviare Adam AI: la chiave API di Groq non è valida o non funziona!\n\n"
                    f"Dettaglio: {msg}\n\n"
                    "Apri le Impostazioni (icona rotella in alto a destra) per verificare o inserire una nuova chiave.",
                    parent=self.root
                )
                self._on_settings()
                return
            else:
                set_key_verified(True)

        def _on_modal_confirm(choice, params):
            import subprocess
            import sys
            import os
            import json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            runtime_main = os.path.join(root_dir, "runtime", "main.py")

            env = os.environ.copy()
            env["GROQ_API_KEY"] = api_key

            if choice == "base":
                subprocess.Popen([sys.executable, runtime_main], cwd=root_dir, env=env)
                self._on_close()
            elif choice == "avatar":
                temp_json = os.path.join(root_dir, "runtime", "temp_run.json")
                av = self.manager.current_avatar.copy()

                prompt_content = ""
                p_path = params.get("prompt_path")
                if p_path and os.path.exists(p_path):
                    try:
                        with open(p_path, "r", encoding="utf-8") as f_p:
                            prompt_content = f_p.read()
                    except:
                        pass
                profile_data = {
                    "language": params["lang"],
                    "gender": params["gender"],
                    "voice_cloning": False,
                    "custom_prompt": prompt_content,
                    "avatar": av,
                    "background_color": self.manager.background_color
                }
                with open(temp_json, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=4, ensure_ascii=False)

                subprocess.Popen([sys.executable, runtime_main, "--profile", "runtime/temp_run.json"], cwd=root_dir, env=env)
                self._on_close()

        modal = RunOptionsModal(self.root, _on_modal_confirm, current_avatar=self.manager.current_avatar)

    def _build_animation_sequence(self) -> List[Dict]:
        seq = []

        def add_step(duration, eyes=None, brows=None, lips=None):
            prev = seq[-1]["overrides"] if seq else {}
            new_overrides = prev.copy()

            if eyes: new_overrides["eyes"] = eyes
            if brows: new_overrides["eyebrows"] = brows
            if lips: new_overrides["lips"] = lips

            seq.append({"duration": duration, "overrides": new_overrides})

        add_step(500, eyes="mid.png", brows="mid.png", lips="smiley.png")

        talking_speed = 120
        phonemes = ["A_E_I.png", "O.png", "B_M_P.png", "EE.png", "L.png", "TH.png", "F_V.png", "mid.png"]

        for p in phonemes:
            add_step(talking_speed, lips=p)
            if p == "B_M_P.png":
                add_step(talking_speed, brows="surprised.png", lips=p)
            elif p == "mid.png":
                add_step(talking_speed, brows="mid.png", lips=p)

        add_step(500, lips="smiley.png", brows="mid.png")
        add_step(150,  eyes="closed.png")
        add_step(800,  eyes="mid.png")
        add_step(1200, eyes="look_left.png")
        add_step(600,  eyes="mid.png")
        add_step(1200, eyes="look_right.png")
        add_step(600,  eyes="mid.png")
        add_step(1500, brows="angry.png")
        add_step(150,  eyes="closed.png")
        add_step(1500, eyes="mid.png")
        add_step(600,  brows="mid.png")
        add_step(1500, brows="surprised.png")
        add_step(800,  brows="mid.png")
        add_step(1500, lips="smiley.png", brows="mid.png", eyes="mid.png")
        add_step(150,  eyes="closed.png")
        add_step(500,  eyes="mid.png")

        return seq

    def _toggle_animation(self):
        if self.is_animating:
            self.is_animating = False
            self.anim_btn.configure(text=LOCALE.get("btn_anim_start"), bg="#e67e22")

            if self.jobs.get("sequence"):
                self.root.after_cancel(self.jobs["sequence"])
                self.jobs["sequence"] = None

            self.anim_state = {}
            self.renderer.render(self.manager.current_avatar)
        else:
            av = self.manager.current_avatar
            has_eyes = av.get("eyes", {}).get("item") is not None
            has_brows = av.get("eyebrows", {}).get("item") is not None
            has_lips = av.get("lips", {}).get("item") is not None

            if not (has_eyes or has_brows or has_lips):
                messagebox.showerror(
                    LOCALE.get("anim_error_title"),
                    LOCALE.get("anim_error_msg")
                )
                return

            if not (has_eyes and has_brows and has_lips):
                proceed = messagebox.askyesno(
                    LOCALE.get("anim_warning_title"),
                    LOCALE.get("anim_warning_msg")
                )
                if not proceed:
                    return

            self.is_animating = True
            self.anim_btn.configure(text=LOCALE.get("btn_anim_stop"), bg=C_DANGER)

            self.sequence_data = self._build_animation_sequence()
            self._run_sequence_step(0)

    def _run_sequence_step(self, step_index: int):
        if not self.is_animating:
            return

        if step_index >= len(self.sequence_data):
            step_index = 0

        step = self.sequence_data[step_index]
        duration = step["duration"]

        self.anim_state = step["overrides"]
        self.renderer.render(self.manager.current_avatar, file_overrides=self.anim_state)
        self.jobs["sequence"] = self.root.after(duration, lambda: self._run_sequence_step(step_index + 1))
