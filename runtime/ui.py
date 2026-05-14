import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import os
import random
import json
import queue
import ctypes 
import threading
import wave
import contextlib

C_BG_MAIN   = "#1e1e2e"
C_PANEL     = "#2a2a40" 
C_SIDEBAR   = "#252538"
C_ACCENT    = "#00d2d3"
C_BTN_PRIM  = "#6c5ce7"
C_BTN_HOVER = "#5f3dc4"
C_BTN_SEC   = "#34344a"
C_BTN_SEC_H = "#4b4b6a"
C_TEXT_MAIN = "#ffffff"
C_TEXT_SUB  = "#a0a0b0"
C_SUCCESS   = "#2ecc71"
C_ERROR     = "#e74c3c"

F_HEADER = ("Segoe UI", 26, "bold")
F_TITLE  = ("Segoe UI", 14, "bold")
F_BODY   = ("Segoe UI", 10)
F_SMALL  = ("Segoe UI", 9)
F_MONO   = ("Consolas", 11, "bold")
F_STATUS = ("Segoe UI", 12, "bold")

STD_DIM = (512, 512)
CTR_X, CTR_Y = STD_DIM[0] // 2, STD_DIM[1] // 2
BACKGROUND_LAYERS = ["base", "nose"]
FOREGROUND_LAYERS = ["accessories", "occhiali", "hair"]
DEFAULT_LIPS_PATH = "assets/lips"
DEFAULT_EYES_PATH = "assets/eyes"
DEFAULT_BROWS_PATH = "assets/eyebrows"

LANG_DATA = {
    "it": {
        "loading": "Caricamento Modelli AI in corso...\nAttendere prego.",
        "loading_prof": "Inizializzazione Modelli e Profilo...\nL'operazione potrebbe richiedere alcuni secondi.",
        "launcher_title": "ADAM AI",
        "launcher_sub": "RUNTIME ENVIRONMENT",
        "guide_title": "📌 REGOLE DI UTILIZZO",
        "guide_text": "1. Scegli l'Avatar di Default o importane uno Custom.\n2. Se cloni una voce, l'audio NON deve superare i 6 secondi.\n3. Parla in modo chiaro vicino al microfono.\n4. Attendi che Adam finisca di parlare prima di interromperlo.\n5. Clicca sulla finestra dell'avatar per attivarla.",
        "cmd_title": "COMANDI RAPIDI",
        "cmd_space": "Premi Spazio per Mutare/Smutare il microfono",
        "cmd_enter": "Premi Invio per resettare la memoria della Chat",
        "cmd_esc": "Premi Esc per chiudere l'applicazione",
        "custom_title": "Vuoi un ADAM personalizzato?",
        "custom_text": "Crea e salva il tuo avatar con 'Adam Creator' per importarlo direttamente da questa pagina.",
        "btn_default": "USA AVATAR DI DEFAULT",
        "btn_custom": "CARICA PROFILO COMPLETO",
        "modal_title": "CARICA PROFILO",
        "modal_f1": "1. File Avatar (.json)",
        "modal_f2": "2. File Prompt Base (.txt)",
        "modal_f3": "3. File Audio Voce (.wav) [Max 6s]",
        "modal_b1": "Seleziona JSON...",
        "modal_b2": "Seleziona TXT...",
        "modal_b3": "Seleziona Audio...",
        "modal_wait": "In attesa dei file...",
        "modal_ready": "Tutti i file necessari sono pronti!",
        "modal_miss": "Mancano dei file obbligatori.",
        "modal_start": "AVVIA ADAM",
        "modal_warn_t": "Dati mancanti",
        "modal_warn_d": "Devi caricare TUTTI i file richiesti prima di avviare.",
        "modal_err_json": "Il file JSON selezionato non è valido o è corrotto.",
        "modal_err_audio": "Errore Audio: L'audio supera i 6 secondi massimi consentiti."
    },
    "en": {
        "loading": "Loading AI Models...\nPlease wait.",
        "loading_prof": "Initializing Models and Profile...\nThis may take a few seconds.",
        "launcher_title": "ADAM AI",
        "launcher_sub": "RUNTIME ENVIRONMENT",
        "guide_title": "📌 RULES OF USE",
        "guide_text": "1. Choose the Default Avatar or import a Custom one.\n2. If cloning a voice, the audio MUST NOT exceed 6 seconds.\n3. Speak clearly into the microphone.\n4. Wait for Adam to finish speaking before interrupting.\n5. Click on the avatar window to activate it.",
        "cmd_title": "QUICK COMMANDS",
        "cmd_space": "Press Space to Mute/Unmute the microphone",
        "cmd_enter": "Press Enter to reset the Chat memory",
        "cmd_esc": "Press Esc to close the application",
        "custom_title": "Want a custom ADAM?",
        "custom_text": "Create and save your avatar with 'Adam Creator' to import it directly from this page.",
        "btn_default": "USE DEFAULT AVATAR",
        "btn_custom": "LOAD CUSTOM PROFILE",
        "modal_title": "LOAD PROFILE",
        "modal_f1": "1. Avatar File (.json)",
        "modal_f2": "2. Base Prompt File (.txt)",
        "modal_f3": "3. Voice Audio File (.wav) [Max 6s]",
        "modal_b1": "Select JSON...",
        "modal_b2": "Select TXT...",
        "modal_b3": "Select Audio...",
        "modal_wait": "Waiting for files...",
        "modal_ready": "All necessary files are ready!",
        "modal_miss": "Missing required files.",
        "modal_start": "START ADAM",
        "modal_warn_t": "Missing Data",
        "modal_warn_d": "You must load ALL required files before starting.",
        "modal_err_json": "The selected JSON file is invalid or corrupted.",
        "modal_err_audio": "Audio Error: The audio exceeds the maximum 6 seconds allowed."
    }
}

