import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "kuruitsugizaki.json"
KEYS = {
    "fl_exe": ("FL Studio's FL64.exe", r"C:\Program Files\Image-Line\FL Studio 2025\FL64.exe"),
    "loopmidi_exe": ("loopMIDI.exe, the virtual MIDI port FL needs before it loads the controller script", r"C:\Program Files (x86)\Tobias Erichsen\loopMIDI\loopMIDI.exe"),
    "fl_hardware": ("FL's Settings\\Hardware folder, where controller scripts are installed", r"Documents\Image-Line\FL Studio\Settings\Hardware"),
    "template": ("the .flp new projects are built from, relative to this folder or absolute", "projects/init/init.flp"),
    "library": ("optional: an .flp FL saved holding tuned plugin instances to reuse by name, each instrument on its own channel and each effect in a mixer slot", "projects/library.flp"),
    "plugin_db": ("FL's Plugin database folder, holding Installed\\Generators and Installed\\Effects; found by itself under Documents when not set", r"Documents\Image-Line\FL Studio\Presets\Plugin database"),
    "effect_template": ("an .flp FL saved with at least one mixer effect; its first effect is the block new effects are built on", "projects/init/fx.flp"),
    "fl_presets": ("FL's factory Plugin presets folder, holding Generators and Effects of .fst files", r"C:\Program Files\Image-Line\FL Studio 2025\Data\Patches\Plugin presets"),
    "fl_user_presets": ("FL's user Plugin presets folder", r"Documents\Image-Line\FL Studio\Presets\Plugin presets"),
    "vst_presets": ("per VST plugin, its vendor preset folders: {plugin: {ext: '.vpreset', dirs: {'': factory folder, 'user': user folder}}}", "{}"),
    "flex_packs": ("FLEX's pack folder, holding the .flexpack files", r"Documents\Image-Line\FLEX\Packs"),
    "diva_presets": ("more folders of Diva .h2p presets, read after Diva's own preset folder; a folder or a list", r"Documents\u-he\Diva.data\Presets\Diva"),
    "sylenth1_presets": ("more folders of Sylenth1 .fxp presets, read after Sylenth1's own preset folder; a folder or a list", r"Documents\LennarDigital\Sylenth1\Presets"),
    "serum2_presets": ("more folders of .SerumPreset files, read after Serum 2's own preset folder; a folder or a list", r"Documents\Xfer\Serum 2 Presets"),
    "vital_presets": ("more folders of .vital files, read after Vital's own User folder", r"Documents\Vital\User"),
    "nks_presets": ("more folders of NKS .nksf presets, read after Native Instruments' User Content and the libraries in Public Documents", r"Documents\Native Instruments\User Content"),
    "claude_desktop_config": ("the Claude desktop app's config file, where setup adds the server and uninstall removes it", r"%APPDATA%\Claude\claude_desktop_config.json"),
    "claude_code_dir": ("the Claude Code profile folder (CLAUDE_CONFIG_DIR) setup adds the server to; not set means Claude Code's default", r"%USERPROFILE%\.claude"),
    "projects_folder": ("the folder of the user's own .flp projects, which profile reads; asked once, 'none' when they have none", r"Documents\Image-Line\FL Studio\Projects"),
    "sample_folders": ("the user's sample folders, which samples lists; a folder or a JSON list of folders, asked once, 'none' when they have none", "no usual place: ask the user"),
    "hide_plugins": ("plugins from FL's plugin database to leave out of plugins and by-name lookup: names or * patterns, case-insensitive, '<format>:<name>' (native, vst3, clap, vst) for one format only, and 'category:<folder>' for every plugin the database files under that category (Effects\\<folder>, Generators\\<folder>); a value set here replaces the default list", "['VFX *', '*NoteBook*', 'category:Visual']"),
}
HIDE = ["Fruity Video Player", "Wave Traveller", "BeepMap", "BassDrum", "Fruity Voltage Controller", "Dashboard", "Fruit Kick",
        "ReWired", "MIDI Out", "ZGameEditor Visualizer", "*NoteBook*", "Fruity Big Clock", "Razer Chroma", "Fruity Dance",
        "VFX *", "Layer", "*Mobile*", "category:Visual", "Fruity Delay 2", "Fruity Parametric EQ",
        "vst:Absynth 5", "vst:Absynth 5 Stereo", "vst:Ample Metal Eclipse", "vst:DUNE 3", "vst:FL Studio VSTi", "vst:FL Studio VSTi (Multi)",
        "vst:Nexus", "vst:Omnisphere", "vst:Absynth 5 FX", "vst:Absynth 5 FX Surround", "vst:FX-Omnisphere", "vst:GClip",
        "vst:HalfTime-64bit", "vst:iZotope Trash 2"]
ASKED = {"projects_folder", "sample_folders"}  # asked of the user once, never detected; [] records the answer "none"
DEFAULTS = {"template": "projects/init/init.flp", "effect_template": "projects/init/fx.flp", "hide_plugins": HIDE}


