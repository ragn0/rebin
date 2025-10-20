import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional


SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "apikey"}


# --- FUNZIONE PER RISOLVERE IL PERCORSO DEL BINARIO ---
def resolve_binary_path(provided_path) -> str:    
    if not os.path.isabs(provided_path):
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cwd_candidate = os.path.abspath(provided_path)
        root_candidate = os.path.join(proj_root, provided_path)
        if os.path.isfile(cwd_candidate):
            binary_real = cwd_candidate
        elif os.path.isfile(root_candidate):
            binary_real = root_candidate
        else:
            binary_real = provided_path
    else:
        binary_real = provided_path
    return binary_real

def monotonic_s() -> float:
    return time.monotonic()

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact_text(text: str, mask: str = "***") -> str:
    patterns = [
        r"(?i)(password|passwd|secret|token|apikey)\s*[:=]\s*\S+",
    ]
    redacted = text
    for pat in patterns:
        redacted = re.sub(pat, lambda m: m.group(0).split("=")[0] + "=" + mask, redacted)
    return redacted


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

# Scrittura atomica del file JSON
def atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

def next_session_filename(prefix: str = "session") -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.json"