STATUS_TRANS = {
    "🟢 PRONTO (Premi SPAZIO per parlare)": {"it": "🟢 PRONTO (Premi SPAZIO per parlare)", "en": "🟢 READY (Press SPACE to talk)"},
    "🟢 PRONTO (Parla pure...)": {"it": "🟢 PRONTO (Parla pure...)", "en": "🟢 READY (Speak now...)"},
    "⚪ PRONTO (Parla pure...)": {"it": "⚪ PRONTO (Parla pure...)", "en": "⚪ READY (Speak now...)"},
    "🟢 IN ASCOLTO (Parla pure...)": {"it": "🟢 IN ASCOLTO (Parla pure...)", "en": "🟢 LISTENING (Speak now...)"},
    "🟡 ELABORAZIONE...": {"it": "🟡 ELABORAZIONE...", "en": "🟡 PROCESSING..."},
    "🔵 PARLO...": {"it": "🔵 PARLO...", "en": "🔵 SPEAKING..."},
    "🔴 MUTO (Premi SPAZIO per parlare)": {"it": "🔴 MUTO (Premi SPAZIO per parlare)", "en": "🔴 MUTED (Press SPACE to talk)"},
    "⚠️ MEMORIA PULITA": {"it": "⚠️ MEMORIA PULITA", "en": "⚠️ MEMORY CLEARED"},
    "CARICA UN PROFILO...": {"it": "CARICA UN PROFILO...", "en": "LOAD A PROFILE..."},
    "⚙️ Sto generando la voce clonata...": {"it": "⚙️ Sto generando la voce clonata...", "en": "⚙️ Generating cloned voice..."},
    "⚙️ Sto elaborando la voce...": {"it": "⚙️ Sto elaborando la voce...", "en": "⚙️ Processing voice..."},
    "⚙️ Sto generando l'audio...": {"it": "⚙️ Sto generando l'audio...", "en": "⚙️ Generating audio..."}
}

image_map_en = {
    "A": "A_E_I.png", "B": "B_M_P.png", "C": "C_D_G_K_N_R_S_T_X_Y_Z.png", 
    "D": "C_D_G_K_N_R_S_T_X_Y_Z.png", "E": "A_E_I.png", "F": "F_V.png",
    "G": "C_D_G_K_N_R_S_T_X_Y_Z.png", "H": "TH.png", "I": "A_E_I.png", 
    "J": "CH_J_SH.png", "K": "C_D_G_K_N_R_S_T_X_Y_Z.png", "L": "L.png",
    "M": "B_M_P.png", "N": "N.png", "O": "O.png", "P": "B_M_P.png",
    "Q": "Q_W.png", "R": "C_D_G_K_N_R_S_T_X_Y_Z.png", "S": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "T": "C_D_G_K_N_R_S_T_X_Y_Z.png", "U": "U.png", "V": "F_V.png",
    "W": "Q_W.png", "X": "C_D_G_K_N_R_S_T_X_Y_Z.png", "Y": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "Z": "C_D_G_K_N_R_S_T_X_Y_Z.png", "CH": "CH_J_SH.png", "SH": "CH_J_SH.png", "TH": "TH.png"
}

image_map_it = {
    "A": "A_E_I.png", "E": "A_E_I.png", "I": "A_E_I.png", "O": "O.png", "U": "U.png",
    "B": "B_M_P.png", "M": "B_M_P.png", "P": "B_M_P.png",
    "F": "F_V.png", "V": "F_V.png",
    "C": "C_D_G_K_N_R_S_T_X_Y_Z.png", "D": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "G": "C_D_G_K_N_R_S_T_X_Y_Z.png", "H": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "K": "C_D_G_K_N_R_S_T_X_Y_Z.png", "R": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "S": "C_D_G_K_N_R_S_T_X_Y_Z.png", "T": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "X": "C_D_G_K_N_R_S_T_X_Y_Z.png", "Y": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "Z": "C_D_G_K_N_R_S_T_X_Y_Z.png", "L": "L.png", "N": "N.png",
    "Q": "Q_W.png", "W": "Q_W.png",
    "J": "CH_J_SH.png", "CH": "C_D_G_K_N_R_S_T_X_Y_Z.png", "GH": "C_D_G_K_N_R_S_T_X_Y_Z.png",
    "GN": "N.png", "GL": "L.png", "SC": "CH_J_SH.png", "SH": "CH_J_SH.png", 
    "TH": "C_D_G_K_N_R_S_T_X_Y_Z.png"
}

def set_titlebar_color(window, hex_color):
    try:
        window.update() 
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        color_ref = ctypes.c_int(b << 16 | g << 8 | r)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(color_ref), ctypes.sizeof(color_ref)
        )
    except Exception:
        pass

class ModernButton(tk.Button):
    def __init__(self, master, **kw):
        self.bg_norm = kw.pop("bg", C_BTN_SEC)
        self.bg_hover = kw.pop("activebackground", C_BTN_SEC_H)
        self.fg_norm = kw.pop("fg", C_TEXT_MAIN)
        super().__init__(master, relief="flat", bd=0, bg=self.bg_norm, fg=self.fg_norm, cursor="hand2", **kw)
        self.bind("<Enter>", lambda _: self.config(bg=self.bg_hover))
        self.bind("<Leave>", lambda _: self.config(bg=self.bg_norm))

