# netstack_core/commands_builtin.py
from __future__ import annotations

from typing import List

from .commands_base import Command, AppContext
from .vless import parse_vless_url


class CreateProfileCommand:
    name = "Create new profile from VLESS URL"
    description = "Parse VLESS URL and generate SOCKS/TUN configs"

    def execute(self, ctx: AppContext) -> None:
        print("\n=== Create new profile from VLESS URL ===")
        url = input("Paste VLESS URL: ").strip()
        if not url:
            print("Empty URL. Cancelled.")
            return
        try:
            vless = parse_vless_url(url)
        except Exception as e:
            print(f"Failed to parse VLESS URL: {e}")
            return

        suggested = ctx.profiles.generate_profile_name(vless.name)
        print(f"Suggested profile name: {suggested}")
        custom = input("Enter profile name (or leave empty to accept): ").strip() or None

        profile = ctx.profiles.create_profile_from_vless(vless, custom_name=custom)
        socks_cfg, tun_cfg = ctx.profiles.get_profile_configs(profile.name)
        print(f"\nProfile '{profile.name}' created.")
        print(f"  SOCKS config: {socks_cfg}")
        print(f"  TUN   config: {tun_cfg}")


class ListProfilesCommand:
    name = "List profiles"
    description = "Show existing profiles"

    def execute(self, ctx: AppContext) -> None:
        profiles = ctx.profiles.list_profiles()
        if not profiles:
            print("\nNo profiles found.")
            return
        print("\nProfiles:")
        for p in profiles:
            print("  -", p)


def _choose_profile(ctx: AppContext) -> str | None:
    profiles = ctx.profiles.list_profiles()
    if not profiles:
        print("No profiles found. Create one first.")
        return None
    print("\nAvailable profiles:")
    for i, p in enumerate(profiles, start=1):
        print(f"  {i}) {p}")
    print("  0) Cancel")
    choice = input("Select profile: ").strip()
    if not choice.isdigit():
        print("Invalid input.")
        return None
    num = int(choice)
    if num == 0:
        return None
    if num < 1 or num > len(profiles):
        print("Number out of range.")
        return None
    return profiles[num - 1]


class RunSocksCommand:
    name = "Run local SOCKS proxy and open proxied shell"
    description = "Starts sing-box in SOCKS mode for selected profile"

    def execute(self, ctx: AppContext) -> None:
        profile_name = _choose_profile(ctx)
        if not profile_name:
            return
        socks_cfg, _ = ctx.profiles.get_profile_configs(profile_name)
        if not socks_cfg.exists():
            print(f"SOCKS config not found for profile '{profile_name}'.")
            return
        ctx.runner.run_socks_shell(
            socks_cfg,
            profile_name,
            ctx.paths.socks_host,
            ctx.paths.socks_port,
        )


class RunVpnCommand:
    name = "Run VPN (TUN mode)"
    description = "Starts sing-box in TUN/VPN mode for selected profile"

    def execute(self, ctx: AppContext) -> None:
        profile_name = _choose_profile(ctx)
        if not profile_name:
            return
        _, tun_cfg = ctx.profiles.get_profile_configs(profile_name)
        if not tun_cfg.exists():
            print(f"TUN config not found for profile '{profile_name}'.")
            return
        ctx.runner.run_vpn_blocking(tun_cfg, profile_name)


class QuitCommand:
    name = "Quit"
    description = "Exit netstack CLI"

    def execute(self, ctx: AppContext) -> None:
        print("Exiting.")
        ctx.running = False


def get_builtin_commands() -> List[Command]:
    return [
        CreateProfileCommand(),
        ListProfilesCommand(),
        RunSocksCommand(),
        RunVpnCommand(),
        QuitCommand(),
    ]
