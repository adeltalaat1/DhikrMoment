import base64
import json
import os
import random
import subprocess
import sys
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, QTimer, Qt, QVariantAnimation
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "DhikrMoment"
APP_TITLE = "لحظة ذكر"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "DhikrMoment"
CONFIG_DIR = Path.home() / "AppData" / "Roaming" / APP_NAME
CONFIG_PATH = CONFIG_DIR / "settings.json"
STARTUP_SHORTCUT_NAME = f"{APP_TITLE}.lnk"
ICON_RELATIVE_PATH = Path("assets") / "app_icon.ico"


@dataclass
class AppSettings:
    enabled: bool = True
    interval_minutes: int = 15
    visible_seconds: int = 9
    show_on_start: bool = True
    show_on_all_screens: bool = True
    close_on_click: bool = True
    blur_radius: int = 36
    fade_duration_ms: int = 1200
    background_darkness: int = 145
    start_with_windows: bool = False

    def normalized(self) -> "AppSettings":
        self.interval_minutes = clamp(self.interval_minutes, 1, 240)
        self.visible_seconds = clamp(self.visible_seconds, 3, 90)
        self.blur_radius = clamp(self.blur_radius, 8, 80)
        self.fade_duration_ms = clamp(self.fade_duration_ms, 300, 3500)
        self.background_darkness = clamp(self.background_darkness, 0, 220)
        return self

    def to_dict(self) -> dict:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class Dhikr:
    id: int
    category: str
    text: str
    repeat: int
    time: str
    virtue: str
    source_type: str

    def meta_text(self) -> str:
        repeat_text = "مرة واحدة" if self.repeat == 1 else f"{self.repeat} مرات"
        return f"{self.category} • {self.time} • {repeat_text}"

    def virtue_text(self) -> str:
        if self.source_type:
            return f"{self.virtue} — {self.source_type}"
        return self.virtue


@dataclass(frozen=True)
class MomentTheme:
    tint: QColor
    accent: QColor
    text: QColor
    muted_text: QColor