class CustomSetupModal(tk.Toplevel):
    def __init__(self, parent, on_confirm_callback, current_lang):
        super().__init__(parent)
        self.on_confirm = on_confirm_callback
        self.current_lang = current_lang
        self.avatar_path = None
        self.prompt_path = None
        self.audio_path = None
        self.needs_audio = False 
        t = LANG_DATA[self.current_lang]
        self.title("Adam Setup")
        self.geometry("500x520")
        self.configure(bg=C_BG_MAIN)
        self.resizable(False, False)
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 260
        self.geometry(f"+{x}+{y}")
        set_titlebar_color(self, C_BG_MAIN)
        self.transient(parent)
        self.grab_set() 
        tk.Label(self, text=t["modal_title"], font=F_TITLE, bg=C_BG_MAIN, fg=C_ACCENT).pack(pady=(30, 20))
        self.container = tk.Frame(self, bg=C_BG_MAIN, padx=40)
        self.container.pack(fill="both", expand=True)
        tk.Label(self.container, text=t["modal_f1"], font=("Segoe UI", 10, "bold"), bg=C_BG_MAIN, fg="white").pack(anchor="w", pady=(0, 5))
        self.btn_avatar = ModernButton(self.container, text=t["modal_b1"], command=self._sel_avatar, width=40, pady=8)
        self.btn_avatar.pack(pady=(0, 15))
        tk.Label(self.container, text=t["modal_f2"], font=("Segoe UI", 10, "bold"), bg=C_BG_MAIN, fg="white").pack(anchor="w", pady=(0, 5))
        self.btn_prompt = ModernButton(self.container, text=t["modal_b2"], command=self._sel_prompt, width=40, pady=8)
        self.btn_prompt.pack(pady=(0, 15))
        self.audio_frame = tk.Frame(self.container, bg=C_BG_MAIN)
        tk.Label(self.audio_frame, text=t["modal_f3"], font=("Segoe UI", 10, "bold"), bg=C_BG_MAIN, fg="#f39c12").pack(anchor="w", pady=(0, 5))
        self.btn_audio = ModernButton(self.audio_frame, text=t["modal_b3"], command=self._sel_audio, width=40, pady=8)
        self.btn_audio.pack(pady=(0, 15))
        self.lbl_status = tk.Label(self.container, text=t["modal_wait"], font=F_SMALL, bg=C_BG_MAIN, fg=C_TEXT_SUB)
        self.lbl_status.pack(pady=(10, 10))
        self.btn_start = ModernButton(self.container, text=t["modal_start"], bg=C_BTN_PRIM, activebackground=C_BTN_HOVER, fg="white", font=("Segoe UI", 11, "bold"), pady=12, command=self._try_confirm)
        self.btn_start.pack(fill="x", side="bottom", pady=20)

    def _sel_avatar(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], title="Select Avatar")
        if f:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                self.avatar_path = f
                self.btn_avatar.config(text=f"✔ {os.path.basename(f)}", bg=C_SUCCESS, fg="white")
                if data.get("voice_cloning", False) == True:
                    self.needs_audio = True
                    self.audio_frame.pack(before=self.lbl_status, fill="x") 
                else:
                    self.needs_audio = False
                    self.audio_path = None 
                    self.btn_audio.config(text=LANG_DATA[self.current_lang]["modal_b3"], bg=C_BTN_SEC)
                    self.audio_frame.pack_forget() 
                self._check_ready()
            except Exception as e:
                messagebox.showerror("JSON Error", LANG_DATA[self.current_lang]["modal_err_json"])
                self.avatar_path = None

    def _sel_prompt(self):
        f = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")], title="Select Prompt")
        if f:
            self.prompt_path = f
            self.btn_prompt.config(text=f"✔ {os.path.basename(f)}", bg=C_SUCCESS, fg="white")
            self._check_ready()

    def _sel_audio(self):
        f = filedialog.askopenfilename(filetypes=[("Audio WAV", "*.wav")], title="Select Audio")
        if f:
            try:
                with contextlib.closing(wave.open(f, 'r')) as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = frames / float(rate)
                    if duration > 6.8:
                        messagebox.showerror("Errore", LANG_DATA[self.current_lang]["modal_err_audio"])
                        self.audio_path = None
                        self.btn_audio.config(text=LANG_DATA[self.current_lang]["modal_b3"], bg=C_BTN_SEC, fg=C_TEXT_MAIN)
                        self._check_ready()
                        return
            except Exception as e:
                messagebox.showerror("Errore", "Impossibile leggere il file audio WAV.")
                return

            self.audio_path = f
            self.btn_audio.config(text=f"✔ {os.path.basename(f)}", bg=C_SUCCESS, fg="white")
            self._check_ready()

    def _check_ready(self):
        t = LANG_DATA[self.current_lang]
        is_ready = bool(self.avatar_path and self.prompt_path)
        if self.needs_audio and not self.audio_path:
            is_ready = False
        if is_ready:
            self.lbl_status.config(text=t["modal_ready"], fg=C_SUCCESS)
        else:
            self.lbl_status.config(text=t["modal_miss"], fg=C_TEXT_SUB)

    def _try_confirm(self):
        t = LANG_DATA[self.current_lang]
        is_ready = bool(self.avatar_path and self.prompt_path)
        if self.needs_audio and not self.audio_path:
            is_ready = False
        if not is_ready:
            messagebox.showwarning(t["modal_warn_t"], t["modal_warn_d"])
            return
        self.on_confirm(self.avatar_path, self.prompt_path, self.audio_path)
        self.destroy()

