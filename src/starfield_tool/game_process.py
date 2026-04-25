import subprocess


_STARFIELD_IMAGES = ("Starfield.exe",)
_LAUNCHER_IMAGES = ("BethesdaNetLauncher.exe", "Starfield_BGS.exe")

# Suppresses the tasklist.exe console flash on Windows; 0 on other platforms
# (where this module's tasklist call fails harmlessly anyway).
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _image_running(image: str) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=_NO_WINDOW,
        )
        return image in result.stdout
    except (subprocess.SubprocessError, OSError):
        return False


def is_starfield_running() -> bool:
    return any(_image_running(img) for img in _STARFIELD_IMAGES)


def is_launcher_running() -> bool:
    return any(_image_running(img) for img in _LAUNCHER_IMAGES)


def is_starfield_or_launcher_running() -> bool:
    return is_starfield_running() or is_launcher_running()