DHIKR_LIST = (
    Dhikr(1, "أذكار عامة", "سُبْحَانَ اللَّهِ", 1, "أي وقت", "من أحب الكلام إلى الله.", "حديث صحيح"),
    Dhikr(2, "أذكار عامة", "الْحَمْدُ لِلَّهِ", 1, "أي وقت", "كلمة عظيمة من أفضل الذكر والثناء على الله.", "حديث صحيح"),
    Dhikr(3, "أذكار عامة", "لَا إِلَهَ إِلَّا اللَّهُ", 1, "أي وقت", "أفضل كلمة التوحيد وأعظم الذكر.", "حديث صحيح"),
    Dhikr(4, "أذكار عامة", "اللَّهُ أَكْبَرُ", 1, "أي وقت", "تعظيم لله وهي من أحب الكلام إليه.", "حديث صحيح"),
    Dhikr(5, "أذكار عامة", "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ", 100, "يوميًا", "تُحط الخطايا ولو كانت مثل زبد البحر.", "حديث صحيح"),
    Dhikr(6, "أذكار عامة", "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ", 1, "أي وقت", "كلمتان خفيفتان على اللسان ثقيلتان في الميزان.", "حديث صحيح"),
    Dhikr(7, "أذكار عامة", "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ", 1, "أي وقت", "كنز من كنوز الجنة.", "حديث صحيح"),
    Dhikr(8, "استغفار", "أَسْتَغْفِرُ اللَّهَ", 1, "أي وقت", "سبب للمغفرة وراحة القلب.", "ذكر مشروع"),
    Dhikr(9, "استغفار", "أَسْتَغْفِرُ اللَّهَ وَأَتُوبُ إِلَيْهِ", 100, "يوميًا", "اقتداء بالنبي ﷺ في كثرة الاستغفار.", "حديث صحيح"),
    Dhikr(10, "الصلاة على النبي", "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ", 1, "أي وقت", "من صلى على النبي ﷺ صلاة صلى الله عليه بها عشرًا.", "حديث صحيح"),
    Dhikr(11, "أذكار الصباح والمساء", "رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ ﷺ نَبِيًّا", 3, "الصباح والمساء", "من الأذكار العظيمة في الرضا بالله والإسلام والنبي ﷺ.", "حديث حسن"),
    Dhikr(12, "أذكار الصباح والمساء", "بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ، وَهُوَ السَّمِيعُ الْعَلِيمُ", 3, "الصباح والمساء", "سبب للحفظ من الضرر بإذن الله.", "حديث صحيح"),
    Dhikr(13, "أذكار الصباح والمساء", "أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ", 3, "المساء", "حفظ ووقاية من الشرور بإذن الله.", "حديث صحيح"),
    Dhikr(14, "أذكار الصباح والمساء", "حَسْبِيَ اللَّهُ لَا إِلَهَ إِلَّا هُوَ، عَلَيْهِ تَوَكَّلْتُ، وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ", 7, "الصباح والمساء", "كفاية للعبد فيما أهمه بإذن الله.", "أثر مشهور"),
    Dhikr(15, "أذكار الصباح والمساء", "اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ", 1, "الصباح", "تجديد التوكل على الله في بداية اليوم.", "حديث"),
    Dhikr(16, "أذكار الصباح والمساء", "اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ", 1, "المساء", "تجديد التوكل على الله في نهاية اليوم.", "حديث"),
    Dhikr(17, "أذكار الصباح والمساء", "اللَّهُمَّ أَنْتَ رَبِّي، لَا إِلَهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَى عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي، فَاغْفِرْ لِي، فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ", 1, "الصباح والمساء", "سيد الاستغفار، ومن أعظم صيغ طلب المغفرة.", "حديث صحيح"),
    Dhikr(18, "أذكار بعد الصلاة", "أَسْتَغْفِرُ اللَّهَ", 3, "بعد الصلاة", "افتتاح الذكر بعد الفريضة بطلب المغفرة.", "حديث صحيح"),
    Dhikr(19, "أذكار بعد الصلاة", "اللَّهُمَّ أَنْتَ السَّلَامُ، وَمِنْكَ السَّلَامُ، تَبَارَكْتَ يَا ذَا الْجَلَالِ وَالْإِكْرَامِ", 1, "بعد الصلاة", "ثناء عظيم على الله بعد الصلاة.", "حديث صحيح"),
    Dhikr(20, "أذكار بعد الصلاة", "سُبْحَانَ اللَّهِ", 33, "بعد الصلاة", "من الذكر المشروع بعد الصلوات المكتوبة.", "حديث صحيح"),
    Dhikr(21, "أذكار بعد الصلاة", "الْحَمْدُ لِلَّهِ", 33, "بعد الصلاة", "من الذكر المشروع بعد الصلوات المكتوبة.", "حديث صحيح"),
    Dhikr(22, "أذكار بعد الصلاة", "اللَّهُ أَكْبَرُ", 33, "بعد الصلاة", "من الذكر المشروع بعد الصلوات المكتوبة.", "حديث صحيح"),
    Dhikr(23, "أذكار بعد الصلاة", "لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ، وَلَهُ الْحَمْدُ، وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ", 1, "بعد الصلاة", "تمام المئة بعد التسبيح والتحميد والتكبير.", "حديث صحيح"),
    Dhikr(24, "أذكار النوم", "بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا", 1, "قبل النوم", "ذكر نبوي عند النوم.", "حديث صحيح"),
    Dhikr(25, "أذكار النوم", "اللَّهُمَّ قِنِي عَذَابَكَ يَوْمَ تَبْعَثُ عِبَادَكَ", 3, "قبل النوم", "دعاء نبوي بالحفظ من عذاب يوم القيامة.", "حديث"),
    Dhikr(26, "أذكار النوم", "سُبْحَانَ اللَّهِ", 33, "قبل النوم", "من وصية النبي ﷺ لفاطمة وعلي رضي الله عنهما.", "حديث صحيح"),
    Dhikr(27, "أذكار النوم", "الْحَمْدُ لِلَّهِ", 33, "قبل النوم", "من الذكر المشروع قبل النوم.", "حديث صحيح"),
    Dhikr(28, "أذكار النوم", "اللَّهُ أَكْبَرُ", 34, "قبل النوم", "خير من خادم كما أرشد النبي ﷺ.", "حديث صحيح"),
    Dhikr(29, "دعاء وذكر عند الضيق", "لَا إِلَهَ إِلَّا أَنْتَ سُبْحَانَكَ، إِنِّي كُنْتُ مِنَ الظَّالِمِينَ", 1, "عند الضيق", "دعاء ذي النون، عظيم في كشف الكرب بإذن الله.", "قرآن وحديث"),
    Dhikr(30, "دعاء وذكر عند الضيق", "حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ", 1, "عند الخوف أو الشدة", "ذكر عظيم في التوكل على الله.", "قرآن"),
    Dhikr(31, "دعاء وذكر عند الضيق", "يَا حَيُّ يَا قَيُّومُ، بِرَحْمَتِكَ أَسْتَغِيثُ", 1, "عند الهم", "استغاثة بالله وطلب إصلاح الحال.", "حديث حسن"),
    Dhikr(32, "الرزق والتوفيق", "رَبِّ إِنِّي لِمَا أَنْزَلْتَ إِلَيَّ مِنْ خَيْرٍ فَقِيرٌ", 1, "أي وقت", "دعاء قرآني جميل لطلب الخير والرزق.", "قرآن"),
    Dhikr(33, "الرزق والتوفيق", "اللَّهُمَّ اكْفِنِي بِحَلَالِكَ عَنْ حَرَامِكَ، وَأَغْنِنِي بِفَضْلِكَ عَمَّنْ سِوَاكَ", 1, "عند الحاجة", "دعاء نافع في طلب الكفاية والاستغناء بالله.", "حديث حسن"),
    Dhikr(34, "أذكار قصيرة للإشعارات", "اذْكُرِ اللَّهَ يَذْكُرْكَ", 1, "إشعار", "تذكير لطيف بالمداومة على الذكر.", "تذكير عام"),
    Dhikr(35, "أذكار قصيرة للإشعارات", "صَلِّ عَلَى النَّبِيِّ ﷺ", 1, "إشعار", "الصلاة على النبي سبب لنيل صلاة الله على العبد.", "حديث صحيح"),
    Dhikr(36, "أذكار قصيرة للإشعارات", "دَقِيقَةُ ذِكْرٍ: سُبْحَانَ اللَّهِ وَبِحَمْدِهِ", 1, "إشعار", "ذكر خفيف وأجره عظيم.", "حديث صحيح"),
    Dhikr(37, "أذكار قصيرة للإشعارات", "لَا تَنْسَ: أَسْتَغْفِرُ اللَّهَ", 1, "إشعار", "تذكير بالاستغفار وتجديد التوبة.", "تذكير عام"),
    Dhikr(38, "أذكار قرآنية", "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً، وَفِي الْآخِرَةِ حَسَنَةً، وَقِنَا عَذَابَ النَّارِ", 1, "أي وقت", "دعاء جامع لخيري الدنيا والآخرة.", "قرآن"),
    Dhikr(39, "أذكار قرآنية", "رَبِّ زِدْنِي عِلْمًا", 1, "قبل التعلم", "دعاء قرآني لطلب زيادة العلم.", "قرآن"),
    Dhikr(40, "أذكار قرآنية", "رَبِّ اشْرَحْ لِي صَدْرِي، وَيَسِّرْ لِي أَمْرِي", 1, "قبل أمر مهم", "دعاء قرآني للتيسير وشرح الصدر.", "قرآن"),
)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def choose_dhikr() -> Dhikr:
    hour = datetime.now().hour
    choices = [dhikr for dhikr in DHIKR_LIST if is_dhikr_suitable_now(dhikr, hour)]
    if not choices:
        choices = list(DHIKR_LIST)

    return random.choice(choices)


