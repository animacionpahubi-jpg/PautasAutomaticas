"""Lectura de WooCommerce de pahubi.com, SOLO GET. Para auditorías; nunca modifica la tienda.

Uso (en esta carpeta):
    python woo_lectura.py orders status=cancelled,failed per_page=50 after=2026-10-01T00:00:00
    python woo_lectura.py orders/4053/notes
    python woo_lectura.py payment_gateways
    python woo_lectura.py shipping/zones
    python woo_lectura.py system_status        (puede fallar si las llaves no tienen permiso)

Lee WOO_URL, WOO_KEY y WOO_SECRET de .env. Nunca imprime las llaves.
"""

import json
import sys
from pathlib import Path

import requests

ENV_FILE = Path(__file__).parent / ".env"


SENSIBLE = ("key", "secret", "token", "password", "pass", "llave", "integrity", "signature")


def ocultar(dato):
    """Tapa valores de campos que parezcan llaves (p. ej. las de Wompi en payment_gateways)."""
    if isinstance(dato, dict):
        limpio = {}
        for k, v in dato.items():
            nombre = str(k).lower() + " " + str(dato.get("id", "")).lower()
            if any(s in str(k).lower() for s in SENSIBLE) or (
                    "value" in dato and any(s in nombre for s in SENSIBLE) and k == "value"):
                limpio[k] = "***" if v else v
            else:
                limpio[k] = ocultar(v)
        return limpio
    if isinstance(dato, list):
        return [ocultar(x) for x in dato]
    return dato


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    env = {}
    for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            k, v = linea.split("=", 1)
            env[k.strip()] = v.strip()
    ruta = sys.argv[1].strip("/")
    params = dict(p.split("=", 1) for p in sys.argv[2:] if "=" in p)
    url = env.get("WOO_URL", "https://pahubi.com").rstrip("/") + "/wp-json/wc/v3/" + ruta
    r = requests.get(url, params={"consumer_key": env["WOO_KEY"],
                                  "consumer_secret": env["WOO_SECRET"], **params}, timeout=60)
    print(f"HTTP {r.status_code}  total={r.headers.get('X-WP-Total', '?')}")
    try:
        datos = r.json()
    except ValueError:
        print(r.text[:2000])
        return
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(ocultar(datos), ensure_ascii=False, indent=1)[:60000])


if __name__ == "__main__":
    main()
