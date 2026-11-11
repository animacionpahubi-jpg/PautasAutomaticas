"""Saca la llave (access token) de la API de Marketing de TikTok y la guarda en .env.

Úsalo una sola vez, cuando TikTok apruebe la app:
1. En .env agrega TIKTOK_APP_ID=... y TIKTOK_SECRET=... (están en business-api.tiktok.com →
   My Apps → la app de Pahubi).
2. Abre el "Advertiser authorization URL" de la app, entra con la cuenta de Eva Solarte_adv
   y autoriza. TikTok te manda a la URL de redirección con ?auth_code=... en la barra.
3. Copia ese auth_code (dura unos 10 minutos y sirve una vez) y ejecuta en esta carpeta:
       python tiktok_token.py EL_AUTH_CODE
4. Reinicia el bot (cierra su ventana y abre iniciar.bat).

La llave no se imprime: solo se escribe en .env.
"""

import sys
from pathlib import Path

import requests

ENV_FILE = Path(__file__).parent / ".env"


def main():
    if len(sys.argv) != 2:
        print("Uso: python tiktok_token.py AUTH_CODE")
        raise SystemExit(1)
    lineas = ENV_FILE.read_text(encoding="utf-8").splitlines()
    env = {l.split("=", 1)[0].strip(): l.split("=", 1)[1].strip()
           for l in lineas if "=" in l and not l.lstrip().startswith("#")}
    if not (env.get("TIKTOK_APP_ID") and env.get("TIKTOK_SECRET")):
        print("Falta TIKTOK_APP_ID o TIKTOK_SECRET en .env")
        raise SystemExit(1)
    r = requests.post("https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/",
                      json={"app_id": env["TIKTOK_APP_ID"], "secret": env["TIKTOK_SECRET"],
                            "auth_code": sys.argv[1].strip()}, timeout=60)
    datos = r.json()
    if datos.get("code") != 0:
        print("TikTok rechazó el código:", datos.get("message"))
        raise SystemExit(1)
    token = datos["data"]["access_token"]
    anunciantes = datos["data"].get("advertiser_ids", [])
    lineas = [l for l in lineas if not l.startswith("TIKTOK_ACCESS_TOKEN=")]
    lineas.append(f"TIKTOK_ACCESS_TOKEN={token}")
    ENV_FILE.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("Listo: llave guardada en .env.")
    print("Cuentas de anuncios autorizadas:", ", ".join(map(str, anunciantes)) or "ninguna")
    if "7546330697932013569" not in map(str, anunciantes):
        print("OJO: no aparece Eva Solarte_adv (7546330697932013569). Autoriza esa cuenta.")


if __name__ == "__main__":
    main()