def is_dhikr_suitable_now(dhikr: Dhikr, hour: int) -> bool:
    if dhikr.time in ("أي وقت", "يوميًا", "إشعار"):
        return True

    if dhikr.time == "الصباح":
        return 4 <= hour < 12

    if dhikr.time == "المساء":
        return 16 <= hour < 24

    if dhikr.time == "الصباح والمساء":
        return 4 <= hour < 12 or 16 <= hour < 24

    if dhikr.time == "قبل النوم":
        return hour >= 21 or hour < 4

    return False


def theme_for_now() -> MomentTheme:
    hour = datetime.now().hour

    if 4 <= hour < 8:
        return MomentTheme(
            tint=QColor(20, 38, 50, 118),
            accent=QColor(245, 190, 105),
            text=QColor(255, 250, 240),
            muted_text=QColor(235, 220, 190),
        )

    if 8 <= hour < 16:
        return MomentTheme(
            tint=QColor(18, 68, 72, 104),
            accent=QColor(93, 210, 184),
            text=QColor(245, 255, 251),
            muted_text=QColor(204, 240, 230),
        )

    if 16 <= hour < 20:
        return MomentTheme(
            tint=QColor(76, 42, 54, 118),
            accent=QColor(240, 151, 104),
            text=QColor(255, 246, 236),
            muted_text=QColor(242, 205, 184),
        )

    return MomentTheme(
        tint=QColor(14, 22, 40, 136),
        accent=QColor(139, 184, 255),
        text=QColor(242, 247, 255),
        muted_text=QColor(198, 214, 240),
    )


