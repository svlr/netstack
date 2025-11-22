# netstack_core/profiles.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .vless import VlessParams


@dataclass
class PathsConfig:
    base_dir: Path
    config_dir: Path
    log_dir: Path
    sing_box_bin: Path
    socks_host: str = "127.0.0.1"
    socks_port: int = 1080


@dataclass
class Profile:
    name: str
    vless: VlessParams


class ProfileManager:
    def __init__(self, paths: PathsConfig):
        self.paths = paths
        self.paths.config_dir.mkdir(exist_ok=True)
        self.paths.log_dir.mkdir(exist_ok=True)

    def sanitize_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            name = "profile"
        clean = []
        for ch in name:
            if ch.isalnum() or ch in "-_":
                clean.append(ch)
            else:
                clean.append("_")
        base = "".join(clean) or "profile"
        return base

    def generate_profile_name(self, base: str) -> str:
        base = self.sanitize_name(base)
        name = base
        i = 1
        while True:
            socks_cfg, tun_cfg = self.get_profile_configs(name)
            if not socks_cfg.exists() and not tun_cfg.exists():
                return name
            i += 1
            name = f"{base}-{i}"

    def list_profiles(self) -> List[str]:
        profiles = set()
        for path in self.paths.config_dir.glob("*.json"):
            name = path.name
            if name.endswith("-socks.json"):
                profiles.add(name[:-11])
            elif name.endswith("-tun.json"):
                profiles.add(name[:-9])
        return sorted(profiles)

    def get_profile_configs(self, profile_name: str) -> Tuple[Path, Path]:
        socks_cfg = self.paths.config_dir / f"{profile_name}-socks.json"
        tun_cfg = self.paths.config_dir / f"{profile_name}-tun.json"
        return socks_cfg, tun_cfg


    def build_vless_outbound(self, params: VlessParams) -> dict:
        return {
            "type": "vless",
            "tag": "proxy",
            "server": params.server,
            "server_port": params.server_port,
            "uuid": params.uuid,
            "flow": params.flow,
            "tls": {
                "enabled": True,
                "server_name": params.sni,
                "utls": {
                    "enabled": True,
                    "fingerprint": params.fp,
                },
                "reality": {
                    "enabled": params.security == "reality",
                    "public_key": params.pbk,
                    "short_id": params.sid,
                },
            },
        }

    def build_socks_config(self, params: VlessParams) -> dict:
        outbound = self.build_vless_outbound(params)
        return {
            "log": {"level": "info"},
            "inbounds": [
                {
                    "type": "socks",
                    "tag": "socks-in",
                    "listen": self.paths.socks_host,
                    "listen_port": self.paths.socks_port,
                    "sniff": True,
                }
            ],
            "outbounds": [outbound],
            "route": {"final": "proxy"},
        }

    def build_tun_config(self, params: VlessParams) -> dict:
        outbound = self.build_vless_outbound(params)
        return {
            "log": {"level": "info"},
            "dns": {
                "servers": [
                    {
                        "tag": "dns-remote",
                        "address": "https://1.1.1.1/dns-query",
                        "strategy": "ipv4_only",
                        "detour": "proxy",
                    }
                ],
                "final": "dns-remote",
                "strategy": "ipv4_only",
            },
            "inbounds": [
                {
                    "type": "tun",
                    "tag": "tun-in",
                    "interface_name": "tun0",
                    "address": ["172.19.0.1/30"],
                    "mtu": 9000,
                    "auto_route": True,
                    "auto_redirect": True,
                    "strict_route": True,
                    "route_exclude_address": [
                        "192.168.0.0/16",
                        "10.0.0.0/8",
                        "172.16.0.0/12",
                    ],
                    "stack": "system",
                    "sniff": True,
                }
            ],
            "outbounds": [
                outbound,
                {"type": "direct", "tag": "direct"},
            ],
            "route": {
                "auto_detect_interface": True,
                "final": "proxy",
            },
        }

    def create_profile_from_vless(
        self,
        vless: VlessParams,
        custom_name: str | None = None,
    ) -> Profile:
        suggested = self.generate_profile_name(vless.name)
        if custom_name:
            profile_name = self.generate_profile_name(custom_name)
        else:
            profile_name = suggested

        socks_cfg, tun_cfg = self.get_profile_configs(profile_name)
        socks_config = self.build_socks_config(vless)
        tun_config = self.build_tun_config(vless)

        with socks_cfg.open("w", encoding="utf-8") as f:
            json.dump(socks_config, f, indent=2, ensure_ascii=False)

        with tun_cfg.open("w", encoding="utf-8") as f:
            json.dump(tun_config, f, indent=2, ensure_ascii=False)

        return Profile(name=profile_name, vless=vless)
