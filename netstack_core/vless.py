# netstack_core/vless.py
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs


@dataclass
class VlessParams:
    uuid: str
    server: str
    server_port: int
    security: str
    pbk: str | None
    sni: str
    sid: str | None
    fp: str
    flow: str
    conn_type: str
    spx: str
    name: str


def parse_vless_url(url: str) -> VlessParams:
    """
    vless://UUID@HOST:PORT?type=tcp&security=reality&pbk=...&fp=chrome&sni=...&sid=...&spx=/#name
    """
    parsed = urlparse(url.strip())
    if parsed.scheme != "vless":
        raise ValueError("URL scheme is not vless://")

    if "@" not in parsed.netloc:
        raise ValueError("Invalid VLESS URL: missing user@host")

    user_part, host_part = parsed.netloc.split("@", 1)
    uuid = user_part
    if ":" in host_part:
        host, port_str = host_part.split(":", 1)
        port = int(port_str)
    else:
        host = host_part
        port = 443

    q = parse_qs(parsed.query)

    def get_param(name: str, default=None):
        vals = q.get(name)
        return vals[0] if vals else default

    security = get_param("security", "reality")
    pbk = get_param("pbk")
    sni = get_param("sni") or host
    sid = get_param("sid") or get_param("short_id")
    fp = get_param("fp", "chrome")
    flow = get_param("flow", "")
    conn_type = get_param("type", "tcp")
    spx = get_param("spx", "/")
    name = parsed.fragment or host

    return VlessParams(
        uuid=uuid,
        server=host,
        server_port=port,
        security=security,
        pbk=pbk,
        sni=sni,
        sid=sid,
        fp=fp,
        flow=flow,
        conn_type=conn_type,
        spx=spx,
        name=name,
    )