def arabic_font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    preferred_fonts = (
        "Amiri",
        "Aref Ruqaa",
        "Noto Naskh Arabic",
        "Segoe UI",
        "Tahoma",
    )
    available_fonts = set(QFontDatabase.families())

    for family in preferred_fonts:
        if family in available_fonts:
            return QFont(family, size, weight)

    return QFont("Arial", size, weight)


def rgba(color: QColor, alpha: int | None = None) -> str:
    value = QColor(color)
    if alpha is not None:
        value.setAlpha(alpha)

    return f"rgba({value.red()}, {value.green()}, {value.blue()}, {value.alpha()})"


def resource_path(relative_path: Path) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def app_icon_path() -> Path:
    return resource_path(ICON_RELATIVE_PATH)


def app_icon() -> QIcon:
    icon = QIcon(str(app_icon_path()))
    if not icon.isNull():
        return icon
    return QIcon()


def startup_python_executable() -> Path:
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return executable

    pythonw = executable.with_name("pythonw.exe")
    return pythonw if pythonw.exists() else executable


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{startup_python_executable()}"'

    return f'"{startup_python_executable()}" "{Path(__file__).resolve()}"'


def startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_shortcut_path() -> Path:
    return startup_folder() / STARTUP_SHORTCUT_NAME


def remove_legacy_registry_startup() -> None:
    if sys.platform != "win32":
        return

    try:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            try:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
            except FileNotFoundError:
                pass
    except OSError:
        pass


def create_startup_shortcut() -> bool:
    if sys.platform != "win32":
        return False

    shortcut_path = startup_shortcut_path()
    if getattr(sys, "frozen", False):
        target_path = Path(sys.executable).resolve()
        arguments = ""
        working_directory = target_path.parent
    else:
        script_path = Path(__file__).resolve()
        target_path = startup_python_executable()
        arguments = f'"{script_path}"'
        working_directory = script_path.parent

    shortcut_path.parent.mkdir(parents=True, exist_ok=True)

    powershell = f"""
    $shortcutPath = {json.dumps(str(shortcut_path), ensure_ascii=False)}
    $targetPath = {json.dumps(str(target_path), ensure_ascii=False)}
    $arguments = {json.dumps(arguments, ensure_ascii=False)}
    $workingDirectory = {json.dumps(str(working_directory), ensure_ascii=False)}
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $targetPath
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = $workingDirectory
    $shortcut.WindowStyle = 7
    $shortcut.Description = {json.dumps(APP_TITLE, ensure_ascii=False)}
    $shortcut.IconLocation = $targetPath + ',0'
    $shortcut.Save()
    """
    encoded = base64.b64encode(powershell.encode("utf-16le")).decode("ascii")

    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    return completed.returncode == 0 and shortcut_path.exists()


def is_start_with_windows_enabled() -> bool:
    if sys.platform != "win32":
        return False

    if startup_shortcut_path().exists():
        return True

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return str(value).strip() == startup_command()
    except OSError:
        return False


def set_start_with_windows(enabled: bool) -> bool:
    if sys.platform != "win32":
        return False

    if enabled:
        shortcut_ok = create_startup_shortcut()
        remove_legacy_registry_startup()
        return shortcut_ok

    try:
        startup_shortcut_path().unlink(missing_ok=True)
    except OSError:
        return False

    remove_legacy_registry_startup()
    return not startup_shortcut_path().exists()


