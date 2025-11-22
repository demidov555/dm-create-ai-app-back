import json
from datetime import datetime
from pprint import pformat


RESET = "\033[0m"
BOLD = "\033[1m"

COLORS = {
    "info": "\033[36m",  # cyan
    "success": "\033[32m",  # green
    "warning": "\033[33m",  # yellow
    "error": "\033[31m",  # red
    "line": "\033[90m",  # gray
    "step": "\033[35m",  # magenta
    "obj": "\033[34m",  # blue
}


def _ts():
    return datetime.now().strftime("%H:%M:%S")


# -----------------------------------------------------
# 🧠 УНИВЕРСАЛЬНЫЙ JSON СЕРИАЛИЗАТОР
# -----------------------------------------------------


def json_serialize(obj):
    """
    Универсальный сериализатор:
    - dict, list, tuple => JSON
    - object => его __dict__
    - Exception => str
    - bytes => utf-8
    - datetime => isoformat
    - UUID => str
    - fallback → repr()
    """
    if obj is None:
        return None

    # простые типы
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # UUID, date, datetime
    if hasattr(obj, "isoformat"):  # datetime types
        return obj.isoformat()

    # bytes
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except:
            return str(obj)

    # dict
    if isinstance(obj, dict):
        return {json_serialize(k): json_serialize(v) for k, v in obj.items()}

    # list / tuple / set
    if isinstance(obj, (list, tuple, set)):
        return [json_serialize(v) for v in obj]

    # Exception
    if isinstance(obj, BaseException):
        return str(obj)

    # pydantic / dataclasses / любые объекты
    if hasattr(obj, "__dict__"):
        return {
            "__class__": obj.__class__.__name__,
            **{k: json_serialize(v) for k, v in obj.__dict__.items()},
        }

    # fallback
    return repr(obj)


def dump_obj(value):
    try:
        data = json_serialize(value)
        text = json.dumps(data, indent=2, ensure_ascii=False)
        return text
    except Exception:
        return pformat(value, width=80, compact=False)


def line():
    print(
        COLORS["line"]
        + "──────────────────────────────────────────────────────────────"
        + RESET
    )


def info(msg):
    text = dump_obj(msg)
    print(f"{COLORS['info']}ℹ️  [{_ts()}] {text}{RESET}")


def success(msg):
    text = dump_obj(msg)
    print(f"{COLORS['success']}✅ [{_ts()}] {text}{RESET}")


def warning(msg):
    text = dump_obj(msg)
    print(f"{COLORS['warning']}⚠️  [{_ts()}] {text}{RESET}")


def error(msg):
    text = dump_obj(msg)
    print(f"{COLORS['error']}⛔ [{_ts()}] {text}{RESET}")


def step(msg):
    text = dump_obj(msg)
    print(f"{COLORS['step']}📦 {text}{RESET}")


def log(prefix, msg):
    text = dump_obj(msg)
    print(f"{COLORS['info']}[{prefix}] {text}{RESET}")
