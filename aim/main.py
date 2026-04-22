"""
╔══════════════════════════════════════════════════════════════════════════╗
║   NUKE ASSIST  -  v7.0                                                   ║
║   Keyboard/Mouse -> Xbox Virtual Controller -> COD Aim Assist            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import sys, os, time, math, threading, subprocess, json, ctypes, random, importlib, shutil, re, zipfile
import urllib.request, tempfile, hashlib, winreg
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Set

try:
    WINDOWS = True
    _ = winreg.HKEY_LOCAL_MACHINE
except Exception:
    WINDOWS = False

try:
    import vgamepad as vg
    VG_OK = True
except ImportError:
    VG_OK = False

try:
    from pynput import keyboard as kb_mod, mouse as ms_mod
    from pynput.keyboard import Key
    from pynput.mouse import Button
    PN_OK = True
except ImportError:
    PN_OK = False

try:
    import tkinter as tk
    from tkinter import font as tkfont
    TK_OK = True
except ImportError:
    TK_OK = False

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── URLs de download ──────────────────────────────────────────────────────
VIGEM_URL   = "https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe"
HIDHIDE_URL = "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHide_1.5.230_x64.exe"
M2J_RELEASE_API = "https://api.github.com/repos/memethyl/Mouse2Joystick/releases/latest"
M2J_FALLBACK_ZIP = "https://github.com/memethyl/Mouse2Joystick/releases/download/v1.2.1/Mouse2Joystick.zip"
JOYTOKEY_URL = "https://joytokey.net/download/JoyToKey_en.zip"

APP_TITLE_DEFAULT = "NUKE ASSIST"
APP_TITLE_STREAM  = "ShrekWallpaper"
CLI_ARGS = {str(a).strip().lower() for a in sys.argv[1:]}
CMD_MOUSE_LOG_DEFAULT = (
    "--mouse-log" in CLI_ARGS
    or "--cmd-mouse-log" in CLI_ARGS
    or "--mouse-cmd" in CLI_ARGS
)

# ── Pasta oculta para drivers/cache ──────────────────────────────────────
# Fica em %TEMP%\nukeassist — oculta para o sistema
_HIDDEN_DIR = os.path.join(tempfile.gettempdir(), "nukeassist")

def _ensure_hidden_dir():
    """Cria a pasta nukeassist em Temp e marca-a como oculta + sistema."""
    try:
        os.makedirs(_HIDDEN_DIR, exist_ok=True)
        # Marcar como Hidden + System no Windows
        ctypes.windll.kernel32.SetFileAttributesW(
            _HIDDEN_DIR,
            0x02 | 0x04  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
        )
    except Exception:
        pass
    return _HIDDEN_DIR


def _ensure_debug_console():
    """
    Garante consola ativa para logs de debug mesmo em build sem CMD.
    """
    if sys.platform != "win32":
        return
    try:
        k32 = ctypes.windll.kernel32
        if not k32.GetConsoleWindow():
            if k32.AllocConsole():
                try:
                    sys.stdout = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")
                    sys.stderr = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")
                except Exception:
                    pass
        try:
            k32.SetConsoleTitleW("NUKE ASSIST - Mouse Log")
        except Exception:
            pass
    except Exception:
        pass

COD_PROCESSES = [
    "cod.exe","BlackOps6.exe","BlackOps7.exe","Warzone.exe",
    "ModernWarfare.exe","cod_warzone.exe","CoDWZ.exe",
    "MW2.exe","MW3.exe","codmw.exe","cod_bo.exe","cod_hq.exe","codhq.exe",
    "BlackOps.exe","bo6.exe","bo7.exe",
]

DEFAULT_KEY_MAP = {
    "w":"LS_UP","a":"LS_LEFT","s":"LS_DOWN","d":"LS_RIGHT",
    "space":"A","ctrl":"B","c":"B",
    "q":"LB","g":"RB","e":"X","r":"X","f":"Y",
    "shift":"L3","tab":"BACK","escape":"START",
    "v":"DDOWN","t":"DUP","1":"DLEFT","2":"DRIGHT",
}

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE    = os.path.join(APP_DIR, "config.json")
ASSETS_DIR     = os.path.join(APP_DIR, "assets")
CTRL_IMG_LOCAL = os.path.join(ASSETS_DIR, "xbox360_controller.png")
PS_CTRL_IMG    = os.path.join(ASSETS_DIR, "ps5_controller.png")
NUKE_TITLE_IMG = os.path.join(ASSETS_DIR, "NUKE_ASSIST.png")
SHREK_IMG      = os.path.join(ASSETS_DIR, "stream_shrek.jpg")
# fallbacks na raiz e uploads
PS_CTRL_FALLBACK    = os.path.join(APP_DIR, "ps5_controller.png")
NUKE_TITLE_FALLBACK = os.path.join(APP_DIR, "NUKE_ASSIST.png")
SHREK_FALLBACK      = os.path.join(APP_DIR, "stream_shrek.jpg")
CTRL_IMG_FALLBACK   = os.path.join(APP_DIR, "xbox360_controller.png")
# Pasta oculta nukeassist (drivers cache)
_NUKEASSIST_DIR = _ensure_hidden_dir()
# Ficheiro de estado de instalação
_INSTALL_STATE  = os.path.join(_NUKEASSIST_DIR, "state.json")
M2J_DIR         = os.path.join(_NUKEASSIST_DIR, "mouse2joystick")
M2J_EXE         = os.path.join(M2J_DIR, "Mouse2Joystick.exe")
JOYTOKEY_DIR    = os.path.join(_NUKEASSIST_DIR, "joytokey")
JOYTOKEY_EXE    = os.path.join(JOYTOKEY_DIR, "JoyToKey.exe")


# =============================================================================
#  CONFIG
# =============================================================================
@dataclass
class Config:
    sens_x: float = 4200.0
    sens_y: float = 3900.0
    deadzone: float = 0.03
    aim_curve: str = "cod"
    aim_strength: float = 0.97
    aim_magnet: float = 0.25
    recoil_on: bool = True
    recoil_pattern: str = "ar"
    recoil_custom: list = field(default_factory=list)
    humanize: bool = False
    micro_jitter: bool = False
    breathing: bool = False
    rapid_fire: bool = False
    rapid_fire_hz: float = 12.0
    slide_cancel: bool = True
    auto_ping: bool = False
    parachute: bool = True
    stream_mode: bool = False
    glass_style: bool = True
    auto_start_cod: bool = True
    steam_integrate: bool = True
    toggle_key: str = "f12"
    key_map: dict = field(default_factory=lambda: dict(DEFAULT_KEY_MAP))
    smooth_profile_v2: bool = False
    smooth_profile_v3: bool = False
    # Backend externo de mouse (Mouse2Joystick) ativo por defeito.
    # O emulador interno entra em modo compatibilidade para evitar duplo dispositivo.
    external_mouse_app: bool = True

    def save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception:
            pass

    @staticmethod
    def load() -> "Config":
        try:
            with open(CONFIG_FILE) as f:
                d = json.load(f)
            c = Config()
            for k, v in d.items():
                if hasattr(c, k):
                    setattr(c, k, v)
            return c
        except Exception:
            return Config()


# =============================================================================
#  STICK CURVES
#  O aim assist rotacional do COD e ativado quando o jogo recebe input XInput.
#  CRITICO: nao inverter x nem y aqui - a inversao e feita antes de chamar a curva.
#  Curvas apenas ajustam a resposta de magnitude, nunca o sinal.
# =============================================================================
class StickCurves:
    @staticmethod
    def cod(x: float, y: float, strength: float = 0.85):
        """
        Perfil CoD: resposta suave que imita um stick fisico real.
        CORRIGIDO: nao inverte direcao. Usa power-curve simples sem
        slow-zone artificial que causava travagem de sensibilidade.
        """
        mag = math.hypot(x, y)
        if mag < 0.001:
            return (0.0, 0.0)
        factor = min((mag ** 0.88) * strength, 1.0)
        return (x / mag * factor, y / mag * factor)

    @staticmethod
    def linear(x: float, y: float, strength: float = 0.9):
        return (x * strength, y * strength)

    @staticmethod
    def apex(x: float, y: float, strength: float = 0.9):
        mag = math.hypot(x, y)
        if mag < 0.001:
            return (0.0, 0.0)
        factor = min((mag ** 0.7) * (1.0 + mag * 0.3) * strength, 1.0)
        return (x / mag * factor, y / mag * factor)

    @staticmethod
    def raw(x: float, y: float, **_):
        return (x, y)


# =============================================================================
#  HUMANIZER
# =============================================================================
class Humanizer:
    def __init__(self):
        self._jx = self._jy = 0.0
        self._bphase = 0.0
        self._bamp   = random.uniform(0.003, 0.007)
        self._bfreq  = random.uniform(0.18, 0.32)

    def jitter(self, x, y):
        # Jitter mais subtil para nao robotizar o movimento.
        self._jx = self._jx * 0.75 + random.gauss(0, 0.0025) * 0.25
        self._jy = self._jy * 0.75 + random.gauss(0, 0.0018) * 0.25
        return (x + self._jx, y + self._jy)

    def breathe(self, x, y, is_ads):
        if not is_ads:
            return (x, y)
        self._bphase += self._bfreq * 0.0083
        by = math.sin(self._bphase) * self._bamp
        bx = math.cos(self._bphase * 0.6) * self._bamp * 0.35
        if self._bphase > math.pi * 2:
            self._bphase = 0
            self._bamp = random.uniform(0.003, 0.007)
        return (x + bx, y + by)

    def timing(self, base: float) -> float:
        return max(0.001, base + random.gauss(0, 0.0015))

    def reset(self):
        self._bphase = 0
        self._bamp = random.uniform(0.003, 0.007)


# =============================================================================
#  RECOIL ENGINE - Auto No-Recoil
# =============================================================================
class RecoilEngine:
    _EMA_ALPHA = 0.16
    _MAX_COMP  = 0.26
    _NOISE_THR = 0.8
    _BASE_FORCE = 0.010
    _RAMP_RATE = 0.09
    _ADS_BONUS = 0.015
    _MAX_ADAPT = 0.12

    def __init__(self):
        self._on       = False
        self._firing   = False
        self._ema_dy   = 0.0
        self._comp     = 0.0
        self._warmup   = 0
        self._fire_t   = 0.0

    def configure(self, preset: str, custom: list = None):
        # Compatibilidade: mantemos assinatura antiga, mas o modo e sempre auto.
        self._on = True

    def fire_start(self):
        self._firing = True
        self._warmup = 4
        self._fire_t = 0.0

    def fire_stop(self):
        self._firing = False
        self._comp = self._comp * 0.2
        self._ema_dy *= 0.6
        self._fire_t = 0.0

    def tick(self, raw_dy: float = 0.0, dt: float = 1.0 / 120.0, aiming: bool = False) -> float:
        """
        raw_dy: delta Y bruto do mouse no tick atual.
        - Positivo: mouse desceu (camera desce)
        - Negativo: mouse subiu (recuo tipico da arma)
        Retorna compensacao para somar no eixo Y do stick direito.
        """
        if not self._on or not self._firing:
            return 0.0

        if self._warmup > 0:
            self._warmup -= 1
            return 0.0

        self._fire_t += max(0.001, dt)

        # Base progressiva por tempo de rajada (sem usar preset fixo).
        base = min(self._BASE_FORCE + self._fire_t * self._RAMP_RATE, self._MAX_COMP)
        if aiming:
            base = min(base + self._ADS_BONUS, self._MAX_COMP)

        # Adaptacao por sinais do utilizador durante o spray.
        if raw_dy < -self._NOISE_THR:
            raw_comp = min(abs(raw_dy) / 220.0, self._MAX_ADAPT)
            self._ema_dy = self._ema_dy * (1.0 - self._EMA_ALPHA) + raw_comp * self._EMA_ALPHA
        else:
            self._ema_dy *= 0.95

        comp_target = min(base + self._ema_dy, self._MAX_COMP)
        self._comp = self._comp * 0.70 + comp_target * 0.30
        return -min(self._comp, self._MAX_COMP)


# =============================================================================
#  SILENT INSTALLER
#  Instala drivers e libs em background na pasta oculta nukeassist.
#  Verifica estado guardado para nao reinstalar desnecessariamente.
# =============================================================================
class SilentInstaller:
    """
    Instala ViGEmBus, HidHide e libs Python silenciosamente.
    - Downloads vao para %TEMP%\\nukeassist (pasta oculta)
    - Estado guardado em state.json para evitar reinstalacoes
    - Instaladores apagados apos instalacao bem-sucedida
    """

    @staticmethod
    def _read_state() -> dict:
        try:
            with open(_INSTALL_STATE) as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def _write_state(d: dict):
        try:
            _ensure_hidden_dir()
            with open(_INSTALL_STATE, "w") as f:
                json.dump(d, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _reg(path) -> bool:
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            winreg.CloseKey(k)
            return True
        except Exception:
            return False

    @staticmethod
    def vigem_installed() -> bool:
        return (SilentInstaller._reg(r"SYSTEM\CurrentControlSet\Services\ViGEm Bus Driver") or
                SilentInstaller._reg(r"SYSTEM\CurrentControlSet\Services\ViGEmBus"))

    @staticmethod
    def hidhide_installed() -> bool:
        return SilentInstaller._reg(r"SYSTEM\CurrentControlSet\Services\HidHide")

    @staticmethod
    def _hidhide_cli() -> Optional[str]:
        """Encontra o HidHideCLI.exe — tenta registo oficial primeiro."""
        # Chave oficial documentada pela nefarius
        try:
            k = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide\Path")
            p, _ = winreg.QueryValueEx(k, "")
            winreg.CloseKey(k)
            cli = os.path.join(os.path.dirname(p), "x64", "HidHideCLI.exe")
            if os.path.exists(cli):
                return cli
        except Exception:
            pass
        # Fallback: paths fixas
        for p in [
            r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
            r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
            r"C:\Program Files\Nefarius\HidHide\x64\HidHideCLI.exe",
        ]:
            if os.path.exists(p):
                return p
        try:
            r = subprocess.run(["where", "HidHideCLI.exe"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return r.stdout.strip().splitlines()[0]
        except Exception:
            pass
        return None

    @staticmethod
    def _dl(url: str, log_fn=None) -> Optional[str]:
        """Download para pasta oculta nukeassist. Retorna path ou None."""
        _ensure_hidden_dir()
        fname = os.path.basename(url.split("?")[0])
        dest  = os.path.join(_NUKEASSIST_DIR, fname)
        if log_fn: log_fn(f"  Download: {fname}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                f.write(r.read())
            # Ocultar ficheiro de instalacao
            ctypes.windll.kernel32.SetFileAttributesW(dest, 0x02)
            return dest
        except Exception as e:
            if log_fn: log_fn(f"  Erro download: {e}")
            return None

    @staticmethod
    def _exists_any(paths) -> bool:
        try:
            return any(os.path.exists(p) for p in paths)
        except Exception:
            return False

    @staticmethod
    def rewasd_installed() -> bool:
        return False  # disabled

    @staticmethod
    def joytokey_installed() -> bool:
        return SilentInstaller._exists_any([
            JOYTOKEY_EXE,
            r"C:\Program Files\JoyToKey\JoyToKey.exe",
            r"C:\Program Files (x86)\JoyToKey\JoyToKey.exe",
        ])

    @staticmethod
    def xmouse_installed() -> bool:
        return SilentInstaller._exists_any([
            r"C:\Program Files\Highresolution Enterprises\X-Mouse Button Control\XMouseButtonControl.exe",
            r"C:\Program Files (x86)\Highresolution Enterprises\X-Mouse Button Control\XMouseButtonControl.exe",
        ])

    @staticmethod
    def _install_joytokey(log_fn=None) -> bool:
        try:
            os.makedirs(JOYTOKEY_DIR, exist_ok=True)
            zip_path = os.path.join(JOYTOKEY_DIR, "JoyToKey_en.zip")
            req = urllib.request.Request(JOYTOKEY_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(zip_path, "wb") as f:
                f.write(r.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(JOYTOKEY_DIR)
            try:
                os.remove(zip_path)
            except Exception:
                pass
        except Exception as e:
            if log_fn: log_fn(f"  JoyToKey install falhou: {e}")
            return False
        return SilentInstaller.joytokey_installed()

    @staticmethod
    def _install_xmouse(log_fn=None) -> bool:
        if SilentInstaller.xmouse_installed():
            return True
        if not shutil.which("choco"):
            if log_fn: log_fn("  Chocolatey nao encontrado para instalar X-Mouse.")
            return False
        try:
            subprocess.run(
                ["choco", "install", "x-mouse-button-control", "-y", "--no-progress", "--limit-output"],
                timeout=600, creationflags=0x08000000)
        except Exception as e:
            if log_fn: log_fn(f"  X-Mouse install falhou: {e}")
            return False
        return SilentInstaller.xmouse_installed()

    @classmethod
    def run_all(cls, log_fn=None, prog_fn=None) -> dict:
        """
        Executa setup completo. Retorna dict com resultados.
        prog_fn(pct, msg) — callback de progresso opcional.
        """
        state  = cls._read_state()
        result = {"vigem": False, "hidhide": False, "libs": False, "needs_reboot": False}

        def step(pct, msg):
            if log_fn: log_fn(msg)
            if prog_fn: prog_fn(pct, msg)

        # ── ViGEmBus ────────────────────────────────────────────────
        step(5, "Verificando ViGEmBus...")
        if cls.vigem_installed():
            step(20, "ViGEmBus: ja instalado")
            result["vigem"] = True
        elif state.get("vigem_installed"):
            step(20, "ViGEmBus: estado cache (instalar manualmente se necessario)")
            result["vigem"] = True
        else:
            step(10, "Instalando ViGEmBus silenciosamente...")
            p = cls._dl(VIGEM_URL, log_fn)
            if p:
                try:
                    subprocess.run([p, "/qn", "/norestart"], timeout=180,
                                   creationflags=0x08000000)  # CREATE_NO_WINDOW
                    try: os.remove(p)
                    except Exception: pass
                except Exception as e:
                    if log_fn: log_fn(f"  Erro instalacao ViGEmBus: {e}")
            ok = cls.vigem_installed()
            result["vigem"] = ok
            if ok:
                state["vigem_installed"] = True
                result["needs_reboot"] = True
                step(20, "ViGEmBus: instalado (reboot necessario)")
            else:
                step(20, "ViGEmBus: falhou — instala manualmente")

        # ── HidHide ────────────────────────────────────────────────
        step(25, "Verificando HidHide...")
        if cls.hidhide_installed():
            step(50, "HidHide: ja instalado")
            result["hidhide"] = True
        elif state.get("hidhide_installed"):
            step(50, "HidHide: estado cache")
            result["hidhide"] = True
        else:
            step(30, "Instalando HidHide silenciosamente...")
            p = cls._dl(HIDHIDE_URL, log_fn)
            if p:
                try:
                    subprocess.run([p, "/qn", "/norestart"], timeout=180,
                                   creationflags=0x08000000)
                    try: os.remove(p)
                    except Exception: pass
                except Exception as e:
                    if log_fn: log_fn(f"  Erro instalacao HidHide: {e}")
            ok = cls.hidhide_installed()
            result["hidhide"] = ok
            if ok:
                state["hidhide_installed"] = True
                result["needs_reboot"] = True
                step(50, "HidHide: instalado (reboot necessario)")
            else:
                step(50, "HidHide: falhou — instala manualmente")

        # ── Python libs ────────────────────────────────────────────
        step(55, "Verificando dependencias Python...")
        libs_ok = True
        for lib in ["vgamepad", "pynput", "pillow"]:
            try:
                __import__(lib if lib != "pillow" else "PIL")
            except ImportError:
                step(60, f"  Instalando {lib}...")
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", lib, "-q",
                     "--target", _NUKEASSIST_DIR],
                    timeout=120, capture_output=True,
                    creationflags=0x08000000)
                if r.returncode != 0:
                    # Fallback: instalar normalmente
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", lib, "-q"],
                        timeout=120, creationflags=0x08000000)
                try:
                    __import__(lib if lib != "pillow" else "PIL")
                except ImportError:
                    libs_ok = False
        result["libs"] = libs_ok
        step(80, "Dependencias Python: OK" if libs_ok else "Algumas libs em falta")

        # ── Mappers auxiliares (JoyToKey / X-Mouse) ──────────────────────

        joy_ok = cls.joytokey_installed()
        if not joy_ok:
            step(88, "Instalando JoyToKey...")
            joy_ok = cls._install_joytokey(log_fn=log_fn)
        step(90, f"JoyToKey: {'OK' if joy_ok else 'falhou'}")

        xm_ok = cls.xmouse_installed()
        if not xm_ok:
            step(92, "Instalando X-Mouse Button Control...")
            xm_ok = cls._install_xmouse(log_fn=log_fn)
        step(94, f"X-Mouse: {'OK' if xm_ok else 'falhou'}")

        result["joytokey"] = joy_ok
        result["xmouse"] = xm_ok
        state["joytokey_installed"] = bool(joy_ok)
        state["xmouse_installed"] = bool(xm_ok)

        cls._write_state(state)
        step(100, "Setup concluido!")
        return result


class ExternalMouseApp:
    """
    Backend externo para mouse->controle (Mouse2Joystick).
    O objetivo e tirar do main.py a logica de movimento do mouse em jogo.
    """

    def __init__(self, log_fn=None):
        self._log = log_fn or print
        self._proc = None
        self._exe = None
        self._last_process_name = "cod.exe"

    def _latest_zip_url(self) -> str:
        try:
            req = urllib.request.Request(M2J_RELEASE_API, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            assets = data.get("assets") or []
            for a in assets:
                url = str(a.get("browser_download_url") or "").strip()
                if url.lower().endswith(".zip"):
                    return url
        except Exception:
            pass
        return M2J_FALLBACK_ZIP

    def _find_exe(self, root_dir: str) -> Optional[str]:
        try:
            direct = os.path.join(root_dir, "Mouse2Joystick.exe")
            if os.path.exists(direct):
                return direct
            for root, _dirs, files in os.walk(root_dir):
                for f in files:
                    if str(f).lower() == "mouse2joystick.exe":
                        return os.path.join(root, f)
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_cod_process_name(default_name: str = "cod.exe") -> str:
        try:
            out = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                timeout=5, stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            known = {p.lower() for p in COD_PROCESSES}
            for line in out.splitlines():
                ln = line.strip()
                if not ln:
                    continue
                img = ln.split('","', 1)[0].strip('"').strip().lower()
                if img in known:
                    return img
        except Exception:
            pass
        return default_name

    @staticmethod
    def _warzone_preset(process_name: str) -> dict:
        """
        Preset Warzone para Mouse2Joystick:
        - botoes de mouse mapeados para gatilhos/ombros;
        - stick direito para camera;
        - cursor travado/escondido e cliques bloqueados no alvo para evitar troca KBM<->controller.
        """
        return {
            "data": {
                "mouse": {
                    "left": 11,    # R2 (disparo)
                    "middle": 14,  # D-UP (ping)
                    "right": 10,   # L2 (ADS)
                    "four": 8,     # L1
                    "five": 9      # R1
                },
                "joystick": 2,      # Right stick
                # Ajuste mais suave para reduzir "movimento robótico".
                "input_delay": 1,
                "x_resist": 42,
                "y_resist": 46,
                "disable_clicks": 0,
                "lock_x_axis": 0,
                "lock_y_axis": 0,
                "hide_cursor": 1,
                "lock_cursor": 1,
                "lock_in_center": 0,
                "process_name": process_name
            }
        }

    def _write_preset(self, exe: str, process_name: str) -> bool:
        try:
            cfg_path = os.path.join(os.path.dirname(exe), "m2j_config.json")
            preset = self._warzone_preset(process_name=process_name)
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(preset, f, indent=4)
            return True
        except Exception as e:
            self._log(f"[Mouse] Nao foi possivel gravar preset do Mouse2Joystick: {e}")
            return False

    def ensure_installed(self) -> Optional[str]:
        exe = self._find_exe(M2J_DIR)
        if exe:
            self._exe = exe
            return exe

        try:
            os.makedirs(M2J_DIR, exist_ok=True)
        except Exception:
            pass

        zip_url = self._latest_zip_url()
        zip_path = os.path.join(_NUKEASSIST_DIR, "Mouse2Joystick.zip")

        try:
            self._log("[Mouse] A instalar backend externo Mouse2Joystick...")
            req = urllib.request.Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(zip_path, "wb") as f:
                f.write(r.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(M2J_DIR)
        except Exception as e:
            self._log(f"[Mouse] Falha no download/extracao do Mouse2Joystick: {e}")
            return None
        finally:
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception:
                pass

        exe = self._find_exe(M2J_DIR)
        if exe:
            self._exe = exe
            self._log("[Mouse] Mouse2Joystick instalado.")
            return exe
        self._log("[Mouse] Mouse2Joystick nao encontrado apos extracao.")
        return None

    def start(self, process_name: Optional[str] = None, restart: bool = False) -> bool:
        exe = self._exe or self.ensure_installed()
        if not exe:
            return False

        target_proc = (str(process_name).strip().lower() if process_name else "").strip()
        if not target_proc:
            target_proc = self._detect_cod_process_name(default_name=self._last_process_name or "cod.exe")
        self._last_process_name = target_proc

        self._write_preset(exe, target_proc)

        alive = self._proc and self._proc.poll() is None
        if alive and not restart:
            return True
        if restart:
            self.stop()
            # Garante uma unica instancia para evitar comportamento "robotico"
            # causado por processos duplicados a enviar input ao mesmo tempo.
            ExternalMouseApp.stop_all()
        elif not alive:
            # Limpeza leve de instancias antigas sem handle local.
            ExternalMouseApp.stop_all()

        try:
            self._proc = subprocess.Popen(
                [exe],
                cwd=os.path.dirname(exe)
            )
            self._log(f"[Mouse] Backend externo ativo (Mouse2Joystick) | preset: {target_proc}")
            return True
        except Exception as e:
            self._log(f"[Mouse] Nao foi possivel iniciar Mouse2Joystick: {e}")
            return False

    def stop(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        ExternalMouseApp.stop_all()

    @staticmethod
    def stop_all(log_fn=None):
        log = log_fn or (lambda *_: None)
        try:
            out = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                timeout=5, stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                ln = line.strip()
                if not ln:
                    continue
                img = ln.split('","', 1)[0].strip('"').strip()
                if img.lower() == "mouse2joystick.exe":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "Mouse2Joystick.exe"],
                            timeout=5, creationflags=0x08000000
                        )
                        log("[Mouse] Processo externo Mouse2Joystick encerrado (compatibilidade).")
                    except Exception:
                        pass
                    break
        except Exception:
            pass


# =============================================================================
#  HIDHIDE MANAGER (robusto: CLI + registo direto)
#  
#  NOTA CRITICA sobre HidHide e teclado/rato:
#  HidHide e destinado a esconder controladores HID (gamepads).
#  Para teclado e rato, o pynput win32_event_filter e o metodo correto,
#  pois esses dispositivos usam drivers WDM diferentes de HID gamepads.
#  O HidHide ativa o "cloak" que bloqueia acesso HID ao nivel de driver,
#  mas para KB+Mouse o suppress via hook de baixo nivel e mais eficaz.
# =============================================================================
class HidHideManager:
    """
    Gerencia o HidHide usando CLI + registo direto.
    Fluxo de hiding para o COD:
    1. Whitelist: este processo pode ver TUDO (incluindo teclado/rato)
    2. Esconder dispositivos HID de entrada (KB+Mouse) do jogo
    3. Ativar cloak -- jogo so ve o Xbox virtual
    """

    def __init__(self, log_fn=None):
        self._log   = log_fn or print
        self._cli   = SilentInstaller._hidhide_cli()
        self.active = False

    def is_installed(self) -> bool:
        return SilentInstaller.hidhide_installed()

    def is_available(self) -> bool:
        return bool(self._cli) and self.is_installed()

    def _run(self, *args) -> tuple:
        if not self._cli:
            return False, ""
        try:
            r = subprocess.run(
                [self._cli] + list(args),
                capture_output=True, text=True, timeout=15,
                creationflags=0x08000000)
            return r.returncode == 0, r.stdout + r.stderr
        except Exception as e:
            return False, str(e)

    def _exe(self) -> str:
        return sys.executable

    def _reg_set_cloak(self, on: bool):
        """Ativa/desativa cloak diretamente no registo — mais fiavel que CLI."""
        try:
            # Registo documentado: HKLM\SYSTEM\CurrentControlSet\Services\HidHide\Parameters
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Services\HidHide\Parameters",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "Active", 0, winreg.REG_DWORD, 1 if on else 0)
            winreg.CloseKey(k)
            return True
        except Exception:
            return False

    def _reg_whitelist_add(self, exe_path: str):
        """Adiciona exe a whitelist via registo."""
        try:
            k = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Services\HidHide\Parameters",
                0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
            try:
                wl, _ = winreg.QueryValueEx(k, "Whitelist")
                if not isinstance(wl, list):
                    wl = list(wl) if wl else []
            except Exception:
                wl = []
            exe_path = exe_path.lower()
            if exe_path not in [x.lower() for x in wl]:
                wl.append(exe_path)
                winreg.SetValueEx(k, "Whitelist", 0, winreg.REG_MULTI_SZ, wl)
            winreg.CloseKey(k)
            return True
        except Exception:
            return False

    def enable(self) -> bool:
        if not self.is_available():
            self._log("[HidHide] Nao instalado — install drivers primeiro")
            return False

        exe = self._exe()

        # 1. Whitelist via CLI (mais compativel)
        ok_wl, _ = self._run("--app-reg", exe)
        if not ok_wl:
            self._reg_whitelist_add(exe)  # fallback registo

        # 2. Esconder dispositivos HID de entrada
        self._hide_input_devices()

        # 3. Ativar cloak — CLI primeiro, registo como fallback
        ok, out = self._run("--cloak-on")
        if not ok:
            ok = self._reg_set_cloak(True)

        if ok:
            self._log("[HidHide] ATIVO — KB+Mouse ocultos ao jogo")
            self.active = True
        else:
            self._log(f"[HidHide] Falhou: {out[:80]}")
        return ok

    def _hide_input_devices(self):
        """
        Lista todos dispositivos HID e esconde os de KB+Mouse.
        Usa --dev-all para obter instance paths e --dev-hide para esconder.
        """
        ok, out = self._run("--dev-all")
        if not ok or not out.strip():
            self._log("[HidHide] Nao foi possivel listar dispositivos")
            self._log("  Abre HidHide Client e esconde teclado/rato manualmente")
            return

        hidden = 0
        # Keywords para identificar KB+Mouse (ingles, portugues, etc.)
        kb_mouse_kw = [
            "keyboard", "mouse", "hid keyboard", "hid mouse",
            "usb hid", "teclado", "rato", "souris", "clavier",
            "\\hid\\vid_", "hid-compliant keyboard", "hid-compliant mouse",
        ]
        # Keywords para EXCLUIR (nao esconder controladores/xbox/vigem)
        ctrl_kw = [
            "xbox", "vigem", "xinput", "xusb", "virtual gamepad",
            "gamepad", "controller", "joystick", "wheel",
            "vid_045e&pid_028e", "vid_045e&pid_02ea", "vid_045e&pid_0b12",
        ]
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            is_kb_mouse = any(k in low for k in kb_mouse_kw)
            is_ctrl     = any(k in low for k in ctrl_kw)
            if is_kb_mouse and not is_ctrl:
                device = line.split("|")[0].strip()
                if device:
                    ok2, _ = self._run("--dev-hide", device)
                    if ok2:
                        hidden += 1
                        short = device[-50:] if len(device) > 50 else device
                        self._log(f"  [HidHide] Oculto: ...{short}")

        if hidden > 0:
            self._log(f"[HidHide] {hidden} dispositivo(s) de entrada ocultos")
        else:
            self._log("[HidHide] Auto-hide: nenhum dispositivo KB/Mouse detetado")
            self._log("  Usa HidHide Client para ocultar manualmente")

    def disable(self) -> bool:
        ok, _ = self._run("--cloak-off")
        if not ok:
            ok = self._reg_set_cloak(False)
        if ok:
            self._log("[HidHide] Desativado")
            self.active = False
        return ok

    def open_client(self):
        for c in [
            r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideClient.exe",
            r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideClient.exe",
        ]:
            if os.path.exists(c):
                subprocess.Popen([c])
                return True
        self._log("[HidHide] Client nao encontrado")
        return False


# =============================================================================
#  STEAM BRIDGE
# =============================================================================
class SteamBridge:
    @staticmethod
    def get_steam_path() -> Optional[str]:
        paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ]
        for hive, kp, vn in paths:
            try:
                k = winreg.OpenKey(hive, kp)
                v, _ = winreg.QueryValueEx(k, vn)
                winreg.CloseKey(k)
                if v and os.path.exists(v):
                    return v
            except Exception:
                pass
        for p in [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]:
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def configure(log_fn=None) -> bool:
        ok = False
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"SOFTWARE\Valve\Steam", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "xinput_enabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "XBoxControllerSupport", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(k)
            if log_fn: log_fn("Steam: XInput ativado")
            ok = True
        except Exception as e:
            if log_fn: log_fn(f"Steam registo: {e}")

        sp = SteamBridge.get_steam_path()
        if sp:
            ud = os.path.join(sp, "userdata")
            if os.path.isdir(ud):
                for uid in os.listdir(ud):
                    vdf = os.path.join(ud, uid, "config", "localconfig.vdf")
                    if os.path.exists(vdf):
                        SteamBridge._patch_vdf(vdf, log_fn)
                        ok = True

        os.environ["SDL_GAMECONTROLLERCONFIG"] = (
            "030000005e0400008e02000014010000,Xbox 360 Controller,"
            "a:b0,b:b1,back:b6,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,"
            "guide:b8,leftshoulder:b4,leftstick:b9,lefttrigger:a2,leftx:a0,lefty:a1,"
            "rightshoulder:b5,rightstick:b10,righttrigger:a5,rightx:a3,righty:a4,"
            "start:b7,x:b2,y:b3,platform:Windows,"
        )
        os.environ["SDL_JOYSTICK_XINPUT"]  = "1"
        os.environ["SDL_JOYSTICK_HIDAPI"]  = "1"
        if log_fn: log_fn("Steam: configuracao completa")
        return ok

    @staticmethod
    def _patch_vdf(path, log_fn=None):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            bak = path + ".tnt_bak"
            if not os.path.exists(bak):
                with open(bak, "w", encoding="utf-8") as f:
                    f.write(content)
            patches = {
                '"XBoxControllerSupport"\t\t"0"': '"XBoxControllerSupport"\t\t"1"',
                '"xinput_enabled"\t\t"0"':        '"xinput_enabled"\t\t"1"',
                '"EnableSteamInput"\t\t"0"':      '"EnableSteamInput"\t\t"1"',
            }
            changed = False
            for old, new in patches.items():
                if old in content:
                    content = content.replace(old, new)
                    changed = True
            if changed:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                if log_fn: log_fn("Steam VDF patched")
        except Exception as e:
            if log_fn: log_fn(f"VDF: {e}")


# =============================================================================
#  COD SETTINGS BRIDGE
#  Tenta forcar os ficheiros de configuracao conhecidos para modo Controller.
# =============================================================================
class CodSettingsBridge:
    REL_PATHS = [
        os.path.join("Call of Duty", "players"),
        os.path.join("Call of Duty", "players2"),
        os.path.join("Call of Duty HQ", "players"),
        os.path.join("Call of Duty HQ", "players2"),
        os.path.join("Modern Warfare", "players"),
        os.path.join("Warzone", "players"),
    ]
    EXTENSIONS = (".cfg", ".ini", ".txt", ".cst", ".json")

    @staticmethod
    def _docs_roots() -> list:
        home = os.path.expanduser("~")
        return [
            os.path.join(home, "Documents"),
            os.path.join(home, "OneDrive", "Documents"),
        ]

    @staticmethod
    def _candidate_files() -> list:
        out = []
        seen = set()
        for base in CodSettingsBridge._docs_roots():
            if not os.path.isdir(base):
                continue
            for rel in CodSettingsBridge.REL_PATHS:
                d = os.path.join(base, rel)
                if not os.path.isdir(d):
                    continue
                for fn in os.listdir(d):
                    fp = os.path.join(d, fn)
                    low = fn.lower()
                    if not os.path.isfile(fp):
                        continue
                    if not low.endswith(CodSettingsBridge.EXTENSIONS):
                        continue
                    try:
                        if os.path.getsize(fp) > 2_500_000:
                            continue
                    except Exception:
                        continue
                    key = fp.lower()
                    if key not in seen:
                        seen.add(key)
                        out.append(fp)
        return out

    @staticmethod
    def _patch_text(content: str) -> tuple[str, bool]:
        changed = False
        rules = [
            (re.compile(r'("AimingInputDevice"\s*:\s*")([^"]+)(")', re.IGNORECASE), r'\1Controller\3'),
            (re.compile(r'("Aiming Input Device"\s*:\s*")([^"]+)(")', re.IGNORECASE), r'\1Controller\3'),
            (re.compile(r'(\bAimingInputDevice\s*=\s*)([^\r\n]+)', re.IGNORECASE), r'\1controller'),
            (re.compile(r'(\baiming_input_device\s*=\s*)([^\r\n]+)', re.IGNORECASE), r'\1controller'),
            (re.compile(r'(\binput[_\s-]*device\s*=\s*)(kbm|keyboard|mouse)', re.IGNORECASE), r'\1controller'),
            (re.compile(r'("input[_\s-]*device"\s*:\s*")(kbm|keyboard|mouse)(")', re.IGNORECASE), r'\1controller\3'),
        ]
        for rx, repl in rules:
            new_content, n = rx.subn(repl, content)
            if n > 0:
                content = new_content
                changed = True
        return content, changed

    @staticmethod
    def force_controller(log_fn=None) -> bool:
        files = CodSettingsBridge._candidate_files()
        if not files:
            if log_fn:
                log_fn("COD config: nenhum ficheiro conhecido encontrado para patch automatico.")
            return False
        patched = 0
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    old = f.read()
                new, changed = CodSettingsBridge._patch_text(old)
                if not changed:
                    continue
                bak = fp + ".controller_bak"
                if not os.path.exists(bak):
                    with open(bak, "w", encoding="utf-8", errors="ignore") as f:
                        f.write(old)
                with open(fp, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(new)
                patched += 1
            except Exception:
                pass
        if log_fn:
            if patched:
                log_fn(f"COD config: modo Controller aplicado em {patched} ficheiro(s).")
            else:
                log_fn("COD config: nenhum campo de input reconhecido para alterar.")
        return patched > 0


# =============================================================================
#  COD WATCHER
# =============================================================================
class CodWatcher:
    def __init__(self):
        self.on_start: Optional[Callable] = None
        self.on_stop:  Optional[Callable] = None
        self._last:    Optional[str]      = None
        self._running  = False
        self._hit_streak = 0
        self._miss_streak = 0

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            found = self._find()
            if found:
                self._hit_streak += 1
                self._miss_streak = 0
                # Debounce de deteccao para evitar flicker ON/OFF.
                if not self._last and self._hit_streak >= 2:
                    self._last = found
                    if self.on_start:
                        self.on_start(found)
                elif self._last:
                    self._last = found
            else:
                self._miss_streak += 1
                self._hit_streak = 0
                # Debounce de perda para nao cair para pass-through por falso negativo.
                if self._last and self._miss_streak >= 2:
                    self._last = None
                    if self.on_stop:
                        self.on_stop()
            time.sleep(2)

    @staticmethod
    def _find() -> Optional[str]:
        try:
            out = subprocess.check_output(
                ["tasklist", "/FO", "CSV", "/NH"],
                timeout=5, stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
            names = []
            for line in out.splitlines():
                ln = line.strip()
                if not ln:
                    continue
                img = ln.split('","', 1)[0].strip('"').strip().lower()
                if img:
                    names.append(img)

            known = {p.lower() for p in COD_PROCESSES}
            for name in names:
                if name in known:
                    return name

            for name in names:
                base = name.rsplit(".", 1)[0]
                if (
                    "warzone" in base
                    or "modernwarfare" in base
                    or "blackops" in base
                    or "codhq" in base
                    or "cod_warzone" in base
                    or base in {"mw2", "mw3", "bo6", "bo7"}
                ):
                    return name
                if re.search(r"(^|[^a-z])cod([^a-z]|$)", base):
                    if base not in {"code", "codec", "codium"}:
                        return name
        except Exception:
            pass

        try:
            t = CodWatcher._foreground_title().lower()
            if any(k in t for k in (
                "call of duty",
                "warzone",
                "modern warfare",
                "black ops",
                "cod hq",
            )):
                return "cod_window"
        except Exception:
            pass
        return None

    @staticmethod
    def _foreground_title() -> str:
        try:
            u32 = ctypes.windll.user32
            hwnd = u32.GetForegroundWindow()
            if not hwnd:
                return ""
            ln = u32.GetWindowTextLengthW(hwnd)
            if ln <= 0:
                return ""
            buf = ctypes.create_unicode_buffer(ln + 1)
            u32.GetWindowTextW(hwnd, buf, ln + 1)
            return str(buf.value or "")
        except Exception:
            return ""


# =============================================================================
#  XBOX EMULATOR
# =============================================================================
class XboxEmulator:
    TICK = 1.0 / 120

    def __init__(self, cfg: Config):
        self.cfg      = cfg
        self.gamepad  = None
        self.pad_type = "x360"
        self.running  = False
        self.paused   = False
        self._cmd_mouse_log = bool(CMD_MOUSE_LOG_DEFAULT)
        self._cmd_mouse_log_last = 0.0
        if self._cmd_mouse_log:
            _ensure_debug_console()
            print("[NUKE] CMD mouse log ativo no arranque.", flush=True)

        self.keys_down: Set[str] = set()
        self.mb_down:   Set[str] = set()
        self.mouse_dx   = 0.0
        self.mouse_dy   = 0.0
        self._mlock     = threading.Lock()

        self._kbl = self._msl = self._lt = None
        self._recoil  = RecoilEngine()
        self._human   = Humanizer()
        self._curves  = StickCurves()

        self._prev_x = self._prev_y = None
        self._raw_input_active = False
        self._raw_thread = None
        self._raw_debug_count = 0
        self._external_mouse = bool(getattr(self.cfg, "external_mouse_app", True))

        self._rf_next  = None
        self._rf_state = False
        self._ping_until  = 0.0
        self._slide_until = 0.0
        self._is_ads      = False
        self._pass        = False
        self._game_active = False
        self._rx_filt     = 0.0
        self._ry_filt     = 0.0
        self._rx_out      = 0.0
        self._ry_out      = 0.0
        self._aa_phase    = 0.0

        self._km:   dict = {}
        self._bmap: dict = {}
        self.on_log:    Optional[Callable] = None
        self.on_status: Optional[Callable] = None

    def set_external_mouse(self, enabled: bool):
        self._external_mouse = bool(enabled)
        self._reset_mouse_pipeline()

    def _log(self, m):
        if self.on_log:
            self.on_log(m)
        else:
            print(m)

    def _notify(self, s):
        if self.on_status:
            self.on_status(s)

    def _cmd_mouse_trace(self, dx: float, dy: float, raw_rx: float, raw_ry: float, rx: float, ry: float):
        """
        Log no CMD apenas quando há movimento real do mouse em jogo.
        """
        if not self._cmd_mouse_log:
            return
        if abs(dx) < 0.0001 and abs(dy) < 0.0001:
            return
        now = time.monotonic()
        # Limite de spam: ~30 linhas/segundo
        if (now - self._cmd_mouse_log_last) < 0.033:
            return
        self._cmd_mouse_log_last = now
        src = "WM_INPUT" if self._raw_input_active else "HOOK"
        ts = time.strftime("%H:%M:%S")
        print(
            f"[MOUSE {ts}] src={src} dx={dx:.2f} dy={dy:.2f} "
            f"raw_rx={raw_rx:.3f} raw_ry={raw_ry:.3f} rx={rx:.3f} ry={ry:.3f} "
            f"pass={self._pass} paused={self.paused}",
            flush=True,
        )

    def _reset_mouse_pipeline(self):
        self._prev_x = None
        self._prev_y = None
        with self._mlock:
            self.mouse_dx = 0.0
            self.mouse_dy = 0.0

        self._rx_filt = self._ry_filt = 0.0
        self._rx_out = self._ry_out = 0.0
        self._aa_phase = 0.0

    def set_game_active(self, active: bool, log: bool = False):
        """
        Controla se o emulador deve agir (partida aberta) ou ficar pass-through
        (fora de partida/menu desktop), mantendo processo ligado.
        """
        active = bool(active)
        self._game_active = active
        self._pass = not active
        self.keys_down.clear()
        self.mb_down.clear()
        self._recoil.fire_stop()
        self._reset_mouse_pipeline()
        try:
            if self.gamepad:
                self.gamepad.reset()
                self.gamepad.update()
                if active:
                    self._wake_controller_presence()
        except Exception:
            pass
        if log:
            self._log("Entrada de jogo: " + ("ATIVA" if active else "INATIVA (pass-through)"))

    # ── driver checks ─────────────────────────────────────────────────
    def _reg(self, p) -> bool:
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, p)
            winreg.CloseKey(k)
            return True
        except Exception:
            return False

    def vigem_ok(self):
        return (self._reg(r"SYSTEM\CurrentControlSet\Services\ViGEm Bus Driver") or
                self._reg(r"SYSTEM\CurrentControlSet\Services\ViGEmBus"))

    def hidhide_ok(self):
        return self._reg(r"SYSTEM\CurrentControlSet\Services\HidHide")

    def python_ok(self):
        try:
            import vgamepad, pynput  # noqa
            return True
        except Exception:
            return False

    def _reload_vgamepad(self) -> bool:
        global VG_OK, vg
        if VG_OK:
            return True
        try:
            vg = importlib.import_module("vgamepad")
            VG_OK = True
            self._log("Dependencia ativa: vgamepad")
        except Exception:
            VG_OK = False
        return VG_OK

    def _reload_pynput(self) -> bool:
        global PN_OK, kb_mod, ms_mod, Key, Button
        if PN_OK:
            return True
        try:
            kb_mod = importlib.import_module("pynput.keyboard")
            ms_mod = importlib.import_module("pynput.mouse")
            Key = kb_mod.Key
            Button = ms_mod.Button
            PN_OK = True
            self._log("Dependencia ativa: pynput")
        except Exception:
            PN_OK = False
        return PN_OK

    def refresh_runtime_deps(self):
        self._reload_vgamepad()
        self._reload_pynput()

    # ── install ───────────────────────────────────────────────────────
    def install_all(self, prog=None):
        result = SilentInstaller.run_all(log_fn=self._log, prog_fn=prog)
        self.refresh_runtime_deps()
        if result.get("needs_reboot"):
            self._log("*** REINICIA O PC para ativar os drivers! ***")
        return result

    def _inst_libs(self) -> bool:
        for p in ["vgamepad", "pynput", "pillow"]:
            subprocess.run([sys.executable, "-m", "pip", "install", p, "-q"],
                           timeout=60, creationflags=0x08000000)
        return True

    # ── virtual device ────────────────────────────────────────────────
    def ensure_gamepad(self, quiet=False) -> bool:
        if not VG_OK:
            if not quiet:
                self._log("vgamepad nao instalado. Aguarda o setup automatico.")
            return False
        if self.gamepad is None:
            try:
                # Restaurado: prioriza X360 virtual para compatibilidade XInput total.
                self.gamepad = vg.VX360Gamepad()
                self.pad_type = "x360"
                self.gamepad.reset()
                self.gamepad.update()
                if not quiet:
                    self._log(f"Controle virtual criado ({self.pad_type.upper()})")
            except Exception as e:
                self.gamepad = None
                if not quiet:
                    self._log(f"Nao foi possivel criar controller: {e}")
                return False
        return True

    def release_gamepad(self, quiet=False) -> bool:
        if self.running:
            if not quiet:
                self._log("Para o emulador primeiro.")
            return False
        if self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass
            self.gamepad = None
            self.pad_type = "x360"
            if not quiet:
                self._log("Controle virtual desligado")
        return True

    def _wake_controller_presence(self):
        """
        Pulso curto no controle virtual para o jogo detectar imediatamente
        input de gamepad/XInput.
        """
        if not self.gamepad:
            return
        try:
            self.gamepad.reset()
            self.gamepad.update()
            time.sleep(0.015)
            btn_a = vg.XUSB_BUTTON.XUSB_GAMEPAD_A
            self.gamepad.press_button(btn_a)
            self.gamepad.update()
            time.sleep(0.02)
            self.gamepad.release_button(btn_a)
            self.gamepad.left_joystick_float(0.09, 0.0)
            self.gamepad.update()
            time.sleep(0.02)
            self.gamepad.reset()
            self.gamepad.update()
        except Exception:
            pass

    # ── start ─────────────────────────────────────────────────────────
    def start(self) -> bool:
        self.refresh_runtime_deps()
        if not VG_OK and not self._external_mouse:
            self._log("ERRO: vgamepad nao instalado!")
            return False
        if not PN_OK:
            self._log("ERRO: pynput nao instalado!")
            return False
        if self.running:
            return True
        try:
            if self._external_mouse:
                # Em modo externo, evita criar controle virtual interno para nao
                # competir com o Mouse2Joystick pelo dispositivo ativo no jogo.
                self.release_gamepad(quiet=True)
            else:
                if not self.ensure_gamepad(quiet=True):
                    return False
            # running precisa estar True antes de arrancar listeners/raw thread,
            # para o loop de WM_INPUT nao morrer por race no arranque.
            self.running = True
            self.keys_down.clear()
            self.mb_down.clear()
            self._reset_mouse_pipeline()
            self._pass   = False
            self._km     = self._resolve_km()
            self._bmap   = self._build_bmap()
            self._human  = Humanizer()
            self._recoil.configure(self.cfg.recoil_pattern, self.cfg.recoil_custom or None)
            self._recoil._on = self.cfg.recoil_on

            self._kbl = kb_mod.Listener(
                on_press=self._kp, on_release=self._kr,
                suppress=False,
                win32_event_filter=self._kbf)
            self._msl = ms_mod.Listener(
                on_move=self._mm, on_click=self._mc,
                suppress=False,
                win32_event_filter=self._msf)
            self._kbl.start()
            self._msl.start()
            # Thread WM_INPUT so e usada no backend interno de rato.
            if not self._external_mouse:
                self._start_raw_input()
            else:
                self._raw_input_active = False
                self._log("[Mouse] Backend externo ativo: pipeline interno desativado.")

            if not self._external_mouse:
                self._lt = threading.Thread(target=self._loop, daemon=True)
                self._lt.start()
                self._wake_controller_presence()
            else:
                self._lt = None

            if self.cfg.steam_integrate:
                threading.Thread(
                    target=lambda: SteamBridge.configure(self._log),
                    daemon=True).start()

            self._notify("running")
            self._log("Emulador ATIVO!")
            self._log(f"Modo controle automatico ativo ({self.pad_type.upper()}).")
            self._log(f"F11 = modo menu (setas/Enter/Esc) | {self._toggle_key_name().upper()} = ativar/desativar")
            self._log("F7 = CMD mouse log ON/OFF")
            return True
        except Exception as e:
            self.running = False
            for l in (self._kbl, self._msl):
                try:
                    if l:
                        l.stop()
                except Exception:
                    pass
            self._kbl = self._msl = None
            self._reset_mouse_pipeline()
            self._log(f"Erro ao iniciar: {e}")
            return False

    def stop(self, keep_gp=True):
        self.running = False
        self._pass   = False
        self.keys_down.clear()
        self.mb_down.clear()
        self._reset_mouse_pipeline()
        for l in (self._kbl, self._msl):
            try:
                if l: l.stop()
            except Exception:
                pass
        self._kbl = self._msl = None
        if self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception:
                pass
        if not keep_gp:
            self.release_gamepad(quiet=True)
        self._notify("stopped")
        self._log("Emulador parado.")

    # ── keymap / bmap ─────────────────────────────────────────────────
    def _resolve_km(self) -> dict:
        m = dict(DEFAULT_KEY_MAP)
        for k, v in (self.cfg.key_map or {}).items():
            nk = str(k).strip().lower()
            nv = str(v).strip().upper()
            if nk and nv and nk not in m:
                m[nk] = nv
        return m

    def _build_bmap(self) -> dict:
        if self.pad_type == "ds4":
            return {
                "A":      vg.DS4_BUTTONS.DS4_BUTTON_CROSS,
                "B":      vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
                "X":      vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
                "Y":      vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,
                "LB":     vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,
                "RB":     vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
                "L3":     vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,
                "R3":     vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
                "BACK":   vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
                "START":  vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,
                "DUP":    "DUP",
                "DDOWN":  "DDOWN",
                "DLEFT":  "DLEFT",
                "DRIGHT": "DRIGHT",
            }
        return {
            "A":      vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            "B":      vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            "X":      vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            "Y":      vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            "LB":     vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            "RB":     vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "L3":     vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            "R3":     vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            "BACK":   vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            "START":  vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            "DUP":    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
            "DDOWN":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            "DLEFT":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            "DRIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        }

    def _toggle_key_name(self) -> str:
        t = str(getattr(self.cfg, "toggle_key", "f12") or "f12").strip().lower()
        return t if t else "f12"

    def _gamebound(self) -> Set[str]:
        s = set(self._km.keys())
        s.update({"w","a","s","d","space","shift","ctrl","c","up","down","left","right"})
        return s

    # ── win32 event filters ───────────────────────────────────────────
    # CRITICO: suppress_event() impede que o evento chegue ao jogo.
    # Com HidHide: o jogo recebe ZERO eventos de rato/teclado.
    # Sem HidHide: pynput suprime via hook, mas menos fiavel.
    @staticmethod
    def _vk(data) -> str:
        vk = int(getattr(data, "vkCode", 0))
        if 0x30 <= vk <= 0x39: return chr(vk).lower()
        if 0x41 <= vk <= 0x5A: return chr(vk + 32)
        if 0x70 <= vk <= 0x7B: return f"f{vk - 0x6f}"
        return {
            0x08: "backspace", 0x09: "tab", 0x0D: "enter", 0x1B: "escape",
            0x20: "space",
            0x10: "shift", 0xA0: "shift", 0xA1: "shift",
            0x11: "ctrl",  0xA2: "ctrl",  0xA3: "ctrl",
            0x25: "left",  0x26: "up",    0x27: "right", 0x28: "down",
        }.get(vk, "")

    def _kbf(self, _msg, data):
        if not self.running or self._pass:
            return True
        if self._external_mouse:
            return True
        kn = self._vk(data)
        if kn in {"f11", "f10", "f7", self._toggle_key_name()}:
            return True
        try:
            if self._kbl:
                self._kbl.suppress_event()
        except Exception:
            pass
        return True

    def _msf(self, _msg, _data):
        if not self.running or self._pass:
            return True
        if self._external_mouse:
            return True
        try:
            if self._msl:
                self._msl.suppress_event()
        except Exception:
            pass
        return True

    # ── listeners ─────────────────────────────────────────────────────
    def _kname(self, key) -> str:
        try:
            return key.char.lower() if key.char else ""
        except AttributeError:
            return {
                Key.space: "space",  Key.shift: "shift",   Key.shift_r: "shift",
                Key.ctrl_l: "ctrl",  Key.ctrl_r: "ctrl",   Key.tab: "tab",
                Key.esc: "escape",   Key.enter: "enter",
                Key.up: "up",        Key.down: "down",
                Key.left: "left",    Key.right: "right",
                Key.f7: "f7",        Key.f10: "f10",      Key.f11: "f11",      Key.f12: "f12",
            }.get(key, "")

    def _kp(self, key):
        if key == Key.f7 and self.running:
            self._cmd_mouse_log = not self._cmd_mouse_log
            if self._cmd_mouse_log:
                _ensure_debug_console()
                print("[NUKE] CMD mouse log ON (F7).", flush=True)
            self._log(f"F7: CMD mouse log {'ON' if self._cmd_mouse_log else 'OFF'}")
            return
        if key == Key.f11 and self.running:
            self._pass = not self._pass
            self.keys_down.clear()
            self.mb_down.clear()
            self._reset_mouse_pipeline()
            if self._pass:
                self._recoil.fire_stop()
                try:
                    if self.gamepad:
                        self.gamepad.reset()
                        self.gamepad.update()
                except Exception:
                    pass
                self._log("F11: MODO MENU - use setas/Enter/Esc (mouse bloqueado)")
            else:
                self._log("F11: MODO JOGO - aim assist ativo")
            return
        if key == Key.f10 and self.running:
            self._log("F10: parando...")
            threading.Thread(target=self.stop, kwargs={"keep_gp": True}, daemon=True).start()
            return
        n = self._kname(key)
        if n == self._toggle_key_name() and self.running:
            self.paused = not self.paused
            if self.paused:
                self._notify("paused")
                self._log(f"{n.upper()}: aim assist DESATIVADO")
            else:
                self._notify("running")
                self._log(f"{n.upper()}: aim assist ATIVADO")
            return
        if n:
            self.keys_down.add(n)
        if self.cfg.slide_cancel and n in ("c", "ctrl"):
            self._slide_until = time.monotonic() + 0.14

    def _kr(self, key):
        n = self._kname(key)
        if n:
            self.keys_down.discard(n)

    def _mm(self, x, y):
        """
        Fallback para delta de rato via coordenadas absolutas pynput.
        Usado quando o raw input thread não está ativo.
        """
        if not self.running or self.paused or self._pass or self._external_mouse:
            self._prev_x = x
            self._prev_y = y
            return
        if self._prev_x is not None and not self._raw_input_active:
            with self._mlock:
                self.mouse_dx += x - self._prev_x
                self.mouse_dy += y - self._prev_y
        self._prev_x, self._prev_y = x, y

    def _msf(self, msg, data):
        if not self.running or self._pass:
            return True
        if self._external_mouse:
            return True
        try:
            if self._msl:
                self._msl.suppress_event()
        except Exception:
            pass
        return True

    # ── Raw Input thread (WM_INPUT) ───────────────────────────────────
    def _start_raw_input(self):
        self._raw_input_active = False
        self._raw_debug_count  = 0   # conta eventos recebidos para debug
        self._raw_thread = threading.Thread(target=self._raw_input_loop, daemon=True)
        self._raw_thread.start()
        # Aguardar brevemente para confirmar se o thread arrancou
        deadline = time.monotonic() + 1.0
        while not self._raw_input_active and time.monotonic() < deadline:
            time.sleep(0.05)
        if not self._raw_input_active:
            self._log("[Mouse] Raw Input nao disponivel — usando hook pynput como fallback")

    def _raw_input_loop(self):
        """
        Lê WM_INPUT com RIDEV_INPUTSINK numa janela message-only.
        Usa offsets fixos em bytes para evitar bug de alinhamento do
        union RAWMOUSE no ctypes x64.

        Layout RAWINPUT x64 (winuser.h):
          Header 24 bytes, depois RAWMOUSE:
            offset 24: usFlags (USHORT, 2 bytes)
            offset 32: lLastX  (LONG, 4 bytes)  ← delta X
            offset 36: lLastY  (LONG, 4 bytes)  ← delta Y
        """
        import ctypes, ctypes.wintypes as wt, struct as _s

        RIDEV_INPUTSINK = 0x00000100
        RID_INPUT       = 0x10000003
        WM_INPUT        = 0x00FF
        PM_REMOVE       = 0x0001
        RIM_TYPEMOUSE   = 0
        MOUSE_MOVE_ABS  = 0x01
        HDR_SIZE        = 24
        OFF_TYPE        = 0
        OFF_FLAGS       = 24
        OFF_LASTX       = 32
        OFF_LASTY       = 36
        BUF_SIZE        = 64

        class RAWINPUTDEVICE(ctypes.Structure):
            _fields_ = [("usUsagePage", wt.USHORT),
                         ("usUsage",     wt.USHORT),
                         ("dwFlags",     wt.DWORD),
                         ("hwndTarget",  wt.HWND)]

        class MSG(ctypes.Structure):
            _fields_ = [("hwnd",    wt.HWND),
                         ("message", wt.UINT),
                         ("wParam",  wt.WPARAM),
                         ("lParam",  wt.LPARAM),
                         ("time",    wt.DWORD),
                         ("pt",      wt.POINT)]

        hwnd = None
        try:
            user32 = ctypes.windll.user32

            hwnd = user32.CreateWindowExW(
                0, "STATIC", "NukeRawInput", 0,
                0, 0, 0, 0, wt.HWND(-3), None, None, None)
            if not hwnd:
                self._log("[RawInput] CreateWindow falhou")
                return

            rid = RAWINPUTDEVICE()
            rid.usUsagePage = 0x01
            rid.usUsage     = 0x02
            rid.dwFlags     = RIDEV_INPUTSINK
            rid.hwndTarget  = hwnd
            if not user32.RegisterRawInputDevices(
                    ctypes.byref(rid), 1, ctypes.sizeof(rid)):
                self._log("[RawInput] RegisterRawInputDevices falhou")
                user32.DestroyWindow(hwnd)
                return

            self._raw_input_active = True
            self._log("[RawInput] Ativo — a receber WM_INPUT")

            buf     = (ctypes.c_byte * BUF_SIZE)()
            buf_ptr = ctypes.cast(buf, ctypes.c_void_p)
            msg     = MSG()

            while self.running:
                got = False
                while user32.PeekMessageW(
                        ctypes.byref(msg), hwnd,
                        WM_INPUT, WM_INPUT, PM_REMOVE):

                    sz  = ctypes.c_uint(BUF_SIZE)
                    ret = user32.GetRawInputData(
                        msg.lParam, RID_INPUT,
                        buf_ptr, ctypes.byref(sz), HDR_SIZE)

                    if ret == 0 or ret == ctypes.c_uint(-1).value:
                        continue

                    raw = bytes(buf[:min(ret, BUF_SIZE)])
                    if len(raw) < OFF_LASTY + 4:
                        continue

                    dw_type = _s.unpack_from("<I", raw, OFF_TYPE)[0]
                    if dw_type != RIM_TYPEMOUSE:
                        continue

                    flags = _s.unpack_from("<H", raw, OFF_FLAGS)[0]
                    if flags & MOUSE_MOVE_ABS:
                        continue

                    lx = _s.unpack_from("<i", raw, OFF_LASTX)[0]
                    ly = _s.unpack_from("<i", raw, OFF_LASTY)[0]

                    if lx or ly:
                        self._raw_debug_count += 1
                        if not self.paused and not self._pass and self.running:
                            with self._mlock:
                                self.mouse_dx += lx
                                self.mouse_dy += ly
                        got = True

                if not got:
                    time.sleep(0.0003)
        except Exception as e:
            self._log(f"[RawInput] Erro: {e}")
        finally:
            was_active = self._raw_input_active
            try:
                if hwnd:
                    ctypes.windll.user32.DestroyWindow(hwnd)
            except Exception:
                pass
            self._raw_input_active = False
            if self.running and was_active:
                self._log("[RawInput] desligou durante execucao, fallback HOOK ativo")

    def _mc(self, x, y, button, pressed):
        if not self.running or self.paused:
            return
        if button == Button.left:
            if pressed:
                self.mb_down.add("lmb")
                self._recoil.fire_start()
                self._is_ads = True
                self._human.reset()
            else:
                self.mb_down.discard("lmb")
                self._recoil.fire_stop()
                self._is_ads = False
        elif button == Button.right:
            if pressed:
                self.mb_down.add("rmb")
                self._is_ads = True
            else:
                self.mb_down.discard("rmb")
                self._is_ads = False
        elif button == Button.middle:
            if pressed and self.cfg.auto_ping:
                self._ping_until = time.monotonic() + 0.15

    # ── loop 120Hz ────────────────────────────────────────────────────
    def _loop(self):
        last_t = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            dt  = max(0.001, now - last_t)
            last_t = now
            if self.paused or self._pass:
                time.sleep(0.02)
                continue
            try:
                if self.gamepad:
                    self._tick(dt)
            except Exception as e:
                self._log(f"loop err: {e}")
            elapsed = time.perf_counter() - now
            st = max(0.0, self.TICK - elapsed)
            if self.cfg.humanize:
                st = self._human.timing(st)
            time.sleep(st)

    def _tick(self, dt: float):
        cfg  = self.cfg
        keys = set(self.keys_down)
        mb   = set(self.mb_down)
        now  = time.monotonic()

        if self._external_mouse:
            with self._mlock:
                self.mouse_dx = self.mouse_dy = 0.0
            dx, dy = 0.0, 0.0
        else:
            with self._mlock:
                dx, dy = self.mouse_dx, self.mouse_dy
                self.mouse_dx = self.mouse_dy = 0.0

        # Debug: log a cada 120 ticks (~1s) se rato não mexer


        # -- Left stick (WASD -> LS) -----------------------------------
        lx = ly = 0.0
        actions = {str(a).upper() for k, a in self._km.items() if k in keys}
        if "LS_UP"    in actions or "w" in keys: ly += 1.0
        if "LS_DOWN"  in actions or "s" in keys: ly -= 1.0
        if "LS_LEFT"  in actions or "a" in keys: lx -= 1.0
        if "LS_RIGHT" in actions or "d" in keys: lx += 1.0
        mag = math.hypot(lx, ly)
        if mag > 1.0:
            lx /= mag
            ly /= mag

        if self._external_mouse:
            self._rx_filt = 0.0
            self._ry_filt = 0.0

        # ── Right stick (rato → RS) ────────────────────────────────────
        #
        # PRINCÍPIO CORRETO (como MKB2Controller, Mouse2Joystick, etc.):
        #   stick = clamp(counts_this_tick / sens, -1.0, 1.0)
        #
        # Onde sens é o número de counts que produz stick=1.0 (full tilt).
        # NÃO dividimos por dt — o dt já está implícito porque acumulamos
        # counts num intervalo fixo de 1/120s.
        #
        # sens_x = 20 significa: 20 counts de rato → stick cheio (muito sensível)
        # sens_x = 200 significa: 200 counts → stick cheio (menos sensível)
        # Default sens_x=4200 no config é a escala ANTIGA (1/185000 * 4200 ≈ 0.023)
        # Vamos manter compatibilidade mas reescalar internamente:
        #   sens_real = sens_x / 185000 * 120   (equivale à fórmula antiga mas correcta)
        #   → com sens_x=4200: sens_real = 4200/185000*120 ≈ 2.73 counts para full stick
        # Isso é DEMASIADO sensível. Escala correcta para 800DPI:
        #   sens_real = sens_x / 2500.0
        #   → com sens_x=4200: sens_real = 1.68 — ainda sensível demais
        # A fórmula mais usada em projetos open source:
        #   stick = tanh(dx * k)   com k = sens / 1000
        # Mas a mais simples e consistente é:
        #   stick = dx / sens_scale,  sens_scale = 50 * (10000/sens_x)
        # → sens_x=4200: scale = 50 * 2.38 = 119 counts para full stick
        # → sens_x=100:  scale = 50 * 100  = 5000 counts (muito lento)
        # → sens_x=12000: scale = 50 * 0.83 = 42 counts (rápido)

        sx = max(200.0, float(cfg.sens_x))
        sy = max(200.0, float(cfg.sens_y))

        # Conversao mouse->stick:
        # - escala mais ampla para evitar saturar em ±1 com pequenos deltas;
        # - eixo Y invertido para bater com convenção XInput (+Y = cima);
        # - tanh evita "cortes" bruscos do clamp e deixa o look mais suave.
        scale_x = 450000.0 / sx
        scale_y = 480000.0 / sy

        raw_rx = math.tanh(dx / scale_x)
        raw_ry = math.tanh(-dy / scale_y)

        # Suavizacao adaptativa:
        # pouco movimento = mais filtro; flick rapido = menos latencia.
        speed = min(1.0, math.hypot(raw_rx, raw_ry))
        alpha = 0.18 + (0.35 * speed)
        self._rx_filt = self._rx_filt * (1.0 - alpha) + raw_rx * alpha
        self._ry_filt = self._ry_filt * (1.0 - alpha) + raw_ry * alpha

        # Decay quando rato parado (parada mais suave).
        if dx == 0.0:
            self._rx_filt *= 0.70
        if dy == 0.0:
            self._ry_filt *= 0.70

        # Threshold de ruído mínimo
        if abs(self._rx_filt) < 0.004: self._rx_filt = 0.0
        if abs(self._ry_filt) < 0.004: self._ry_filt = 0.0

        rx, ry = self._rx_filt, self._ry_filt

        # -- Stick curve (aim assist trigger) -------------------------
        if rx != 0.0 or ry != 0.0:
            c = cfg.aim_curve
            if c == "cod":
                rx, ry = StickCurves.cod(rx, ry, cfg.aim_strength)
            elif c == "linear":
                rx, ry = StickCurves.linear(rx, ry, cfg.aim_strength)
            elif c == "apex":
                rx, ry = StickCurves.apex(rx, ry, cfg.aim_strength)
            else:
                rx, ry = StickCurves.raw(rx, ry)

        # Micro movimento em ADS para manter aim-assist rotacional "acordado".
        if "rmb" in mb:
            if math.hypot(rx, ry) < 0.06:
                self._aa_phase += dt * 7.5
                rx += math.sin(self._aa_phase) * 0.0022
                ry += math.cos(self._aa_phase * 0.85) * 0.0014
        else:
            self._aa_phase = 0.0

        # -- Recoil ---------------------------------------------------
        if "lmb" in mb and cfg.recoil_on:
            rc = self._recoil.tick(raw_dy=dy, dt=dt, aiming=("rmb" in mb or self._is_ads))
            ry = max(-1.0, min(1.0, ry + rc))

        # -- Humanizer ------------------------------------------------
        # Aplicar humanizer apenas em ADS/tiro para nao poluir look normal.
        if cfg.humanize and (self._is_ads or "lmb" in mb or "rmb" in mb):
            if cfg.micro_jitter:
                rx, ry = self._human.jitter(rx, ry)
            if cfg.breathing:
                rx, ry = self._human.breathe(rx, ry, self._is_ads)

        # -- Dead zone ------------------------------------------------
        dz   = max(0.0, float(cfg.deadzone))
        # Deadzone menor no RS para nao travar micro-ajustes do rato.
        dz_rs = max(0.008, min(0.025, dz * 0.60))
        if abs(rx) < dz_rs: rx = 0.0
        if abs(ry) < dz_rs: ry = 0.0
        if abs(lx) < dz: lx = 0.0
        if abs(ly) < dz: ly = 0.0

        # CMD log (debug): so imprime quando o mouse mexe no jogo.
        self._cmd_mouse_trace(dx, dy, raw_rx, raw_ry, rx, ry)

        # -- Enviar ao XInput -----------------------------------------
        self.gamepad.reset()
        ly_out = -ly if self.pad_type == "ds4" else ly
        ry_out = -ry if self.pad_type == "ds4" else ry
        self.gamepad.left_joystick_float(lx, ly_out)
        self.gamepad.right_joystick_float(rx, ry_out)

        lt = 255 if "rmb" in mb else 0
        if cfg.rapid_fire and "lmb" in mb:
            if self._rf_next is None or now >= self._rf_next:
                self._rf_state = not self._rf_state
                self._rf_next  = now + 0.5 / max(1.0, cfg.rapid_fire_hz)
            rt = 255 if self._rf_state else 0
        else:
            rt = 255 if "lmb" in mb else 0
            self._rf_next  = None
            self._rf_state = False

        self.gamepad.left_trigger(lt)
        self.gamepad.right_trigger(rt)

        dpad_up = dpad_down = dpad_left = dpad_right = False
        for k, a in self._km.items():
            if k in keys:
                au = str(a).upper()
                b = self._bmap.get(au)
                if au == "DUP":
                    dpad_up = True
                elif au == "DDOWN":
                    dpad_down = True
                elif au == "DLEFT":
                    dpad_left = True
                elif au == "DRIGHT":
                    dpad_right = True
                elif b:
                    self.gamepad.press_button(b)

        if "shift" in keys:
            if self.pad_type == "ds4":
                self.gamepad.press_button(vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
            else:
                self.gamepad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)

        if cfg.slide_cancel and now < self._slide_until:
            if "shift" in keys or "L3" in actions:
                self.gamepad.press_button(self._bmap["A"])

        if cfg.auto_ping and now < self._ping_until:
            dpad_up = True

        if cfg.parachute:
            if "up"    in keys: dpad_up = True
            if "down"  in keys: dpad_down = True
            if "left"  in keys: dpad_left = True
            if "right" in keys: dpad_right = True

        if self.pad_type == "ds4":
            if dpad_up and dpad_right:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
            elif dpad_up and dpad_left:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
            elif dpad_down and dpad_right:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
            elif dpad_down and dpad_left:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
            elif dpad_up:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH
            elif dpad_down:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH
            elif dpad_left:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
            elif dpad_right:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
            else:
                d = vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE
            self.gamepad.directional_pad(d)
        else:
            if dpad_up:
                self.gamepad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
            if dpad_down:
                self.gamepad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            if dpad_left:
                self.gamepad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
            if dpad_right:
                self.gamepad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        self.gamepad.update()


# =============================================================================
#  GUI
# =============================================================================
class GUI:
    # Paleta NUKE ASSIST: preto profundo + amarelo nuclear + detalhes dourados
    BG    = "#080b0f"; GLASS = "#0c1018"; PANEL = "#101620"; SOFT = "#182030"
    BORD  = "#2a3a50"; ACC   = "#ffbf1f"; ACCHI = "#ffe066"
    OK    = "#39e88e"; WARN  = "#ffd166"; ERR   = "#ff4f6a"
    TEXT  = "#f0f4ff"; MUTED = "#7a8aaa"
    # Para status labels: mascarar nomes de drivers
    DRV_MASK = "SYS"

    def __init__(self):
        self.cfg = Config.load()
        if not hasattr(self.cfg, "external_mouse_app"):
            self.cfg.external_mouse_app = True
            self.cfg.save()
        elif not bool(getattr(self.cfg, "external_mouse_app", True)):
            self.cfg.external_mouse_app = True
            self.cfg.save()
        # Migracao de perfil para suavidade melhorada (aplica uma vez).
        if not bool(getattr(self.cfg, "smooth_profile_v2", False)):
            self.cfg.deadzone = min(float(getattr(self.cfg, "deadzone", 0.04)), 0.04)
            self.cfg.humanize = False
            self.cfg.micro_jitter = False
            self.cfg.breathing = False
            self.cfg.smooth_profile_v2 = True
            self.cfg.save()
        # Perfil v3: defaults focados em smoothness + aim assist mais forte.
        if not bool(getattr(self.cfg, "smooth_profile_v3", False)):
            self.cfg.sens_x = 4200.0
            self.cfg.sens_y = 3900.0
            self.cfg.deadzone = 0.03
            self.cfg.aim_curve = "cod"
            self.cfg.aim_strength = 0.97
            self.cfg.humanize = False
            self.cfg.micro_jitter = False
            self.cfg.breathing = False
            self.cfg.smooth_profile_v2 = True
            self.cfg.smooth_profile_v3 = True
            self.cfg.save()
        self.emu = XboxEmulator(self.cfg)
        self.emu.on_log = self._log
        self.emu.on_status = self._on_status
        self._hh = HidHideManager(log_fn=self._log_safe)
        self._mx = ExternalMouseApp(log_fn=self._log_safe)
        if not bool(getattr(self.cfg, "external_mouse_app", True)):
            ExternalMouseApp.stop_all()

        self._watcher = CodWatcher()
        self._watcher.on_start = self._on_cod_start
        self._watcher.on_stop = self._on_cod_stop
        self._watcher.start()

        self._prepare_assets()

        self.root = tk.Tk()
        self.root.title(APP_TITLE_DEFAULT)
        self.root.configure(bg=self.BG)
        self.root.geometry("1040x720")
        self.root.resizable(False, False)
        # Comeca com frame padrao para manter comportamento estavel de minimizar/restaurar.
        # O modo borderless e reaplicado no _on_map quando a janela fica normal.
        self.root.overrideredirect(False)
        try:
            self.root.wm_attributes("-alpha", 0.97 if self.cfg.glass_style else 1.0)
        except Exception:
            pass

        self._round_r = 44
        self._drag_origin = None
        self._auto_setup_running = False
        self._capture_hotkey = False
        self._settings_open = False
        self._virtual_ok = False
        self._cod_active = False

        self._title_photo = None
        self._ctrl_photo = None
        self._shrek_photo = None

        self._build_ui()
        self._build_stream_overlay()
        self._center()
        self.root.update_idletasks()
        self._ensure_taskbar_entry()
        self._apply_glass_style()
        self.root.bind("<Map>", self._on_map)
        self.root.bind("<Configure>", self._on_configure)
        self.root.bind("<KeyPress>", self._on_key_capture)

        if not bool(getattr(self.cfg, "external_mouse_app", True)):
            self._virtual_ok = self.emu.ensure_gamepad(quiet=True)
        else:
            self._virtual_ok = False
        self._upd_virtual()
        self._apply_stream()
        self._load_imgs()

        threading.Thread(target=self._env_check, daemon=True).start()
        threading.Thread(target=self._auto_setup, daemon=True).start()

    def _prepare_assets(self):
        try:
            os.makedirs(ASSETS_DIR, exist_ok=True)
        except Exception:
            return
        # Copiar assets do diretorio raiz para assets/ se nao existirem
        copies = [
            (os.path.join(APP_DIR, "NUKE_ASSIST.png"),      NUKE_TITLE_IMG),
            (os.path.join(APP_DIR, "ps5_controller.png"),   PS_CTRL_IMG),
            (os.path.join(APP_DIR, "stream_shrek.jpg"),     SHREK_IMG),
            (os.path.join(APP_DIR, "xbox360_controller.png"), CTRL_IMG_LOCAL),
        ]
        for src, dst in copies:
            try:
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
            except Exception:
                pass

    def _build_ui(self):
        self._shell = tk.Frame(self.root, bg=self.BG)
        self._shell.pack(fill="both", expand=True, padx=8, pady=8)

        # Barra nuclear superior (linha amarela)
        tk.Frame(self._shell, bg=self.ACC, height=2).pack(fill="x", pady=(0, 2))

        top = tk.Frame(self._shell, bg=self.BG, height=30)
        top.pack(fill="x", pady=(0, 0))
        top.pack_propagate(False)
        self._bind_drag(top)

        lf = tk.Frame(top, bg=self.BG)
        lf.pack(side="left", fill="x", expand=True)
        self._bind_drag(lf)
        self._dotc = tk.Canvas(lf, width=10, height=10, bg=self.BG, highlightthickness=0)
        self._dotc.pack(side="left", padx=(4, 5))
        self._dotid = self._dotc.create_oval(1, 1, 9, 9, fill=self.ERR, outline="")
        self._svar = tk.StringVar(value="INATIVO")
        tk.Label(lf, textvariable=self._svar, bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        self._cod_lbl = tk.Label(lf, text=" | Jogo: nao detetado", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8))
        self._cod_lbl.pack(side="left")

        rf = tk.Frame(top, bg=self.BG)
        rf.pack(side="right")
        for txt, cmd, hover in [("_", self._minimize, self.WARN), ("X", self._close, self.ERR)]:
            b = tk.Button(rf, text=txt, command=cmd, relief="flat", cursor="hand2",
                          bg=self.SOFT, fg=self.MUTED, activebackground=hover,
                          activeforeground="#100800", width=2, font=("Segoe UI", 9, "bold"))
            b.pack(side="left", padx=(0, 3))

        center = tk.Frame(self._shell, bg=self.BG)
        center.pack(fill="both", expand=True, pady=(2, 8))
        self._bind_drag(center)

        # Logo NUKE ASSIST
        self._title_lbl = tk.Label(center, bg=self.BG)
        self._title_lbl.place(relx=0.50, rely=0.18, anchor="center")

        # Imagem controlo
        self._ctrl_lbl = tk.Label(center, bg=self.BG)
        self._ctrl_lbl.place(relx=0.50, rely=0.56, anchor="center")

        # Botao principal de ativacao
        self._hotkey_btn = tk.Button(
            center, text="", command=self._toggle_hotkey_capture,
            relief="flat", cursor="hand2", width=30, pady=11,
            bg=self.ACC, fg="#1a0e00", activebackground=self.ACCHI,
            font=("Bahnschrift SemiBold", 10))
        self._hotkey_btn.place(relx=0.50, rely=0.905, anchor="center")
        self._sync_hotkey_chip()

        # Botao settings (canto)
        self._open_btn = tk.Button(
            self._shell, text=">", command=self._toggle_settings,
            relief="flat", cursor="hand2", width=3, pady=4,
            bg=self.SOFT, fg=self.ACC, activebackground=self.ACC,
            activeforeground="#1a0e00", font=("Segoe UI", 12, "bold"))
        self._open_btn.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

        self._build_settings_panel()

    def _build_settings_panel(self):
        self._settings = tk.Frame(
            self._shell, bg=self.PANEL, width=340,
            highlightbackground=self.ACC, highlightthickness=1)
        self._settings.place(x=2000, y=0, relheight=1.0)

        # Header do painel
        hd = tk.Frame(self._settings, bg=self.PANEL)
        hd.pack(fill="x", padx=12, pady=(12, 6))
        hdl = tk.Frame(hd, bg=self.PANEL); hdl.pack(side="left", fill="x", expand=True)

        # Linha amarela decorativa
        tk.Frame(hdl, bg=self.ACC, height=2).pack(fill="x", pady=(0, 4))
        tk.Label(hdl, text="NUKE ASSIST", bg=self.PANEL, fg=self.ACC,
                 font=("Bahnschrift SemiBold", 15)).pack(anchor="w")
        tk.Label(hdl, text="CONFIGURACOES", bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")

        self._close_settings_btn = tk.Button(
            hd, text="<", command=self._close_settings, relief="flat", cursor="hand2",
            bg=self.SOFT, fg=self.ACC, activebackground=self.ACC, activeforeground="#1a0e00",
            width=2, font=("Segoe UI", 10, "bold"))
        self._close_settings_btn.pack(side="right", padx=(6, 0), pady=(2, 0))

        tk.Frame(self._settings, bg=self.ACC, height=1).pack(fill="x", padx=12, pady=(0, 8))

        # Botoes AIM ON/OFF + HID + GLASS
        st = tk.Frame(self._settings, bg=self.PANEL)
        st.pack(fill="x", padx=12, pady=(0, 8))
        self._sbtn = tk.Button(st, text="AIM OFF", command=self._toggle_emu,
                               relief="flat", cursor="hand2", width=10, pady=5,
                               bg=self.SOFT, fg=self.TEXT,
                               activebackground=self.ACC, activeforeground="#1a0e00",
                               font=("Segoe UI", 8, "bold"))
        self._sbtn.pack(side="left", padx=(0, 4))

        self._hh_btn = tk.Button(st, text="HID OFF", command=self._toggle_hh,
                                 relief="flat", cursor="hand2", width=10, pady=5,
                                 bg=self.SOFT, fg=self.TEXT,
                                 activebackground=self.OK, activeforeground="#0a1a0a",
                                 font=("Segoe UI", 8, "bold"))
        self._hh_btn.pack(side="left", padx=(0, 4))

        self._glass_btn = tk.Button(st, text="GLASS", command=self._toggle_glass,
                                    relief="flat", cursor="hand2", width=8, pady=5,
                                    bg=self.SOFT, fg=self.TEXT,
                                    activebackground=self.ACC, activeforeground="#1a0e00",
                                    font=("Segoe UI", 8, "bold"))
        self._glass_btn.pack(side="left")

        # Sliders
        sl = tk.Frame(self._settings, bg=self.PANEL)
        sl.pack(fill="x", padx=12)
        self._add_slider(sl, "Sens X",       100,   12000, self.cfg.sens_x,        lambda v: setattr(self.cfg, "sens_x", v),        25,   int)
        self._add_slider(sl, "Sens Y",       100,   12000, self.cfg.sens_y,        lambda v: setattr(self.cfg, "sens_y", v),        25,   int)
        self._add_slider(sl, "Deadzone %",   0,     25,    self.cfg.deadzone*100,  lambda v: setattr(self.cfg, "deadzone", v/100),  0.1,  lambda v: round(v,1))
        self._add_slider(sl, "Aim Strength", 0.4,   1.0,   self.cfg.aim_strength,  lambda v: setattr(self.cfg, "aim_strength", v),  0.01, lambda v: round(v,2))
        self._add_slider(sl, "Rapid Fire Hz",1,     30,    self.cfg.rapid_fire_hz, lambda v: setattr(self.cfg, "rapid_fire_hz", v), 1,    int)

        tk.Frame(self._settings, bg=self.BORD, height=1).pack(fill="x", padx=12, pady=(6, 4))

        # Toggles
        tg = tk.Frame(self._settings, bg=self.PANEL)
        tg.pack(fill="x", padx=12, pady=(0, 6))
        self._toggle_buttons = {}
        toggles = [
            ("humanize",       "Humanize"),
            ("micro_jitter",   "Jitter"),
            ("breathing",      "Breathing"),
            ("rapid_fire",     "Rapid Fire"),
            ("slide_cancel",   "Slide"),
            ("auto_ping",      "Auto Ping"),
            ("parachute",      "Parachute"),
            ("steam_integrate","Steam"),
            ("stream_mode",    "Stream"),
        ]
        for i, (attr, text) in enumerate(toggles):
            b = tk.Button(tg, text=text, relief="flat", cursor="hand2", width=10, pady=4,
                          font=("Segoe UI", 8),
                          command=lambda a=attr: self._flip_cfg(a))
            b.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
            tg.columnconfigure(i % 2, weight=1)
            self._toggle_buttons[attr] = b
        self._sync_toggle_buttons()

        tk.Frame(self._settings, bg=self.BORD, height=1).pack(fill="x", padx=12, pady=(4, 4))

        # Aim Curve
        crv = tk.Frame(self._settings, bg=self.PANEL)
        crv.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(crv, text="STICK CURVE", bg=self.PANEL, fg=self.ACC,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(0, 2))
        self._curve_btns = {}
        rw = tk.Frame(crv, bg=self.PANEL); rw.pack(fill="x")
        for c in ["cod", "linear", "apex", "raw"]:
            b = tk.Button(rw, text=c.upper(), relief="flat", cursor="hand2", width=7, pady=4,
                          font=("Segoe UI", 8), command=lambda c=c: self._set_curve(c))
            b.pack(side="left", padx=(0, 3))
            self._curve_btns[c] = b
        self._sync_curve_buttons()

        # Recoil - opcao unica: Zero Recoil Automatico
        rc = tk.Frame(self._settings, bg=self.PANEL)
        rc.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(rc, text="ZERO RECOIL", bg=self.PANEL, fg=self.ACC,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(0, 2))
        tk.Label(
            rc,
            text=(
                "Compensacao automatica de recuo baseada no movimento real do mouse.\n"
                "Nao usa padroes fixos: adapta-se em tempo real."
            ),
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 7),
            justify="left", wraplength=290).pack(anchor="w", pady=(0, 4))

        self._recoil_auto_btn = tk.Button(
            rc,
            text="ZERO RECOIL: ON" if self.cfg.recoil_on else "ZERO RECOIL: OFF",
            relief="flat", cursor="hand2", width=20, pady=5,
            font=("Segoe UI", 8, "bold"),
            bg=self.ACC if self.cfg.recoil_on else self.SOFT,
            fg="#1a0e00" if self.cfg.recoil_on else self.MUTED,
            activebackground=self.ACCHI, activeforeground="#1a0e00",
            command=self._toggle_recoil_auto)
        self._recoil_auto_btn.pack(anchor="w")

        tk.Frame(self._settings, bg=self.BORD, height=1).pack(fill="x", padx=12, pady=(4, 4))

        # Status deps (mascarado)
        dp = tk.Frame(self._settings, bg=self.PANEL)
        dp.pack(fill="x", padx=12, pady=(0, 4))
        self._dlbls = {}
        for dep in ["ViGEmBus", "HidHide", "vgamepad", "pynput", "Xbox"]:
            f = tk.Frame(dp, bg=self.SOFT, padx=4, pady=3)
            f.pack(side="left", padx=(0, 3))
            tk.Label(f, text=self.DRV_MASK, bg=self.SOFT, fg=self.MUTED,
                     font=("Segoe UI", 6)).pack()
            lbl = tk.Label(f, text="...", bg=self.SOFT, fg=self.WARN,
                           font=("Segoe UI", 6, "bold"))
            lbl.pack()
            self._dlbls[dep] = lbl

        stat = tk.Frame(self._settings, bg=self.PANEL)
        stat.pack(fill="x", padx=12, pady=(0, 4))
        self._vigem_lbl = tk.Label(stat, text=f"{self.DRV_MASK}: ...",
                                   bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8))
        self._vigem_lbl.pack(anchor="w")
        self._hh_status = tk.Label(stat, text=f"{self.DRV_MASK}: ...",
                                   bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8))
        self._hh_status.pack(anchor="w")
        self._x360_lbl = tk.Label(stat, text="Virtual: ...",
                                  bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8))
        self._x360_lbl.pack(anchor="w")

        # LOG
        lg = tk.Frame(self._settings, bg=self.PANEL)
        lg.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self._logb = tk.Text(lg, bg="#08111e", fg=self.TEXT,
                             font=("Consolas", 8), relief="flat",
                             height=8, wrap="word",
                             insertbackground=self.ACC)
        self._logb.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lg, command=self._logb.yview, bg=self.PANEL,
                          troughcolor=self.SOFT, relief="flat")
        sb.pack(side="right", fill="y")
        self._logb.configure(yscrollcommand=sb.set)
        self._logb.config(state="disabled")

        self._sync_hh_btn()
        self._sync_glass_btn()
        self._sync_start_btn()

    def _add_slider(self, parent, name, lo, hi, val, setter, resolution, caster):
        w = tk.Frame(parent, bg=self.PANEL)
        w.pack(fill="x", pady=(0, 5))
        row = tk.Frame(w, bg=self.PANEL); row.pack(fill="x")
        tk.Label(row, text=name, bg=self.PANEL, fg=self.MUTED,
                 font=("Segoe UI", 8)).pack(side="left", anchor="w")
        vv = tk.Label(row, text=str(caster(val)), bg=self.PANEL, fg=self.ACC,
                      font=("Bahnschrift SemiBold", 9))
        vv.pack(side="right", anchor="e")
        def _cb(v):
            fv = float(v); setter(fv)
            vv.config(text=str(caster(fv)))
        tk.Scale(w, from_=lo, to=hi, resolution=resolution, orient="horizontal",
                 showvalue=False, bg=self.PANEL, fg=self.ACC,
                 troughcolor=self.SOFT, activebackground=self.ACCHI,
                 highlightthickness=0, bd=0, sliderrelief="flat",
                 command=_cb).pack(fill="x")

    def _flip_cfg(self, attr):
        setattr(self.cfg, attr, not bool(getattr(self.cfg, attr)))
        if attr == "stream_mode":
            self._apply_stream()
        self._sync_toggle_buttons()

    def _sync_toggle_buttons(self):
        for attr, b in self._toggle_buttons.items():
            on = bool(getattr(self.cfg, attr))
            b.config(
                bg=self.ACC if on else self.SOFT,
                fg="#1a0e00" if on else self.MUTED,
                activebackground=self.ACCHI if on else self.ACC,
                activeforeground="#1a0e00")

    def _set_curve(self, c):
        self.cfg.aim_curve = c
        self._sync_curve_buttons()

    def _sync_curve_buttons(self):
        for k, b in self._curve_btns.items():
            on = (k == self.cfg.aim_curve)
            b.config(bg=self.ACC if on else self.SOFT,
                     fg="#1a0e00" if on else self.MUTED,
                     activebackground=self.ACCHI)

    def _toggle_recoil_auto(self):
        self.cfg.recoil_on = not self.cfg.recoil_on
        if self.emu._recoil:
            self.emu._recoil._on = self.cfg.recoil_on
        on = self.cfg.recoil_on
        self._recoil_auto_btn.config(
            text="ZERO RECOIL: ON" if on else "ZERO RECOIL: OFF",
            bg=self.ACC if on else self.SOFT,
            fg="#1a0e00" if on else self.MUTED)
        self._log("Zero Recoil: " + ("ATIVO" if on else "DESATIVO"))
        self.cfg.save()

    def _toggle_settings(self):
        self._settings_open = not self._settings_open
        self._open_btn.config(text="<" if self._settings_open else ">")
        self._position_settings_panel()

    def _close_settings(self):
        self._settings_open = False
        self._open_btn.config(text=">")
        self._position_settings_panel()

    def _position_settings_panel(self):
        w = max(1040, self.root.winfo_width())
        h = max(720, self.root.winfo_height())
        sw = 330
        x = w - sw if self._settings_open else w + 2
        self._settings.place(x=x, y=0, width=sw, height=h)

    def _sync_hotkey_chip(self):
        key = str(getattr(self.cfg, "toggle_key", "f12") or "f12").upper()
        if self._capture_hotkey:
            self._hotkey_btn.config(text="▶  PRESSIONE UMA TECLA...",
                                    bg=self.ACCHI, fg="#1a0e00")
        else:
            stat = "ON" if self.emu.running else "OFF"
            col  = self.OK if self.emu.running else self.ACC
            self._hotkey_btn.config(
                text=f"[{key}]  NUKE ASSIST  —  {stat}",
                bg=col, fg="#081a08" if self.emu.running else "#1a0e00")

    def _toggle_hotkey_capture(self):
        self._capture_hotkey = True
        self._sync_hotkey_chip()
        try:
            self.root.focus_force()
        except Exception:
            pass

    def _on_key_capture(self, event):
        if not self._capture_hotkey:
            return
        name = self._event_to_key(event)
        if not name:
            return "break"
        self.cfg.toggle_key = name
        self._capture_hotkey = False
        self._sync_hotkey_chip()
        self._log(f"Tecla de ativacao alterada para {name.upper()}")
        self.cfg.save()
        return "break"

    def _event_to_key(self, event) -> str:
        k = str(event.keysym or "").strip().lower()
        mapk = {
            "space": "space", "escape": "escape", "esc": "escape",
            "control_l": "ctrl", "control_r": "ctrl", "ctrl_l": "ctrl", "ctrl_r": "ctrl",
            "shift_l": "shift", "shift_r": "shift", "return": "enter", "backspace": "backspace",
            "up": "up", "down": "down", "left": "left", "right": "right", "tab": "tab",
        }
        if k in mapk:
            return mapk[k]
        if len(k) == 1 and k.isprintable():
            return k
        if k.startswith("f") and k[1:].isdigit():
            return k
        return ""

    def _bind_drag(self, w):
        def _sm(e):
            self._drag_origin = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y())
        def _mv(e):
            if not self._drag_origin:
                return
            sx, sy, wx, wy = self._drag_origin
            self.root.geometry(f"+{wx + (e.x_root - sx)}+{wy + (e.y_root - sy)}")
        w.bind("<ButtonPress-1>", _sm)
        w.bind("<B1-Motion>", _mv)

    def _center(self):
        self.root.update_idletasks()
        w, h = 1040, 720
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{max(20, (sw-w)//2)}+{max(20, (sh-h)//2)}")
        self._position_settings_panel()

    def _toggle_emu(self):
        if self.emu.running:
            self.emu.stop(keep_gp=True)
            try:
                self._mx.stop()
            except Exception:
                pass
        else:
            self._start_emu()
        self._sync_start_btn()
        self._upd_virtual()
        threading.Thread(target=self._env_check, daemon=True).start()

    def _sync_start_btn(self):
        if self.emu.running and not self.emu.paused:
            self._sbtn.config(text="AIM  ON", bg=self.OK, fg="#081a08",
                              activebackground="#50ff9a")
        elif self.emu.running and self.emu.paused:
            self._sbtn.config(text="PAUSADO", bg=self.WARN, fg="#1f1500")
        else:
            self._sbtn.config(text="AIM OFF", bg=self.SOFT, fg=self.TEXT,
                              activebackground=self.ACC)

    def _start_emu(self):
        self._apply_km()
        if bool(getattr(self.cfg, "external_mouse_app", True)):
            target_proc = CodWatcher._find() or "cod.exe"
            ok_ext = self._mx.start(process_name=target_proc, restart=True)
            self.emu.set_external_mouse(ok_ext)
            if not ok_ext:
                self._log("[Mouse] Falha ao iniciar backend externo; mouse interno reativado.")
        else:
            ExternalMouseApp.stop_all(log_fn=self._log)
            self.emu.set_external_mouse(False)
        ok = self.emu.start()
        if ok:
            self._capture_hotkey = False
            # Mantem o modo controle ativo por defeito.
            self.emu.set_game_active(True, log=False)
            self._sync_hotkey_chip()
        self._sync_start_btn()
        self._upd_virtual()
        threading.Thread(target=self._env_check, daemon=True).start()

    def _toggle_hh(self):
        if self._hh.active:
            self._hh.disable()
        else:
            self._hh.enable()
        self._sync_hh_btn()

    def _sync_hh_btn(self):
        if self._hh.active:
            self._hh_btn.config(text="HID  ON", bg=self.OK, fg="#081a08",
                                activebackground="#50ff9a")
        else:
            self._hh_btn.config(text="HID OFF", bg=self.SOFT, fg=self.TEXT,
                                activebackground=self.OK)

    def _toggle_glass(self):
        self.cfg.glass_style = not bool(self.cfg.glass_style)
        self._apply_glass_style()
        self._sync_glass_btn()
        self.cfg.save()

    def _sync_glass_btn(self):
        on = bool(self.cfg.glass_style)
        self._glass_btn.config(text="GLASS ON" if on else "GLASS OFF",
                               bg=self.ACC if on else self.SOFT,
                               fg="#1a0e00" if on else self.TEXT)

    def _auto_setup(self):
        """
        Setup automatico ao abrir:
        1. Verifica estado na pasta nukeassist (evita reinstalar)
        2. Instala drivers/libs silenciosamente se necessario
        3. Ativa HidHide + emulador automaticamente
        4. Forca modo Controller nos configs do COD
        """
        if self._auto_setup_running:
            return
        self._auto_setup_running = True
        try:
            self._log("[Setup] Iniciando configuracao automatica...")

            # Instalar tudo silenciosamente (usa cache de estado)
            result = SilentInstaller.run_all(
                log_fn=self._log,
                prog_fn=lambda pct, msg: self._log(f"  [{pct}%] {msg}")
            )

            # Recarregar modulos se recém-instalados
            self.emu.refresh_runtime_deps()

            # Backend externo de mouse (Mouse2Joystick).
            ext_mouse = bool(getattr(self.cfg, "external_mouse_app", True))
            if ext_mouse:
                target_proc = CodWatcher._find() or "cod.exe"
                ok_ext = self._mx.start(process_name=target_proc, restart=True)
                self.emu.set_external_mouse(ok_ext)
                if ok_ext:
                    self._log("[Setup] Mouse externo ativo (Mouse2Joystick).")
                else:
                    self._log("[Setup] Mouse externo falhou; backend interno mantido.")
            else:
                ExternalMouseApp.stop_all(log_fn=self._log)
                self.emu.set_external_mouse(False)
                self._log("[Setup] Mouse interno (compatibilidade) ativo.")

            # Criar gamepad virtual
            if (not ext_mouse) and (not self.emu.gamepad):
                self.emu.ensure_gamepad(quiet=True)
            self.root.after(0, self._upd_virtual)

            # Steam integration
            if self.cfg.steam_integrate:
                self._log("[Setup] Configurando Steam...")
                SteamBridge.configure(self._log)

            # Ativar HidHide (esconder KB+Mouse do jogo)
            if (not ext_mouse) and self._hh.is_available():
                self._hh.enable()
                self.root.after(0, self._sync_hh_btn)
            else:
                if not ext_mouse:
                    self._log("[Setup] HidHide nao disponivel ainda")
                else:
                    self._log("[Setup] HidHide ignorado no modo mouse externo (compatibilidade).")
                if (not ext_mouse) and result.get("needs_reboot"):
                    self._log("[Setup] *** REINICIA O PC para ativar drivers ***")

            # Iniciar emulador automaticamente
            if not self.emu.running:
                self.root.after(0, self._start_emu)
            else:
                self.emu.set_game_active(True, log=False)

            # Forcar modo Controller nos configs do COD
            self._force_controller_mode()

            # Refresh status
            self.root.after(300, lambda: threading.Thread(
                target=self._env_check, daemon=True).start())

            self._log("[Setup] Configuracao automatica concluida!")
        except Exception as e:
            self._log(f"[Setup] Erro: {e}")
        finally:
            self._auto_setup_running = False

    def _force_controller_mode(self):
        ext_mouse = bool(getattr(self.cfg, "external_mouse_app", True))
        if not ext_mouse:
            self.emu.ensure_gamepad(quiet=True)
        if not self.emu.running:
            self.root.after(0, self._start_emu)
            time.sleep(1.0)
        if not ext_mouse:
            self._hh.enable()
            self.root.after(0, self._sync_hh_btn)
        CodSettingsBridge.force_controller(self._log)
        if not ext_mouse:
            self.emu._wake_controller_presence()
        self._log("Modo controle automatico reforcado.")

    def _apply_km(self):
        if self.emu.running:
            self.emu._km = self.emu._resolve_km()

    def _upd_virtual(self):
        ok = self.emu.gamepad is not None
        self._virtual_ok = ok
        col = self.OK if ok else self.ERR
        kind = self.emu.pad_type.upper() if ok else "--"
        if hasattr(self, "_x360_lbl"):
            self._x360_lbl.config(text=f"Virtual: {kind} {'ON' if ok else 'OFF'}", fg=col)

    def _build_stream_overlay(self):
        self._stream_overlay = tk.Frame(self._shell, bg=self.BG)
        self._stream_lbl = tk.Label(self._stream_overlay, bg=self.BG)
        self._stream_lbl.pack(fill="both", expand=True)

    def _apply_stream(self):
        sm = bool(self.cfg.stream_mode)
        title = APP_TITLE_STREAM if sm else APP_TITLE_DEFAULT
        self.root.title(title)
        if self._stream_overlay:
            if sm:
                self._load_shrek()
                self._stream_overlay.place(x=0, y=0, relwidth=1, relheight=1)
                self._stream_overlay.lift()
            else:
                self._stream_overlay.place_forget()

    def _env_check(self):
        checks = {
            "ViGEmBus": self.emu.vigem_ok(),
            "HidHide":  self.emu.hidhide_ok(),
            "vgamepad": VG_OK,
            "pynput":   PN_OK,
            "Xbox":     self.emu.gamepad is not None,
        }
        for name, ok in checks.items():
            c = self.OK if ok else self.ERR
            t = "OK" if ok else "FALTA"
            if name in self._dlbls:
                self.root.after(0, lambda n=name, c=c, t=t: self._dlbls[n].config(text=t, fg=c))
        ok_v = checks["ViGEmBus"]; ok_h = checks["HidHide"]
        self.root.after(0, lambda: self._vigem_lbl.config(
            text=f"{self.DRV_MASK}: OK" if ok_v else f"{self.DRV_MASK}: falta",
            fg=self.OK if ok_v else self.ERR))
        self.root.after(0, lambda: self._hh_status.config(
            text=f"{self.DRV_MASK}: OK" if ok_h else f"{self.DRV_MASK}: falta",
            fg=self.OK if ok_h else self.WARN))
        self.root.after(0, self._upd_virtual)

    def _on_status(self, s):
        d = {"running": (self.OK, "ATIVO"), "paused": (self.WARN, "PAUSADO"), "stopped": (self.ERR, "INATIVO")}
        c, t = d.get(s, (self.ERR, "INATIVO"))
        self.root.after(0, lambda: (
            self._dotc.itemconfig(self._dotid, fill=c),
            self._svar.set(t),
            self._sync_start_btn(),
            self._sync_hotkey_chip()
        ))

    def _log_safe(self, msg):
        try:
            self.root.after(0, lambda: self._log(msg))
        except Exception:
            pass

    def _log(self, msg):
        if self.cfg.stream_mode or not hasattr(self, "_logb"):
            return
        ts = time.strftime("%H:%M:%S")
        def _u():
            self._logb.config(state="normal")
            self._logb.insert("end", f"[{ts}] {msg}\n")
            self._logb.see("end")
            self._logb.config(state="disabled")
        self.root.after(0, _u)

    def _on_cod_start(self, proc):
        self._cod_active = True
        self._log(f"{proc} detetado!")
        if bool(getattr(self.cfg, "external_mouse_app", True)):
            # Atualiza o preset com o executavel real do jogo e reinicia o backend externo.
            ok_ext = self._mx.start(process_name=proc, restart=True)
            self.emu.set_external_mouse(ok_ext)
        self.root.after(0, lambda: self._cod_lbl.config(text=f" | Jogo: {proc}", fg=self.OK))
        if not self.emu.running:
            self.root.after(500, self._start_emu)
        else:
            self.emu.set_game_active(True, log=True)
        self.root.after(1200, lambda: threading.Thread(target=self._force_controller_mode, daemon=True).start())

    def _on_cod_stop(self):
        self._cod_active = False
        self._log("Jogo fechado.")
        if self.emu.running:
            # CORRIGIDO: era True (bug) — deve ser False para desativar pass-through
            self.emu.set_game_active(False, log=False)
        self.root.after(0, lambda: self._cod_lbl.config(text=" | Jogo: nao detetado", fg=self.MUTED))

    def _load_imgs(self):
        threading.Thread(target=self._load_title, daemon=True).start()
        threading.Thread(target=self._load_ctrl, daemon=True).start()

    def _load_title(self):
        if not PIL_OK:
            return
        try:
            # Procurar NUKE_ASSIST.png em varios locais
            candidates = [
                NUKE_TITLE_IMG, NUKE_TITLE_FALLBACK,
                os.path.join(APP_DIR, "NUKE ASSIST.png"),
                os.path.join(APP_DIR, "assets", "NUKE ASSIST.png"),
            ]
            p = next((c for c in candidates if os.path.exists(c)), None)
            if not p:
                # Gerar titulo NUKE ASSIST em texto se imagem nao existir
                self.root.after(0, self._make_text_title)
                return
            img = Image.open(p).convert("RGBA")
            # Remover fundo preto (transparencia)
            px = img.load()
            w0, h0 = img.size
            for y in range(h0):
                for x in range(w0):
                    r, g, b, a = px[x, y]
                    if r < 40 and g < 40 and b < 40:
                        px[x, y] = (r, g, b, 0)
                    elif r < 60 and g < 60 and b < 60:
                        px[x, y] = (r, g, b, max(0, int(a * 0.15)))
            bb = img.getbbox()
            if bb:
                img = img.crop(bb)
            img = self._fit_image(img, 560, 130)
            ph = ImageTk.PhotoImage(img)
            self.root.after(0, lambda: self._set_title(ph))
        except Exception:
            self.root.after(0, self._make_text_title)

    def _make_text_title(self):
        """Gera logo NUKE ASSIST em canvas se imagem nao disponivel."""
        if not hasattr(self, "_title_lbl"):
            return
        try:
            # Criar canvas com texto estilizado
            c = tk.Canvas(self._title_lbl.master, bg=self.BG,
                          width=500, height=90, highlightthickness=0)
            c.create_text(250, 45, text="NUKE  ASSIST",
                          font=("Bahnschrift SemiBold", 36),
                          fill=self.ACC)
            c.create_text(250, 75, text="CONTROLLER EMULATION ENGINE",
                          font=("Segoe UI", 9), fill=self.MUTED)
            c.place(relx=0.5, rely=0.18, anchor="center")
        except Exception:
            pass

    def _set_title(self, ph):
        self._title_photo = ph
        self._title_lbl.config(image=ph)

    def _load_ctrl(self):
        if not PIL_OK:
            return
        try:
            p = None
            # Visual restaurado mais limpo e sem cortes: preferir imagem local principal.
            if os.path.exists(CTRL_IMG_LOCAL):
                p = CTRL_IMG_LOCAL
            elif os.path.exists(CTRL_IMG_FALLBACK):
                p = CTRL_IMG_FALLBACK
            elif os.path.exists(PS_CTRL_IMG):
                p = PS_CTRL_IMG
            elif os.path.exists(PS_CTRL_FALLBACK):
                p = PS_CTRL_FALLBACK
            if not p:
                return
            img = Image.open(p).convert("RGBA")
            bb = img.getbbox()
            if bb:
                img = img.crop(bb)
            img = self._fit_image(img, 560, 320)
            ph = ImageTk.PhotoImage(img)
            self.root.after(0, lambda: self._set_ctrl(ph))
        except Exception:
            pass

    def _fit_image(self, img, max_w: int, max_h: int):
        iw, ih = img.size
        if iw <= 0 or ih <= 0:
            return img
        scale = min(max_w / iw, max_h / ih)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))
        return img.resize((nw, nh), Image.LANCZOS)

    def _set_ctrl(self, ph):
        self._ctrl_photo = ph
        self._ctrl_lbl.config(image=ph)

    def _load_shrek(self):
        if not PIL_OK:
            return
        try:
            p = SHREK_IMG if os.path.exists(SHREK_IMG) else SHREK_FALLBACK
            if not os.path.exists(p):
                return
            img = Image.open(p).resize((1040, 720), Image.LANCZOS)
            ph = ImageTk.PhotoImage(img)
            self._shrek_photo = ph
            if self._stream_lbl:
                self._stream_lbl.config(image=ph)
        except Exception:
            pass

    def _effects(self):
        if sys.platform != "win32":
            return
        if self.cfg.glass_style:
            self._blur()
        else:
            self._clear_blur()
        self._rounded()
        self._dwm_round()

    def _blur(self):
        try:
            class ACCENT(ctypes.Structure):
                _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                            ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]
            class WCAD(ctypes.Structure):
                _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]
            a = ACCENT(); a.AccentState = 4; a.AccentFlags = 2; a.GradientColor = 0xC0080b0f
            d = WCAD(); d.Attribute = 19; d.SizeOfData = ctypes.sizeof(a)
            d.Data = ctypes.cast(ctypes.pointer(a), ctypes.c_void_p)
            fn = ctypes.windll.user32.SetWindowCompositionAttribute
            fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(WCAD)]; fn.restype = ctypes.c_int
            fn(ctypes.c_void_p(self.root.winfo_id()), ctypes.byref(d))
        except Exception:
            pass

    def _clear_blur(self):
        try:
            class ACCENT(ctypes.Structure):
                _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                            ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]
            class WCAD(ctypes.Structure):
                _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]
            a = ACCENT(); a.AccentState = 0; a.AccentFlags = 0; a.GradientColor = 0
            d = WCAD(); d.Attribute = 19; d.SizeOfData = ctypes.sizeof(a)
            d.Data = ctypes.cast(ctypes.pointer(a), ctypes.c_void_p)
            fn = ctypes.windll.user32.SetWindowCompositionAttribute
            fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(WCAD)]; fn.restype = ctypes.c_int
            fn(ctypes.c_void_p(self.root.winfo_id()), ctypes.byref(d))
        except Exception:
            pass

    def _dwm_round(self):
        try:
            v = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(self.root.winfo_id()), ctypes.c_uint(33), ctypes.byref(v), ctypes.sizeof(v))
        except Exception:
            pass

    def _rounded(self):
        if sys.platform != "win32":
            return
        try:
            w = max(1, self.root.winfo_width()); h = max(1, self.root.winfo_height())
            hrgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1, self._round_r, self._round_r)
            ctypes.windll.user32.SetWindowRgn(ctypes.c_void_p(self.root.winfo_id()), hrgn, True)
        except Exception:
            pass

    def _apply_glass_style(self):
        try:
            self.root.wm_attributes("-alpha", 0.97 if self.cfg.glass_style else 1.0)
        except Exception:
            pass
        self._effects()
        self._sync_glass_btn()

    def _ensure_taskbar_entry(self):
        if sys.platform != "win32":
            return
        try:
            hwnd = ctypes.c_void_p(self.root.winfo_id())
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            exstyle = (exstyle | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)
        except Exception:
            pass

    def _on_map(self, _=None):
        if self.root.state() == "normal":
            self._ensure_taskbar_entry()
            self.root.after(20, lambda: self.root.overrideredirect(True))
            self.root.after(40, self._apply_glass_style)

    def _on_configure(self, e):
        if e.widget is self.root:
            self._position_settings_panel()
            self._rounded()

    def _minimize(self):
        self.root.update_idletasks()
        self.root.overrideredirect(False)
        self._ensure_taskbar_entry()
        self.root.iconify()

    def _close(self):
        if self._hh.active:
            self._hh.disable()
        try:
            self._mx.stop()
        except Exception:
            pass
        self._watcher.stop()
        self.emu.stop(keep_gp=False)
        self.cfg.save()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()


if __name__ == "__main__":
    if sys.platform != "win32":
        print("NUKE ASSIST requer Windows 10/11.")
        sys.exit(1)
    if not TK_OK:
        print("Instala Python com tkinter.")
        sys.exit(1)
    # DPI awareness: evita coordenadas erradas em ecrãs com escala > 100%
    # e corrige inversão/saltos do rato em jogos com raw input ativo.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()   # fallback Windows 7/8
        except Exception:
            pass
    # Garantir pasta oculta existe ao arrancar
    _ensure_hidden_dir()
    if CMD_MOUSE_LOG_DEFAULT:
        _ensure_debug_console()
        print("[NUKE] Mouse CMD log ativo (--mouse-log).")
        print("[NUKE] Vai mostrar logs quando mexer o mouse em jogo.")
    GUI().run()
