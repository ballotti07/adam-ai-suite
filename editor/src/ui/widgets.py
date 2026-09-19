import tkinter as tk
from src.ui.theme import C_BTN_NORM, C_BTN_HOVER, C_TEXT_MAIN, C_ACCENT

class ModernButton(tk.Button):
    def __init__(self, master, **kw):
        self.bg_norm = kw.pop("bg", C_BTN_NORM)
        self.bg_hover = kw.pop("activebackground", C_BTN_HOVER)
        self.fg_norm = kw.pop("fg", C_TEXT_MAIN)
        relief = kw.pop("relief", "flat")
        bd = kw.pop("bd", 0)
        self.is_active = False

        super().__init__(
            master, 
            relief=relief, 
            bd=bd, 
            bg=self.bg_norm, 
            fg=self.fg_norm, 
            cursor="hand2", 
            **kw
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        if str(self.cget("state")) == "disabled":
            return
        if not self.is_active:
            self["bg"] = self.bg_hover

    def _on_leave(self, _):
        if str(self.cget("state")) == "disabled":
            return
        if not self.is_active:
            self["bg"] = self.bg_norm

    def update_colors(self, bg=None, activebackground=None, fg=None) -> None:
        if bg:
            self.bg_norm = bg
            self["bg"] = bg
        if activebackground:
            self.bg_hover = activebackground
            self["activebackground"] = activebackground
        if fg:
            self.fg_norm = fg
            self["fg"] = fg

    def set_active_state(self, active: bool = True) -> None:
        self.is_active = active
        if active:
            self.configure(bg=C_ACCENT, fg="#000000")
        else:
            self.configure(bg=self.bg_norm, fg=self.fg_norm)