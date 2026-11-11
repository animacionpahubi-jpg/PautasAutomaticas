"""Conecta la cuenta de Mercado Libre de PAHUBI SAS (app "Pahubi Metricas", solo lectura).

Pasos (una sola vez):
1. En .env agrega ML_APP_ID=... y ML_SECRET=... (developers.mercadolibre.com.co → Pahubi Metricas).
2. Ejecuta en esta carpeta:   python mercadolibre_token.py
   Te imprime un enlace. Ábrelo, entra con la cuenta PAHUBI SAS y autoriza.
   Mercado Libre te manda a https://pahubi.com/?code=TG-...  Copia el valor de code
   (dura unos minutos y sirve una sola vez).
3. Ejecuta:   python mercadolibre_token.py TG-EL_CODIGO
   Guarda las llaves en .env (no las imprime).
4. Prueba:    python mercadolibre_token.py --probar
   Renueva la llave y cuenta los pedidos recientes, sin mostrar datos de clientes.

La llave de acceso dura 6 horas. El bot la renueva sola con refrescar(); cada renovación
entrega un ML_REFRESH_TOKEN nuevo, que también se guarda en .env.
"""

import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

ENV_FILE = Path(__file__).parent / ".env"
REDIRECT = "https://pahubi.com/"
API = "https://api.mercadolibre.com"


def leer_env():
    lineas = ENV_FILE.read_text(encoding="utf-8").splitlines()
    env = {l.split("=", 1)[0].strip(): l.split("=", 1)[1].strip()
           for l in lineas if "=" in l and not l.lstrip().startswith("#")}
    return lineas, env


def guardar_env(valores):
    lineas, _ = leer_env()
    claves = set(valores)
    lineas = [l for l in lineas if l.split("=", 1)[0].strip() not in claves]
    lineas += [f"{k}={v}" for k, v in valores.items()]
    ENV_FILE.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def credenciales():
    _, env = leer_env()
    if not (env.get("ML_APP_ID") and env.get("ML_SECRET")):
        print("Falta ML_APP_ID o ML_SECRET en .env")
        raise SystemExit(1)
    return env


def pedir_token(datos):
    r = requests.post(f"{API}/oauth/token", data=datos,
                      headers={"accept": "application/json"}, timeout=60)
    j = r.json()
    if r.status_code != 200 or "access_token" not in j:
        print("Mercado Libre rechazó la solicitud:", j.get("message") or j.get("error") or r.status_code)
        raise SystemExit(1)
    guardar_env({"ML_ACCESS_TOKEN": j["access_token"],
                 "ML_REFRESH_TOKEN": j.get("refresh_token", ""),
                 "ML_USER_ID": str(j.get("user_id", ""))})
    return j


def refrescar():
    """Renueva la llave con ML_REFRESH_TOKEN y la guarda. Devuelve el access_token nuevo."""
    env = credenciales()
    if not env.get("ML_REFRESH_TOKEN"):
        print("Falta ML_REFRESH_TOKEN: primero autoriza con el código.")
        raise SystemExit(1)
    j = pedir_token({"grant_type": "refresh_token", "client_id": env["ML_APP_ID"],
                     "client_secret": env["ML_SECRET"], "refresh_token": env["ML_REFRESH_TOKEN"]})
    return j["access_token"]


def probar():
    token = refrescar()
    _, env = leer_env()
    h = {"Authorization": f"Bearer {token}"}
    yo = requests.get(f"{API}/users/me", headers=h, timeout=60).json()
    print("Cuenta conectada:", yo.get("nickname"), "| país:", yo.get("site_id"))
    p = requests.get(f"{API}/orders/search", headers=h, timeout=60,
                     params={"seller": env["ML_USER_ID"], "sort": "date_desc", "limit": 1}).json()
    print("Pedidos registrados en la cuenta:", p.get("paging", {}).get("total", "sin dato"))
    i = requests.get(f"{API}/users/{env['ML_USER_ID']}/items/search", headers=h, timeout=60).json()
    print("Publicaciones en la cuenta:", i.get("paging", {}).get("total", "sin dato"))


def main():
    env = credenciales()
    if len(sys.argv) == 1:
        url = "https://auth.mercadolibre.com.co/authorization?" + urlencode(
            {"response_type": "code", "client_id": env["ML_APP_ID"], "redirect_uri": REDIRECT})
        print("Abre este enlace, entra con PAHUBI SAS y autoriza:\n")
        print(url)
        print("\nLuego copia el code=TG-... de la barra y ejecuta: python mercadolibre_token.py TG-...")
    elif sys.argv[1] == "--probar":
        probar()
    else:
        j = pedir_token({"grant_type": "authorization_code", "client_id": env["ML_APP_ID"],
                         "client_secret": env["ML_SECRET"], "code": sys.argv[1].strip(),
                         "redirect_uri": REDIRECT})
        print("Listo: llaves guardadas en .env. Usuario de Mercado Libre:", j.get("user_id"))
        print("Ahora prueba con: python mercadolibre_token.py --probar")


if __name__ == "__main__":
    main()