class Ui:
    def __init__(self, params=None, auto_load_profile=None):
        self.params = params or {}
        self.auto_load_profile = auto_load_profile
        self.window_title = self.params.get('window_title', "Adam AI - Runtime")
        self.window_width = 1000  
        self.window_height = 650
        self.root = tk.Tk()
        self.root.title(self.window_title)
        self.root.configure(bg=C_BG_MAIN) 
        self.root.resizable(False, False)
        self.ui_queue = queue.Queue()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.window_width) // 2
        y = (screen_h - self.window_height) // 2
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        set_titlebar_color(self.root, C_BG_MAIN)
        self.assets_ready = False
        self.custom_prompt_path = None
        self.is_ui_ready = False
        self.img_refs = []
        self.canvas = None 
        self.bottom_bar = None
        self.status_label = None
        self.audio_canvas = None
        self.audio_dot_id = None
        self.base_dot_radius = 5
        self.paths = {
            "eyes": DEFAULT_EYES_PATH,
            "eyebrows": DEFAULT_BROWS_PATH,
            "lips": DEFAULT_LIPS_PATH
        }
        self.cache_lips = {}
        self.cache_eyes = {}
        self.cache_brows = {}
        self.cache_overlays = {}
        self.current_avatar_data = {}
        self.exit_callback = None
        self.toggle_mute_callback = None
        self.reset_chat_callback = None
        self.profile_loaded_callback = None
        self.audio_duration = 0
        self.kill = False
        self.is_custom = False
        self.lip_sync_id = None
        self.active_image_map = image_map_en 
        self.current_lang = "it"
        self.ui_texts = {} 
        self.current_phoneme = "end"
        self.current_volume = 0
        self._show_loading()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind_all("<KeyRelease>", self.on_key_release)
        self._check_queue()

    def set_language_map(self, lang):
        if lang == "it":
            self.active_image_map = image_map_it
        else:
            self.active_image_map = image_map_en

    def _check_queue(self):
        try:
            while True:
                msg_type, data = self.ui_queue.get_nowait()
                if msg_type == "status": self._internal_update_status(*data)
                elif msg_type == "audio": self._internal_update_audio(data)
                elif msg_type == "say": self._internal_say(*data)
                elif msg_type == "listen": self._internal_listen()
                elif msg_type == "idle": self._internal_idle()
                elif msg_type == "chat": self._internal_update_chat(*data)
                elif msg_type == "volume": self._internal_update_volume(data)
                elif msg_type == "lips_realtime": self.update_lips(data) 
                elif msg_type == "clear_chat": self._internal_clear_chat()
                elif msg_type == "app_ready": self._internal_app_ready()
                elif msg_type == "profile_ready": self._finalize_profile_load(data)
        except queue.Empty:
            pass
        finally:
            if not self.kill:
                self.root.after(50, self._check_queue)

    def _show_loading(self, title="ADAM AI", subtitle="SYSTEM INITIALIZATION", msg=""):
        self.loading_frame = tk.Frame(self.root, bg=C_BG_MAIN)
        self.loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.loading_frame.tkraise() 
        center_frame = tk.Frame(self.loading_frame, bg=C_BG_MAIN)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(center_frame, text=title, font=("Segoe UI", 32, "bold"), bg=C_BG_MAIN, fg=C_ACCENT).pack(pady=(0, 5))
        tk.Label(center_frame, text=subtitle, font=("Segoe UI", 12, "bold", "italic"), bg=C_BG_MAIN, fg=C_TEXT_SUB).pack(pady=(0, 25))
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", thickness=6, background=C_ACCENT, troughcolor=C_PANEL, bordercolor=C_BG_MAIN)
        self.progress = ttk.Progressbar(center_frame, style="TProgressbar", orient="horizontal", length=250, mode="indeterminate")
        self.progress.pack(pady=(0, 20))
        self.progress.start(15)
        display_msg = msg if msg else LANG_DATA[self.current_lang]["loading"]
        self.ui_texts["lbl_loading"] = tk.Label(center_frame, text=display_msg, font=F_BODY, bg=C_BG_MAIN, fg="white", justify="center")
        self.ui_texts["lbl_loading"].pack()

    def _internal_app_ready(self):
        if hasattr(self, 'loading_frame') and self.loading_frame.winfo_exists():
            self.progress.stop()
            self.loading_frame.destroy()
        if self.auto_load_profile:
            self.root.after(100, lambda: threading.Thread(target=self._thread_process_direct_load, args=(self.auto_load_profile,), daemon=True).start())
        else:
            self._show_launcher()

    def _thread_process_direct_load(self, json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if self.profile_loaded_callback:
                self.profile_loaded_callback(data) 
            self.ui_queue.put(("profile_ready", data))
        except Exception as e:
            self.ui_queue.put(("status", (f"Error: {str(e)[:20]}", C_ERROR)))

    def _show_launcher(self):
        self.launcher_frame = tk.Frame(self.root, bg=C_BG_MAIN)
        self.launcher_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lang_mb = tk.Menubutton(self.launcher_frame, text="IT" if self.current_lang == "it" else "EN", font=("Segoe UI", 14, "bold"), bg=C_PANEL, fg=C_ACCENT, activebackground=C_SIDEBAR, activeforeground=C_TEXT_MAIN, cursor="hand2", bd=0, indicatoron=0, padx=12, pady=6)
        self.lang_menu = tk.Menu(self.lang_mb, tearoff=0, bg=C_PANEL, fg=C_TEXT_MAIN, activebackground=C_ACCENT, activeforeground=C_BG_MAIN, font=("Segoe UI", 11), borderwidth=0)
        self.lang_menu.add_command(label="Italiano", command=lambda: self._on_language_select("it"))
        self.lang_menu.add_command(label="English", command=lambda: self._on_language_select("en"))
        self.lang_mb["menu"] = self.lang_menu
        self.lang_mb.place(relx=0.96, rely=0.02, anchor="ne")
        main_container = tk.Frame(self.launcher_frame, bg=C_BG_MAIN)
        main_container.pack(fill="both", expand=True, padx=40, pady=(60, 40))
        left_col = tk.Frame(main_container, bg=C_PANEL, padx=30, pady=30)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 25))
        t = LANG_DATA[self.current_lang]
        self.ui_texts["lbl_title"] = tk.Label(left_col, text=t["launcher_title"], font=F_HEADER, bg=C_PANEL, fg=C_TEXT_MAIN)
        self.ui_texts["lbl_title"].pack(anchor="w")
        self.ui_texts["lbl_sub"] = tk.Label(left_col, text=t["launcher_sub"], font=("Segoe UI", 10, "bold", "italic"), bg=C_PANEL, fg=C_ACCENT)
        self.ui_texts["lbl_sub"].pack(anchor="w", pady=(0, 20))
        self.ui_texts["lbl_guide_title"] = tk.Label(left_col, text=t["guide_title"], font=F_TITLE, bg=C_PANEL, fg="white")
        self.ui_texts["lbl_guide_title"].pack(anchor="w", pady=(10, 5))
        self.ui_texts["lbl_guide_text"] = tk.Label(left_col, text=t["guide_text"], font=F_BODY, bg=C_PANEL, fg=C_TEXT_SUB, justify="left", wraplength=400)
        self.ui_texts["lbl_guide_text"].pack(anchor="w", pady=(0, 15))
        cmd_box = tk.Frame(left_col, bg=C_SIDEBAR, padx=20, pady=20)
        cmd_box.pack(fill="x", pady=(20, 0), side="bottom")
        self.ui_texts["lbl_cmd_title"] = tk.Label(cmd_box, text=t["cmd_title"], font=("Segoe UI", 10, "bold"), bg=C_SIDEBAR, fg=C_ACCENT)
        self.ui_texts["lbl_cmd_title"].pack(anchor="w", pady=(0, 10))
        self.ui_texts["cmd_descs"] = []
        cmds = [("[SPAZIO]", "cmd_space"), ("[INVIO]", "cmd_enter"), ("[ESC]", "cmd_esc")]
        for key, dict_key in cmds:
            row = tk.Frame(cmd_box, bg=C_SIDEBAR)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=key, font=F_MONO, bg=C_SIDEBAR, fg=C_TEXT_MAIN, width=10, anchor="w").pack(side="left")
            lbl_desc = tk.Label(row, text=t[dict_key], font=F_SMALL, bg=C_SIDEBAR, fg=C_TEXT_SUB)
            lbl_desc.pack(side="left")
            self.ui_texts["cmd_descs"].append((lbl_desc, dict_key))
        right_col = tk.Frame(main_container, bg=C_BG_MAIN, width=360)
        right_col.pack(side="right", fill="y")
        right_col.pack_propagate(False)
        info_box = tk.Frame(right_col, bg=C_PANEL, padx=25, pady=25)
        info_box.pack(fill="x", anchor="n")
        self.ui_texts["lbl_custom_title"] = tk.Label(info_box, text=t["custom_title"], font=F_TITLE, bg=C_PANEL, fg="white")
        self.ui_texts["lbl_custom_title"].pack(anchor="w", pady=(0, 10))
        self.ui_texts["lbl_custom_text"] = tk.Label(info_box, text=t["custom_text"], font=F_BODY, bg=C_PANEL, fg=C_TEXT_SUB, justify="left", wraplength=310)
        self.ui_texts["lbl_custom_text"].pack(anchor="w")
        btn_container = tk.Frame(right_col, bg=C_BG_MAIN)
        btn_container.pack(side="bottom", fill="x")
        self.ui_texts["btn_default"] = ModernButton(btn_container, text=t["btn_default"], font=("Segoe UI", 11, "bold"), pady=18, command=self._load_default_flow)
        self.ui_texts["btn_default"].pack(fill="x", pady=(12, 0), side="bottom")
        self.ui_texts["btn_custom"] = ModernButton(btn_container, text=t["btn_custom"], bg=C_BTN_PRIM, activebackground=C_BTN_HOVER, fg="white", font=("Segoe UI", 11, "bold"), pady=18, command=self._open_custom_modal)
        self.ui_texts["btn_custom"].pack(fill="x", pady=(12, 12), side="bottom")

    def _on_language_select(self, lang_code):
        self.current_lang = lang_code
        
        if hasattr(self, 'lang_mb') and self.lang_mb.winfo_exists():
            self.lang_mb.config(text="IT" if lang_code == "it" else "EN")

        if hasattr(self, 'lang_mb_chat') and self.lang_mb_chat.winfo_exists():
            self.lang_mb_chat.config(text="IT" if lang_code == "it" else "EN")
            
        t = LANG_DATA[self.current_lang]
        key_map = {
            "lbl_loading": "loading", "lbl_title": "launcher_title", "lbl_sub": "launcher_sub",
            "lbl_guide_title": "guide_title", "lbl_guide_text": "guide_text",
            "lbl_cmd_title": "cmd_title", "lbl_custom_title": "custom_title",
            "lbl_custom_text": "custom_text", "btn_default": "btn_default",
            "btn_custom": "btn_custom"
        }
        for ui_key, json_key in key_map.items():
            if ui_key in self.ui_texts and self.ui_texts[ui_key].winfo_exists():
                self.ui_texts[ui_key].config(text=t[json_key])
                
        if "cmd_descs" in self.ui_texts:
            for lbl, dict_key in self.ui_texts["cmd_descs"]:
                if lbl.winfo_exists():
                    lbl.config(text=t[dict_key])
                    
        if hasattr(self, 'last_status_key') and self.last_status_key:
            translated = STATUS_TRANS.get(self.last_status_key, {}).get(self.current_lang, self.last_status_key)
            if self.status_label:
                self.status_label.config(text=translated)

        if hasattr(self, 'language_change_callback') and self.language_change_callback:
            self.language_change_callback(lang_code)

    def _open_custom_modal(self):
        CustomSetupModal(self.root, self._load_custom_flow, self.current_lang)

    def _switch_to_avatar_view(self):
        if hasattr(self, 'launcher_frame') and self.launcher_frame.winfo_exists():
            self.launcher_frame.destroy()
        self.window_width = 862
        self.window_height = 560 
        x = (self.root.winfo_screenwidth() - self.window_width) // 2
        y = (self.root.winfo_screenheight() - self.window_height) // 2
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        self.root.configure(bg=C_BG_MAIN)
        main_frame = tk.Frame(self.root, bg=C_BG_MAIN)
        main_frame.pack(fill="both", expand=True)
        left_frame = tk.Frame(main_frame, width=512, bg=C_PANEL)
        left_frame.pack(side="left", fill="y")
        left_frame.pack_propagate(False)
        right_frame = tk.Frame(main_frame, bg=C_BG_MAIN)
        right_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)
        self.lang_mb_chat = tk.Menubutton(right_frame, text="IT" if self.current_lang == "it" else "EN", font=("Segoe UI", 10, "bold"), bg=C_PANEL, fg=C_ACCENT, activebackground=C_SIDEBAR, activeforeground=C_TEXT_MAIN, cursor="hand2", bd=0, indicatoron=0, padx=8, pady=2)
        self.lang_menu_chat = tk.Menu(self.lang_mb_chat, tearoff=0, bg=C_PANEL, fg=C_TEXT_MAIN, activebackground=C_ACCENT, activeforeground=C_BG_MAIN, font=("Segoe UI", 9), borderwidth=0)
        self.lang_menu_chat.add_command(label="Italiano", command=lambda: self._on_language_select("it"))
        self.lang_menu_chat.add_command(label="English", command=lambda: self._on_language_select("en"))
        self.lang_mb_chat["menu"] = self.lang_menu_chat
        self.lang_mb_chat.place(relx=1.0, rely=0.0, anchor="ne")
        chat_title = "Chat"
        tk.Label(right_frame, text=chat_title, font=F_TITLE, bg=C_BG_MAIN, fg=C_ACCENT).pack(anchor="w", pady=(0, 10))
        self.chat_box = scrolledtext.ScrolledText(right_frame, wrap="word", font=F_BODY, bg=C_PANEL, fg=C_TEXT_MAIN, bd=0, padx=10, pady=10)
        self.chat_box.pack(fill="both", expand=True)
        self.chat_box.config(state="disabled")
        self.chat_box.tag_config("user", foreground="#2ecc71", font=("Segoe UI", 10, "bold"))
        self.chat_box.tag_config("adam", foreground="#00d2d3", font=("Segoe UI", 10, "bold"))

        self.canvas = tk.Canvas(left_frame, width=512, height=512, bg="white", highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)
        self.bottom_bar = tk.Frame(left_frame, bg=C_PANEL, height=48)
        self.bottom_bar.pack(side="bottom", fill="x")
        self.bottom_bar.pack_propagate(False)
        init_text = "🟢 PRONTO (Premi SPAZIO per parlare)" if self.current_lang == "it" else "🟢 READY (Press SPACE to talk)"
        self.status_label = tk.Label(self.bottom_bar, text=init_text, font=F_STATUS, bg=C_PANEL, fg="#2ecc71", anchor="w")
        self.status_label.pack(side="left", padx=15, fill="y")
        self.audio_canvas = tk.Canvas(self.bottom_bar, width=40, height=40, bg=C_PANEL, highlightthickness=0)
        self.audio_canvas.pack(side="right", padx=15, pady=4)
        self.audio_dot_id = self.audio_canvas.create_oval(15, 15, 25, 25, fill="#ff4757", outline="", tags="ui_audio")

    def _internal_update_chat(self, origin, text):
        if not getattr(self, "chat_box", None): return 
        origin_lower = origin.lower()
        if "user" in origin_lower:
            display_origin = "Tu:" if self.current_lang == "it" else "You:"
            tag = "user"
        elif "adam" in origin_lower:
            display_origin = "Adam:"
            tag = "adam"
        else:
            return
        self.chat_box.config(state="normal")
        self.chat_box.insert("end", f"{display_origin}\n", tag)
        self.chat_box.insert("end", f"{text}\n\n")
        self.chat_box.see("end") 
        self.chat_box.config(state="disabled")

    def _internal_clear_chat(self):
        if getattr(self, "chat_box", None):
            self.chat_box.config(state="normal")
            self.chat_box.delete("1.0", "end")
            self.chat_box.config(state="disabled")

    def update_status(self, text, color="white"): self.ui_queue.put(("status", (text, color)))
    def update_audio_level(self, level): self.ui_queue.put(("audio", level))
    def say(self, text, audio_duration=0): self.ui_queue.put(("say", (text, audio_duration)))
    def listen(self): self.ui_queue.put(("listen", None))
    def idle(self): self.ui_queue.put(("idle", None))
    def set_lips_realtime(self, char): self.ui_queue.put(("lips_realtime", char))
    def clear_chat(self): self.ui_queue.put(("clear_chat", None))
    
    def log_message(self, origin, text):
        print(f"[{origin}] {text}")
        self.ui_queue.put(("chat", (origin, text)))
        
    def set_callbacks(self, on_toggle_mute=None, on_reset_chat=None, on_exit=None, on_profile_loaded=None, on_language_change=None):
        self.toggle_mute_callback = on_toggle_mute
        self.reset_chat_callback = on_reset_chat
        self.exit_callback = on_exit
        self.profile_loaded_callback = on_profile_loaded
        self.language_change_callback = on_language_change

    def _internal_update_status(self, text, color):
        self.last_status_key = text 
        translated_text = STATUS_TRANS.get(text, {}).get(self.current_lang, text)
        if self.status_label:
            self.status_label.config(text=translated_text, fg=color)

    def _internal_update_audio(self, level):
        if self.audio_dot_id and self.audio_canvas:
            r = min(self.base_dot_radius + (level * 18), 19) 
            self.audio_canvas.coords(self.audio_dot_id, 20-r, 20-r, 20+r, 20+r)
            self.audio_canvas.itemconfig(self.audio_dot_id, fill="#ff4757" if level > 0.05 else "#57606f")


    def _cancel_lip_sync(self):
        if getattr(self, 'lip_sync_id', None) is not None:
            self.root.after_cancel(self.lip_sync_id)
            self.lip_sync_id = None

    def _internal_listen(self):
        self._internal_update_audio(0) 
        self._cancel_lip_sync()
        self.update_eyebrows("surprised")
        self.update_lips("end")
        self.audio_duration = 0

    def _internal_idle(self):
        self._internal_update_audio(0) 
        self._cancel_lip_sync()
        self.update_eyebrows("mid")
        self.update_lips("end")
        self.audio_duration = 0

    def _load_default_flow(self):
        self.is_custom = False
        self.custom_prompt_path = None 
        self._on_language_select("en")
        self._show_loading("ADAM AI", "LOADING DEFAULT PROFILE", LANG_DATA[self.current_lang]["loading_prof"])
        self.root.after(100, lambda: threading.Thread(target=self._thread_process_default_load, daemon=True).start())

    def _thread_process_default_load(self):
        try:
            if self.profile_loaded_callback:
                self.profile_loaded_callback({
                    "language": "en", 
                    "gender": "male", 
                    "custom_prompt": ""
                })
            self.ui_queue.put(("profile_ready", "default"))
        except Exception as e:
            self.ui_queue.put(("status", (f"Error: {str(e)[:20]}", "#e74c3c")))

    def _load_custom_flow(self, json_path, txt_path, audio_path):
        self.custom_prompt_path = txt_path
        self._show_loading("ADAM AI", "LOADING CUSTOM PROFILE", LANG_DATA[self.current_lang]["loading_prof"])
        self.root.after(100, lambda: threading.Thread(target=self._thread_process_custom_load, args=(json_path, txt_path, audio_path), daemon=True).start())

    def _thread_process_custom_load(self, json_path, txt_path, audio_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(txt_path, "r", encoding="utf-8") as f_txt:
                data["custom_prompt"] = f_txt.read()
            if audio_path:
                data["voice_ref_path"] = audio_path
            ref_text = data.get("voice_ref_text", "")
            if not ref_text or str(ref_text).strip() == "":
                data["voice_ref_text"] = "Oggi è una splendida giornata per creare qualcosa di incredibile insieme."
            else:
                data["voice_ref_text"] = str(ref_text).strip()
            if self.profile_loaded_callback:
                self.profile_loaded_callback(data) 
            self.ui_queue.put(("profile_ready", data))
        except Exception as e:
            self.ui_queue.put(("status", (f"Error: {str(e)[:20]}", C_ERROR)))

    def _finalize_profile_load(self, data):
        if data == "default":
            self.is_custom = False
            self._switch_to_avatar_view()
            self._build_default_images()
        else:
            self.is_custom = True
            lang = data.get("language", "en") 
            self._on_language_select(lang)
            self.set_language_map(lang) 
            self._switch_to_avatar_view()
            avatar_data = data.get("avatar", {})
            self._compose_custom_background(avatar_data)
            self._update_dynamic_paths(avatar_data)
        self._init_assets()
        self.is_ui_ready = True
        if hasattr(self, 'loading_frame') and self.loading_frame.winfo_exists():
            self.progress.stop()
            self.loading_frame.destroy()

    def _build_default_images(self):
        self.paths["eyes"] = os.path.join("assets", "default", "eyes")
        self.paths["eyebrows"] = os.path.join("assets", "default", "eyebrows")
        self.paths["lips"] = os.path.join("assets", "default", "lips")
        default_assets_dir = os.path.join("assets", "default")
        bg_img = Image.new("RGBA", STD_DIM, (255, 255, 255, 255))
        bg_candidates = [
            os.path.join(default_assets_dir, "base", "mid.png"),
            os.path.join(default_assets_dir, "base", "01.png"),
            os.path.join(default_assets_dir, "character.png")
        ]
        sfondo_caricato = False
        for bg_path in bg_candidates:
            if os.path.exists(bg_path):
                try:
                    layer = Image.open(bg_path).convert("RGBA")
                    if layer.size != STD_DIM: 
                        layer = layer.resize(STD_DIM, Image.Resampling.LANCZOS)
                    bg_img = Image.alpha_composite(bg_img, layer)
                    sfondo_caricato = True
                    break
                except Exception as e:
                    pass
        if not sfondo_caricato:
            self.canvas.configure(bg="white")
        else:
            self.sfondo = bg_img
            self.sfondo_tk = ImageTk.PhotoImage(self.sfondo)
            self.canvas.create_image(0, 0, anchor="nw", image=self.sfondo_tk, tags="bg")
        check_path = os.path.join(self.paths["eyes"], "mid.png")
        if os.path.exists(check_path):
            with Image.open(check_path) as img:
                if img.size == STD_DIM:
                    self.is_custom = True

    def _compose_custom_background(self, avatar_data):
        bg_img = Image.new("RGBA", STD_DIM, (255, 255, 255, 255))
        for layer in BACKGROUND_LAYERS:
            if layer in avatar_data:
                item = avatar_data[layer].get("item")
                color = avatar_data[layer].get("color", "default")
                if not item: continue
                item = item.replace("/", os.sep).replace("\\", os.sep)
                candidates = [
                    os.path.join("assets", layer, item, color, "mid.png"),
                    os.path.join("assets", layer, item, "mid.png"),
                    os.path.join("assets", layer, item, color, "01.png"),
                    os.path.join("assets", layer, item, "01.png")
                ]
                for p in candidates:
                    if os.path.exists(p):
                        try: 
                            found = Image.open(p).convert("RGBA")
                            if found.size != STD_DIM: 
                                found = found.resize(STD_DIM, Image.Resampling.LANCZOS)
                            bg_img.alpha_composite(found)
                            break
                        except Exception: 
                            continue
        self.sfondo = bg_img
        self.sfondo_tk = ImageTk.PhotoImage(self.sfondo)
        self.canvas.create_image(0, 0, anchor="nw", image=self.sfondo_tk, tags="bg")

    def _update_dynamic_paths(self, avatar_data):
        self.current_avatar_data = avatar_data
        for cat in ["eyes", "eyebrows", "lips"]:
            if cat in avatar_data:
                item = avatar_data[cat].get("item")
                if item:
                    item = item.replace("/", os.sep).replace("\\", os.sep)
                    color = avatar_data[cat].get("color")
                    p_col = os.path.join("assets", cat, item, color)
                    p_base = os.path.join("assets", cat, item)
                    self.paths[cat] = p_col if os.path.exists(p_col) else p_base

    def _init_assets(self):
        try:
            target_size = STD_DIM if self.is_custom else (650, 650)
            lips_size = STD_DIM if self.is_custom else (144, 84)

            def load_to_cache(cat, name, size):
                p = os.path.join(self.paths.get(cat, f"assets/{cat}"), name)
                if not os.path.exists(p):
                    p = os.path.join("assets", cat, name)
                if os.path.exists(p):
                    return ImageTk.PhotoImage(Image.open(p).convert("RGBA").resize(size, Image.Resampling.LANCZOS))
                return None

            self.cache_eyes["mid"] = load_to_cache("eyes", "mid.png", target_size)
            self.cache_eyes["closed"] = load_to_cache("eyes", "closed.png", target_size)
            self.cache_eyes["right"] = load_to_cache("eyes", "look_right.png", target_size)
            self.cache_eyes["left"] = load_to_cache("eyes", "look_left.png", target_size)
            self.cache_brows["mid"] = load_to_cache("eyebrows", "mid.png", target_size)
            self.cache_brows["angry"] = load_to_cache("eyebrows", "angry.png", target_size)
            self.cache_brows["surprised"] = load_to_cache("eyebrows", "surprised.png", target_size)
            lips_path = self.paths.get("lips", "assets/lips")
            smiley = load_to_cache("lips", "smiley.png", lips_size)
            self.cache_lips["smiley"] = smiley
            for k, v in self.active_image_map.items():
                p = os.path.join(lips_path, v)
                if os.path.exists(p): 
                    self.cache_lips[k] = ImageTk.PhotoImage(Image.open(p).convert("RGBA").resize(lips_size, Image.Resampling.LANCZOS))
                else: 
                    self.cache_lips[k] = smiley
            self.cache_overlays = {}
            if self.is_custom and hasattr(self, 'current_avatar_data'):
                for layer in FOREGROUND_LAYERS:
                    data = self.current_avatar_data.get(layer)
                    if data and data.get("item"):
                        item = data["item"].replace("/", os.sep).replace("\\", os.sep)
                        color = data.get("color", "default")
                        disk_cat = "glasses" if layer == "occhiali" else layer
                        candidates = [
                            os.path.join("assets", disk_cat, item, color, "mid.png"),
                            os.path.join("assets", disk_cat, item, "mid.png"),
                            os.path.join("assets", disk_cat, item, color, "01.png")
                        ]
                        for p in candidates:
                            if os.path.exists(p):
                                self.cache_overlays[layer] = ImageTk.PhotoImage(Image.open(p).convert("RGBA").resize(STD_DIM, Image.Resampling.LANCZOS))
                                break
            self.assets_ready = True
            self.refresh_scene()
        except Exception as e: 
            print(f"Errore asset: {e}")

    def refresh_scene(self):
        if not self.assets_ready: return
        self.update_lips("end")
        self.reopen_eyes()
        self.update_eyebrows("mid")
        self.draw_overlays()

    def draw_overlays(self):
        if not self.canvas: return
        self.canvas.delete("overlay")
        draw_order = ["accessories", "occhiali", "hair"]
        if self.is_custom and hasattr(self, 'current_avatar_data'):
            hair_item = self.current_avatar_data.get("hair", {}).get("item")
            if hair_item and str(hair_item).startswith("corti"):
                draw_order = ["accessories", "hair", "occhiali"]
        for layer in draw_order:
            if layer in self.cache_overlays:
                self.canvas.create_image(CTR_X, CTR_Y, anchor="center", image=self.cache_overlays[layer], tags="overlay")
        self.canvas.tag_raise("overlay")

    def _get_coords(self, cat):
        if self.is_custom: return CTR_X, CTR_Y
        if cat == "eyes": return 240, 220
        if cat == "lips": return 242, 347
        if "eyebrows" in cat: return 240, 255
        return CTR_X, CTR_Y

    def add_image(self, photo_img, x, y, tag=""):
        if not self.canvas or not photo_img: return
        try:
            self.img_refs.append(photo_img)
            if len(self.img_refs) > 50:
                self.img_refs.pop(0)
            self.canvas.create_image(x, y, anchor="center", image=photo_img, tags=tag)
        except Exception as e: 
            print(e)

    def _internal_say(self, text, audio_duration):
        self._internal_update_audio(0) 
        self.text = text
        self.audio_duration = audio_duration * 1000
        self.update_eyebrows("mid")
        self.lip_sync()

    def _internal_update_volume(self, vol):
        self.current_volume = vol
        self._refresh_lips_display()

    def _refresh_lips_display(self):
        target = self.current_phoneme if self.current_volume > 250 else "end"
        self._draw_lips_image(target)

    def _draw_lips_image(self, char):
        if not self.assets_ready or not self.canvas: return
        x, y = self._get_coords("lips")
        self.canvas.delete("lips")
        if char in [None, "end", ",", "."]:
            img = self.cache_lips.get("smiley")
        else:
            key = str(char).upper()
            if key not in self.cache_lips: key = "smiley"
            img = self.cache_lips.get(key)
        if img: self.add_image(img, x, y, tag="lips")

    def update_lips(self, char=None):
        self.current_phoneme = char
        self._refresh_lips_display()

    def blink_eyes(self):
        if not self.assets_ready or not self.canvas: return
        self.canvas.delete("eyes")
        x, y = self._get_coords("eyes")
        if random.randint(1, 2) % 2 == 0:
            self.move_eyes()
            wait = random.randint(500, 2000)
        else:
            self.add_image(self.cache_eyes.get("closed"), x, y, tag="eyes")
            wait = random.randint(100, 300)
        self.root.after(wait, self.reopen_eyes)

    def reopen_eyes(self):
        if not self.assets_ready or not self.canvas: return
        self.canvas.delete("eyes")
        x, y = self._get_coords("eyes")
        self.add_image(self.cache_eyes.get("mid"), x, y, tag="eyes")
        if not self.kill:
            self.root.after(random.randint(500, 5000), self.blink_eyes)

    def move_eyes(self):
        if not self.assets_ready or not self.canvas: return
        self.canvas.delete("eyes")
        x, y = self._get_coords("eyes")
        off_x = 0 if self.is_custom else 2
        y_off = 0 if self.is_custom else 1
        if random.randint(1, 2) % 2 == 0:
            self.add_image(self.cache_eyes.get("right"), x, y + y_off, tag="eyes")
        else:
            self.add_image(self.cache_eyes.get("left"), x + off_x, y + y_off, tag="eyes")

    def move_eyebrows(self):
        if not self.assets_ready or not self.canvas: return
        wait = 750
        r = random.randint(1, 3)
        self.canvas.delete("eyebrows")
        mode = "mid"
        if r % 3 == 0: mode = "angry"
        elif r % 3 == 1: mode = "surprised"
        else: wait = 2500
        self.update_eyebrows(mode)
        if not self.kill:
            self.root.after(random.randint(wait, wait * 2), self.move_eyebrows)

    def update_eyebrows(self, mode):
        if not self.assets_ready or not self.canvas: return
        self.canvas.delete("eyebrows")
        key, coord_key = "mid", "eyebrows_mid"
        if mode == "angry": 
            key, coord_key = "angry", "eyebrows_angry"
        elif mode == "surprised": 
            key, coord_key = "surprised", "eyebrows_surp"
        img = self.cache_brows.get(key)
        x, y = self._get_coords(coord_key)
        self.add_image(img, x, y, tag="eyebrows")

    def show_lips(self):
        self.lip_sync()

    def lip_sync(self):
        self._cancel_lip_sync() 
        letters = [l for l in self.text.upper() if l in self.active_image_map or l in [",", "."]]
        if letters: 
            base_wait = max(20, int(self.audio_duration / len(letters))) if getattr(self, 'audio_duration', 0) > 0 else 50
            self.display_images(letters, 0, base_wait)

    def display_images(self, letters, index, base_wait=50):
        if self.kill or not self.canvas: return
        wait = base_wait
        if index < len(letters):
            l = letters[index]
            if index + 1 < len(letters) and l in ["C", "T", "P", "S"] and letters[index+1] == "H":
                l += "H"
                index += 1
            if l == ",": wait = min(base_wait * 3, 300)
            elif l == ".": wait = min(base_wait * 5, 500)
            self.update_lips(l)
            self.lip_sync_id = self.root.after(wait, lambda: self.display_images(letters, index + 1, base_wait))
        else:
            self.update_lips("end")
            self.lip_sync_id = None

    def on_closing(self):
        self.kill = True
        self._cancel_lip_sync() 
        self.root.destroy()
        if self.exit_callback: self.exit_callback()

    def on_key_release(self, event):
        if event.keysym == "space" and self.toggle_mute_callback: 
            self.toggle_mute_callback()
        elif event.keysym == "Return" and self.reset_chat_callback: 
            self.reset_chat_callback()
        elif event.keysym == "Escape":
            self.on_closing()

    def start(self):
        try: self.root.mainloop()
        except Exception: pass