class Missing(RuntimeError):
    pass


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def documents() -> Path:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as k:
            return Path(winreg.QueryValueEx(k, "Personal")[0])
    except Exception:
        return Path.home() / "Documents"


def _fl_dir(data: dict) -> Path | None:
    if data.get("fl_exe"):
        return Path(data["fl_exe"]).parent
    found = sorted(Path(r"C:\Program Files\Image-Line").glob("FL Studio*/FL64.exe"))
    return found[-1].parent if found else None


def _places(data: dict) -> dict:
    d, fl = documents(), _fl_dir(data)
    il = d / "Image-Line"
    pub = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Documents"
    return {
        "fl_exe": [fl / "FL64.exe"] if fl else [],
        "loopmidi_exe": [Path(r"C:\Program Files (x86)\Tobias Erichsen\loopMIDI\loopMIDI.exe"), Path(r"C:\Program Files\Tobias Erichsen\loopMIDI\loopMIDI.exe")],
        "fl_hardware": [il / "FL Studio" / "Settings" / "Hardware"],
        "fl_presets": [fl / "Data" / "Patches" / "Plugin presets"] if fl else [],
        "fl_user_presets": [il / "FL Studio" / "Presets" / "Plugin presets"],
        "plugin_db": [il / "FL Studio" / "Presets" / "Plugin database"],
        "flex_packs": [il / "FLEX" / "Packs"],
        "diva_presets": [d / "u-he" / "Diva.data" / "Presets" / "Diva"],
        "sylenth1_presets": [d / "LennarDigital" / "Sylenth1" / "Presets"],
        "serum2_presets": [d / "Xfer" / "Serum 2 Presets"],
        "vital_presets": [d / "Vital" / "User"],
        "nks_presets": [d / "Native Instruments" / "User Content"] + (sorted(pub.glob("* Library")) if pub.is_dir() else []),
        "claude_desktop_config": [Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"],
        "claude_code_dir": [Path(os.environ["CLAUDE_CONFIG_DIR"])] if os.environ.get("CLAUDE_CONFIG_DIR") else [Path.home() / ".claude"],
    }


def detect(key: str, data: dict | None = None) -> str | None:
    data = load() if data is None else data
    return next((str(p) for p in _places(data).get(key, []) if p.exists()), None)


def roots(key: str) -> list[Path]:
    data = load()
    v = data.get(key)
    extra = [v] if isinstance(v, str) else list(v or [])
    out = []
    for p in [p for p in _places(data).get(key, []) if p.is_dir()] + [Path(x) if Path(x).is_absolute() else ROOT / x for x in extra]:
        if p.is_dir() and all(p.resolve() != q.resolve() for q in out):
            out.append(p)
    return out


def get(key: str, default=None):
    data = load()
    if key in data:
        return data[key]
    if key in DEFAULTS:
        return DEFAULTS[key]
    found = detect(key, data)
    return found if found is not None else default


def need(key: str) -> str:
    value = get(key)
    if value:
        return value
    what, usual = KEYS[key]
    raise Missing(f"{key} is not set: {what}, usually {usual}. Ask the user where it is on their machine, then set it with the config tool (key='{key}') or in {FILE.name}; do not guess.")


def path(key: str) -> Path:
    v = need(key)
    p = Path(v[0] if isinstance(v, list) else v)
    return p if p.is_absolute() else ROOT / p


def claude_desktop() -> Path:
    """The Claude desktop app's config file: the one setup was given, else the app's usual one."""
    return Path(load().get("claude_desktop_config") or _places({})["claude_desktop_config"][0])


def claude_code_env() -> dict:
    """The environment to run the claude CLI in: CLAUDE_CONFIG_DIR set to the profile folder setup was given, if any."""
    env = dict(os.environ)
    if load().get("claude_code_dir"):
        env["CLAUDE_CONFIG_DIR"] = load()["claude_code_dir"]
    return env


def put(key: str, value) -> dict:
    data = load()
    data[key] = value
    FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def status() -> dict:
    data = load()
    out = {}
    for key, (what, usual) in KEYS.items():
        value = data.get(key, DEFAULTS.get(key))
        found = None
        if value is None:
            found = detect(key, data)
        if value is None and found is None:
            out[key] = {"set": False, "what": what, "usually": usual}
            continue
        if found is not None:
            out[key] = {"set": False, "detected": found, "exists": True}
            continue
        if key in ASKED and value == []:
            out[key] = {"set": True, "value": "none", "what": what}
            continue
        if not isinstance(value, str):
            out[key] = {"set": key in data, "value": value}
            continue
        p = Path(value)
        p = p if p.is_absolute() else ROOT / p
        out[key] = {"set": True, "value": value, "exists": p.exists(), "default": key not in data}
    for key in sorted(set(data) - set(KEYS)):
        out[key] = {"set": True, "value": data[key]}
    return out