class SettingsStore:
    def __init__(self) -> None:
        self.settings = self.load()

    def load(self) -> AppSettings:
        data = {}
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}

        valid_keys = {field.name for field in fields(AppSettings)}
        clean_data = {key: value for key, value in data.items() if key in valid_keys}
        settings = AppSettings(**clean_data).normalized()
        settings.start_with_windows = is_start_with_windows_enabled()
        return settings

    def save(self) -> bool:
        requested_startup = self.settings.start_with_windows
        startup_write_ok = set_start_with_windows(requested_startup)
        self.settings.start_with_windows = is_start_with_windows_enabled()

        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(self.settings.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return False

        return startup_write_ok and self.settings.start_with_windows == requested_startup

    def update(self, settings: AppSettings) -> bool:
        self.settings = settings.normalized()
        return self.save()


class DhikrMomentOverlay(QWidget):
    def __init__(
        self,
        dhikr: Dhikr,
        settings: AppSettings,
        screen=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.dhikr = dhikr
        self.settings = settings
        self.screen_ref = screen or QGuiApplication.primaryScreen()
        self.theme = theme_for_now()
        self._closing = False
        self._glow_alpha = 28
        self._text_target = QPoint(0, 0)
        self._background = QPixmap()

        if self.screen_ref is None:
            raise RuntimeError("No screen is available.")

        self._setup_window()
        self._background = self._grab_blurred_background()
        self._setup_text()

    def _setup_window(self) -> None:
        self.setGeometry(self.screen_ref.geometry())
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def _setup_text(self) -> None:
        text_width = max(320, min(1040, self.width() - 160))
        details_width = max(300, min(760, text_width - 100))

        self.text_group = QWidget(self)
        self.text_group.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.text_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        shadow = QGraphicsDropShadowEffect(self.text_group)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 210))
        self.text_group.setGraphicsEffect(shadow)
        self.text_shadow = shadow

        layout = QVBoxLayout(self.text_group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.text_label = QLabel(self.dhikr.text, self.text_group)
        self.text_label.setFixedWidth(text_width)
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setFont(arabic_font(self._text_size(), QFont.Weight.Bold))
        self.text_label.setStyleSheet(
            f"""
            QLabel {{
                color: {rgba(self.theme.text, 252)};
                background: transparent;
            }}
            """
        )

        self.meta_label = QLabel(self.dhikr.meta_text(), self.text_group)
        self.meta_label.setFixedWidth(details_width)
        self.meta_label.setWordWrap(True)
        self.meta_label.setTextFormat(Qt.TextFormat.PlainText)
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.meta_label.setFont(arabic_font(self._meta_size(), QFont.Weight.Medium))
        self.meta_label.setStyleSheet(
            f"""
            QLabel {{
                color: {rgba(self.theme.muted_text, 232)};
                background: transparent;
            }}
            """
        )

        self.virtue_label = QLabel(self.dhikr.virtue_text(), self.text_group)
        self.virtue_label.setFixedWidth(details_width)
        self.virtue_label.setWordWrap(True)
        self.virtue_label.setTextFormat(Qt.TextFormat.PlainText)
        self.virtue_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.virtue_label.setFont(arabic_font(self._virtue_size()))
        self.virtue_label.setStyleSheet(
            f"""
            QLabel {{
                color: {rgba(self.theme.muted_text, 214)};
                background: transparent;
            }}
            """
        )

        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.meta_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.virtue_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self._place_text(offset_y=26)

    def _text_size(self) -> int:
        if self.width() < 700:
            if len(self.dhikr.text) > 150:
                return 24
            if len(self.dhikr.text) > 95:
                return 27
            return 34
        if len(self.dhikr.text) > 190:
            return 30
        if len(self.dhikr.text) > 125:
            return 34
        if len(self.dhikr.text) > 70:
            return 40
        if len(self.dhikr.text) > 45:
            return 48
        return 60

    def _meta_size(self) -> int:
        return 16 if self.width() < 700 else 19

    def _virtue_size(self) -> int:
        return 15 if self.width() < 700 else 18

    def _place_text(self, offset_y: int = 0) -> None:
        self.text_group.adjustSize()
        x = (self.width() - self.text_group.width()) // 2
        y = (self.height() - self.text_group.height()) // 2
        self._text_target = QPoint(x, y)
        self.text_group.move(x, y + offset_y)

    def _grab_blurred_background(self) -> QPixmap:
        screenshot = self.screen_ref.grabWindow(
            0,
            0,
            0,
            self.screen_ref.geometry().width(),
            self.screen_ref.geometry().height(),
        )

        if screenshot.isNull():
            fallback = QPixmap(self.size())
            fallback.fill(QColor(10, 14, 20))
            return fallback

        small = screenshot.scaled(
            max(1, screenshot.width() // 3),
            max(1, screenshot.height() // 3),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        blurred_small = self._blur_pixmap(small, max(8, self.settings.blur_radius // 2))
        return blurred_small.scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _blur_pixmap(self, pixmap: QPixmap, radius: int) -> QPixmap:
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

        item = QGraphicsPixmapItem(pixmap)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(radius)
        item.setGraphicsEffect(blur)
        scene.addItem(item)

        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        scene.render(painter, QRectF(result.rect()), QRectF(pixmap.rect()))
        painter.end()

        return result

    def show_moment(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

        self._start_fade_in()
        self._start_text_motion()
        self._start_breathing_light()

        QTimer.singleShot(self.settings.visible_seconds * 1000, self.fade_out)

    def _start_fade_in(self) -> None:
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_in_animation.setDuration(self.settings.fade_duration_ms)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_in_animation.start()

    def _start_text_motion(self) -> None:
        start = QPoint(self._text_target.x(), self._text_target.y() + 26)
        self.text_group.move(start)

        self.text_motion = QPropertyAnimation(self.text_group, b"pos", self)
        self.text_motion.setDuration(self.settings.fade_duration_ms + 250)
        self.text_motion.setStartValue(start)
        self.text_motion.setEndValue(self._text_target)
        self.text_motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.text_motion.start()

    def _start_breathing_light(self) -> None:
        self.breath_animation = QVariantAnimation(self)
        self.breath_animation.setDuration(3200)
        self.breath_animation.setStartValue(18)
        self.breath_animation.setEndValue(44)
        self.breath_animation.setLoopCount(-1)
        self.breath_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.breath_animation.valueChanged.connect(self._set_glow_alpha)
        self.breath_animation.start()

    def _set_glow_alpha(self, value) -> None:
        self._glow_alpha = int(value)
        self.text_shadow.setBlurRadius(28 + (self._glow_alpha / 4))
        self.update()

    def fade_out(self) -> None:
        if self._closing:
            return

        self._closing = True

        if hasattr(self, "breath_animation"):
            self.breath_animation.stop()

        duration = self.settings.fade_duration_ms + 350
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_out_animation.setDuration(duration)
        self.fade_out_animation.setStartValue(self.windowOpacity())
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_out_animation.finished.connect(self.close)
        self.fade_out_animation.start()

        end = QPoint(self._text_target.x(), self._text_target.y() - 22)
        self.text_exit_motion = QPropertyAnimation(self.text_group, b"pos", self)
        self.text_exit_motion.setDuration(duration)
        self.text_exit_motion.setStartValue(self.text_group.pos())
        self.text_exit_motion.setEndValue(end)
        self.text_exit_motion.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.text_exit_motion.start()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self._background.isNull():
            painter.fillRect(self.rect(), QColor(10, 14, 20))
        else:
            painter.drawPixmap(self.rect(), self._background)

        painter.fillRect(self.rect(), QColor(0, 0, 0, self.settings.background_darkness))

        wash = QLinearGradient(0, 0, self.width(), self.height())
        wash.setColorAt(0.0, self.theme.tint)
        wash.setColorAt(0.55, QColor(0, 0, 0, 42))

        accent = QColor(self.theme.accent)
        accent.setAlpha(34)
        wash.setColorAt(1.0, accent)
        painter.fillRect(self.rect(), QBrush(wash))

        center = QPointF(self.rect().center())
        glow = QRadialGradient(center, min(self.width(), self.height()) * 0.34)
        glow_color = QColor(self.theme.accent)
        glow_color.setAlpha(self._glow_alpha)
        glow.setColorAt(0.0, glow_color)
        glow.setColorAt(0.42, QColor(255, 255, 255, 8))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), QBrush(glow))

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space):
            self.fade_out()
            return

        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.settings.close_on_click:
            self.fade_out()
            return

        super().mousePressEvent(event)


class DhikrMomentScheduler:
    def __init__(self, store: SettingsStore) -> None:
        self.store = store
        self.overlays: list[DhikrMomentOverlay] = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_dhikr_moment)
        self.apply_settings()

        if self.store.settings.enabled and self.store.settings.show_on_start:
            QTimer.singleShot(700, self.show_dhikr_moment)

    def apply_settings(self) -> None:
        self.timer.stop()
        if self.store.settings.enabled:
            interval_ms = max(1, self.store.settings.interval_minutes) * 60 * 1000
            self.timer.start(interval_ms)

    def show_dhikr_moment(self, force: bool = False) -> None:
        if not force and not self.store.settings.enabled:
            return

        if any(overlay.isVisible() for overlay in self.overlays):
            return

        dhikr = choose_dhikr()
        if self.store.settings.show_on_all_screens:
            screens = QGuiApplication.screens()
        else:
            screens = [QGuiApplication.primaryScreen()]

        self.overlays = []
        for screen in screens:
            if screen is None:
                continue

            overlay = DhikrMomentOverlay(dhikr, self.store.settings, screen)
            overlay.destroyed.connect(lambda _=None, item=overlay: self._forget(item))
            self.overlays.append(overlay)
            overlay.show_moment()

    def close_overlays(self) -> None:
        for overlay in list(self.overlays):
            overlay.close()
        self.overlays.clear()

    def _forget(self, overlay: DhikrMomentOverlay) -> None:
        if overlay in self.overlays:
            self.overlays.remove(overlay)


class SettingsWindow(QDialog):
    def __init__(self, store: SettingsStore, scheduler: DhikrMomentScheduler, on_saved) -> None:
        super().__init__()
        self.store = store
        self.scheduler = scheduler
        self.on_saved = on_saved

        self.setWindowTitle(f"إعدادات {APP_TITLE}")
        self.setWindowIcon(app_icon())
        self.setMinimumWidth(460)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #101820;
                color: #f4f7f8;
            }
            QLabel, QCheckBox {
                color: #f4f7f8;
                font-size: 13px;
            }
            QSpinBox {
                background-color: #192630;
                color: #f4f7f8;
                border: 1px solid #38515c;
                border-radius: 6px;
                padding: 6px 8px;
                min-height: 24px;
            }
            QPushButton {
                background-color: #2f8f83;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 9px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #37a295;
            }
            QPushButton#secondaryButton {
                background-color: #23323d;
            }
            QPushButton#secondaryButton:hover {
                background-color: #2f414d;
            }
            """
        )

        self._build_ui()
        self.load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 18)
        root.setSpacing(16)

        title = QLabel(APP_TITLE)
        title.setFont(arabic_font(18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("تحكم بسيط في لحظة الذكر التي تظهر على الشاشة.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #b7c7ce;")

        root.addWidget(title)
        root.addWidget(subtitle)

        self.enabled_check = QCheckBox("تفعيل ظهور الأذكار")
        self.show_on_start_check = QCheckBox("عرض ذكر عند تشغيل الأداة")
        self.all_screens_check = QCheckBox("العرض على كل الشاشات")
        self.close_on_click_check = QCheckBox("إخفاء الذكر عند الضغط بالماوس")
        self.startup_check = QCheckBox("تشغيل الأداة تلقائيا مع ويندوز")

        checks = QVBoxLayout()
        checks.setSpacing(8)
        checks.addWidget(self.enabled_check)
        checks.addWidget(self.show_on_start_check)
        checks.addWidget(self.all_screens_check)
        checks.addWidget(self.close_on_click_check)
        checks.addWidget(self.startup_check)
        root.addLayout(checks)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.interval_spin = self._spin(1, 240, " دقيقة")
        self.visible_spin = self._spin(3, 90, " ثانية")
        self.blur_spin = self._spin(8, 80)
        self.darkness_spin = self._spin(0, 220)
        self.fade_spin = self._spin(300, 3500, " ms")

        form.addRow("يظهر كل", self.interval_spin)
        form.addRow("مدة الظهور", self.visible_spin)
        form.addRow("قوة البلور", self.blur_spin)
        form.addRow("تعتيم الخلفية", self.darkness_spin)
        form.addRow("نعومة الحركة", self.fade_spin)
        root.addLayout(form)

        buttons = QHBoxLayout()

        self.show_now_button = QPushButton("إظهار الآن")
        self.save_button = QPushButton("حفظ")
        self.close_button = QPushButton("إغلاق")
        self.close_button.setObjectName("secondaryButton")

        self.show_now_button.clicked.connect(lambda: self.scheduler.show_dhikr_moment(force=True))
        self.save_button.clicked.connect(self.save_values)
        self.close_button.clicked.connect(self.hide)

        buttons.addWidget(self.show_now_button)
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)

    def _spin(self, minimum: int, maximum: int, suffix: str = "") -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(minimum, maximum)
        spin.setSuffix(suffix)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return spin

    def load_values(self) -> None:
        settings = self.store.settings
        self.enabled_check.setChecked(settings.enabled)
        self.show_on_start_check.setChecked(settings.show_on_start)
        self.all_screens_check.setChecked(settings.show_on_all_screens)
        self.close_on_click_check.setChecked(settings.close_on_click)
        self.startup_check.setChecked(settings.start_with_windows)
        self.interval_spin.setValue(settings.interval_minutes)
        self.visible_spin.setValue(settings.visible_seconds)
        self.blur_spin.setValue(settings.blur_radius)
        self.darkness_spin.setValue(settings.background_darkness)
        self.fade_spin.setValue(settings.fade_duration_ms)

    def save_values(self) -> None:
        settings = AppSettings(
            enabled=self.enabled_check.isChecked(),
            interval_minutes=self.interval_spin.value(),
            visible_seconds=self.visible_spin.value(),
            show_on_start=self.show_on_start_check.isChecked(),
            show_on_all_screens=self.all_screens_check.isChecked(),
            close_on_click=self.close_on_click_check.isChecked(),
            blur_radius=self.blur_spin.value(),
            fade_duration_ms=self.fade_spin.value(),
            background_darkness=self.darkness_spin.value(),
            start_with_windows=self.startup_check.isChecked(),
        )

        ok = self.store.update(settings)
        self.scheduler.apply_settings()
        self.load_values()
        self.on_saved(ok)

        if not ok:
            QMessageBox.warning(
                self,
                APP_TITLE,
                "تم حفظ الإعدادات، لكن لم أستطع ضبط التشغيل التلقائي مع ويندوز.",
            )


class TrayController:
    def __init__(self, store: SettingsStore, scheduler: DhikrMomentScheduler) -> None:
        self.store = store
        self.scheduler = scheduler
        self.settings_window = SettingsWindow(store, scheduler, self._after_settings_saved)

        self.tray = QSystemTrayIcon(app_icon())
        self.tray.setToolTip(APP_TITLE)
        self.tray.activated.connect(self._on_tray_activated)

        self.menu = QMenu()
        self.show_now_action = QAction("إظهار ذكر الآن")
        self.enabled_action = QAction()
        self.settings_action = QAction("الإعدادات")
        self.startup_action = QAction("تشغيل مع ويندوز")
        self.quit_action = QAction("خروج")

        self.startup_action.setCheckable(True)

        self.show_now_action.triggered.connect(lambda: self.scheduler.show_dhikr_moment(force=True))
        self.enabled_action.triggered.connect(self.toggle_enabled)
        self.settings_action.triggered.connect(self.show_settings)
        self.startup_action.triggered.connect(self.toggle_startup)
        self.quit_action.triggered.connect(self.quit_app)

        self.menu.addAction(self.show_now_action)
        self.menu.addAction(self.enabled_action)
        self.menu.addSeparator()
        self.menu.addAction(self.settings_action)
        self.menu.addAction(self.startup_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self.tray.setContextMenu(self.menu)
        self.update_actions()
        self.tray.show()

        if QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(APP_TITLE, "الأداة تعمل الآن بجانب الساعة.", QSystemTrayIcon.MessageIcon.Information, 2500)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_settings()

    def show_settings(self) -> None:
        self.settings_window.load_values()
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def toggle_enabled(self) -> None:
        self.store.settings.enabled = not self.store.settings.enabled
        ok = self.store.save()
        self.scheduler.apply_settings()
        self._after_settings_saved(ok)

    def toggle_startup(self, checked: bool) -> None:
        self.store.settings.start_with_windows = checked
        ok = self.store.save()
        self._after_settings_saved(ok)

    def _after_settings_saved(self, ok: bool = True) -> None:
        self.update_actions()
        if not ok and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(
                APP_TITLE,
                "لم أستطع ضبط التشغيل التلقائي. جرّب تشغيل الأداة كمسؤول لو احتجت.",
                QSystemTrayIcon.MessageIcon.Warning,
                3500,
            )

    def update_actions(self) -> None:
        if self.store.settings.enabled:
            self.enabled_action.setText("إيقاف مؤقت")
            self.tray.setToolTip(f"{APP_TITLE} - تعمل")
        else:
            self.enabled_action.setText("تشغيل")
            self.tray.setToolTip(f"{APP_TITLE} - متوقفة مؤقتا")

        self.startup_action.setChecked(self.store.settings.start_with_windows)

    def quit_app(self) -> None:
        self.scheduler.close_overlays()
        self.tray.hide()
        QApplication.quit()


def install_startup_from_cli(enabled: bool) -> int:
    store = SettingsStore()
    store.settings.start_with_windows = enabled
    ok = store.save()

    if ok:
        print("تم تفعيل التشغيل التلقائي." if enabled else "تم إلغاء التشغيل التلقائي.")
        return 0

    print("تعذر تعديل التشغيل التلقائي.")
    return 1


def main() -> int:
    if "--install-startup" in sys.argv:
        return install_startup_from_cli(True)

    if "--uninstall-startup" in sys.argv:
        return install_startup_from_cli(False)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)

    store = SettingsStore()
    scheduler = DhikrMomentScheduler(store)
    tray = TrayController(store, scheduler)

    app.scheduler = scheduler
    app.tray_controller = tray

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
