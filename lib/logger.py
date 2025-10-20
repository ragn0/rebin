import os
import platform
import time
from typing import Any, Dict, List, Optional

from utilities import atomic_write_json, monotonic_s, next_session_filename 


class SessionLogger:
    def __init__(
        self,
        binary_path: Optional[str],
        env: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.t0 = monotonic_s()
        self.log: Dict[str, Any] = {
            "id": time.strftime("%Y%m%d_%H%M%S"),
            "target": binary_path,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "args": [],
            "env": env or {},
            "inputs": [],
            "outputs": [],
            "exit_code": None,
            "error": None,
            "metadata": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            } | (metadata or {}),
        }

    def add_arglist(self, args: List[str]) -> None:
        self.log["args"] = list(args)

    def record_input(self, data: bytes) -> None:
        self.log["inputs"].append({"t": monotonic_s() - self.t0, "data": data.decode(errors="ignore")})

    def record_output(self, data: bytes) -> None:
        self.log["outputs"].append({"t": monotonic_s() - self.t0, "data": data.decode(errors="ignore")})

    def finalize(self, exit_code, error) -> None:
        self.log["exit_code"] = exit_code
        self.log["error"] = error

    def save(self, session_out: Optional[str] = None) -> str:
        curr_dir = os.getcwd()
        if not os.path.exists("sessions"):
            os.makedirs("sessions")
        out_path = session_out or os.path.join(f"{curr_dir}/sessions", next_session_filename("session"))
        atomic_write_json(out_path, self.log)
        return out_path


