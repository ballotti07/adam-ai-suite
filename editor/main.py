import os
import sys
import argparse
import tkinter as tk

editor_dir = os.path.dirname(os.path.abspath(__file__))
if editor_dir not in sys.path:
    sys.path.insert(0, editor_dir)

from src.app import AdamCreatorApp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adam Creator")
    parser.add_argument("--profile", default=None, help="Path to avatar profile JSON to load")
    args, _ = parser.parse_known_args()

    root = tk.Tk()
    app = AdamCreatorApp(root, initial_profile=args.profile)
    root.mainloop()
