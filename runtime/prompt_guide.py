import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

C_BG_MAIN   = '#1e1e2e'
C_PANEL     = '#2a2a40'
C_SIDEBAR   = '#252538'
C_ACCENT    = '#00d2d3'
C_BTN_NORM  = '#34344a'
C_BTN_HOVER = '#4b4b6a'
C_TEXT_MAIN = '#ffffff'
C_TEXT_SUB  = '#a0a0b0'
F_SMALL     = ('Segoe UI', 9)

class ModernButton(tk.Button):
    def __init__(self, master, **kw):
        self.bg_norm = kw.pop('bg', C_BTN_NORM)
        self.bg_hover = kw.pop('activebackground', C_BTN_HOVER)
        self.fg_norm = kw.pop('fg', C_TEXT_MAIN)
        super().__init__(master, relief='flat', bd=0, bg=self.bg_norm, fg=self.fg_norm, cursor='hand2', **kw)
        self.bind('<Enter>', lambda _: self.config(bg=self.bg_hover))
        self.bind('<Leave>', lambda _: self.config(bg=self.bg_norm))

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
        prompt_dir = os.path.join(current_dir, "prompt")
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


