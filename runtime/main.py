import argparse
import json
import threading
import time
import sys
from os.path import join
from ui import Ui

def load_config(config_file):
    with open(config_file, "r") as file:
        return json.load(file)

def run_adam_thread(ui, config):
    time.sleep(0.5) 
    try:
        from adam import Adam
        
        adam = Adam(ui, config)
        ui.ui_queue.put(("app_ready", None))
        adam.play()
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Adam AI Runtime")
        parser.add_argument("--config", default="default.json")
        parser.add_argument("--profile", default=None, help="Path to avatar profile JSON")
        args = parser.parse_args()
        
        config = load_config(join("configs", args.config))
        ui_params = config.get("Ui", {}).get("params", {})
        
        ui = Ui(params=ui_params, auto_load_profile=args.profile)
        
        t = threading.Thread(target=run_adam_thread, args=(ui, config), daemon=True)
        t.start()
        
        ui.start()
    except KeyboardInterrupt:
        sys.exit(0)