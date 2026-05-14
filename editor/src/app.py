from __future__ import annotations
import concurrent.futures
import os
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional
from PIL import Image, ImageTk, ImageDraw

from src.utils.config import APP_NAME, WINDOW_SIZE
from src.utils.constants import LAYER_ORDER, OPTIONAL_CATS, Cat
from src.utils.colors import color_to_hex
from src.utils.recorder import AudioRecorder
import time

from src.ui.theme import (
    C_BG_MAIN, C_SIDEBAR, C_PANEL, C_ACCENT, C_TEXT_MAIN, C_TEXT_SUB,
    C_DANGER, C_CARD_BG, F_HEADER, F_TITLE, F_BTN, F_SMALL
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
        w, h = 800, 700
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
        header.pack(fill="x", padx=25, pady=20)

        tk.Label(header, text=LOCALE.get("help_title"), font=("Segoe UI", 20, "bold"),
                 bg=C_PANEL, fg=C_ACCENT).pack(side="left")

        tk.Button(header, text="✕", font=("Arial", 16), bg=C_PANEL, fg=C_TEXT_SUB,
                  bd=0, relief="flat", activebackground=C_DANGER, activeforeground="white",
                  cursor="hand2", command=self.destroy).pack(side="right")

        content = tk.Frame(main, bg=C_PANEL)
        content.pack(fill="both", expand=True, padx=40, pady=5)
        content.columnconfigure(0, weight=0, minsize=70)
        content.columnconfigure(1, weight=1)

        steps = [
            ("help_step_1_title", "help_step_1_desc", "🎨"),
            ("help_step_2_title", "help_step_2_desc", "🖌️"),
            ("help_step_3_title", "help_step_3_desc", "📂"),
            ("help_step_4_title", "help_step_4_desc", "🎲"),
            ("help_step_5_title", "help_step_5_desc", "📷"),
            ("help_step_6_title", "help_step_6_desc", "⚙️"),
            ("help_step_7_title", "help_step_7_desc", "🎬"),
            ("help_step_lang_title", "help_step_lang_desc", "🌍"),
        ]

        for i, (t_key, d_key, icon) in enumerate(steps):
            icon_cell = tk.Frame(content, bg=C_PANEL)
            icon_cell.grid(row=i, column=0, sticky="nsew")
            lbl = tk.Label(icon_cell, text=icon, font=("Segoe UI", 24), bg=C_PANEL, fg=C_TEXT_MAIN)
            pos_x = 0.73 if "step_2" in t_key else 0.5
            lbl.place(relx=pos_x, y=0, anchor="n")

            txt_frame = tk.Frame(content, bg=C_PANEL)
            txt_frame.grid(row=i, column=1, sticky="ew", pady=10)

            tk.Label(txt_frame, text=LOCALE.get(t_key), font=("Segoe UI", 12, "bold"),
                     bg=C_PANEL, fg="white", anchor="w").pack(fill="x")

            tk.Label(txt_frame, text=LOCALE.get(d_key), font=("Segoe UI", 10),
                     bg=C_PANEL, fg="#b0b0c0", anchor="w", wraplength=600, justify="left").pack(fill="x")

        self.header_frame = header 
        tk.Label(main, text=LOCALE.get("help_close_tip"), font=("Segoe UI", 9, "italic"),
                 bg=C_PANEL, fg="#666").pack(side="bottom", pady=20)

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

class RunOptionsModal(tk.Toplevel):
    def __init__(self, parent, on_confirm_callback):
        super().__init__(parent)
        self.on_confirm = on_confirm_callback
        self.prompt_path = None
        self.choice = None
        
        self.title("Opzioni di Avvio")
        self.geometry("400x420")
        self.configure(bg=C_BG_MAIN)
        self.resizable(False, False)
        
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 210
        self.geometry(f"+{x}+{y}")
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Opzioni di Avvio", font=F_TITLE, bg=C_BG_MAIN, fg=C_ACCENT).pack(pady=(20, 10))
        
        self.btn_base = ModernButton(self, text="Avvia solo Applicazione", command=self._choose_base, pady=10)
        self.btn_base.pack(fill="x", padx=40, pady=5)
        
        self.btn_avatar = ModernButton(self, text="Avvia con Personaggio Corrente", command=self._choose_avatar, pady=10)
        self.btn_avatar.pack(fill="x", padx=40, pady=5)
        
        self.setup_frame = tk.Frame(self, bg=C_BG_MAIN)
        
        tk.Label(self.setup_frame, text="File Prompt (.txt):", font=F_SMALL, bg=C_BG_MAIN, fg="white").pack(anchor="w", pady=(5,0))
        self.btn_sel_prompt = ModernButton(self.setup_frame, text="Seleziona file...", command=self._sel_prompt, pady=8)
        self.btn_sel_prompt.pack(fill="x", pady=(0, 10))
        
        tk.Label(self.setup_frame, text="Lingua:", font=F_SMALL, bg=C_BG_MAIN, fg="white").pack(anchor="w")
        self.combo_lang = ttk.Combobox(self.setup_frame, values=["Italiano", "Inglese"], state="readonly")
        self.combo_lang.set("Italiano")
        self.combo_lang.pack(fill="x", pady=(0, 10))
        
        tk.Label(self.setup_frame, text="Voce:", font=F_SMALL, bg=C_BG_MAIN, fg="white").pack(anchor="w")
        self.combo_gender = ttk.Combobox(self.setup_frame, values=["Maschio", "Femmina"], state="readonly")
        self.combo_gender.set("Maschio")
        self.combo_gender.pack(fill="x", pady=(0, 10))
        
        self.btn_confirm = ModernButton(self.setup_frame, text="Conferma e Avvia", bg="#2ecc71", activebackground="#27ae60", command=self._confirm_avatar, pady=12)
        self.btn_confirm.pack(fill="x", pady=(10, 0))
        
    def _sel_prompt(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], title="Seleziona Prompt")
        if f:
            self.prompt_path = f
            self.btn_sel_prompt.config(text=os.path.basename(f), bg="#2ecc71", fg="white")

    def _choose_base(self):
        self.choice = "base"
        self.on_confirm(self.choice, {})
        self.destroy()
        
    def _choose_avatar(self):
        self.btn_base.pack_forget()
        self.btn_avatar.pack_forget()
        self.setup_frame.pack(fill="both", expand=True, padx=40, pady=10)
        
    def _confirm_avatar(self):
        if not self.prompt_path:
            from tkinter import messagebox
            messagebox.showwarning("Dati mancanti", "Devi selezionare un file prompt!")
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
    def __init__(self, root: tk.Tk):
        self.root = root
        self._resize_job = None

        self._init_window()

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
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        base_val = self.current_cat_enum.value
        self.manager.set_color(base_val, "skin_1")
        self.root.update_idletasks()
        self._refresh_grid(reset_scroll=True)
        self._draw_palette()
        self.renderer.render(self.manager.current_avatar)
        self._update_ui_text()

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

        self.btn_help = ModernButton(tools, text="", bg="#3a3a50", command=self._on_help, font=F_BTN, padx=15, pady=8)
        self.btn_help.grid(row=0, column=0, sticky="nsew", padx=5)

        self.btn_export = ModernButton(tools, text="", bg="#2980b9", command=self._on_export_png, font=F_BTN, padx=15, pady=8)
        self.btn_export.grid(row=0, column=1, sticky="nsew", padx=5)

        self.btn_save = ModernButton(tools, text="", bg=C_ACCENT, command=self._on_save_json, font=F_BTN, padx=15, pady=8, activeforeground="white")
        self.btn_save.grid(row=0, column=2, sticky="nsew", padx=5)

        self.btn_lang = ModernButton(frame, text="IT", bg="#3a3a50", command=self._show_lang_menu, font=("Segoe UI", 10, "bold"), padx=12, pady=5)
        self.btn_lang.pack(side="right", padx=0)

        self.lang_menu = tk.Menu(self.root, tearoff=0, bg=C_PANEL, fg="white", activebackground=C_ACCENT, font=("Segoe UI", 10))
        for code, label in LANG_DISPLAY.items():
            self.lang_menu.add_command(label=label, command=lambda l=code: self._set_lang(l))

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=C_SIDEBAR, width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.lbl_cats_header = tk.Label(sidebar, text="", bg=C_SIDEBAR, fg=C_TEXT_SUB, font=("Segoe UI", 10, "bold"))
        self.lbl_cats_header.pack(pady=(20, 10))

        for cat in LAYER_ORDER:
            val = cat.value
            icon = generate_solid_icon(val)
            self.icons_cache[val] = icon

            btn = ModernButton(
                sidebar, text="", image=icon, compound="left",
                anchor="w", padx=20, pady=12, font=F_BTN,
                command=lambda c=cat: self._change_cat(c)
            )
            btn.pack(fill="x", pady=4, padx=10)
            self.cat_btns[val] = btn

        self.cat_btns[LAYER_ORDER[0].value].set_active_state(True)

        actions = tk.Frame(sidebar, bg=C_SIDEBAR)
        actions.pack(side="bottom", fill="x", padx=10, pady=20)
        actions.columnconfigure((0, 1), weight=1)

        self.btn_random = ModernButton(actions, text="", bg="#34344a", command=self._on_random, font=F_BTN, pady=12)
        self.btn_random.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.btn_reset = ModernButton(actions, text="", bg=C_DANGER, command=self._on_reset, font=F_BTN, pady=12)
        self.btn_reset.grid(row=0, column=1, sticky="ew", padx=(5, 0))

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
        self.lbl_centering.pack(pady=5)

        btn_container = tk.Frame(right, bg=C_SIDEBAR)
        btn_container.pack(fill="x", padx=40, pady=20)
        btn_container.columnconfigure(0, weight=1, uniform="bottom_btns")
        btn_container.columnconfigure(1, weight=1, uniform="bottom_btns")

        self.anim_btn = ModernButton(btn_container, text="", bg="#e67e22", command=self._toggle_animation, font=F_BTN, pady=12)
        self.anim_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.run_btn = ModernButton(btn_container, text="", bg="#2ecc71", activebackground="#27ae60", command=self._run_runtime, font=F_BTN, pady=12)
        self.run_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

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
        self.canvas_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
        self.btn_lang.config(text=LOCALE.current_lang.upper())
        self.lbl_title.config(text=LOCALE.get("header_title"))
        self.lbl_subtitle.config(text=LOCALE.get("header_subtitle"))
        self.btn_import.config(text=LOCALE.get("btn_import"))
        self.btn_help.config(text=LOCALE.get("btn_help"))
        self.btn_export.config(text=LOCALE.get("btn_export"))
        self.btn_save.config(text=LOCALE.get("btn_save_json"))
        self.lbl_cats_header.config(text=LOCALE.get("lbl_categories"))
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

        anim_txt = "btn_anim_stop" if self.is_animating else "btn_anim_start"
        self.anim_btn.config(text=LOCALE.get(anim_txt))
        if hasattr(self, 'run_btn'):
            self.run_btn.config(text=LOCALE.get("btn_run_runtime"))
        self._draw_palette()

    def _show_lang_menu(self):
        x = self.btn_lang.winfo_rootx()
        y = self.btn_lang.winfo_rooty() + self.btn_lang.winfo_height()
        self.lang_menu.post(x, y)

    def _set_lang(self, code: str):
        LOCALE.set_language(code)
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

    def _select_item(self, item_name: str | None):
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
        self.manager.set_color(self.current_cat_enum.value, color_name)
        if self.is_animating: self._toggle_animation()
        self.renderer.render(self.manager.current_avatar)
        self._draw_palette()

    def _on_random(self):
        if self.is_animating: self._toggle_animation()
        self.manager.randomize(OPTIONAL_CATS)
        self.renderer.render(self.manager.current_avatar)
        self._refresh_grid(reset_scroll=False)
        self._draw_palette()

    def _on_reset(self):
        if self.is_animating: self._toggle_animation()
        self.manager.reset_all()
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
            if self.manager.load_profile(f):
                self.renderer.render(self.manager.current_avatar)
                self._refresh_grid(reset_scroll=False)
                self._draw_palette()
                messagebox.showinfo(LOCALE.get("msg_import_title"), LOCALE.get("msg_import_success"))
            else:
                messagebox.showerror(LOCALE.get("msg_error_title"), LOCALE.get("msg_import_error"))

    def _on_export_png(self):
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Image", "*.png")], initialfile="avatar.png")
        if f and self.renderer.export_image(self.manager.current_avatar, f):
            messagebox.showinfo(LOCALE.get("msg_export_title"), f"{LOCALE.get('msg_export_desc')}{os.path.basename(f)}")

    def _on_help(self):
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.lift()
        else:
            self.help_window = HelpModal(self.root)

    def _run_runtime(self):
        def _on_modal_confirm(choice, params):
            import subprocess
            import sys
            import os
            import json
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            runtime_main = os.path.join(root_dir, "runtime", "main.py")
            
            if choice == "base":
                subprocess.Popen([sys.executable, runtime_main], cwd=root_dir)
                self._on_close()
            elif choice == "avatar":
                temp_json = os.path.join(root_dir, "runtime", "temp_run.json")
                av = self.manager.current_avatar.copy()
                
                prompt_content = ""
                try:
                    with open(params["prompt_path"], "r", encoding="utf-8") as f_p:
                        prompt_content = f_p.read()
                except:
                    pass

                profile_data = {
                    "language": params["lang"],
                    "gender": params["gender"],
                    "voice_cloning": False,
                    "custom_prompt": prompt_content,
                    "avatar": av
                }
                with open(temp_json, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=4)
                    
                subprocess.Popen([sys.executable, runtime_main, "--profile", "runtime/temp_run.json"], cwd=root_dir)
                self._on_close()
                
        modal = RunOptionsModal(self.root, _on_modal_confirm)

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