# netstack_core/singbox_runner.py
from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .profiles import PathsConfig


@dataclass
class SingBoxProcessInfo:
    process: subprocess.Popen
    log_file: Path


class SingBoxRunner:
    def __init__(self, paths: PathsConfig):
        self.paths = paths
        self.current_proc: SingBoxProcessInfo | None = None

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def start(self, config_path: Path, log_prefix: str) -> SingBoxProcessInfo:
        self.paths.log_dir.mkdir(exist_ok=True)
        log_file = self.paths.log_dir / f"{log_prefix}-{self._timestamp()}.log"
        log_fh = log_file.open("ab", buffering=0)

        proc = subprocess.Popen(
            [str(self.paths.sing_box_bin), "run", "-c", str(config_path)],
            stdout=log_fh,
            stderr=log_fh,
        )
        info = SingBoxProcessInfo(process=proc, log_file=log_file)
        self.current_proc = info
        return info

    def stop(self):
        if not self.current_proc:
            return
        proc = self.current_proc.process
        print(f"\nStopping sing-box (PID {proc.pid})...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        self.current_proc = None

    # --------- high-level режимы ---------

    def run_socks_shell(
        self,
        config_path: Path,
        profile_name: str,
        socks_host: str,
        socks_port: int,
    ):
        print(f"\nStarting sing-box (SOCKS mode) for profile '{profile_name}'...")
        info = self.start(config_path, f"{profile_name}-socks")
        print(f"sing-box started. Log file: {info.log_file}")
        print(f"Local SOCKS5 proxy: {socks_host}:{socks_port}")

        env = os.environ.copy()
        proxy = f"socks5h://{socks_host}:{socks_port}"
        env["ALL_PROXY"] = proxy
        env["all_proxy"] = proxy
        env["http_proxy"] = proxy
        env["https_proxy"] = proxy

        print("\nExample test inside subshell: curl ifconfig.me")
        print("You are now in a subshell with proxy enabled.")
        print("Exit this subshell (Ctrl+D or 'exit') to stop sing-box and return to menu.\n")

        try:
            subprocess.call(["bash"], env=env)
        except FileNotFoundError:
            print("Error: 'bash' not found. Install bash or change the shell command.")
        finally:
            self.stop()


    def run_vpn_blocking(self, config_path: Path, profile_name: str):
        if os.geteuid() != 0:
            print("Error: TUN/VPN mode requires root. Run this script with sudo.")
            return

        print(f"\nStarting sing-box (TUN/VPN mode) for profile '{profile_name}'...")
        info = self.start(config_path, f"{profile_name}-tun")
        print(f"sing-box started. Log file: {info.log_file}")
        print("TUN interface: tun0")
        print("Your system traffic should now go through this VPN (except local LAN).")
        print("Type 'q' and press Enter to stop VPN and return to the menu.\n")

        try:
            while True:
                cmd = input("[netstack vpn] > ").strip().lower()
                if cmd in ("q", "quit", "exit"):
                    break
        finally:
            print("\nStopping VPN...")
            self.stop()

