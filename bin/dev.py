"""Dev server: auto-restarts the app on source file changes."""
import subprocess
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SRC_DIR = Path(__file__).parent.parent / "src"
APP_CMD = [sys.executable, "-m", "starfield_tool"]


class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.last_restart = 0.0

    def start_app(self):
        self.stop_app()
        print(f"\n--- Starting app ---")
        self.process = subprocess.Popen(APP_CMD, cwd=SRC_DIR.parent)

    def stop_app(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def on_modified(self, event):
        if not event.src_path.endswith(".py"):
            return
        # Debounce — ignore rapid successive changes
        now = time.time()
        if now - self.last_restart < 1.0:
            return
        self.last_restart = now
        print(f"Changed: {Path(event.src_path).name} — restarting...")
        self.start_app()


def main():
    handler = RestartHandler()
    observer = Observer()
    observer.schedule(handler, str(SRC_DIR), recursive=True)
    observer.start()

    print(f"Watching {SRC_DIR} for changes...")
    handler.start_app()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        handler.stop_app()
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
