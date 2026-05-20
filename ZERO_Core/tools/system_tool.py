"""
SystemTool — System stats and safe command execution for ZERO.
"""

import subprocess
import shlex

import psutil


# Commands ZERO is allowed to execute (prefix allow-list for safety)
_ALLOWED_PREFIXES = (
    "ls", "df", "du", "free", "uname", "uptime", "who", "ps",
    "top", "htop", "cat", "head", "tail", "grep", "find",
    "git", "pip", "python", "nvidia-smi", "lscpu", "lsblk",
    "systemctl status", "journalctl", "ping", "curl", "wget",
    "echo", "date", "pwd", "hostname",
)


class SystemTool:

    # ── Stats ──────────────────────────────────────────────────────────────────

    def get_stats(self) -> str:
        cpu   = psutil.cpu_percent(interval=0.5)
        ram   = psutil.virtual_memory()
        disk  = psutil.disk_usage("/")

        ram_used  = ram.used  / (1024 ** 3)
        ram_total = ram.total / (1024 ** 3)
        disk_used = disk.used / (1024 ** 3)
        disk_tot  = disk.total / (1024 ** 3)

        return (
            f"CPU: {cpu:.1f}%  |  "
            f"RAM: {ram_used:.1f}/{ram_total:.1f} GB ({ram.percent}%)  |  "
            f"Disk: {disk_used:.0f}/{disk_tot:.0f} GB ({disk.percent}%)"
        )

    # ── Safe shell ─────────────────────────────────────────────────────────────

    def run_command(self, cmd: str) -> str:
        cmd = cmd.strip()
        if not cmd:
            return "[System] No command provided."

        # Safety check — only allow white-listed command prefixes
        if not any(cmd.startswith(p) for p in _ALLOWED_PREFIXES):
            return (
                f"[System] Command '{cmd.split()[0]}' is not on the allow-list. "
                "Ask Rahul to add it if needed."
            )

        try:
            result = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout.strip() or result.stderr.strip()
            return output[:2000] if output else "[System] Command produced no output."
        except subprocess.TimeoutExpired:
            return "[System] Command timed out (15 s)."
        except FileNotFoundError:
            return f"[System] '{cmd.split()[0]}' not found in PATH."
        except Exception as e:
            return f"[System Error] {e}"
