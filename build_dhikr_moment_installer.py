import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"
ICON = ROOT / "assets" / "app_icon.ico"
INNO_SCRIPT = ROOT / "dhikr_moment_installer.iss"


def run(command: list[str]) -> None:
    print(" ".join(str(part) for part in command))
    subprocess.run(command, cwd=ROOT, check=True)


def find_iscc() -> Path:
    found = shutil.which("ISCC.exe")
    if found:
        return Path(found)

    candidates = [
        Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("ISCC.exe not found. Install Inno Setup first.")


def clean_output() -> None:
    for path in (BUILD, DIST, RELEASE):
        if path.exists():
            shutil.rmtree(path)
    RELEASE.mkdir(exist_ok=True)

    for spec in ROOT.glob("DhikrMoment*.spec"):
        spec.unlink(missing_ok=True)


def build_app() -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--noconsole",
        "--clean",
        "--name",
        "DhikrMoment",
        "--icon",
        str(ICON),
        "--add-data",
        f"{ICON};assets",
        "--add-data",
        f"{ROOT / 'assets' / 'app_icon.png'};assets",
        "لحظة_ذكر.py",
    ]
    run(command)


def build_installer() -> None:
    run([str(find_iscc()), str(INNO_SCRIPT)])


def main() -> int:
    clean_output()
    build_app()
    build_installer()
    print(f"\nتم إنشاء المثبت: {RELEASE / 'DhikrMomentSetup.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
