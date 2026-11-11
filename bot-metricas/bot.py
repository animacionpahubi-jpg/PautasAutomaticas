"""Bot de Telegram de métricas de pautas Pahubi.

Fuentes:
- Meta Ads vía Windsor.ai (gasto, clics, visitas a la página).
- WooCommerce directo (pedidos reales pagados, por UTM de campaña).
- Claude para recomendaciones.

Configuración en .env (ver .env). Ejecutar: python bot.py
"""

import html
import json
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import anthropic
import requests

BASE = Path(__file__).parent
STATE_FILE = BASE / "estado.json"
TZ_BOGOTA = timezone(timedelta(hours=-5))


def cargar_env():
    env = {}
    for linea in (BASE / ".env").read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = cargar_env()
TG = f"https://api.telegram.org/bot{ENV['TELEGRAM_TOKEN']}"
CUENTA_PAHUBI = ENV.get("META_CUENTA_PAHUBI", "2071312623652434")
AUTORIZADOS = {x.strip() for x in ENV.get("ALLOWED_CHAT_IDS", "").split(",") if x.strip()}
HORA_RESUMEN = int(ENV.get("HORA_RESUMEN_DIARIO", "8"))

CONTEXTO_NEGOCIO = """\
Pahubi (pahubi.com, Colombia) vende pañitos húmedos y papel higiénico húmedo biodegradable (flushable).
Combos en pahubi.com: papel higiénico húmedo $32.200, pañitos $25.109, mixto $28.700, sachets x100 $27.900.
Ticket promedio por pedido: ~$60.000. Bodegas en Bogotá, Medellín, Cali, Barranquilla, Cartagena y Pasto.
Eva (eva_eco_d) es la marca de divulgación ambiental: busca alcance y seguidores, no ventas.
Reglas del negocio:
- Las ventas reales salen de WooCommerce (pedidos pagados por UTM), nunca de las compras que reporta Meta.
- Todo anuncio debe usar una publicación orgánica existente y llevar UTM a pahubi.com.
- WhatsApp: solo +57 300 5060274 (ventas) y +57 304 3900861 (asesoría).
- No hay contraentrega y no se promete envío gratis.
- Cualquier cambio de presupuesto, activación o publicación lo aprueba Ivan (dueño).
- Las campañas reales se llaman "[Estrategia N] ...".
"""


# ---------- Telegram ----------

def tg(metodo, **datos):
    r = requests.post(f"{TG}/{metodo}", json=datos, timeout=60)
    return r.json()


def enviar(chat_id, texto):
    # Telegram limita a 4096 caracteres por mensaje.
    for i in range(0, len(texto), 4000):
        tg("sendMessage", chat_id=chat_id, text=texto[i:i + 4000],
           parse_mode="HTML", disable_web_page_preview=True)


# ---------- Datos ----------

def windsor_datos(conector, campos, desde, hasta, cuenta):
    clave = ENV.get("WINDSOR_API_KEY")
    if not clave:
        raise RuntimeError("Falta WINDSOR_API_KEY en .env")
    r = requests.get(f"https://connectors.windsor.ai/{conector}", timeout=180, params={
        "api_key": clave,
        "date_from": desde.isoformat(),
        "date_to": hasta.isoformat(),
        "fields": ",".join(["account_id"] + campos),
    })
    r.raise_for_status()
    filas = r.json().get("data", [])
    return [f for f in filas if str(f.get("account_id")) == cuenta]


def windsor(campos, desde, hasta):
    return windsor_datos("facebook", campos, desde, hasta, CUENTA_PAHUBI)


def metricas_meta(desde, hasta):
    filas = windsor(["campaign", "campaign_status", "adset_name", "spend", "impressions",
                     "reach", "link_clicks", "actions_landing_page_view"], desde, hasta)
    agregado = {}
    for f in filas:
        clave = (f.get("campaign") or "?", f.get("adset_name") or "?")
        a = agregado.setdefault(clave, {"estado": f.get("campaign_status"), "gasto": 0,
                                        "impresiones": 0, "clics": 0, "visitas": 0})
        a["gasto"] += f.get("spend") or 0
        a["impresiones"] += f.get("impressions") or 0
        a["clics"] += int(f.get("link_clicks") or 0)
        a["visitas"] += int(f.get("actions_landing_page_view") or 0)
    return agregado


ORIGENES_WOO = {"organic": "Búsqueda orgánica", "typein": "Directo (escribió la URL)",
                "referral": "Referido (otro sitio)", "utm": "UTM sin campaña",
                "admin": "Creado en el panel", "sin_atribucion": "Sin atribución"}
FUENTES_META = {"meta", "facebook", "fb", "instagram", "ig"}


def pedidos_woo(desde, hasta):
    """Pedidos pagados (processing/completed/delivered) agrupados por utm_campaign. None si no hay claves."""
    if not (ENV.get("WOO_KEY") and ENV.get("WOO_SECRET")):
        return None
    url = ENV.get("WOO_URL", "https://pahubi.com").rstrip("/") + "/wp-json/wc/v3/orders"
    por_campana, pagina = {}, 1
    while True:
        r = requests.get(url, timeout=60, params={
            "consumer_key": ENV["WOO_KEY"], "consumer_secret": ENV["WOO_SECRET"],
            "status": "processing,completed,delivered", "per_page": 100, "page": pagina,
            "after": f"{desde.isoformat()}T00:00:00", "before": f"{hasta.isoformat()}T23:59:59",
        })
        r.raise_for_status()
        pedidos = r.json()
        for p in pedidos:
            meta = {m.get("key"): m.get("value") for m in p.get("meta_data", [])}
            origen = meta.get("_wc_order_attribution_source_type") or "sin_atribucion"
            campana = (meta.get("_wc_order_attribution_utm_campaign")
                       or ORIGENES_WOO.get(origen, origen))
            fuente = (meta.get("_wc_order_attribution_utm_source") or "").lower()
            c = por_campana.setdefault(campana, {"pedidos": 0, "ventas": 0.0,
                                                 "meta": fuente in FUENTES_META})
            c["pedidos"] += 1
            c["ventas"] += float(p.get("total") or 0)
        if len(pedidos) < 100:
            return por_campana
        pagina += 1


# ---------- Alertas de pedidos ----------

CADA_CUANTO_ALERTAS = 180  # segundos entre revisiones de pedidos
ESTADOS_ALERTA = {
    "processing": "✅ <b>Pedido pagado</b>",
    "failed": "❌ <b>Pago fallido</b>",
    "cancelled": "❌ <b>Pedido cancelado</b>",
}


def woo(ruta, **params):
    url = ENV.get("WOO_URL", "https://pahubi.com").rstrip("/") + "/wp-json/wc/v3/" + ruta
    r = requests.get(url, timeout=60, params={
        "consumer_key": ENV["WOO_KEY"], "consumer_secret": ENV["WOO_SECRET"], **params})
    r.raise_for_status()
    return r.json()


def origen_pedido(meta):
    campana = meta.get("_wc_order_attribution_utm_campaign")
    fuente = meta.get("_wc_order_attribution_utm_source")
    referente = meta.get("_wc_order_attribution_referrer") or ""
    if campana:
        return f"pauta {campana}"
    if fuente:
        return {"ig": "Instagram", "instagram": "Instagram", "meta": "Meta",
                "facebook": "Facebook", "fb": "Facebook"}.get(fuente.lower(), fuente)
    if "instagram" in referente:
        return "Instagram"
    tipo = meta.get("_wc_order_attribution_source_type") or "sin_atribucion"
    return ORIGENES_WOO.get(tipo, tipo)


def motivo_fallo(order_id):
    """Busca en las notas del pedido por qué no se pagó (Wompi o tiempo vencido)."""
    for nota in woo(f"orders/{order_id}/notes"):
        texto = nota.get("note", "")
        if "límite de tiempo" in texto:
            return "no terminó de pagar (se venció)"
        m = re.search(r"Wompi payment DECLINED\. TRANSACTION ID:\s*\(([^)]+)\)", texto)
        if m:
            try:
                d = requests.get(f"https://production.wompi.co/v1/transactions/{m.group(1)}",
                                 timeout=20).json().get("data") or {}
                if d.get("status_message"):
                    return f"Wompi rechazó: {d['status_message']}"
            except (requests.RequestException, ValueError):
                pass
            return "Wompi rechazó el pago"
    return None


def texto_alerta(p):
    meta = {m.get("key"): m.get("value") for m in p.get("meta_data", [])}
    productos = ", ".join(f"{i['name']} ×{i['quantity']}" for i in p.get("line_items", []))
    lineas = [
        f"{ESTADOS_ALERTA[p['status']]} #{p['number']}",
        f"{cop(float(p.get('total') or 0))} · {html.escape(p['billing'].get('city') or '?')}",
        f"Origen: {html.escape(origen_pedido(meta))}",
        html.escape(productos),
    ]
    if p["status"] == "processing":
        programada = meta.get("_recompra_pahubi_programada") == "yes"
        lineas.append("Recompra programada: " + ("sí ✅" if programada else "no ❌ (revisar el fragmento)"))
    else:
        motivo = motivo_fallo(p["id"])
        if motivo:
            lineas.append(f"Motivo: {html.escape(motivo)}")
    return "\n".join(lineas)


def revisar_pedidos(estado):
    if not (ENV.get("WOO_KEY") and ENV.get("WOO_SECRET")):
        return
    ahora = time.time()
    if ahora - estado.get("ultima_revision_pedidos", 0) < CADA_CUANTO_ALERTAS:
        return
    primera_vez = "pedidos_vistos" not in estado
    vistos = estado.setdefault("pedidos_vistos", {})
    desde = datetime.now(timezone.utc) - timedelta(days=2)
    pedidos = woo("orders", status="any", per_page=50, orderby="modified",
                  modified_after=desde.strftime("%Y-%m-%dT%H:%M:%S"), dates_are_gmt="true")
    for p in pedidos:
        clave = str(p["id"])
        if vistos.get(clave) == p["status"]:
            continue
        vistos[clave] = p["status"]
        # La primera vez solo se registra lo que ya existía, sin avisar.
        if not primera_vez and p["status"] in ESTADOS_ALERTA:
            texto = texto_alerta(p)
            for chat_id in AUTORIZADOS:
                enviar(chat_id, texto)
    # Olvidar pedidos viejos para que el archivo no crezca sin límite.
    ids_recientes = {str(p["id"]) for p in pedidos}
    estado["pedidos_vistos"] = {k: v for k, v in vistos.items() if k in ids_recientes}
    estado["ultima_revision_pedidos"] = ahora
    guardar_estado(estado)


# ---------- Formato ----------

ESTADOS = {"ACTIVE": "Activa", "PAUSED": "Pausada", "ARCHIVED": "Archivada", "DELETED": "Eliminada"}


def cop(valor):
    return "$" + f"{valor:,.0f}".replace(",", ".")


def reporte(desde, hasta, titulo):
    meta = metricas_meta(desde, hasta)
    lineas = [f"<b>{html.escape(titulo)}</b>", f"{desde:%d/%m} – {hasta:%d/%m}", ""]
    total = 0
    if not meta:
        lineas.append("Sin gasto en Meta en este periodo.")
    for (campana, conjunto), m in sorted(meta.items(), key=lambda x: -x[1]["gasto"]):
        total += m["gasto"]
        cpv = cop(m["gasto"] / m["visitas"]) if m["visitas"] else "—"
        carga = f"{m['visitas'] / m['clics']:.0%}" if m["clics"] else "—"
        lineas += [
            f"<b>{html.escape(campana)}</b> ({ESTADOS.get(m['estado'], m['estado'] or '?')})",
            f"  {html.escape(conjunto)}",
            f"  Gasto {cop(m['gasto'])} · Clics {m['clics']} · Visitas {m['visitas']} ({carga} cargan)",
            f"  Costo por visita: {cpv}",
            "",
        ]
    lineas.append(f"<b>Gasto total Meta: {cop(total)}</b>")

    lineas.append("")
    try:
        woo = pedidos_woo(desde, hasta)
    except requests.RequestException as e:
        woo = None
        lineas.append(f"⚠️ WooCommerce no respondió: {html.escape(str(e)[:150])}")
    if woo is None:
        lineas.append("Ventas reales: falta configurar WOO_KEY / WOO_SECRET en .env")
    else:
        n = sum(c["pedidos"] for c in woo.values())
        v = sum(c["ventas"] for c in woo.values())
        lineas.append(f"<b>Ventas reales WooCommerce: {n} pedidos · {cop(v)}</b>")
        for campana, c in sorted(woo.items(), key=lambda x: -x[1]["ventas"]):
            lineas.append(f"  {html.escape(campana)}: {c['pedidos']} · {cop(c['ventas'])}")
        v_meta = sum(c["ventas"] for c in woo.values() if c["meta"])
        lineas.append(f"Ventas que llegaron desde Meta (UTM): {cop(v_meta)}")
        if total:
            lineas.append(f"Retorno de la pauta (ventas Meta / gasto Meta): {v_meta / total:.1f}x")
    return "\n".join(lineas)


# ---------- Recomendaciones (Claude) ----------

SISTEMA = (
    "Eres el analista de pautas de Pahubi. Respondes en español, para leer en Telegram: "
    "texto plano, sin tablas ni markdown, máximo unas 25 líneas.\n\n" + CONTEXTO_NEGOCIO
)


def recomendaciones():
    hoy = datetime.now(TZ_BOGOTA).date()
    desde = hoy - timedelta(days=14)
    datos = {
        "reporte_14_dias": reporte(desde, hoy, "Últimos 14 días"),
        "por_edad_genero": windsor(["campaign", "age", "gender", "spend", "link_clicks",
                                     "actions_landing_page_view"], desde, hoy),
        "por_region": windsor(["campaign", "region", "spend", "link_clicks",
                                "actions_landing_page_view"], desde, hoy),
    }
    pregunta = (
        "Con estos datos, dame de 3 a 5 recomendaciones concretas para ampliar el público "
        "y vender más, ordenadas por impacto esperado. Para cada una: qué hacer, por qué "
        "(citando el dato), presupuesto de prueba sugerido y cómo medir el éxito con "
        "pedidos de WooCommerce. Señala si hay datos insuficientes. Recuerda que todo "
        "cambio lo aprueba Ivan.\n\n" + json.dumps(datos, ensure_ascii=False, default=str)
    )
    if ENV.get("ANTHROPIC_API_KEY"):
        texto = preguntar_api(pregunta)
    else:
        texto = preguntar_claude_code(pregunta)
    return "<b>Recomendaciones (últimos 14 días)</b>\n\n" + html.escape(texto, quote=False)


def preguntar(pregunta, sistema=None):
    if ENV.get("ANTHROPIC_API_KEY"):
        return preguntar_api(pregunta, sistema)
    return preguntar_claude_code(pregunta, sistema)


def preguntar_claude_code(pregunta, sistema=None):
    """Usa Claude Code instalado en este PC (la suscripción de claude.ai), sin API de pago."""
    ejecutable = shutil.which("claude")
    if not ejecutable:
        return "No encontré Claude Code en este PC y no hay ANTHROPIC_API_KEY en .env."
    r = subprocess.run(
        [ejecutable, "-p", "--model", ENV.get("CLAUDE_CODE_MODELO", "sonnet"),
         "--append-system-prompt", sistema or SISTEMA],
        input=pregunta, capture_output=True, text=True, encoding="utf-8",
        timeout=600, cwd=BASE,
    )
    if r.returncode != 0:
        return "Claude Code falló: " + (r.stderr or r.stdout)[:300]
    return r.stdout.strip()


def preguntar_api(pregunta, sistema=None):
    client = anthropic.Anthropic(api_key=ENV["ANTHROPIC_API_KEY"])
    respuesta = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=16000,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=sistema or SISTEMA,
        messages=[{"role": "user", "content": pregunta}],
    )
    if respuesta.stop_reason == "refusal":
        return "Claude no pudo generar recomendaciones con estos datos."
    return "".join(b.text for b in respuesta.content if b.type == "text")


# ---------- Eva: promociones con aprobación ----------
# El bot propone promocionar publicaciones de Eva que ya despegaron solas y, solo si
# alguien autorizado toca "Aprobar", las promociona en Meta a través de Windsor.

EVA_CUENTA_ADS = ENV.get("META_CUENTA_EVA", "1805850660019527")  # "Eva Daferu"; nunca la 1435739040823706
EVA_PAGINA = "760382010492488"         # página de Facebook "Eva eco d"
EVA_IG = "39880468148266282"           # eva_eco_d tal como la nombra la API de Windsor
EVA_TIKTOK = "_000Cp4jcBvrzsupxtZJiFprH86LrezouZEl"
EVA_TIKTOK_ADS = "7546330697932013569"  # "Eva Solarte_adv"
EVA_PRESUPUESTO_DIA = int(ENV.get("EVA_PRESUPUESTO_DIARIO", "30000"))
EVA_DIAS_PROMO = int(ENV.get("EVA_DIAS_PROMO", "5"))
EVA_FACTOR = float(ENV.get("EVA_FACTOR", "2"))  # proponer si el alcance es N veces la mediana (90 días)
HORA_EVA = 10         # revisión diaria de Eva (hora de Bogotá)
EVA_OPCIONES_PRESUPUESTO = [15000, 30000, 50000]
EVA_OPCIONES_DIAS = [3, 5, 7]
EVA_PUBLICOS = {
    "co": ("Colombia, 25–60", {"geo_locations": {"countries": ["CO"]},
                               "age_min": 25, "age_max": 60}),
    "jov": ("Colombia, 18–44", {"geo_locations": {"countries": ["CO"]},
                                "age_min": 18, "age_max": 44}),
    "lat": ("Colombia + México, Argentina, Chile, Perú y Ecuador, 25–60",
            {"geo_locations": {"countries": ["CO", "MX", "AR", "CL", "PE", "EC"]},
             "age_min": 25, "age_max": 60}),
}


def windsor_mcp(herramienta, argumentos):
    """Llama una herramienta del servidor MCP de Windsor (necesario para ejecutar acciones)."""
    cabeceras = {"Authorization": f"Bearer {ENV['WINDSOR_API_KEY']}",
                 "Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"}

    def post(cuerpo):
        r = requests.post("https://mcp.windsor.ai/", headers=cabeceras, json=cuerpo, timeout=180)
        r.raise_for_status()
        return r

    r = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "bot-pahubi", "version": "1"}}})
    if r.headers.get("mcp-session-id"):
        cabeceras["Mcp-Session-Id"] = r.headers["mcp-session-id"]
    post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    r = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
              "params": {"name": herramienta, "arguments": argumentos}})
    datos = None
    for linea in r.text.splitlines():  # respuesta en formato de eventos (SSE)
        if linea.startswith("data:"):
            datos = json.loads(linea[5:])
    if datos is None:
        datos = r.json()
    if "error" in datos:
        raise RuntimeError(datos["error"].get("message", str(datos["error"]))[:500])
    resultado = datos["result"]
    texto = "".join(c.get("text", "") for c in resultado.get("content", []))
    # Windsor a veces devuelve el error como texto normal, sin marcarlo como error.
    if resultado.get("isError") or texto.startswith("Error calling tool"):
        raise RuntimeError(texto[:500])
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def token_confirmacion(resultado):
    """Windsor no ejecuta en la primera llamada lo que gasta plata (crear activo, encender, subir
    presupuesto): devuelve una vista previa con confirmation_token. Lo busca venga como venga."""
    if isinstance(resultado, dict):
        if resultado.get("confirmation_token"):
            return str(resultado["confirmation_token"])
        for v in resultado.values():
            t = token_confirmacion(v)
            if t:
                return t
    elif isinstance(resultado, list):
        for v in resultado:
            t = token_confirmacion(v)
            if t:
                return t
    elif isinstance(resultado, str):
        m = re.search(r'confirmation_token"?\s*[:=]\s*"?([A-Za-z0-9._\-]{8,})', resultado)
        if m:
            return m.group(1)
    return None


def ejecutar_meta(cuenta_ads, accion, params):
    """Ejecuta una acción de Meta por Windsor. Solo se llama después de que una persona aprobó
    en Telegram (botón ✅ o ⏸), así que si Windsor pide confirmación, se confirma esa misma acción."""
    if cuenta_ads in CUENTAS_PROHIBIDAS:
        raise RuntimeError(f"Cuenta {cuenta_ads} prohibida; revisa .env")
    args = {"connector": "facebook", "account": cuenta_ads, "action": accion, "params": params}
    resultado = windsor_mcp("execute_action", args)
    token = token_confirmacion(resultado)
    if token:
        resultado = windsor_mcp("execute_action", {**args, "confirmation_token": token})
    return resultado


def accion_eva(accion, params):
    return ejecutar_meta(EVA_CUENTA_ADS, accion, params)


def buscar_id(resultado, *claves):
    """Encuentra el id creado dentro de la respuesta de Windsor, venga como venga anidado."""
    if isinstance(resultado, dict):
        for c in claves:
            if resultado.get(c):
                return str(resultado[c])
        for v in resultado.values():
            encontrado = buscar_id(v, *claves)
            if encontrado:
                return encontrado
    elif isinstance(resultado, list):
        for v in resultado:
            encontrado = buscar_id(v, *claves)
            if encontrado:
                return encontrado
    elif isinstance(resultado, str):
        m = re.search(r'"?(?:%s)"?\s*[:=]\s*"?(\d{6,})' % "|".join(claves), resultado)
        if m:
            return m.group(1)
        # Windsor también responde en texto: "Campaign created successfully with id 1202…"
        m = re.search(r"\bid\s+(\d{6,})", resultado, re.I)
        if m:
            return m.group(1)
    return None


def huella(texto):
    """Primeras letras del texto sin símbolos, para emparejar el post de IG con el de Facebook."""
    return "".join(c for c in (texto or "").lower() if c.isalnum())[:40]


def a_fecha(texto):
    return datetime.strptime(texto, "%Y-%m-%dT%H:%M:%S%z")


def candidatos_eva(dias=7, factor=EVA_FACTOR):
    """Publicaciones recientes de Eva con alcance >= factor × mediana, listas para promocionar."""
    hoy = datetime.now(TZ_BOGOTA).date()
    posts = {}
    for f in windsor_datos("instagram", ["media_id", "timestamp", "media_caption", "media_reach",
                                         "media_permalink"], hoy - timedelta(days=90), hoy, EVA_IG):
        if f.get("media_id") and f.get("timestamp"):
            f["media_caption"] = " ".join((f.get("media_caption") or "").split())
            posts[f["media_id"]] = f
    ahora = datetime.now(timezone.utc)
    viejos = sorted(p.get("media_reach") or 0 for p in posts.values()
                    if ahora - a_fecha(p["timestamp"]) > timedelta(days=2))
    mediana = viejos[len(viejos) // 2] if viejos else 0
    facebook = {huella(f.get("post_message")): f["post_id"] for f in windsor_datos(
        "facebook_organic", ["post_id", "post_message"], hoy - timedelta(days=dias + 3), hoy, EVA_PAGINA)}
    lista = []
    for p in posts.values():
        alcance = p.get("media_reach") or 0
        if ahora - a_fecha(p["timestamp"]) > timedelta(days=dias) or alcance < factor * mediana:
            continue
        lista.append({"media_id": p["media_id"], "texto": p.get("media_caption") or "",
                      "alcance": int(alcance), "veces": alcance / mediana if mediana else 0,
                      "enlace": p.get("media_permalink") or "",
                      "post_fb": facebook.get(huella(p.get("media_caption")))})
    return sorted(lista, key=lambda c: -c["alcance"]), int(mediana)


def promo_activa(estado):
    ahora = time.time()
    for promo in estado.get("eva_promos", []):
        if promo.get("fin", 0) > ahora and not promo.get("pausada"):
            return promo
    return None


def costos_historicos_eva():
    """Costo por persona alcanzada y por vista de la pauta de Eva en los últimos 90 días."""
    hoy = datetime.now(TZ_BOGOTA).date()
    m = metricas_eva(hoy - timedelta(days=90), hoy).values()
    gasto = sum(x["gasto"] for x in m)
    alcance = sum(x["alcance"] for x in m)
    vistas = sum(x["vistas"] for x in m)
    if not (gasto and alcance and vistas):
        return None
    return {"por_persona": gasto / alcance, "por_vista": gasto / vistas}


def texto_propuesta(p):
    total = p["presupuesto"] * p["dias"]
    lineas = [
        "🚀 <b>Eva: propuesta de promoción (Instagram + Facebook)</b>",
        f"«{html.escape(p['texto'][:140])}…»",
        f"Alcance orgánico: {p['alcance']:,} personas "
        f"({p['veces']:.1f} veces la mediana de {p['mediana']:,})".replace(",", "."),
    ]
    if p.get("enlace"):
        lineas.append(f'<a href="{html.escape(p["enlace"])}">Ver publicación</a>')
    lineas += [
        "",
        f"<b>Presupuesto:</b> {cop(p['presupuesto'])}/día × {p['dias']} días = <b>{cop(total)}</b>",
        f"<b>Público:</b> {EVA_PUBLICOS[p['publico']][0]}",
    ]
    costos = p.get("costos")
    if costos:
        personas = total / costos["por_persona"]
        vistas = total / costos["por_vista"]
        lineas.append(
            f"<b>Estimado:</b> {personas * 0.7:,.0f}–{personas * 1.3:,.0f} personas alcanzadas · "
            f"{vistas * 0.7:,.0f}–{vistas * 1.3:,.0f} vistas".replace(",", "."))
        lineas.append(f"(según lo que costó la pauta de Eva en 90 días: {cop(costos['por_persona'])}"
                      f" por persona, {cop(costos['por_vista'])} por vista)")
        if p["publico"] == "lat":
            lineas.append("Otros países: sin historial, el estimado es solo de referencia.")
        if p["veces"] < 1:
            lineas.append("⚠️ Este post va por debajo de lo normal de Eva; promocionarlo "
                          "probablemente cueste más que el estimado. Mejor esperar uno que despegue.")
    else:
        lineas.append("Estimado: MISSING, Eva no tiene pauta en los últimos 90 días.")
    lineas.append("\nAjusta con los botones y luego aprueba.")
    return "\n".join(lineas)


def teclado_propuesta(post_fb, p):
    def marca(texto, elegido):
        return f"• {texto} •" if elegido else texto
    return {"inline_keyboard": [
        [{"text": marca(cop(v), v == p["presupuesto"]), "callback_data": f"eva_p:{post_fb}:{v}"}
         for v in EVA_OPCIONES_PRESUPUESTO],
        [{"text": marca(f"{d} días", d == p["dias"]), "callback_data": f"eva_d:{post_fb}:{d}"}
         for d in EVA_OPCIONES_DIAS],
        [{"text": marca({"co": "CO 25–60", "jov": "CO 18–44", "lat": "+LatAm"}[k],
                        k == p["publico"]), "callback_data": f"eva_a:{post_fb}:{k}"}
         for k in EVA_PUBLICOS],
        [{"text": "✅ Aprobar", "callback_data": f"eva_ok:{post_fb}"},
         {"text": "❌ Rechazar", "callback_data": f"eva_no:{post_fb}"}],
    ]}


def proponer_eva(estado, candidato, mediana, chat_ids):
    estado.setdefault("eva_vistos", []).append(candidato["media_id"])
    if not candidato["post_fb"]:
        guardar_estado(estado)
        for chat_id in chat_ids:
            enviar(chat_id, f"🚀 Eva: «{html.escape(candidato['texto'][:80])}…» va muy bien "
                            f"({candidato['alcance']} personas), pero no la encontré en la página "
                            "de Facebook de Eva y sin eso no se puede promocionar. "
                            "Compártela también en Facebook.")
        return
    p = {"media_id": candidato["media_id"], "texto": candidato["texto"][:200],
         "alcance": candidato["alcance"], "veces": candidato["veces"], "mediana": mediana,
         "enlace": candidato["enlace"], "presupuesto": EVA_PRESUPUESTO_DIA,
         "dias": EVA_DIAS_PROMO, "publico": "co", "costos": costos_historicos_eva()}
    estado.setdefault("eva_propuestas", {})[candidato["post_fb"]] = p
    guardar_estado(estado)
    for chat_id in chat_ids:
        tg("sendMessage", chat_id=chat_id, text=texto_propuesta(p), parse_mode="HTML",
           disable_web_page_preview=True,
           reply_markup=teclado_propuesta(candidato["post_fb"], p))


def mejor_tiktok_eva(dias=14):
    """El video de TikTok de Eva con más vistas en los últimos días, comparado con su mediana."""
    hoy = datetime.now(TZ_BOGOTA).date()
    videos = {}
    for f in windsor_datos("tiktok_organic", ["video_id", "date", "video_caption",
                                              "video_views_count", "video_share_url"],
                           hoy - timedelta(days=90), hoy, EVA_TIKTOK):
        if f.get("video_id"):
            videos[f["video_id"]] = f
    if not videos:
        return None
    vistas = sorted(v.get("video_views_count") or 0 for v in videos.values())
    mediana = vistas[len(vistas) // 2]
    recientes = [v for v in videos.values()
                 if v.get("date") and date.fromisoformat(v["date"]) >= hoy - timedelta(days=dias)]
    if not recientes:
        return None
    mejor = max(recientes, key=lambda v: v.get("video_views_count") or 0)
    return {"texto": " ".join((mejor.get("video_caption") or "").split()),
            "vistas": int(mejor.get("video_views_count") or 0), "mediana": int(mediana),
            "enlace": mejor.get("video_share_url") or "", "video_id": str(mejor["video_id"])}


def texto_tiktok(v):
    lineas = ["🎵 <b>Eva en TikTok: mejor video reciente</b>",
              f"«{html.escape(v['texto'][:120])}…»",
              f"{v['vistas']:,} vistas (mediana {v['mediana']:,})".replace(",", ".")]
    if v["enlace"]:
        lineas.append(f'<a href="{html.escape(v["enlace"])}">Ver video</a>')
    lineas += [
        "",
        "TikTok no deja que el bot cree promociones; hazlo tú en unos minutos:",
        "1. En la app de TikTok de Eva: abre el video → ••• → <b>Configuración de anuncios</b> → "
        "activa la autorización y copia el código.",
        "2. ads.tiktok.com → cuenta <b>Eva Solarte_adv</b> → Crear → objetivo "
        "<b>Reproducciones de video</b>.",
        "3. En el anuncio elige <b>Publicación de TikTok (Spark Ads)</b> y pega el código.",
        "4. Presupuesto y días a tu gusto; público Colombia 25–60.",
        "Así queda en Ads Manager y el bot la vigila y te deja pausarla. "
        "(Si usas «Promocionar» desde la app, el bot no la ve.)",
    ]
    return "\n".join(lineas)


def aprobar_eva(estado, post_fb, quien):
    activa = promo_activa(estado)
    if activa:
        return (f"Ya hay una promoción activa («{html.escape(activa['texto'][:50])}») hasta el "
                f"{datetime.fromtimestamp(activa['fin'], TZ_BOGOTA):%d/%m}. Una a la vez.")
    propuesta = estado.get("eva_propuestas", {}).get(post_fb)
    if not propuesta:
        return "Esa propuesta ya no está vigente."
    campana = estado.get("eva_campana")
    if not campana:
        campana = buscar_id(accion_eva("create_campaign", {
            "name": "EVA_Bot_Promociones", "objective": "OUTCOME_ENGAGEMENT",
            "special_ad_categories": [], "is_adset_budget_sharing_enabled": False,
            "status": "active"}), "campaign_id", "id")
        if not campana:
            return "Windsor no devolvió el id de la campaña; revisa Ads Manager."
        estado["eva_campana"] = campana
        guardar_estado(estado)
    inicio = datetime.now(TZ_BOGOTA)
    fin = inicio + timedelta(days=propuesta["dias"])
    nombre = f"Eva bot · {propuesta['texto'][:30]} · {inicio:%d-%m}"
    conjunto = buscar_id(accion_eva("create_adset", {
        "campaign_id": campana, "name": nombre, "optimization_goal": "POST_ENGAGEMENT",
        "billing_event": "IMPRESSIONS", "destination_type": "ON_POST",
        "daily_budget": propuesta["presupuesto"], "end_time": fin.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "promoted_object": {"page_id": EVA_PAGINA},
        "targeting": EVA_PUBLICOS[propuesta["publico"]][1], "status": "active"}),
        "adset_id", "id")
    if not conjunto:
        return "Windsor no devolvió el id del conjunto de anuncios; revisa Ads Manager."
    try:
        anuncio = buscar_id(accion_eva("boost_post", {
            "adset_id": conjunto, "post_id": post_fb, "name": nombre, "status": "active"}),
            "ad_id", "id")
    except Exception:
        accion_eva("pause_adset", {"adset_id": conjunto})  # no dejar nada gastando a medias
        raise
    estado.setdefault("eva_promos", []).append({
        "adset_id": conjunto, "ad_id": anuncio, "post_fb": post_fb, "texto": propuesta["texto"],
        "inicio": inicio.timestamp(), "fin": fin.timestamp(), "aprobo": quien})
    estado["eva_propuestas"].pop(post_fb, None)
    guardar_estado(estado)
    return (f"✅ Promoción creada y activa: {cop(propuesta['presupuesto'])}/día hasta el "
            f"{fin:%d/%m} · {EVA_PUBLICOS[propuesta['publico']][0]}.\n"
            f"Te mando el resultado cada mañana con la opción de pausarla.")


def pausar_eva(estado, conjunto):
    accion_eva("pause_adset", {"adset_id": conjunto})
    for promo in estado.get("eva_promos", []):
        if promo["adset_id"] == conjunto:
            promo["pausada"] = True
    guardar_estado(estado)
    return "⏸ Promoción pausada."


def metricas_eva(desde, hasta):
    filas = windsor_datos("facebook", ["campaign", "adset_id", "adset_name", "spend", "reach",
                                       "actions_video_view", "actions_post_engagement"],
                          desde, hasta, EVA_CUENTA_ADS)
    agregado = {}
    for f in filas:
        a = agregado.setdefault(f.get("adset_id") or "?", {
            "nombre": f.get("adset_name") or f.get("campaign") or "?",
            "gasto": 0, "alcance": 0, "vistas": 0, "interacciones": 0})
        a["gasto"] += f.get("spend") or 0
        a["alcance"] += int(f.get("reach") or 0)
        a["vistas"] += int(f.get("actions_video_view") or 0)
        a["interacciones"] += int(f.get("actions_post_engagement") or 0)
    return agregado


def seguidores_eva():
    hoy = datetime.now(TZ_BOGOTA).date()
    ig = windsor_datos("instagram", ["followers_count"], hoy - timedelta(days=1), hoy, EVA_IG)
    tt = windsor_datos("tiktok_organic", ["total_followers_count"], hoy - timedelta(days=1), hoy,
                       EVA_TIKTOK)
    return {"ig": int(ig[0]["followers_count"]) if ig else None,
            "tiktok": int(tt[0]["total_followers_count"]) if tt else None}


def reporte_eva(desde, hasta, titulo, estado):
    lineas = [f"<b>{html.escape(titulo)}</b>", f"{desde:%d/%m} – {hasta:%d/%m}", ""]
    total = 0
    for conjunto, m in sorted(metricas_eva(desde, hasta).items(), key=lambda x: -x[1]["gasto"]):
        total += m["gasto"]
        cpv = cop(m["gasto"] / m["vistas"]) if m["vistas"] else "—"
        lineas += [f"<b>{html.escape(m['nombre'][:60])}</b>",
                   f"  Gasto {cop(m['gasto'])} · Alcance {m['alcance']} · Vistas {m['vistas']}",
                   f"  Costo por vista: {cpv} · Interacciones {m['interacciones']}", ""]
    lineas.append(f"<b>Gasto Eva: {cop(total)}</b>" if total else "Sin pauta en este periodo.")
    seg = seguidores_eva()
    historial = estado.get("eva_seguidores", {})
    antes = historial.get(desde.isoformat()) or {}
    for red, nombre in (("ig", "Instagram"), ("tiktok", "TikTok")):
        if seg[red] is not None:
            cambio = f" ({seg[red] - antes[red]:+d} desde el {desde:%d/%m})" if antes.get(red) else ""
            lineas.append(f"Seguidores {nombre}: {seg[red]:,}{cambio}".replace(",", "."))
    candidatos, mediana = candidatos_eva(dias=(hasta - desde).days + 1, factor=0)
    if candidatos:
        lineas += ["", f"<b>Mejores publicaciones de IG</b> (mediana {mediana})"]
        for c in candidatos[:3]:
            lineas.append(f"  {c['alcance']} · {html.escape(c['texto'][:60])}")
    activa = promo_activa(estado)
    if activa:
        lineas += ["", f"Promoción activa hasta el "
                       f"{datetime.fromtimestamp(activa['fin'], TZ_BOGOTA):%d/%m}: "
                       f"«{html.escape(activa['texto'][:50])}»"]
    return "\n".join(lineas)


def revisar_eva(estado):
    """Una vez al día: guarda seguidores, reporta la promoción activa y propone nuevas."""
    ahora = datetime.now(TZ_BOGOTA)
    if ahora.hour < HORA_EVA or estado.get("ultima_revision_eva") == ahora.date().isoformat():
        return
    estado["ultima_revision_eva"] = ahora.date().isoformat()
    guardar_estado(estado)
    estado.setdefault("eva_seguidores", {})[ahora.date().isoformat()] = seguidores_eva()
    activa = promo_activa(estado)
    if activa:
        ayer = ahora.date() - timedelta(days=1)
        m = metricas_eva(ayer, ayer).get(activa["adset_id"])
        if m:
            cpv = cop(m["gasto"] / m["vistas"]) if m["vistas"] else "—"
            texto = (f"📊 <b>Eva, promoción de ayer</b>\n«{html.escape(activa['texto'][:60])}»\n"
                     f"Gasto {cop(m['gasto'])} · Alcance {m['alcance']} · Vistas {m['vistas']}\n"
                     f"Costo por vista: {cpv} (referencia: oso hormiguero $7,5)")
            botones = [[{"text": "⏸ Pausar", "callback_data": f"eva_pausa:{activa['adset_id']}"}]]
            for chat_id in AUTORIZADOS:
                tg("sendMessage", chat_id=chat_id, text=texto, parse_mode="HTML",
                   reply_markup={"inline_keyboard": botones})
    elif not promo_ig_activa(estado, "eva"):
        # Ahora las propuestas automáticas de Eva son en Instagram (post o Reel existente).
        candidatos, _ = candidatos_ig("eva")
        vistos = set(estado.get("eva_vistos", [])) | set(estado.get("ig_vistos", []))
        nuevos = [c for c in candidatos if c["media_id"] not in vistos]
        if nuevos:
            proponer_ig(estado, "eva", nuevos[0], AUTORIZADOS)
    revisar_promos_ig(estado)
    # TikTok: si un video despegó solo, se propone como Spark Ad (requiere TIKTOK_ACCESS_TOKEN).
    if TT_TOKEN and not promo_tt_activa(estado):
        video = mejor_tiktok_eva(dias=7)
        if (video and video["vistas"] >= EVA_FACTOR * video["mediana"]
                and video["video_id"] not in estado.get("tt_vistos", [])):
            proponer_tt(estado, video, AUTORIZADOS)
    # Promociones de TikTok (del bot o creadas a mano): el bot las vigila y deja pausarlas.
    ayer = ahora.date() - timedelta(days=1)
    for c in windsor_datos("tiktok", ["campaign_id", "campaign_name", "spend", "reach",
                                      "impressions"], ayer, ayer, EVA_TIKTOK_ADS):
        if not c.get("spend"):
            continue
        texto = (f"🎵 <b>Eva en TikTok, promoción de ayer</b>\n{html.escape(c.get('campaign_name') or '?')}\n"
                 f"Gasto {cop(c['spend'])} · Alcance {int(c.get('reach') or 0)} · "
                 f"Impresiones {int(c.get('impressions') or 0)}")
        botones = [[{"text": "⏸ Pausar", "callback_data": f"eva_ttpausa:{c['campaign_id']}"}]]
        for chat_id in AUTORIZADOS:
            tg("sendMessage", chat_id=chat_id, text=texto, parse_mode="HTML",
               reply_markup={"inline_keyboard": botones})
    guardar_estado(estado)


# ---------- Instagram: promociones con aprobación (Eva y Pahubi) ----------
# Promociona un post o Reel que YA existe en Instagram, solo en Instagram, con presupuesto
# total y fecha de fin. Nada se crea sin que alguien autorizado toque "Aprobar". Todo se crea
# pausado y se activa al final, para que nada quede gastando a medias si algo falla.

CUENTAS_PROHIBIDAS = {"1189939789598673", "1435739040823706"}
IG_OBJETIVOS = {
    "alcance": {"etiqueta": "Alcance", "objective": "OUTCOME_AWARENESS",
                "optimization_goal": "REACH", "destination_type": None},
    "interaccion": {"etiqueta": "Interacción", "objective": "OUTCOME_ENGAGEMENT",
                    "optimization_goal": "POST_ENGAGEMENT", "destination_type": "ON_POST"},
    "trafico": {"etiqueta": "Visitas a pahubi.com", "objective": "OUTCOME_TRAFFIC",
                "optimization_goal": "LANDING_PAGE_VIEWS", "destination_type": "WEBSITE"},
    # Ventas: Meta busca compradores con el píxel; la venta real se mide igual en WooCommerce.
    "ventas": {"etiqueta": "Ventas", "objective": "OUTCOME_SALES",
               "optimization_goal": "OFFSITE_CONVERSIONS", "destination_type": "WEBSITE"},
    # Seguidores: Tráfico → visitas al perfil de Instagram (lo que trajo seguidores en oct).
    # Primera vez por API: si Meta rechaza el formato, el conjunto queda pausado y avisa.
    "seguidores": {"etiqueta": "Seguidores (visitas al perfil)", "objective": "OUTCOME_TRAFFIC",
                   "optimization_goal": "VISIT_INSTAGRAM_PROFILE",
                   "destination_type": "INSTAGRAM_PROFILE"},
}
OBJETIVOS_WEB = {"trafico", "ventas"}
PIXEL_PAHUBI = ENV.get("META_PIXEL_PAHUBI", "1985025489050897")
# Fichas de producto a las que puede mandar una pauta de Pahubi (nunca /tienda/ ni el inicio).
PRODUCTOS = {
    "papel": ("Combo papel higiénico", "https://pahubi.com/producto/combo-papel-higienico-humedo-biodegradable/"),
    "panitos": ("Combo pañitos", "https://pahubi.com/producto/combo-panitos-humedos-biodegradables/"),
    "mixto": ("Combo mixto", "https://pahubi.com/producto/combo-mixto-panitos-y-papel-higienico-humedos-biodegradables/"),
}


def cerca_de(*ciudades, km=40):
    return {"custom_locations": [{"latitude": la, "longitude": lo, "radius": km,
                                  "distance_unit": "kilometer"} for la, lo in ciudades]}


BOGOTA, MEDELLIN, CALI = (4.7110, -74.0721), (6.2442, -75.5812), (3.4516, -76.5320)
BARRANQUILLA, CARTAGENA, PASTO = (10.9685, -74.7813), (10.3910, -75.4794), (1.2136, -77.2811)
ETIQUETA_PUBLICO = {"co": "Colombia 18–65", "adul": "Colombia 25+", "lat": "+LatAm",
                    "jamv": "6 ciudades", "bog": "Bogotá"}
CUENTAS_IG = {
    "eva": {
        "nombre": "Eva", "ads": EVA_CUENTA_ADS, "pagina": EVA_PAGINA,
        "ig_user": "17841476069788612", "ig_datos": EVA_IG, "usuario_ig": "eva_eco_d",
        "objetivos": ["seguidores", "alcance", "interaccion"], "link": None,
        "publicos": {"co": ("Colombia, 18–65", {"countries": ["CO"]}, 18, 65),
                     "adul": ("Colombia, 25–60", {"countries": ["CO"]}, 25, 60),
                     "lat": ("CO, MX, AR, CL, PE, EC, 25–60",
                             {"countries": ["CO", "MX", "AR", "CL", "PE", "EC"]}, 25, 60)},
        "aprobadores": AUTORIZADOS,
    },
    "pahubi": {
        "nombre": "Pahubi", "ads": CUENTA_PAHUBI, "pagina": "675857115617706",
        "ig_user": "17841475486858296", "ig_datos": "28697586686529710",  # pahubi.colombia
        "usuario_ig": "pahubi.colombia",
        "objetivos": ["trafico", "ventas", "seguidores", "alcance"], "link": PRODUCTOS["papel"][1],
        "publicos": {"jamv": ("Bogotá, Medellín, Cali, Barranquilla, Cartagena y Pasto (+40 km), 25–54",
                              cerca_de(BOGOTA, MEDELLIN, CALI, BARRANQUILLA, CARTAGENA, PASTO), 25, 54),
                     "bog": ("Bogotá y la Sabana (+40 km), 25–54", cerca_de(BOGOTA), 25, 54),
                     "adul": ("Colombia, 25–54", {"countries": ["CO"]}, 25, 54),
                     "co": ("Colombia, 18–65", {"countries": ["CO"]}, 18, 65)},
        # Pahubi lo aprueba Ivan. Si PAHUBI_APROBADORES está vacío, aprueban los autorizados
        # (con el aviso de que debe ser con el OK de Ivan).
        "aprobadores": {x.strip() for x in ENV.get("PAHUBI_APROBADORES", "").split(",") if x.strip()}
                       or AUTORIZADOS,
    },
}
IG_OPCIONES_TOTAL = [30000, 50000, 100000, 200000]
IG_OPCIONES_DIAS = [2, 3, 5, 7]
IG_OPCIONES_DIARIO = [10000, 20000, 30000, 50000]  # presupuesto por día (botón "Por día")
DIAS_PUBLICACIONES = 365  # el bot escoge entre las publicaciones del último año, no solo las recientes


def accion_meta(cuenta, accion, params):
    return ejecutar_meta(CUENTAS_IG[cuenta]["ads"], accion, params)


def posts_ig(cuenta, dias=90):
    hoy = datetime.now(TZ_BOGOTA).date()
    posts = {}
    for f in windsor_datos("instagram", ["media_id", "timestamp", "media_caption", "media_reach",
                                         "media_permalink", "media_product_type", "media_saved",
                                         "media_shares", "media_reel_avg_watch_time", "media_views"],
                           hoy - timedelta(days=dias), hoy, CUENTAS_IG[cuenta]["ig_datos"]):
        if f.get("media_id") and f.get("timestamp"):
            f["media_caption"] = " ".join((f.get("media_caption") or "").split())
            posts[f["media_id"]] = f
    return posts


def candidatos_ig(cuenta, dias=7, factor=EVA_FACTOR, enlace=None):
    """Posts recientes con alcance >= factor × mediana (90 días). Con enlace, busca ese post."""
    posts = posts_ig(cuenta, dias=DIAS_PUBLICACIONES if enlace else 90)
    ahora = datetime.now(timezone.utc)
    viejos = sorted(p.get("media_reach") or 0 for p in posts.values()
                    if ahora - a_fecha(p["timestamp"]) > timedelta(days=2))
    mediana = viejos[len(viejos) // 2] if viejos else 0
    lista = []
    codigo = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels)/([\w-]+)", enlace or "")
    for p in posts.values():
        alcance = p.get("media_reach") or 0
        if codigo:
            if f"/{codigo.group(1)}" not in (p.get("media_permalink") or ""):
                continue
        elif ahora - a_fecha(p["timestamp"]) > timedelta(days=dias) or alcance < factor * mediana:
            continue
        lista.append({"media_id": p["media_id"], "texto": p.get("media_caption") or "",
                      "alcance": int(alcance), "veces": alcance / mediana if mediana else 0,
                      "enlace": p.get("media_permalink") or "",
                      "reel": p.get("media_product_type") == "REELS"})
    return sorted(lista, key=lambda c: -c["alcance"]), int(mediana)


def costos_cuenta(cuenta):
    """Costo por persona alcanzada y por visita a la página en 90 días, por objetivo de campaña.
    Si hay campañas del mismo objetivo se usan esas; si no, el promedio de la cuenta."""
    hoy = datetime.now(TZ_BOGOTA).date()
    filas = windsor_datos("facebook", ["campaign_objective", "spend", "reach",
                                       "actions_landing_page_view"],
                          hoy - timedelta(days=90), hoy, CUENTAS_IG[cuenta]["ads"])

    def calcular(fs):
        gasto = sum(f.get("spend") or 0 for f in fs)
        alcance = sum(int(f.get("reach") or 0) for f in fs)
        visitas = sum(int(f.get("actions_landing_page_view") or 0) for f in fs)
        return {"por_persona": gasto / alcance if alcance else None,
                "por_visita": gasto / visitas if visitas else None}
    costos = {"todas": calcular(filas)}
    for o, d in IG_OBJETIVOS.items():
        mismas = [f for f in filas if f.get("campaign_objective") == d["objective"]]
        costos[o] = calcular(mismas) if mismas else costos["todas"]
    return costos


def promo_ig_activa(estado, cuenta):
    ahora = time.time()
    for promo in estado.get("ig_promos", []):
        if promo["cuenta"] == cuenta and promo["fin"] > ahora and not promo.get("pausada"):
            return promo
    return None


def corto(texto, limite=550):
    """Recorta el texto plano (antes de escapar) para que la propuesta quepa en un mensaje."""
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


def resumen_recomendacion(p):
    """La recomendación en pocas líneas: veredicto + solo los puntos en ❌ o ⚠️ (máx. 3)."""
    lineas = []
    if p.get("veredicto"):
        lineas.append(f"\n🎯 <b>Recomendación: {html.escape(str(p['veredicto']))}</b>")
    malos = [x for x in (p.get("chequeo") or []) if str(x).startswith(("❌", "⚠"))]
    for punto in malos[:3]:
        lineas.append(html.escape(str(punto), quote=False))
    if p.get("corte"):
        lineas.append(f"✂️ <b>Se corta si:</b> {html.escape(corto(p['corte']), quote=False)}")
    return lineas


def teclado_confirmar(red, pid):
    return {"inline_keyboard": [[
        {"text": "✅ Confirmar y crear", "callback_data": f"{red}_si:{pid}"},
        {"text": "↩️ Cambiar algo", "callback_data": f"{red}_volver:{pid}"}]]}


def resumen_confirmar_ig(p):
    """Lo que se va a crear, con los ajustes que dejó la persona, antes del clic final."""
    c = CUENTAS_IG[p["cuenta"]]
    nombre_pub, _, edad_min, edad_max = c["publicos"][p["publico"]]
    fbig = p.get("redes") == "fbig" and p["objetivo"] != "seguidores"
    inicio = datetime.now(TZ_BOGOTA)
    fin = inicio + timedelta(days=p["dias"])
    if p.get("modo") == "diario" and p.get("diario"):
        plata = f"{cop(p['diario'])} por día × {p['dias']} días = <b>{cop(p['diario'] * p['dias'])}</b>"
    else:
        plata = f"<b>{cop(p['total'])}</b> en total (~{cop(p['total'] / p['dias'])}/día)"
    lineas = ["📋 <b>Confirma la pauta</b>",
              f"• <b>Cuenta:</b> {c['nombre']}",
              f"• <b>Red:</b> {'Facebook + Instagram' if fbig else 'Instagram'}",
              f"• <b>Publicación:</b> «{html.escape(p['texto'][:60])}…»"
              + (f' (<a href="{html.escape(p["enlace"])}">ver</a>)' if p.get("enlace") else ""),
              f"• <b>Objetivo:</b> {IG_OBJETIVOS[p['objetivo']]['etiqueta']}",
              f"• <b>Presupuesto:</b> {plata}",
              f"• <b>Fechas:</b> {inicio:%d/%m %H:%M} → {fin:%d/%m %H:%M} ({p['dias']} días)",
              f"• <b>Público:</b> {nombre_pub.split(' (')[0]} · {edad_min}–{edad_max} años"]
    if p["objetivo"] in OBJETIVOS_WEB:
        nombre_prod, _ = PRODUCTOS.get(p.get("producto") or "", (None, c["link"]))
        lineas.append(f"• <b>Lleva a:</b> {html.escape(nombre_prod or 'pahubi.com')} (con UTM)")
    elif p["objetivo"] == "seguidores":
        lineas.append(f"• <b>Lleva a:</b> perfil @{c['usuario_ig']}")
    if fbig:
        lineas.append("ℹ️ Es UN solo presupuesto para las dos redes: Meta lo reparte entre "
                      "Facebook e Instagram según dónde rinda más. No se duplica.")
    if p.get("redes") == "fbig" and p["objetivo"] == "seguidores":
        lineas.append("ℹ️ Seguidores va solo en Instagram (lleva al perfil de IG).")
    if p["cuenta"] == "pahubi":
        lineas.append("\n⚠️ ¿Ya tienes el OK de Ivan?")
    lineas.append("\nAl confirmar se crea y queda activa (Meta la revisa en minutos).")
    return "\n".join(lineas)


def resumen_confirmar_tt(p):
    inicio = datetime.now(TZ_BOGOTA)
    fin = inicio + timedelta(days=p["dias"])
    return "\n".join([
        "📋 <b>Confirma la pauta</b>",
        "• <b>Cuenta:</b> Eva · TikTok (Spark Ad)",
        f"• <b>Video:</b> «{html.escape(p['texto'][:60])}…»"
        + (f' (<a href="{html.escape(p["enlace"])}">ver</a>)' if p.get("enlace") else ""),
        f"• <b>Objetivo:</b> {TT_OBJETIVOS.get(p.get('objetivo'), TT_OBJETIVOS['alcance'])['etiqueta']}",
        (f"• <b>Presupuesto:</b> {cop(p['diario'])} por día × {p['dias']} días = <b>{cop(p['total'])}</b>"
         if p.get("modo") == "diario" and p.get("diario") else
         f"• <b>Presupuesto:</b> <b>{cop(p['total'])}</b> en total (~{cop(p['total'] / p['dias'])}/día)"),
        f"• <b>Fechas:</b> {inicio:%d/%m %H:%M} → {fin:%d/%m %H:%M} ({p['dias']} días)",
        "• <b>Público:</b> Colombia · todas las edades",
        "\nAl confirmar se crea y queda activa (TikTok la revisa antes de mostrarla)."])


def texto_propuesta_ig(p):
    c = CUENTAS_IG[p["cuenta"]]
    obj = IG_OBJETIVOS[p["objetivo"]]
    nombre_pub, _, edad_min, edad_max = c["publicos"][p["publico"]]
    fin = datetime.now(TZ_BOGOTA) + timedelta(days=p["dias"])
    tipo = "Reel" if p.get("reel") else "Publicación"
    fbig = p.get("redes") == "fbig"
    red = "Facebook + Instagram" if fbig else "Instagram"
    lineas = [f"🚀 <b>Pauta lista · {c['nombre']} · {red}</b>"]
    if p.get("enlace"):
        lineas.append(f'🎬 <a href="{html.escape(p["enlace"])}">{tipo} a pautar</a>: '
                      f"«{html.escape(p['texto'][:90])}…»")
    else:
        lineas.append(f"🎬 {tipo}: «{html.escape(p['texto'][:90])}…»")
    lineas.append(f"   Alcance orgánico {p['alcance']:,}".replace(",", ".")
                  + (f" ({p['veces']:.1f}× lo normal)" if p.get("veces") else ""))
    if p.get("por_que"):
        lineas.append(f"   <i>Por qué este: {html.escape(corto(p['por_que']), quote=False)}</i>")
    lineas += [
        "",
        "⚙️ <b>Configuración</b>",
        f"• <b>Objetivo:</b> {obj['etiqueta']}",
        (f"• <b>Presupuesto:</b> {cop(p['diario'])} por día × {p['dias']} días = "
         f"{cop(p['total'])} total" if p.get("modo") == "diario" else
         f"• <b>Presupuesto:</b> {cop(p['total'])} total · ~{cop(p['total'] / p['dias'])}/día"),
        f"• <b>Días:</b> {p['dias']} (desde que apruebes hasta el {fin:%d/%m})",
        f"• <b>Público:</b> {nombre_pub.split(' (')[0].split(', 2')[0]} · {edad_min}–{edad_max} años · "
        f"hombres y mujeres",
        ("• <b>Dónde:</b> Facebook (feed, historias, reels) + Instagram (feed, historias, "
         "reels, explorar). Un solo presupuesto que Meta reparte entre las dos, no uno por "
         "cada red" if fbig else
         "• <b>Dónde:</b> solo Instagram (feed, historias, reels, explorar)"),
    ]
    if p["objetivo"] in OBJETIVOS_WEB:
        nombre_prod, url = PRODUCTOS.get(p.get("producto") or "", (None, c["link"]))
        lineas.append(f"• <b>Botón:</b> Comprar → {html.escape(nombre_prod or url)} (ficha)")
        lineas.append("• <b>Medición:</b> UTM a WooCommerce"
                      + (" + píxel (compra)" if p["objetivo"] == "ventas" else ""))
    elif p["objetivo"] == "seguidores":
        lineas.append(f"• <b>Botón:</b> Ver perfil → @{c['usuario_ig']}")
    elif p["objetivo"] == "alcance":
        lineas.append("• <b>Frecuencia:</b> máximo 2 veces por persona cada 7 días")
    costos = (p.get("costos") or {}).get("trafico" if p["objetivo"] == "ventas" else p["objetivo"]) or {}

    def num(x):
        return f"{x:,.0f}".replace(",", ".")
    if p.get("estimado"):
        lineas.append(f"📊 <b>Estimado:</b> {html.escape(corto(p['estimado']), quote=False)}")
    elif p["objetivo"] in OBJETIVOS_WEB and costos.get("por_visita"):
        v = p["total"] / costos["por_visita"]
        lineas.append(f"📊 <b>Estimado:</b> {num(v * 0.6)}–{num(v * 1.2)} visitas a la página "
                      f"(a {cop(costos['por_visita'])} por visita en los últimos 90 días)")
    elif p["objetivo"] == "seguidores":
        lineas.append("📊 <b>Estimado:</b> en oct salió a ~$350 por seguidor; se mide por el "
                      "crecimiento diario de seguidores.")
    elif costos.get("por_persona"):
        n = p["total"] / costos["por_persona"]
        lineas.append(f"📊 <b>Estimado:</b> {num(n * 0.7)}–{num(n * 1.3)} personas alcanzadas "
                      f"(a {cop(costos['por_persona'] * 1000)} por cada 1.000 en los últimos 90 días)")
    else:
        lineas.append("📊 Estimado: MISSING (sin pauta reciente en esta cuenta).")
    lineas += resumen_recomendacion(p)
    if p["cuenta"] == "pahubi":
        lineas.append("\n⚠️ Pahubi: aprobar con el OK de Ivan.")
    lineas.append(f"\n🔒 {'Plata y días' if p.get('objetivo_libre') else 'Objetivo, plata y días'}: "
                  "los que escogiste. Si quieres otros, vuelve a tocar el botón del menú."
                  if p.get("bloqueado") else
                  "\nCambia lo que quieras con los botones y dale ✅.")
    return "\n".join(lineas)


def teclado_propuesta_ig(pid, p):
    c = CUENTAS_IG[p["cuenta"]]

    def marca(texto, elegido):
        return f"• {texto} •" if elegido else texto
    diario = p.get("modo") == "diario"
    filas = [
        [{"text": marca(IG_OBJETIVOS[o]["etiqueta"].split(" (")[0], o == p["objetivo"]),
          "callback_data": f"ig_o:{pid}:{o}"} for o in c["objetivos"]],
        [{"text": marca("Presupuesto total", not diario), "callback_data": f"ig_m:{pid}:total"},
         {"text": marca("Presupuesto por día", diario), "callback_data": f"ig_m:{pid}:diario"}],
        ([{"text": marca(f"{cop(v)}/día", v == p.get("diario")), "callback_data": f"ig_y:{pid}:{v}"}
          for v in IG_OPCIONES_DIARIO] if diario else
         [{"text": marca(cop(v), v == p["total"]), "callback_data": f"ig_t:{pid}:{v}"}
          for v in IG_OPCIONES_TOTAL]),
        [{"text": marca("Solo Instagram", p.get("redes", "ig") == "ig"), "callback_data": f"ig_r:{pid}:ig"},
         {"text": marca("Facebook + Instagram", p.get("redes") == "fbig"),
          "callback_data": f"ig_r:{pid}:fbig"}],
        [{"text": marca(f"{d} días", d == p["dias"]), "callback_data": f"ig_d:{pid}:{d}"}
         for d in IG_OPCIONES_DIAS],
        [{"text": marca(ETIQUETA_PUBLICO.get(k, k), k == p["publico"]),
          "callback_data": f"ig_a:{pid}:{k}"} for k in c["publicos"]],
    ]
    if p.get("bloqueado"):  # plata, días y objetivo ya escogidos antes: no se repreguntan
        filas = (([filas[0]] if p.get("objetivo_libre") else []) + [filas[5]]
                 + ([filas[3]] if p["cuenta"] == "pahubi" else []))
    if p["objetivo"] in OBJETIVOS_WEB:
        filas.append([{"text": marca(nombre, k == p.get("producto")), "callback_data": f"ig_l:{pid}:{k}"}
                      for k, (nombre, _) in PRODUCTOS.items()])
    filas.append([{"text": "✅ Aprobar", "callback_data": f"ig_ok:{pid}"},
                  {"text": "❌ Rechazar", "callback_data": f"ig_no:{pid}"}])
    return {"inline_keyboard": filas}


def proponer_ig(estado, cuenta, candidato, chat_ids, plan=None):
    """plan: lo que decidió /pauta (objetivo, público, presupuesto, por qué...). Sin plan, valores base."""
    estado.setdefault("ig_vistos", []).append(candidato["media_id"])
    pid = f"{cuenta[0]}{candidato['media_id'][-10:]}"
    c = CUENTAS_IG[cuenta]
    p = {**candidato, "cuenta": cuenta, "texto": candidato["texto"][:200],
         "objetivo": c["objetivos"][0], "total": IG_OPCIONES_TOTAL[1], "dias": 3,
         "publico": next(iter(c["publicos"])), "producto": "papel" if c["link"] else None,
         "costos": costos_cuenta(cuenta), **(plan or {})}
    estado.setdefault("ig_propuestas", {})[pid] = p
    guardar_estado(estado)
    for chat_id in chat_ids:
        tg("sendMessage", chat_id=chat_id, text=texto_propuesta_ig(p), parse_mode="HTML",
           disable_web_page_preview=False, reply_markup=teclado_propuesta_ig(pid, p))


def aprobar_ig(estado, pid, quien):
    p = estado.get("ig_propuestas", {}).get(pid)
    if not p:
        return "Esa propuesta ya no está vigente."
    cuenta, c, obj = p["cuenta"], CUENTAS_IG[p["cuenta"]], IG_OBJETIVOS[p["objetivo"]]
    if quien not in c["aprobadores"]:
        return f"Solo pueden aprobar promociones de {c['nombre']} los IDs en PAHUBI_APROBADORES."
    activa = promo_ig_activa(estado, cuenta)
    if activa:
        return (f"{c['nombre']} ya tiene una promoción activa hasta el "
                f"{datetime.fromtimestamp(activa['fin'], TZ_BOGOTA):%d/%m}. Una a la vez.")
    # Validaciones antes de crear cualquier cosa en Meta.
    if p["objetivo"] not in c["objetivos"]:
        return f"El objetivo {p['objetivo']} no está permitido para {c['nombre']}; no se creó nada."
    if p["objetivo"] == "ventas" and cuenta != "pahubi":
        return "El objetivo Ventas solo se usa en la cuenta de Pahubi; no se creó nada."
    con_link = p["objetivo"] in OBJETIVOS_WEB or bool(c["link"] and p["objetivo"] == "alcance")
    link = PRODUCTOS.get(p.get("producto") or "", (None, c["link"]))[1] if con_link else None
    if con_link and (not link or not link.startswith("https://pahubi.com/producto/")):
        return "La pauta debe mandar a una ficha de producto de pahubi.com; no se creó nada."
    # 1. Campaña (una por cuenta y objetivo, se reutiliza; sin presupuesto propio no gasta).
    clave = f"{cuenta}:{p['objetivo']}"
    campana = estado.setdefault("ig_campanas", {}).get(clave)
    if not campana:
        respuesta = accion_meta(cuenta, "create_campaign", {
            "name": f"{c['nombre'].upper()}_Bot_IG_{obj['etiqueta'].split()[0]}",
            "objective": obj["objective"], "special_ad_categories": [],
            "is_adset_budget_sharing_enabled": False, "status": "active"})
        campana = buscar_id(respuesta, "campaign_id", "id")
        if not campana:
            return ("No se creó la campaña. Windsor respondió: "
                    + html.escape(str(respuesta)[:400]))
        estado["ig_campanas"][clave] = campana
        guardar_estado(estado)
    # 2. Conjunto, pausado: solo Instagram, presupuesto total y fecha de fin.
    inicio = datetime.now(TZ_BOGOTA)
    fin = inicio + timedelta(days=p["dias"])
    nombre_pub, geo, edad_min, edad_max = c["publicos"][p["publico"]]
    nombre = f"{c['nombre']} bot IG · {p['texto'][:30]} · {inicio:%d-%m}"
    redes = {"publisher_platforms": ["instagram"],
             "instagram_positions": ["stream", "story", "explore", "reels"]}
    if p.get("redes") == "fbig":
        redes = {"publisher_platforms": ["facebook", "instagram"],
                 "facebook_positions": ["feed", "story", "facebook_reels"],
                 "instagram_positions": ["stream", "story", "explore", "reels"]}
    if p.get("objetivo") == "seguidores":  # visitas al perfil de IG: Facebook no aplica
        redes = {"publisher_platforms": ["instagram"],
                 "instagram_positions": ["stream", "story", "explore", "reels"]}
    presupuesto = ({"daily_budget": p["diario"]} if p.get("modo") == "diario" and p.get("diario")
                   else {"lifetime_budget": p["total"]})
    conjunto_params = {
        "campaign_id": campana, "name": nombre, "optimization_goal": obj["optimization_goal"],
        "billing_event": "IMPRESSIONS", **presupuesto,
        "end_time": fin.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "paused",
        "targeting": {"geo_locations": geo, "age_min": edad_min, "age_max": edad_max,
                      **redes, "targeting_automation": {"advantage_audience": 0}},
    }
    if obj["destination_type"]:
        conjunto_params["destination_type"] = obj["destination_type"]
    if p["objetivo"] == "interaccion":
        conjunto_params["promoted_object"] = {"page_id": c["pagina"]}
    if p["objetivo"] == "ventas":
        conjunto_params["promoted_object"] = {"pixel_id": PIXEL_PAHUBI, "custom_event_type": "PURCHASE"}
    if p["objetivo"] == "alcance":
        conjunto_params["extra_params"] = {"frequency_control_specs": [
            {"event": "IMPRESSIONS", "interval_days": 7, "max_frequency": 2}]}
    respuesta = accion_meta(cuenta, "create_adset", conjunto_params)
    conjunto = buscar_id(respuesta, "adset_id", "id")
    if not conjunto:
        return ("No se creó el conjunto (la campaña quedó sin gastar). Windsor respondió: "
                + html.escape(str(respuesta)[:400]))
    # 3. Anuncio con el post existente de Instagram (no se crea contenido nuevo).
    utm = f"bot_ig_{cuenta}_{p['objetivo']}_{inicio:%Y%m%d}_{p['media_id'][-5:]}"
    creativo = {"name": nombre, "object_id": c["pagina"], "instagram_user_id": c["ig_user"],
                "source_instagram_media_id": p["media_id"]}
    if con_link:
        creativo["call_to_action"] = {"type": "SHOP_NOW", "value": {"link": link}}
        creativo["url_tags"] = f"utm_source=instagram&utm_medium=paid&utm_campaign={utm}"
    elif p["objetivo"] == "seguidores":
        creativo["call_to_action"] = {"type": "VIEW_INSTAGRAM_PROFILE", "value": {
            "link": f"https://www.instagram.com/{c['usuario_ig']}/"}}
    try:
        anuncio = buscar_id(accion_meta(cuenta, "create_ad", {
            "adset_id": conjunto, "name": nombre, "creative": creativo, "status": "active"}),
            "ad_id", "id")
        if not anuncio:
            raise RuntimeError("Windsor no devolvió el id del anuncio")
        # 4. Todo listo: se encienden anuncio, conjunto y campaña (Windsor los puede dejar pausados).
        accion_meta(cuenta, "enable_ad", {"ad_id": anuncio})
        accion_meta(cuenta, "enable_adset", {"adset_id": conjunto})
        accion_meta(cuenta, "enable_campaign", {"campaign_id": campana})
    except Exception:
        try:
            accion_meta(cuenta, "pause_adset", {"adset_id": conjunto})
        except Exception:
            pass
        raise
    estado.setdefault("ig_promos", []).append({
        "cuenta": cuenta, "adset_id": conjunto, "ad_id": anuncio, "media_id": p["media_id"],
        "texto": p["texto"], "objetivo": p["objetivo"], "total": p["total"], "utm": utm if con_link else None,
        "corte": p.get("corte"), "proposito": p.get("proposito"),
        "seguidores_inicio": seguidores_ig(cuenta) if p["objetivo"] == "seguidores" else None,
        "inicio": inicio.timestamp(), "fin": fin.timestamp(), "aprobo": quien})
    estado["ig_propuestas"].pop(pid, None)
    guardar_estado(estado)
    red = "Facebook + Instagram" if redes["publisher_platforms"] == ["facebook", "instagram"] else "Instagram"
    plata = (f"{cop(p['diario'])}/día ({cop(p['total'])} en total)" if "daily_budget" in presupuesto
             else cop(p["total"]))
    return (f"✅ {c['nombre']}: promoción creada y activa en {red}.\n"
            f"{IG_OBJETIVOS[p['objetivo']]['etiqueta']} · {plata} hasta el {fin:%d/%m %H:%M} · "
            f"{nombre_pub}.\nMeta la revisa (minutos a pocas horas). Te mando el resultado cada "
            "mañana con la opción de pausarla." + (f"\nUTM: {utm}" if con_link else ""))


def seguidores_ig(cuenta):
    hoy = datetime.now(TZ_BOGOTA).date()
    try:
        filas = windsor_datos("instagram", ["followers_count"], hoy - timedelta(days=2), hoy,
                              CUENTAS_IG[cuenta]["ig_datos"])
    except requests.RequestException:
        return None
    valores = [int(f["followers_count"]) for f in filas if f.get("followers_count")]
    return max(valores) if valores else None


def metricas_ig_promo(promo, desde, hasta):
    filas = windsor_datos("facebook", ["adset_id", "spend", "reach", "impressions", "link_clicks",
                                       "actions_landing_page_view", "actions_video_view",
                                       "actions_post_engagement"],
                          desde, hasta, CUENTAS_IG[promo["cuenta"]]["ads"])
    m = {"gasto": 0, "alcance": 0, "impresiones": 0, "clics": 0, "visitas": 0, "vistas": 0,
         "interacciones": 0}
    for f in filas:
        if str(f.get("adset_id")) != promo["adset_id"]:
            continue
        m["gasto"] += f.get("spend") or 0
        m["alcance"] += int(f.get("reach") or 0)
        m["impresiones"] += int(f.get("impressions") or 0)
        m["clics"] += int(f.get("link_clicks") or 0)
        m["visitas"] += int(f.get("actions_landing_page_view") or 0)
        m["vistas"] += int(f.get("actions_video_view") or 0)
        m["interacciones"] += int(f.get("actions_post_engagement") or 0)
    return m


def texto_metricas_ig(promo, m, titulo, desde, hasta):
    c = CUENTAS_IG[promo["cuenta"]]
    lineas = [f"📊 <b>{c['nombre']} en Instagram, {titulo}</b>",
              f"«{html.escape(promo['texto'][:60])}»",
              f"Gasto {cop(m['gasto'])} de {cop(promo['total'])} · Alcance {m['alcance']:,} · "
              f"Impresiones {m['impresiones']:,}".replace(",", ".")]
    if m["alcance"]:
        lineas.append(f"Costo por 1.000 personas: {cop(m['gasto'] / m['alcance'] * 1000)}")
    if promo.get("objetivo") == "seguidores":
        lineas.append(f"Clics {m['clics']} · Vistas {m['vistas']}")
        ahora_seg, antes = seguidores_ig(promo["cuenta"]), promo.get("seguidores_inicio")
        if ahora_seg and antes:
            ganados = ahora_seg - antes
            lineas.append(f"<b>Seguidores de la cuenta: {antes:,} → {ahora_seg:,} ({ganados:+,})</b>"
                          .replace(",", "."))
            if ganados > 0 and m["gasto"]:
                lineas.append(f"Costo por seguidor (aprox., incluye orgánicos): "
                              f"{cop(m['gasto'] / ganados)}")
    elif promo["cuenta"] == "eva":
        lineas.append(f"Vistas {m['vistas']} · Interacciones {m['interacciones']}")
    else:
        lineas.append(f"Clics {m['clics']} · Visitas a pahubi.com {m['visitas']}")
        try:
            woo = pedidos_woo(desde, hasta)
        except requests.RequestException:
            woo = None
        if woo is not None:
            v = woo.get(promo["utm"]) or {"pedidos": 0, "ventas": 0}
            lineas.append(f"<b>Ventas reales con su UTM: {v['pedidos']} pedidos · {cop(v['ventas'])}</b>")
    if promo.get("corte"):
        lineas.append(f"Regla de corte: {html.escape(promo['corte'][:300])}")
    return "\n".join(lineas)


def revisar_promos_ig(estado):
    """Cada mañana: resultado de ayer de cada promoción activa y resumen final de las que acabaron."""
    hoy = datetime.now(TZ_BOGOTA).date()
    ayer = hoy - timedelta(days=1)
    for promo in estado.get("ig_promos", []):
        if promo.get("resumen_final"):
            continue
        cuenta = promo["cuenta"]
        destinatarios = AUTORIZADOS | CUENTAS_IG[cuenta]["aprobadores"]
        inicio = datetime.fromtimestamp(promo["inicio"], TZ_BOGOTA).date()
        if promo["fin"] < time.time() or promo.get("pausada"):
            m = metricas_ig_promo(promo, inicio, hoy)
            texto = texto_metricas_ig(promo, m, "resumen final", inicio, hoy)
            for chat_id in destinatarios:
                enviar(chat_id, texto)
            promo["resumen_final"] = True
            try:
                aprender_de_promo(promo, m, inicio, hoy)
            except Exception as e:  # el aprendizaje no debe frenar el resumen
                print("No pude anotar el aprendizaje:", e)
            continue
        m = metricas_ig_promo(promo, ayer, ayer)
        texto = texto_metricas_ig(promo, m, "ayer", ayer, ayer)
        botones = [[{"text": "⏸ Pausar", "callback_data": f"ig_pausa:{cuenta}:{promo['adset_id']}"}]]
        for chat_id in destinatarios:
            tg("sendMessage", chat_id=chat_id, text=texto, parse_mode="HTML",
               reply_markup={"inline_keyboard": botones})
    guardar_estado(estado)


def aprender_de_promo(promo, m, inicio, hoy):
    """Anota en el manual el resultado real de una promo del bot que terminó."""
    objetivo = promo.get("objetivo")
    ventas = None
    efecto = None
    if objetivo in OBJETIVOS_WEB and promo.get("utm"):
        woo = pedidos_woo(inicio, hoy) or {}
        ventas = (woo.get(promo["utm"]) or {}).get("pedidos", 0)
        efecto = efecto_indirecto(inicio, hoy)
    if objetivo in OBJETIVOS_WEB:
        tipo, n, limite = "visitas a la web", m["visitas"], CORTE["visita_web"]
    elif objetivo == "seguidores":
        ganados = None
        if promo.get("seguidores_inicio"):
            ahora_seg = seguidores_ig(promo["cuenta"])
            ganados = ahora_seg - promo["seguidores_inicio"] if ahora_seg else None
        tipo, n, limite = "seguidores (cuenta)", ganados or 0, CORTE["seguidor"]
    else:
        tipo, n, limite = "personas alcanzadas", m["alcance"], None
    costo = m["gasto"] / n if n else None
    anotar_aprendizaje(
        f"{inicio} a {hoy}", f"{CUENTAS_IG[promo['cuenta']]['nombre']} (Meta, bot)",
        f"{IG_OBJETIVOS[objetivo]['etiqueta']} · «{promo['texto'][:40]}»"
        + (f" · propósito: {promo['proposito'][:60]}" if promo.get("proposito") else ""),
        cop(m["gasto"]), f"{n:,} {tipo}".replace(",", "."),
        cop(costo) if costo and limite else "—",
        (f"{ventas} pedidos" if ventas is not None else "—")
        + (f"; {texto_indirecto(efecto)}" if efecto else ""),
        lectura_resultado("visitas a la web" if objetivo in OBJETIVOS_WEB else tipo, costo, limite,
                          ventas, efecto))


def pausar_ig(estado, cuenta, conjunto):
    accion_meta(cuenta, "pause_adset", {"adset_id": conjunto})
    for promo in estado.get("ig_promos", []):
        if promo["adset_id"] == conjunto:
            promo["pausada"] = True
    guardar_estado(estado)
    return "⏸ Promoción pausada."


def comando_promo(chat_id, cuenta, texto, estado):
    c = CUENTAS_IG[cuenta]
    if promo_ig_activa(estado, cuenta):
        enviar(chat_id, f"{c['nombre']} ya tiene una promoción activa. Una a la vez.")
        return
    partes = texto.split(maxsplit=1)
    enlace = partes[1].strip() if len(partes) > 1 else None
    enviar(chat_id, "Buscando la publicación…" if enlace else
           f"Buscando la mejor publicación reciente de {c['nombre']} en Instagram…")
    candidatos, mediana = candidatos_ig(cuenta, dias=14, factor=0, enlace=enlace)
    if not candidatos:
        enviar(chat_id, "No encontré esa publicación en Instagram (si se acaba de subir, Windsor "
                        "puede tardar unas horas en verla)." if enlace else
               f"{c['nombre']} no tiene publicaciones en Instagram en los últimos 14 días.")
        return
    proponer_ig(estado, cuenta, candidatos[0], [chat_id])


# ---------- Pauta con propósito ----------
# "/pauta quiero vender papel higiénico en Bogotá" → Claude lee el manual (playbook_pautas.md),
# los costos reales, las publicaciones y las ventas, y arma la pauta. El bot valida cada valor
# contra las listas permitidas y la muestra con los botones de siempre. Nada se crea sin ✅.

PLAYBOOK = BASE / "playbook_pautas.md"
CRITERIOS_VENTA = BASE / "criterios_venta.md"  # skills ads, ad-creative, cro y social, para todo propósito
PALABRAS_VENTA = ("vend", "venta", "compra", "pedido", "pahubi.com")


def salud_tienda(dias=14):
    """Cuántos pedidos creados terminan pagados: si la tienda no cobra, más pauta no sirve."""
    if not (ENV.get("WOO_KEY") and ENV.get("WOO_SECRET")):
        return "MISSING (sin llaves de WooCommerce)"
    url = ENV.get("WOO_URL", "https://pahubi.com").rstrip("/") + "/wp-json/wc/v3/orders"
    desde = (datetime.now(TZ_BOGOTA) - timedelta(days=dias)).strftime("%Y-%m-%dT00:00:00")
    estados, pagina = {}, 1
    clientes = {}  # correo -> pagó alguna vez (un reintento que luego pagó no es un cliente perdido)
    while True:
        r = requests.get(url, timeout=60, params={
            "consumer_key": ENV["WOO_KEY"], "consumer_secret": ENV["WOO_SECRET"],
            "status": "any", "per_page": 100, "page": pagina, "after": desde})
        r.raise_for_status()
        pedidos = r.json()
        for p in pedidos:
            if p["status"] in ("trash", "checkout-draft"):
                continue
            estados[p["status"]] = estados.get(p["status"], 0) + 1
            correo = (p.get("billing", {}).get("email") or f"pedido{p['id']}").lower()
            pago = p["status"] in ("processing", "completed", "delivered")
            clientes[correo] = clientes.get(correo, False) or pago
        if len(pedidos) < 100:
            break
        pagina += 1
    pagaron = sum(clientes.values())
    return {"dias": dias, "pedidos_por_estado": estados, "clientes_que_intentaron": len(clientes),
            "clientes_que_pagaron": pagaron,
            "porcentaje_clientes_que_pagaron": round(100 * pagaron / len(clientes)) if clientes else None,
            "nota": "se cuenta por cliente: varios intentos de la misma persona cuentan una vez"}

SISTEMA_PAUTA = (
    "Eres el estratega de pautas de Pahubi SAS y de Eva (eva_eco_d). Recibes un propósito y "
    "datos reales, y devuelves SOLO un objeto JSON válido, sin texto antes ni después. Sigue el "
    "manual al pie de la letra; si el propósito choca con una regla, elige lo que la cumple y "
    "explícalo. Nunca inventes datos: si falta uno, dilo en 'advertencias'. Escribe en español de "
    "Colombia, claro y corto, para leer en Telegram: cada campo de texto en máximo 3 frases, "
    "y 'advertencias' en máximo 3 puntos cortos.\n\n" + CONTEXTO_NEGOCIO
)


PAUTADAS_FILE = BASE / "publicaciones_pautadas.json"


def codigo_ig(enlace):
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels)/([\w-]+)", enlace or "")
    return m.group(1) if m else None


def pautadas():
    """Publicaciones que ya se pautaron alguna vez (a mano o por el bot). Windsor (plan de prueba)
    solo deja ver 30 días de anuncios, así que el bot guarda la lista y la va llenando."""
    try:
        datos = json.loads(PAUTADAS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        datos = {}
    ig = set(datos.get("instagram", []))
    tt = set(datos.get("tiktok", []))
    antes = (len(ig), len(tt))
    hoy = datetime.now(TZ_BOGOTA).date()
    for cuenta_ads in (CUENTA_PAHUBI, EVA_CUENTA_ADS):
        try:
            for f in windsor_datos("facebook", ["ad_id", "effective_instagram_media_id",
                                                "instagram_permalink_url"],
                                   hoy - timedelta(days=29), hoy, cuenta_ads):
                for x in (f.get("effective_instagram_media_id"), codigo_ig(f.get("instagram_permalink_url"))):
                    if x:
                        ig.add(str(x))
        except requests.RequestException:
            pass
    try:
        for promo in leer_estado().get("ig_promos", []):
            ig.add(str(promo.get("media_id")))
        for promo in leer_estado().get("tt_promos", []):
            tt.add(str(promo.get("video_id")))
    except Exception:
        pass
    if (len(ig), len(tt)) != antes:
        datos.update({"instagram": sorted(ig), "tiktok": sorted(tt)})
        PAUTADAS_FILE.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return ig, tt


def resumen_posts(cuenta, dias=DIAS_PUBLICACIONES, n=35):
    """Las publicaciones con más posibilidad para pautar: vistas, alcance y, sobre todo, cuánto la
    compartieron y guardaron (lo que la gente ya premió gratis). Primero las que nunca se pautaron."""
    ahora = datetime.now(timezone.utc)
    posts = [p for p in posts_ig(cuenta, dias=dias).values()
             if ahora - a_fecha(p["timestamp"]) <= timedelta(days=dias)]
    alcances = sorted(p.get("media_reach") or 0 for p in posts)
    mediana = alcances[len(alcances) // 2] if alcances else 0
    ya_ig, _ = pautadas()

    def ya(p):
        return str(p["media_id"]) in ya_ig or (codigo_ig(p.get("media_permalink")) or "-") in ya_ig

    def puntaje(p):
        alcance = p.get("media_reach") or 0
        premio = (p.get("media_shares") or 0) * 2 + (p.get("media_saved") or 0)
        nota = (alcance / mediana if mediana else 0) + 100 * premio / max(alcance, 50)
        return nota * (0.5 if ya(p) else 1)  # sin pautar primero; las pautadas quedan, pero detrás
    posts.sort(key=lambda p: -puntaje(p))
    return [{"media_id": p["media_id"], "fecha": p["timestamp"][:10],
             "ya_se_pauto": ya(p),
             "vistas": int(p.get("media_views") or 0) or None,
             "alcance_organico": int(p.get("media_reach") or 0),
             "veces_lo_normal": round((p.get("media_reach") or 0) / mediana, 1) if mediana else None,
             "compartidos": int(p.get("media_shares") or 0),
             "guardados": int(p.get("media_saved") or 0),
             "seg_vista_promedio": round((p.get("media_reel_avg_watch_time") or 0) / 1000, 1) or None,
             "tipo": "reel" if p.get("media_product_type") == "REELS" else "post",
             "texto": (p.get("media_caption") or "")[:160]} for p in posts[:n]]


def datos_para_pauta(estado):
    hoy = datetime.now(TZ_BOGOTA).date()
    datos = {"fecha_hoy": hoy.isoformat(), "publicaciones": {}, "costos_90_dias": {},
             "promos_del_bot_activas": [
                 {"cuenta": x["cuenta"], "objetivo": x["objetivo"],
                  "hasta": datetime.fromtimestamp(x["fin"], TZ_BOGOTA).date().isoformat()}
                 for x in estado.get("ig_promos", []) if x["fin"] > time.time() and not x.get("pausada")]}
    for cuenta in CUENTAS_IG:
        try:
            datos["publicaciones"][cuenta] = resumen_posts(cuenta)
            datos["costos_90_dias"][cuenta] = costos_cuenta(cuenta)
        except requests.RequestException as e:
            datos["publicaciones"][cuenta] = f"sin datos ({str(e)[:80]})"
    try:
        datos["pauta_pahubi_14_dias"] = reporte(hoy - timedelta(days=13), hoy, "Pahubi 14 días")
    except requests.RequestException:
        datos["pauta_pahubi_14_dias"] = "sin datos"
    try:
        datos["pauta_eva_7_dias"] = metricas_eva(hoy - timedelta(days=6), hoy)
        datos["seguidores_eva"] = seguidores_eva()
    except requests.RequestException:
        pass
    try:  # para juzgar también el efecto indirecto (vieron la pauta y compraron después sin UTM)
        datos["ventas_por_semana_12_semanas"] = ventas_semanales_por_origen()
    except requests.RequestException:
        pass
    try:  # todas las campañas (también las hechas a mano), para no duplicar ni chocar
        datos["todas_las_campanas_30_dias"] = [
            {"nombre": c["nombre"], "plataforma": c["plataforma"], "cuenta": c["cuenta"],
             "activa": campana_activa(c), "desde": c["inicio"], "hasta": c["ultimo_gasto"],
             "gasto": round(c["gasto"]), "resultado": f"{r[1]} {r[0]}",
             "costo_por_resultado": round(r[2]) if r[2] else None}
            for c in campanas_todas().values() for r in [resultado_campana(c)] if c["gasto"]]
    except requests.RequestException:
        pass
    return datos


def pedir_plan(proposito, estado):
    opciones = {
        cuenta: {"objetivos": c["objetivos"], "publicos": {k: v[0] for k, v in c["publicos"].items()}}
        for cuenta, c in CUENTAS_IG.items()}
    datos = datos_para_pauta(estado)
    if any(p in proposito.lower() for p in PALABRAS_VENTA):
        try:
            datos["salud_tienda_14_dias"] = salud_tienda()
        except requests.RequestException as e:
            datos["salud_tienda_14_dias"] = f"MISSING ({str(e)[:80]})"
    tiktok_listo = bool(TT_TOKEN)
    if tiktok_listo:
        try:
            datos["videos_tiktok_eva"] = [{k: v for k, v in x.items() if k not in ("enlace", "mediana")}
                                          for x in videos_tiktok_eva()]
        except requests.RequestException as e:
            datos["videos_tiktok_eva"] = f"sin datos ({str(e)[:80]})"
            tiktok_listo = False
    if tiktok_listo:
        texto_tiktok_opcion = (
            f"- plataforma \"tiktok\" (solo cuenta eva; Spark Ad con un video que ya está en su "
            f"TikTok): objetivo uno de {list(TT_OBJETIVOS)}; video_id uno de videos_tiktok_eva; "
            f"total uno de {TT_OPCIONES_TOTAL}; dias uno de {TT_OPCIONES_DIAS} (TikTok pide "
            f"mínimo $20.000 por día). Escoge TikTok o Instagram según dónde cumpla mejor el "
            f"propósito y salga más barato según el manual.\n")
    else:
        texto_tiktok_opcion = "- plataforma \"tiktok\": todavía no se puede crear desde el bot\n"
    criterios = (f"CRITERIOS DE EXPERTO (escoge la publicación y configura con ellos, punto por "
                 f"punto; nuestra historia pesa más):\n{CRITERIOS_VENTA.read_text(encoding='utf-8')}\n\n")
    pregunta = (
        f"PROPÓSITO: {proposito}\n\n"
        f"MANUAL DE PAUTAS:\n{PLAYBOOK.read_text(encoding='utf-8')}\n\n"
        + criterios +
        f"OPCIONES PERMITIDAS (usa solo estas claves):\n"
        f"- plataforma \"meta\" (Instagram): cuenta y objetivos/públicos: "
        f"{json.dumps(opciones, ensure_ascii=False)}; producto (solo si el objetivo es trafico o "
        f"ventas): {list(PRODUCTOS)}; total (COP) uno de {IG_OPCIONES_TOTAL}; dias uno de "
        f"{IG_OPCIONES_DIAS}; media_id: una de las publicaciones de esa cuenta, o null si "
        f"ninguna sirve\n" + texto_tiktok_opcion + "\n"
        "DEVUELVE ESTE JSON:\n"
        '{"plataforma": "...", "cuenta": "...", "objetivo": "...", "media_id": "... o null", '
        '"video_id": "solo si plataforma es tiktok, o null", '
        '"producto": "... o null", "publico": "...", "total": 0, "dias": 0, '
        '"por_que": "2-4 frases citando datos", "estimado": "rango esperado y en qué se basa", '
        '"medir": "qué número mirar y dónde", "corte": "regla concreta para pausar", '
        '"advertencias": "datos que faltan o riesgos, o vacío", '
        '"texto_si_no_se_puede": "si plataforma es tiktok o media_id es null: qué hacer a mano o '
        'qué publicación existente sería la menos mala, en pasos cortos; si no, vacío", '
        '"veredicto": "VA, PRUEBA BARATA, ARREGLAR PRIMERO o NO TODAVÍA", '
        '"chequeo": ["una línea por punto del chequeo de ESE propósito, empezando con ✅, ⚠️ o ❌ '
        'y con el dato que lo prueba, máx. 15 palabras"], '
        '"segunda_opcion": "la siguiente mejor publicación (fecha y de qué trata) y por qué quedó '
        'detrás, en 1 frase", '
        '"lo_que_nos_ha_funcionado": "1-2 frases: qué dice nuestra historia (sección 7 y datos) '
        'sobre esta decisión"}\n'
        "SIEMPRE arma la pauta completa con la mejor publicación existente (media_id, o video_id "
        "en TikTok), aunque el veredicto sea ARREGLAR PRIMERO o NO TODAVÍA. El veredicto, el "
        "chequeo y las advertencias son tu recomendación; quien aprueba decide si pauta. Solo "
        "deja media_id y video_id en null si la cuenta no tiene ni una publicación.\n\n"
        f"DATOS:\n{json.dumps(datos, ensure_ascii=False, default=str)}"
    )
    respuesta = preguntar(pregunta, SISTEMA_PAUTA)
    m = re.search(r"\{.*\}", respuesta, re.S)
    if not m:
        raise RuntimeError("Claude no devolvió un plan legible: " + respuesta[:200])
    return json.loads(m.group(0))


def validar_plan(plan, estado):
    """Ajusta el plan a las opciones permitidas. Devuelve (cuenta, candidato, plan) o (None, None, motivo)."""
    cuenta = plan.get("cuenta")
    if cuenta not in CUENTAS_IG:
        return None, None, "Claude propuso una cuenta que no existe."
    c = CUENTAS_IG[cuenta]
    if c["ads"] in CUENTAS_PROHIBIDAS:
        return None, None, "Cuenta prohibida en .env."
    objetivo = plan.get("objetivo") if plan.get("objetivo") in c["objetivos"] else c["objetivos"][0]
    publico = plan.get("publico") if plan.get("publico") in c["publicos"] else next(iter(c["publicos"]))
    producto = plan.get("producto") if plan.get("producto") in PRODUCTOS else ("papel" if c["link"] else None)
    def entero(x):
        return int(re.sub(r"\D", "", str(x)) or 0)
    total = min(IG_OPCIONES_TOTAL, key=lambda v: abs(v - entero(plan.get("total"))))
    dias = min(IG_OPCIONES_DIAS, key=lambda d: abs(d - entero(plan.get("dias"))))
    lista = resumen_posts(cuenta, n=1000)
    posts = {p["media_id"]: p for p in lista}
    post = posts.get(str(plan.get("media_id") or ""))
    if not post and lista:
        # Claude no escogió una válida: se propone la mejor según el ranking, para que siempre
        # se pueda pautar; la persona decide con la recomendación a la vista.
        post = lista[0]
        plan["advertencias"] = ("Escogí la publicación con mejores señales porque Claude no "
                                "dejó una. " + str(plan.get("advertencias") or ""))
    if not post:
        return None, None, "la cuenta no tiene publicaciones en Instagram"
    candidato = {"media_id": post["media_id"], "texto": post["texto"],
                 "alcance": post["alcance_organico"], "veces": 0, "reel": post["tipo"] == "reel",
                 "enlace": ""}
    for p in posts_ig(cuenta, dias=DIAS_PUBLICACIONES).values():
        if p["media_id"] == post["media_id"]:
            candidato["enlace"] = p.get("media_permalink") or ""
    ajustes = {"objetivo": objetivo, "publico": publico, "producto": producto, "total": total,
               "dias": dias}
    ajustes.update({k: str(plan.get(k) or "") for k in ("por_que", "estimado", "medir", "corte",
                                                       "advertencias", "veredicto",
                                                       "lo_que_nos_ha_funcionado",
                                                       "segunda_opcion")})
    ajustes["chequeo"] = [str(x) for x in (plan.get("chequeo") or [])][:9]
    return cuenta, candidato, ajustes


def texto_chequeo(plan):
    """El veredicto '¿va a vender?' con el chequeo de experto y lo que nos ha funcionado."""
    lineas = []
    if plan.get("veredicto"):
        lineas.append(f"\n🎯 <b>¿Va a vender? {html.escape(str(plan['veredicto']))}</b>")
    for punto in plan.get("chequeo") or []:
        lineas.append(html.escape(str(punto), quote=False))
    if plan.get("segunda_opcion"):
        lineas.append(f"\n🥈 <b>Segunda opción:</b> "
                      f"{html.escape(str(plan['segunda_opcion']), quote=False)}")
    if plan.get("lo_que_nos_ha_funcionado"):
        lineas.append(f"\n📚 <b>Nuestra experiencia:</b> "
                      f"{html.escape(str(plan['lo_que_nos_ha_funcionado']), quote=False)}")
    return lineas


def proponer_tt_desde_plan(estado, plan, proposito, destinos, fijo=None):
    """Valida el plan de TikTok contra lo permitido y lo propone con botones. Devuelve un error o None."""
    if plan.get("cuenta") not in (None, "eva"):
        return "TikTok solo está conectado para la cuenta de Eva"
    videos = {v["video_id"]: v for v in videos_tiktok_eva(n=1000)}
    video = videos.get(str(plan.get("video_id")))
    if not video:
        return "El video que escogió Claude no está en el TikTok de Eva"
    if promo_tt_activa(estado):
        return "Ya hay una promoción de TikTok del bot activa (una a la vez)"

    def entero(x):
        return int(re.sub(r"\D", "", str(x)) or 0)
    total = min(TT_OPCIONES_TOTAL, key=lambda v: abs(v - entero(plan.get("total"))))
    dias = min(TT_OPCIONES_DIAS, key=lambda d: abs(d - entero(plan.get("dias"))))
    if total < TT_MINIMO_DIA * dias:
        total = TT_MINIMO_DIA * dias
    if fijo:  # lo decidió la persona en el reparto: se respeta tal cual
        total, dias = fijo["total"], fijo["dias"]
    ajustes = {"objetivo": plan.get("objetivo") if plan.get("objetivo") in TT_OBJETIVOS else "alcance",
               "total": total, "dias": dias, "proposito": proposito,
               "chequeo": [str(x) for x in (plan.get("chequeo") or [])][:9]}
    if fijo:
        ajustes["bloqueado"] = True
    if fijo and fijo.get("modo") == "diario":
        ajustes.update({"modo": "diario", "diario": fijo["diario"]})
    ajustes.update({k: str(plan.get(k) or "") for k in (
        "por_que", "estimado", "medir", "corte", "advertencias", "veredicto",
        "lo_que_nos_ha_funcionado", "segunda_opcion")})
    proponer_tt(estado, {k: video[k] for k in ("video_id", "texto", "vistas", "mediana", "enlace")},
                destinos, plan=ajustes)
    return None


PLAN_DIARIOS = [10000, 20000, 30000, 50000]
PLAN_TOTALES = [50000, 100000, 140000, 200000]
PLAN_DIAS = [3, 5, 7]
IG_MINIMO_DIA = 5000  # aprox.: Meta acepta poco por día, pero con menos casi no entrega
ATAJOS_EVA = {"/seguidores_eva", "/seguidores", "/visibilidad_eva", "/eva_pahubi"}


def nombre_atajo(comando):
    return next((d for c, d in MENU if f"/{c}" == comando), comando)


def total_plan(p):
    return p["diario"] * p["dias"] if p["modo"] == "diario" else p["total"]


def texto_plan(p):
    t = total_plan(p)
    plata = (f"{cop(p['diario'])} por día × {p['dias']} días = <b>{cop(t)}</b>"
             if p["modo"] == "diario" else f"<b>{cop(t)}</b> en {p['dias']} días (~{cop(t / p['dias'])}/día)")
    return "\n".join([
        f"💸 <b>{html.escape(nombre_atajo(p['comando']))}</b>",
        "¿Cuánta plata y por cuántos días?",
        "",
        f"<b>Presupuesto:</b> {plata}",
        "",
        "Escoge con los botones y toca ▶ <b>Ver opciones</b>."
        + (" Te muestro cómo repartirlo entre TikTok e Instagram." if p["comando"] in ATAJOS_EVA else "")])


def teclado_plan(pid, p):
    def marca(texto, elegido):
        return f"• {texto} •" if elegido else texto
    diario = p["modo"] == "diario"
    return {"inline_keyboard": [
        [{"text": marca("Por día", diario), "callback_data": f"pl_m:{pid}:diario"},
         {"text": marca("Total", not diario), "callback_data": f"pl_m:{pid}:total"}],
        ([{"text": marca(f"{cop(v)}/día", v == p["diario"]), "callback_data": f"pl_v:{pid}:{v}"}
          for v in PLAN_DIARIOS] if diario else
         [{"text": marca(cop(v), v == p["total"]), "callback_data": f"pl_v:{pid}:{v}"}
          for v in PLAN_TOTALES]),
        [{"text": marca(f"{d} días", d == p["dias"]), "callback_data": f"pl_n:{pid}:{d}"}
         for d in PLAN_DIAS],
        [{"text": "▶ Ver opciones", "callback_data": f"pl_go:{pid}"},
         {"text": "🤖 Que decida el bot", "callback_data": f"pl_bot:{pid}"}],
    ]}


def iniciar_plan(chat_id, comando, extra, estado):
    pid = str(int(time.time() * 10) % 10**9)
    p = {"comando": comando, "extra": extra, "modo": "diario", "diario": 20000,
         "total": 140000, "dias": 7}
    estado.setdefault("planes", {})[pid] = p
    guardar_estado(estado)
    tg("sendMessage", chat_id=chat_id, text=texto_plan(p), parse_mode="HTML",
       reply_markup=teclado_plan(pid, p))


def opciones_reparto(total, dias, comando):
    """Repartos posibles entre TikTok e Instagram (Eva) que cumplen los mínimos de cada red."""
    M, m = TT_MINIMO_DIA, IG_MINIMO_DIA

    def r(x):
        return int(round(x / 1000) * 1000)
    ops = []
    if total >= 2 * M:  # todo en TikTok
        d = dias if total >= M * dias else total // M
        ops.append({"titulo": "Todo en TikTok",
                    "tt": {"modo": "diario", "diario": r(total / d), "dias": d,
                           "total": r(total / d) * d}})
    if total >= (M + m) * dias:  # las dos, todos los días
        resto = total - M * dias
        ops.append({"titulo": "TikTok e Instagram, todos los días",
                    "tt": {"modo": "diario", "diario": M, "dias": dias, "total": M * dias},
                    "ig": {"modo": "total", "total": r(resto), "dias": dias}})
    else:  # las dos: TikTok menos días, Instagram todos los días con lo que sobra
        vistos = set()
        for k in (dias - 1, dias - 2, round(total / 2 / M)):
            resto = total - k * M
            if k >= 2 and k not in vistos and resto >= m * dias:
                vistos.add(k)
                ops.append({"titulo": f"TikTok {k} días + Instagram {dias} días",
                            "tt": {"modo": "diario", "diario": M, "dias": k, "total": k * M},
                            "ig": {"modo": "total", "total": r(resto), "dias": dias}})
    if total >= m * dias:  # todo en Instagram
        ops.append({"titulo": "Todo en Instagram",
                    "ig": {"modo": "diario", "diario": r(total / dias), "dias": dias,
                           "total": r(total / dias) * dias}})
    # Recomendada: seguidores y visibilidad salen más baratos en TikTok; Eva × Pahubi, repartida.
    preferida = 1 if comando == "/eva_pahubi" and len(ops) > 2 else 0
    for i, o in enumerate(ops):
        o["recomendada"] = i == preferida
    return ops


def linea_opcion(o):
    partes = []
    if o.get("tt"):
        t = o["tt"]
        partes.append(f"TikTok {cop(t['diario'])}/día × {t['dias']} días = {cop(t['total'])}")
    if o.get("ig"):
        i = o["ig"]
        partes.append(f"Instagram {cop(i['total'])} en {i['dias']} días (~{cop(i['total'] / i['dias'])}/día)")
    total = sum(o[x]["total"] for x in ("tt", "ig") if o.get(x))
    return " + ".join(partes) + f" → total {cop(total)}"


def texto_opciones(p):
    t, d = total_plan(p), p["dias"]
    lineas = [f"💸 <b>{html.escape(nombre_atajo(p['comando']))}</b>",
              f"Tu presupuesto: <b>{cop(t)}</b> en {d} días (~{cop(t / d)}/día)", ""]
    ambas = (TT_MINIMO_DIA + IG_MINIMO_DIA) * d
    if t < ambas:
        lineas += [f"❌ <b>Repartir {cop(t / d)} por día entre TikTok e Instagram todos los días "
                   "no se puede:</b> TikTok pide mínimo "
                   f"{cop(TT_MINIMO_DIA)} por día él solo, e Instagram necesita ~{cop(IG_MINIMO_DIA)} "
                   f"por día para entregar. Para las dos todos los días hacen falta "
                   f"{cop(TT_MINIMO_DIA + IG_MINIMO_DIA)}/día ({cop(ambas)} en {d} días).", ""]
    lineas.append("<b>Lo que sí se puede con tu plata:</b>")
    for n, o in enumerate(p["opciones"], 1):
        lineas.append(f"{n}. <b>{o['titulo']}</b>{' ⭐ recomendada' if o['recomendada'] else ''}\n"
                      f"   {linea_opcion(o)}")
    lineas += ["", "ℹ️ Seguidor: ~$130 en TikTok, ~$286 la visita al perfil en IG (nov 2026).",
               "Escoge una opción y armo la(s) pauta(s) con la mejor publicación de cada red."]
    return "\n".join(lineas)


def teclado_opciones(pid, p):
    filas = [[{"text": f"{n}. {o['titulo']}{' ⭐' if o['recomendada'] else ''}",
               "callback_data": f"pl_o:{pid}:{n - 1}"}] for n, o in enumerate(p["opciones"], 1)]
    filas.append([{"text": "↩️ Cambiar la plata o los días", "callback_data": f"pl_back:{pid}"}])
    return {"inline_keyboard": filas}


def publicacion_del_link(texto):
    """Si el texto trae el link de un post de IG (Pahubi o Eva) o de un video de TikTok de Eva,
    devuelve los campos del plan para usar esa publicación. Si no, None."""
    codigo = codigo_ig(texto)
    if codigo:
        for cuenta in CUENTAS_IG:
            for p in posts_ig(cuenta, dias=DIAS_PUBLICACIONES).values():
                if f"/{codigo}" in (p.get("media_permalink") or ""):
                    return {"plataforma": "meta", "cuenta": cuenta, "media_id": p["media_id"],
                            "video_id": None}
    m = re.search(r"tiktok\.com/.*?/video/(\d{10,})", texto or "")
    if m:
        return {"plataforma": "tiktok", "cuenta": "eva", "video_id": m.group(1), "media_id": None}
    return None


def texto_reparto(fijo):
    partes = []
    if fijo.get("tt"):
        t = fijo["tt"]
        partes.append(f"TikTok {cop(t['diario'])}/día × {t['dias']} días" if t.get("modo") == "diario"
                      else f"TikTok {cop(t['total'])} en {t['dias']} días")
    if fijo.get("ig"):
        i = fijo["ig"]
        partes.append(f"Instagram {cop(i['diario'])}/día × {i['dias']} días" if i.get("modo") == "diario"
                      else f"Instagram {cop(i['total'])} en {i['dias']} días")
    return " + ".join(partes)


def armar_con_reparto(estado, plan, proposito, destinos, fijo, avisar):
    """Arma una propuesta por cada red del reparto que escogió la persona, con su presupuesto."""
    objetivo = fijo.get("objetivo")
    if fijo.get("tt"):
        p_tt = {**plan, "plataforma": "tiktok", "cuenta": "eva"}
        p_tt["objetivo"] = objetivo if objetivo in TT_OBJETIVOS else "alcance"
        if not p_tt.get("video_id"):
            try:
                libres = [v for v in videos_tiktok_eva() if not v.get("ya_se_pauto")]
                p_tt["video_id"] = libres[0]["video_id"] if libres else None
            except requests.RequestException:
                pass
        error = (proponer_tt_desde_plan(estado, p_tt, proposito, destinos, fijo["tt"])
                 if p_tt.get("video_id") else "no encontré videos de TikTok de Eva")
        if error:
            avisar(f"⚠️ No pude armar la parte de TikTok: {html.escape(error)}.")
    if fijo.get("ig"):
        cuenta = fijo.get("cuenta") or plan.get("cuenta") or "eva"
        p_ig = {**plan, "plataforma": "meta", "cuenta": cuenta}
        if objetivo in CUENTAS_IG[cuenta]["objetivos"]:
            p_ig["objetivo"] = objetivo
        cuenta, candidato, ajustes = validar_plan(p_ig, estado)
        if not cuenta:
            avisar(f"⚠️ No pude armar la parte de Instagram: {html.escape(ajustes)}.")
            return
        i = fijo["ig"]
        ajustes.update({"total": i["total"], "dias": i["dias"], "proposito": proposito,
                        "bloqueado": True, "objetivo_libre": objetivo is None})
        if i.get("modo") == "diario":
            ajustes.update({"modo": "diario", "diario": i["diario"]})
        ajustes.pop("estimado", None)  # el de Claude era para otro presupuesto; se recalcula
        if promo_ig_activa(estado, cuenta):
            avisar(f"⚠️ {CUENTAS_IG[cuenta]['nombre']} ya tiene una promoción del bot activa; "
                   "esta queda como propuesta, pero no se podrá aprobar hasta que termine.")
        proponer_ig(estado, cuenta, candidato, destinos, plan=ajustes)


def comando_pauta(chat_id, texto, estado, fijo=None):
    """chat_id puede ser un chat o una lista de chats (la propuesta semanal va a todos).
    fijo: reparto y presupuesto que ya escogió la persona (pregunta previa de plata y días)."""
    destinos = [chat_id] if isinstance(chat_id, str) else list(chat_id)

    def avisar(mensaje):
        for d in destinos:
            enviar(d, mensaje)
    proposito = texto.partition(" ")[2].strip() if texto.startswith("/") else texto.strip()
    if len(proposito) < 8:
        avisar("Dime para qué es la pauta. Ejemplos:\n"
                        "/pauta vender papel higiénico en Bogotá con $100 mil\n"
                        "/pauta más seguidores para Eva esta semana\n"
                        "/pauta que conozcan Pahubi en Medellín")
        return
    avisar("Armando la pauta con el manual, los costos reales y las ventas de "
                    "WooCommerce… (1–2 min)")
    if fijo:
        proposito += (f" REPARTO YA DECIDIDO POR LA PERSONA (no lo cambies): {texto_reparto(fijo)}."
                      " Escoge la mejor publicación para cada red del reparto POR SEPARADO: "
                      "media_id de Instagram y/o video_id de TikTok. En cada red, primero las que "
                      "NUNCA se pautaron en ESA red (ya_se_pauto false); no repitas en Instagram "
                      "algo ya pautado en Instagram solo porque en TikTok sirve.")
    plan = pedir_plan(proposito, estado)
    elegida = publicacion_del_link(proposito)
    if elegida:  # la persona escogió la publicación pegando el link: se respeta
        plan.update({k: v for k, v in elegida.items() if v or not fijo})
        if not fijo:  # con reparto hay dos redes: el porqué de Claude ya dice cuál escogiste
            plan["por_que"] = ("La escogiste tú. " + str(plan.get("por_que") or ""))
    if fijo:
        armar_con_reparto(estado, plan, proposito, destinos, fijo, avisar)
        return
    # Siempre se arma una pauta aprobable: el veredicto es recomendación, la decisión es humana.
    if plan.get("plataforma") == "tiktok" and TT_TOKEN:
        if not plan.get("video_id"):
            try:
                libres = [v for v in videos_tiktok_eva() if not v.get("ya_se_pauto")]
                plan["video_id"] = libres[0]["video_id"] if libres else None
            except requests.RequestException:
                pass
        error = (proponer_tt_desde_plan(estado, plan, proposito, destinos)
                 if plan.get("video_id") else "No encontré videos de TikTok de Eva")
        if not error:
            return
        plan["advertencias"] = (f"{error}; te la propongo en Instagram. "
                                f"{plan.get('advertencias') or ''}")
        plan["cuenta"] = "eva"
        if plan.get("objetivo") not in CUENTAS_IG["eva"]["objetivos"]:
            plan["objetivo"] = "seguidores" if "seguidor" in proposito.lower() else "alcance"
    if plan.get("cuenta") not in CUENTAS_IG:
        plan["cuenta"] = "pahubi" if any(p in proposito.lower() for p in PALABRAS_VENTA) else "eva"
    cuenta, candidato, ajustes = validar_plan(plan, estado)
    if not cuenta:
        avisar(f"No pude armar la pauta: {html.escape(ajustes)}. "
                        + html.escape(str(plan.get("texto_si_no_se_puede") or plan.get("por_que") or "")))
        return
    if promo_ig_activa(estado, cuenta):
        avisar(f"⚠️ {CUENTAS_IG[cuenta]['nombre']} ya tiene una promoción del bot activa; "
                        "esta queda como propuesta, pero no se podrá aprobar hasta que termine.")
    ajustes["proposito"] = proposito
    proponer_ig(estado, cuenta, candidato, destinos, plan=ajustes)


# ---------- Vigilancia de TODAS las pautas, avisos de corte, aprendizaje y propuesta semanal ----------
# El bot mira las campañas de Meta (Pahubi y Eva) y TikTok (Eva), hechas por él o a mano.
# - Aviso de corte: cuando una campaña rompe una regla del manual, avisa con ⏸ Pausar.
#   NUNCA pausa solo: la pausa la toca una persona.
# - Aprendizaje: cuando una pauta termina, escribe su resultado real en playbook_pautas.md,
#   que es lo que Claude lee al armar la siguiente.
# - Propuesta semanal: cada lunes propone una pauta para Pahubi y otra para Eva.

CADA_CUANTO_CORTE = 3 * 3600  # revisa cada 3 horas, de 7 a. m. a 9 p. m.
DIA_PROPUESTA = int(ENV.get("DIA_PROPUESTA_SEMANAL", "0"))  # 0 = lunes
HORA_PROPUESTA = int(ENV.get("HORA_PROPUESTA_SEMANAL", "9"))
GA4_PROPIEDAD = ENV.get("GA4_PROPIEDAD", "492755256")
CORTE = {"gasto_minimo": 20000,          # antes de esto no se juzga una campaña
         "visita_web": 400,              # costo máximo por visita a pahubi.com
         "visita_perfil": 500,           # costo máximo por visita al perfil de IG
         "seguidor": 500,                # costo máximo por seguidor (TikTok)
         "sesiones_sin_carrito": 300}    # visitas con una UTM sin ningún carrito ni venta
CUENTAS_VIGILAR = [("meta", "pahubi", CUENTA_PAHUBI), ("meta", "eva", EVA_CUENTA_ADS),
                   ("tiktok", "eva", EVA_TIKTOK_ADS)]
FUENTES_NO_PAUTA = {"(direct)", "(organic)", "(referral)", "(not set)", ""}
SECCION_APRENDIZAJES = "## 7. Aprendizajes automáticos (los escribe el bot)"


def campanas_todas(dias=30):
    """Campañas con datos en los últimos días, agregadas. Clave: 'plataforma:id'."""
    hoy = datetime.now(TZ_BOGOTA).date()
    desde = hoy - timedelta(days=dias - 1)
    campanas = {}
    for plataforma, cuenta, cuenta_ads in CUENTAS_VIGILAR:
        if cuenta_ads in CUENTAS_PROHIBIDAS:
            continue
        if plataforma == "meta":
            filas = windsor_datos("facebook", ["date", "campaign_id", "campaign", "campaign_objective",
                                               "campaign_status", "spend", "link_clicks",
                                               "actions_landing_page_view", "reach"], desde, hoy, cuenta_ads)
        else:
            filas = windsor_datos("tiktok", ["date", "campaign_id", "campaign_name", "campaign_status",
                                             "objective_type", "spend", "clicks", "follows",
                                             "impressions"], desde, hoy, cuenta_ads)
        for f in filas:
            cid = str(f.get("campaign_id") or "")
            if not cid:
                continue
            c = campanas.setdefault(f"{plataforma}:{cid}", {
                "plataforma": plataforma, "cuenta": cuenta, "id": cid,
                "nombre": f.get("campaign") or f.get("campaign_name") or "?",
                "objetivo": f.get("campaign_objective") or f.get("objective_type") or "",
                "estado": "", "fecha_estado": "", "gasto": 0.0, "clics": 0, "visitas_web": 0,
                "alcance": 0, "seguidores": 0, "inicio": None, "ultimo_gasto": None})
            fecha = f.get("date") or ""
            if fecha >= c["fecha_estado"]:
                c["estado"], c["fecha_estado"] = f.get("campaign_status") or "", fecha
            gasto = float(f.get("spend") or 0)
            c["gasto"] += gasto
            c["clics"] += int(f.get("link_clicks") or f.get("clicks") or 0)
            c["visitas_web"] += int(f.get("actions_landing_page_view") or 0)
            c["alcance"] += int(f.get("reach") or f.get("impressions") or 0)
            c["seguidores"] += int(f.get("follows") or 0)
            if gasto > 0:
                c["inicio"] = min(c["inicio"] or fecha, fecha)
                c["ultimo_gasto"] = max(c["ultimo_gasto"] or fecha, fecha)
    return campanas


def campana_activa(c):
    hace_2 = (datetime.now(TZ_BOGOTA).date() - timedelta(days=2)).isoformat()
    return (c["estado"] in ("ACTIVE", "CAMPAIGN_STATUS_ENABLE")
            and bool(c["ultimo_gasto"]) and c["ultimo_gasto"] >= hace_2)


def resultado_campana(c):
    """(qué busca, cantidad, costo por cada uno, límite del manual o None)."""
    if c["plataforma"] == "tiktok":
        if c["objetivo"] == "ENGAGEMENT" or (c["seguidores"] and not c["clics"]):
            tipo, n, limite = "seguidores", c["seguidores"], CORTE["seguidor"]
        elif c["objetivo"] in ("TRAFFIC", "WEB_CONVERSIONS"):
            tipo, n, limite = "visitas a la web", c["clics"], CORTE["visita_web"]
        else:
            return "alcance", c["alcance"], None, None
    elif c["objetivo"] == "OUTCOME_SALES" or (c["visitas_web"] and c["visitas_web"] >= 0.1 * c["clics"]):
        tipo, n, limite = "visitas a la web", c["visitas_web"], CORTE["visita_web"]
    elif c["objetivo"] == "OUTCOME_TRAFFIC" and c["clics"]:
        tipo, n, limite = "visitas al perfil", c["clics"], CORTE["visita_perfil"]
    else:
        return "alcance", c["alcance"], None, None
    return tipo, n, (c["gasto"] / n if n else None), limite


def linea_campana(c):
    tipo, n, costo, _ = resultado_campana(c)
    red = "TikTok" if c["plataforma"] == "tiktok" else "Meta"
    costo_txt = f" · {cop(costo)} c/u" if costo and tipo != "alcance" else ""
    return (f"• <b>{html.escape(c['nombre'])}</b> ({red}, {CUENTAS_IG[c['cuenta']]['nombre']})\n"
            f"  Gasto {cop(c['gasto'])} · {miles(n)} {tipo}{costo_txt}")


def miles(n):
    return f"{n:,.0f}".replace(",", ".")


# Ventas que NO traen UTM de campaña: quien vio la pauta y volvió después escribiendo la página,
# buscando en Google o entrando por la bio de IG cae aquí. Por eso se compara contra lo normal.
ORIGENES_INDIRECTOS = {ORIGENES_WOO["typein"], ORIGENES_WOO["organic"], ORIGENES_WOO["referral"],
                       ORIGENES_WOO["utm"], ORIGENES_WOO["sin_atribucion"]}


def ventas_indirectas(desde, hasta):
    woo = pedidos_woo(desde, hasta) or {}
    return sum(v["pedidos"] for k, v in woo.items() if k in ORIGENES_INDIRECTOS)


def efecto_indirecto(inicio, fin):
    """Ventas sin UTM durante la pauta y 7 días después, contra el promedio de las 8 semanas antes.
    Devuelve (reales, esperadas) o None. Es una señal, no una prueba: otras cosas también mueven
    esas ventas (temporada, Google, clientes que repiten)."""
    try:
        ini = date.fromisoformat(str(inicio))
        hasta = min(date.fromisoformat(str(fin)) + timedelta(days=7), datetime.now(TZ_BOGOTA).date())
        dias = (hasta - ini).days + 1
        base = ventas_indirectas(ini - timedelta(days=56), ini - timedelta(days=1))
        return ventas_indirectas(ini, hasta), base / 56 * dias
    except (requests.RequestException, TypeError, ValueError):
        return None


def texto_indirecto(efecto):
    if not efecto:
        return ""
    reales, esperadas = efecto
    señal = (" ↑ posible efecto de la pauta" if reales >= esperadas * 1.5 and reales - esperadas >= 2
             else "")
    return f"sin UTM: {reales} (lo normal: {esperadas:.1f}){señal}"


def ventas_semanales_por_origen(semanas=12):
    """Para que Claude vea si en semanas con pauta suben las ventas directas o de Google."""
    hoy = datetime.now(TZ_BOGOTA).date()
    lunes = hoy - timedelta(days=hoy.weekday())
    salida = []
    for i in range(semanas, 0, -1):
        ini = lunes - timedelta(weeks=i)
        woo = pedidos_woo(ini, ini + timedelta(days=6)) or {}
        salida.append({"semana": ini.isoformat(),
                       "con_utm_de_campana": sum(v["pedidos"] for k, v in woo.items()
                                                 if k not in ORIGENES_INDIRECTOS),
                       "sin_utm": sum(v["pedidos"] for k, v in woo.items() if k in ORIGENES_INDIRECTOS)})
    return salida


def ventas_de_campana(c):
    """Pedidos pagados en WooCommerce cuya utm_campaign corresponde a esta campaña (por palabras)."""
    try:
        hasta = min(date.fromisoformat(c["ultimo_gasto"]) + timedelta(days=7),
                    datetime.now(TZ_BOGOTA).date())
        woo = pedidos_woo(date.fromisoformat(c["inicio"]), hasta) or {}
    except (requests.RequestException, TypeError, ValueError):
        return None
    nombre = re.sub(r"[^a-z0-9]", "", c["nombre"].lower())
    pedidos = ventas = 0
    for utm, v in woo.items():
        partes = [p for p in re.split(r"[_\-\s]+", utm.lower()) if len(p) >= 3]
        if partes and all(re.sub(r"[^a-z0-9]", "", p) in nombre for p in partes):
            pedidos += v["pedidos"]
            ventas += v["ventas"]
    return pedidos, ventas


def texto_vigilancia(campanas=None):
    campanas = campanas if campanas is not None else campanas_todas()
    activas = [c for c in campanas.values() if campana_activa(c)]
    if not activas:
        return "<b>Pautas activas:</b> ninguna."
    return "<b>Todas las pautas activas (incluye las hechas a mano)</b>\n" + "\n".join(
        linea_campana(c) for c in sorted(activas, key=lambda c: -c["gasto"]))


def destinatarios(cuenta):
    return AUTORIZADOS | CUENTAS_IG[cuenta]["aprobadores"]


def avisar_corte(estado, clave, texto, botones_pausa):
    """Manda el aviso una sola vez por campaña y regla. botones_pausa: [(etiqueta, callback)]."""
    avisos = estado.setdefault("avisos_corte", {})
    if clave in avisos:
        return
    avisos[clave] = time.time()
    guardar_estado(estado)
    filas = [[{"text": f"⏸ Pausar {e}"[:60], "callback_data": cb}] for e, cb in botones_pausa]
    filas.append([{"text": "👍 Dejarla seguir", "callback_data": "corte_s:x"}])
    cuentas = {cb.split(":")[2] for _, cb in botones_pausa} or {"eva"}
    for chat_id in set().union(*(destinatarios(c) for c in cuentas)):
        tg("sendMessage", chat_id=chat_id, text=texto, parse_mode="HTML",
           disable_web_page_preview=True, reply_markup={"inline_keyboard": filas})


def boton_pausa(c):
    return (c["nombre"][:40], f"corte_p:{c['plataforma']}:{c['cuenta']}:{c['id']}")


def revisar_cortes(estado, forzar=False):
    ahora = datetime.now(TZ_BOGOTA)
    if not forzar and (not 7 <= ahora.hour <= 21
                       or time.time() - estado.get("ultimo_corte", 0) < CADA_CUANTO_CORTE):
        return
    estado["ultimo_corte"] = time.time()
    guardar_estado(estado)
    campanas = campanas_todas()
    pie = ("\n\nYo no la pauso: si estás de acuerdo, toca ⏸. Si es de Pahubi o mueve presupuesto, "
           "con el OK de Ivan.")
    # 1. Reglas por campaña: gasto sin resultados, o resultado más caro que el límite del manual.
    for clave, c in campanas.items():
        if not campana_activa(c) or c["gasto"] < CORTE["gasto_minimo"]:
            continue
        tipo, n, costo, limite = resultado_campana(c)
        if tipo == "alcance":
            continue
        if n == 0:
            motivo = f"lleva {cop(c['gasto'])} y 0 {tipo}"
        elif limite and costo > limite:
            motivo = (f"cada una de sus {tipo} sale a {cop(costo)}; el límite del manual es "
                      f"{cop(limite)}")
        else:
            continue
        avisar_corte(estado, f"costo:{clave}",
                     f"✂️ <b>Regla de corte</b>\n{linea_campana(c)}\n\nMotivo: {motivo}.{pie}",
                     [boton_pausa(c)])
    # 2. Regla por UTM (GA4 + WooCommerce): muchas visitas y ni un carrito ni una venta.
    hoy = ahora.date()
    filas = windsor_datos("googleanalytics4", ["campaign", "sessions", "add_to_carts", "transactions"],
                          hoy - timedelta(days=13), hoy, GA4_PROPIEDAD)
    por_utm = {}
    for f in filas:
        nombre = f.get("campaign") or ""
        if nombre in FUENTES_NO_PAUTA:
            continue
        a = por_utm.setdefault(nombre, {"sesiones": 0, "carritos": 0, "compras": 0})
        a["sesiones"] += int(f.get("sessions") or 0)
        a["carritos"] += int(f.get("add_to_carts") or 0)
        a["compras"] += int(f.get("transactions") or 0)
    try:
        woo = pedidos_woo(hoy - timedelta(days=13), hoy) or {}
    except requests.RequestException:
        woo = {}
    web_activas = [c for c in campanas.values() if campana_activa(c)
                   and resultado_campana(c)[0] == "visitas a la web"]
    for utm, a in por_utm.items():
        if (a["sesiones"] >= CORTE["sesiones_sin_carrito"] and not a["carritos"] and not a["compras"]
                and not (woo.get(utm) or {}).get("pedidos")):
            avisar_corte(estado, f"utm:{utm}",
                         f"✂️ <b>Regla de corte: la pauta trae visitas que no compran</b>\n"
                         f"UTM <b>{html.escape(utm)}</b>: {a['sesiones']} visitas a pahubi.com en 14 días, "
                         f"0 carritos y 0 ventas en WooCommerce.\nEl manual dice cortar a las "
                         f"{CORTE['sesiones_sin_carrito']} visitas sin carritos.\n\nCampañas activas que "
                         f"llevan a la web:\n" + ("\n".join(linea_campana(c) for c in web_activas)
                                                  or "(ninguna activa ahora)") + pie,
                         [boton_pausa(c) for c in web_activas])
    # 3. Aprendizaje de las campañas que ya terminaron.
    anotar_terminadas(estado, campanas)


def anotar_aprendizaje(fecha, cuenta, pauta, gasto, resultado, costo, ventas, lectura):
    texto = PLAYBOOK.read_text(encoding="utf-8")
    if SECCION_APRENDIZAJES not in texto:
        texto = (texto.rstrip() + f"\n\n{SECCION_APRENDIZAJES}\n\n"
                 "Cada pauta que termina queda aquí con su resultado real; el bot lo lee al armar "
                 "la siguiente. Se puede corregir o borrar a mano.\n\n"
                 "| Fecha | Cuenta | Pauta | Gasto | Resultado | Costo c/u | Ventas Woo | Lectura |\n"
                 "|---|---|---|---|---|---|---|---|")
    celdas = [fecha, cuenta, pauta, gasto, resultado, costo, ventas, lectura]
    fila = "| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in celdas) + " |"
    PLAYBOOK.write_text(texto.rstrip() + "\n" + fila + "\n", encoding="utf-8")


def lectura_resultado(tipo, costo, limite, ventas=None, efecto=None):
    if tipo == "visitas a la web":
        if ventas:
            return f"vendió ({ventas} pedidos)"
        if efecto and efecto[0] >= efecto[1] * 1.5 and efecto[0] - efecto[1] >= 2:
            return "0 ventas con UTM, pero subieron las ventas sin UTM: posible efecto indirecto, revisar"
        return "no vendió, ni directo ni indirecto: no repetir igual"
    if not costo or not limite:
        return "sin resultado medible"
    if costo <= limite * 0.4:
        return "funcionó: barato, repetir"
    if costo <= limite:
        return "aceptable"
    return "caro: no repetir igual"


def anotar_terminadas(estado, campanas):
    """Escribe en el manual las campañas (a mano o del bot) que dejaron de gastar."""
    anotadas = set(estado.setdefault("aprendidas", []))
    hoy = datetime.now(TZ_BOGOTA).date()
    hace_2 = (hoy - timedelta(days=2)).isoformat()
    inicio_ventana = (hoy - timedelta(days=29)).isoformat()
    for clave, c in campanas.items():
        terminada = c["ultimo_gasto"] and (c["ultimo_gasto"] < hace_2 or not campana_activa(c))
        # Las promos del bot se anotan por conjunto en revisar_promos_ig (comparten campaña).
        # Las que empezaron antes de la ventana de 30 días tienen cifras cortadas: no se anotan.
        if (clave in anotadas or not terminada or c["gasto"] < 10000
                or "_Bot_IG_" in c["nombre"] or c["inicio"] <= inicio_ventana):
            continue
        tipo, n, costo, limite = resultado_campana(c)
        if tipo == "visitas a la web":
            v = ventas_de_campana(c)
            efecto = efecto_indirecto(c["inicio"], c["ultimo_gasto"])
            ventas_txt = (f"{v[0]} pedidos ({cop(v[1])})" if v else "sin dato") + (
                f"; {texto_indirecto(efecto)}" if efecto else "")
            lectura = lectura_resultado(tipo, costo, limite, v[0] if v else None, efecto)
        elif tipo == "alcance":
            costo = c["gasto"] / n * 1000 if n else None
            ventas_txt, lectura = "—", "alcance: no mide seguidores ni ventas"
        else:
            ventas_txt, lectura = "—", lectura_resultado(tipo, costo, limite)
        anotar_aprendizaje(
            f"{c['inicio']} a {c['ultimo_gasto']}", f"{CUENTAS_IG[c['cuenta']]['nombre']} "
            f"({'TikTok' if c['plataforma'] == 'tiktok' else 'Meta'})", c["nombre"], cop(c["gasto"]),
            f"{miles(n)} {'personas alcanzadas' if tipo == 'alcance' else tipo}",
            (f"{cop(costo)} por 1.000" if tipo == "alcance" else cop(costo)) if costo else "—",
            ventas_txt, lectura)
        anotadas.add(clave)
    estado["aprendidas"] = sorted(anotadas)
    guardar_estado(estado)


PROPOSITO_VENDER = (
    "la mejor pauta para vender más en pahubi.com (pedidos pagados en WooCommerce). Si no vale la "
    "pena pautar (no hay contenido que venda o algo de la tienda frena las ventas), dilo y di qué "
    "hacer primero.")
PROPOSITO_SEGUIDORES = (
    "la mejor pauta para ganar seguidores para Eva, en TikTok o Instagram: donde el seguidor "
    "salga más barato con un video que ya demostró que trae gente.")
PROPOSITO_SEGUIDORES_PAHUBI = (
    "la mejor pauta para ganar seguidores en el Instagram de Pahubi (cuenta pahubi, objetivo "
    "seguidores), con una publicación que ya exista y dé ganas de seguir la cuenta.")
PROPOSITO_VISIBILIDAD_EVA = (
    "visibilidad para Eva: que mucha gente vea a Eva (objetivo alcance), en TikTok o Instagram, "
    "donde salgan más personas por cada $1.000 con un video que se entienda sin sonido.")
PROPOSITO_EVA_PAHUBI = (
    "Eva × Pahubi: que el público de Eva conozca Pahubi (cuenta eva, objetivo alcance, en TikTok "
    "o Instagram). Escoge una publicación de Eva que muestre o mencione a Pahubi. NO es una pauta "
    "de ventas: la del plástico trajo ~700 visitas y 0 carritos. Se mide por personas alcanzadas "
    "y por si suben las visitas al perfil de Pahubi. La publicación debe llevar #Publicidad y la "
    "etiqueta de colaboración pagada; si no la lleva, dilo en advertencias. Si ninguna "
    "publicación de Eva muestra a Pahubi, veredicto NO TODAVÍA, pero igual arma la pauta con la "
    "más cercana.")
PROPOSITOS_SEMANALES = [
    "Propuesta semanal: " + PROPOSITO_VENDER,
    "Propuesta semanal: " + PROPOSITO_SEGUIDORES,
]
ATAJOS_PAUTA = {"/vender": PROPOSITO_VENDER, "/seguidores_pahubi": PROPOSITO_SEGUIDORES_PAHUBI,
                "/seguidores_eva": PROPOSITO_SEGUIDORES, "/seguidores": PROPOSITO_SEGUIDORES,
                "/visibilidad_eva": PROPOSITO_VISIBILIDAD_EVA, "/eva_pahubi": PROPOSITO_EVA_PAHUBI}

# Menú de Telegram (botón "Menú"): lo más usado primero.
MENU = [
    ("vender", "💰 Pahubi: pauta para vender en pahubi.com"),
    ("seguidores_pahubi", "📈 Pahubi: pauta para ganar seguidores"),
    ("seguidores_eva", "📈 Eva: pauta para ganar seguidores (TikTok o IG)"),
    ("visibilidad_eva", "👀 Eva: pauta de visibilidad (TikTok o IG)"),
    ("eva_pahubi", "🤝 Eva × Pahubi: que conozcan Pahubi"),
    ("pautas", "Cómo van todas las pautas (y cuáles cortar)"),
    ("hoy", "Lo que va de hoy en Pahubi"),
    ("pahubi", "Métricas de Pahubi (7 días)"),
    ("eva", "Pauta, seguidores y mejores posts de Eva"),
    ("propuestas", "Propuestas de pauta de la semana"),
    ("pauta", "Pauta con propósito libre (escríbelo)"),
    ("promo_eva", "Promocionar el mejor post de Eva"),
    ("promo_pahubi", "Promocionar un post de Pahubi"),
    ("recomendaciones", "Ideas para ampliar el público"),
]


def propuesta_semanal(estado, forzar=False):
    ahora = datetime.now(TZ_BOGOTA)
    semana = ahora.strftime("%G-%V")
    if not forzar and (ahora.weekday() != DIA_PROPUESTA or ahora.hour < HORA_PROPUESTA
                       or estado.get("ultima_propuesta_semanal") == semana):
        return
    estado["ultima_propuesta_semanal"] = semana
    guardar_estado(estado)
    for chat_id in AUTORIZADOS:
        enviar(chat_id, "📅 <b>Propuestas de la semana</b>\n" + texto_vigilancia())
    for proposito in PROPOSITOS_SEMANALES:
        try:
            comando_pauta(sorted(AUTORIZADOS), proposito, estado)
        except Exception as e:  # una propuesta fallida no debe frenar la otra
            for chat_id in AUTORIZADOS:
                enviar(chat_id, f"⚠️ No pude armar una propuesta semanal: {html.escape(str(e)[:200])}")


# ---------- TikTok: Spark Ads con aprobación (API de Marketing de TikTok) ----------
# Queda apagado hasta que TikTok apruebe la app y TIKTOK_ACCESS_TOKEN esté en .env
# (se saca con tiktok_token.py). Se promociona un video que YA está publicado en la cuenta
# de Eva, como Spark Ad, con objetivo Alcance. Nada se crea sin el botón "Aprobar".
# OJO: los nombres de campos siguen la documentación de la API v1.3; la primera promoción
# real confirma que TikTok los acepta.

TT_API = "https://business-api.tiktok.com/open_api/v1.3/"
TT_TOKEN = ENV.get("TIKTOK_ACCESS_TOKEN")
TT_COLOMBIA = "3686110"  # id de ubicación de Colombia en TikTok (GeoNames)
TT_OPCIONES_TOTAL = [60000, 100000, 150000]  # TikTok pide mínimo ~$20.000 por día
TT_OPCIONES_DIAS = [3, 5, 7]
TT_OPCIONES_DIARIO = [20000, 30000, 50000]  # TikTok pide mínimo ~$20.000 por día
TT_MINIMO_DIA = 20000  # TikTok no acepta menos por día en el grupo de anuncios
# Copiados de las campañas hechas a mano que funcionaron en la cuenta de Eva.
TT_OBJETIVOS = {
    "seguidores": {"etiqueta": "Seguidores", "campaign": "ENGAGEMENT",
                   "grupo": {"optimization_goal": "FOLLOWERS", "billing_event": "OCPM"}},
    "alcance": {"etiqueta": "Alcance", "campaign": "REACH",
                "grupo": {"optimization_goal": "REACH", "billing_event": "CPM",
                          "frequency": 3, "frequency_schedule": 5}},
}


def videos_tiktok_eva(dias=DIAS_PUBLICACIONES, n=30):
    """Videos de TikTok de Eva con lo que la gente ya premió gratis (para escoger un Spark Ad)."""
    hoy = datetime.now(TZ_BOGOTA).date()
    videos = {}
    for f in windsor_datos("tiktok_organic", [
            "video_id", "date", "video_caption", "video_views_count", "video_shares",
            "video_likes", "video_new_followers", "video_average_time_watched", "video_share_url"],
            hoy - timedelta(days=dias), hoy, EVA_TIKTOK):
        if f.get("video_id"):
            videos[str(f["video_id"])] = f
    vistas = sorted(v.get("video_views_count") or 0 for v in videos.values())
    mediana = vistas[len(vistas) // 2] if vistas else 0

    def puntaje(v):
        ver = v.get("video_views_count") or 0
        premio = (v.get("video_shares") or 0) * 2 + (v.get("video_new_followers") or 0) * 3
        return (ver / mediana if mediana else 0) + 100 * premio / max(ver, 100)
    pautados = set()
    if TT_TOKEN:  # videos que ya se pautaron: sus vistas incluyen las pagadas
        try:
            anuncios = tiktok_api("ad/get/", {"advertiser_id": EVA_TIKTOK_ADS, "page_size": 100}, "GET")
            pautados = {str(a.get("tiktok_item_id")) for a in anuncios.get("list", [])}
        except (RuntimeError, requests.RequestException):
            pass
    pautados |= pautadas()[1]
    # sin pautar primero; las pautadas quedan detrás (sus vistas incluyen las pagadas)
    lista = sorted(videos.values(), key=lambda v: (str(v["video_id"]) in pautados, -puntaje(v)))[:n]
    return [{"video_id": str(v["video_id"]), "fecha": str(v.get("date") or "")[:10],
             "ya_se_pauto": str(v["video_id"]) in pautados,
             "vistas": int(v.get("video_views_count") or 0),
             "veces_lo_normal": round((v.get("video_views_count") or 0) / mediana, 1) if mediana else None,
             "compartidos": int(v.get("video_shares") or 0),
             "seguidores_que_trajo": int(v.get("video_new_followers") or 0),
             "seg_vista_promedio": v.get("video_average_time_watched"),
             "enlace": v.get("video_share_url") or "", "mediana": int(mediana),
             "texto": " ".join((v.get("video_caption") or "").split())[:160]} for v in lista]


def tiktok_api(ruta, cuerpo=None, metodo="POST"):
    cabeceras = {"Access-Token": TT_TOKEN, "Content-Type": "application/json"}
    if metodo == "GET":
        r = requests.get(TT_API + ruta, headers=cabeceras, timeout=60,
                         params={k: json.dumps(v) if isinstance(v, (list, dict)) else v
                                 for k, v in (cuerpo or {}).items()})
    else:
        r = requests.post(TT_API + ruta, headers=cabeceras, json=cuerpo or {}, timeout=60)
    r.raise_for_status()
    datos = r.json()
    if datos.get("code") != 0:
        raise RuntimeError(f"TikTok: {datos.get('message')} (código {datos.get('code')})")
    return datos.get("data") or {}


def identidad_tiktok_eva(estado):
    """La identidad (cuenta de TikTok de Eva vinculada) que firma los Spark Ads."""
    if estado.get("tt_identidad"):
        return estado["tt_identidad"]
    try:
        lista = tiktok_api("identity/get/", {"advertiser_id": EVA_TIKTOK_ADS}, "GET")
    except RuntimeError:
        # La app no tiene el permiso de "TikTok accounts": se toma la identidad de los anuncios
        # que ya existen (los Spark Ads hechos a mano usan la cuenta de TikTok de Eva).
        anuncios = tiktok_api("ad/get/", {"advertiser_id": EVA_TIKTOK_ADS, "page_size": 50}, "GET")
        lista = {"identity_list": [
            {"identity_id": a.get("identity_id"), "identity_type": a.get("identity_type"),
             "identity_authorized_bc_id": a.get("identity_authorized_bc_id"), "display_name": "Eva"}
            for a in anuncios.get("list", []) if a.get("identity_id")]}
    for i in lista.get("identity_list", []):
        if i.get("identity_type") in ("TT_USER", "BC_AUTH_TT"):
            estado["tt_identidad"] = {k: i.get(k) for k in
                                      ("identity_id", "identity_type", "identity_authorized_bc_id",
                                       "display_name")}
            guardar_estado(estado)
            return estado["tt_identidad"]
    raise RuntimeError("No encontré la cuenta de TikTok de Eva vinculada al anunciante. "
                       "Vincúlala en TikTok Ads Manager → Herramientas → Cuentas de TikTok.")


def promo_tt_activa(estado):
    ahora = time.time()
    return next((p for p in estado.get("tt_promos", [])
                 if p["fin"] > ahora and not p.get("pausada")), None)


def texto_propuesta_tt(p):
    fin = datetime.now(TZ_BOGOTA) + timedelta(days=p["dias"])
    if p.get("objetivo") == "seguidores":
        objetivo, referencia = "Seguidores", "~$130 por seguidor (Zunzuncito, nov 2026)"
    else:
        objetivo, referencia = ("Alcance (máx. 3 veces por persona cada 5 días)",
                                "~$380 por 1.000 personas (Xpressa, nov 2026)")
    lineas = ["🚀 <b>Pauta lista · Eva · TikTok (Spark Ad)</b>"]
    if p.get("enlace"):
        lineas.append(f'🎬 <a href="{html.escape(p["enlace"])}">Video a pautar</a>: '
                      f"«{html.escape(p['texto'][:90])}…»")
    else:
        lineas.append(f"🎬 Video: «{html.escape(p['texto'][:90])}…»")
    lineas.append(f"   {p['vistas']:,} vistas orgánicas".replace(",", ".")
                  + (f" (mediana {p['mediana']:,})".replace(",", ".") if p.get("mediana") else ""))
    if p.get("por_que"):
        lineas.append(f"   <i>Por qué este: {html.escape(corto(p['por_que']), quote=False)}</i>")
    lineas += ["",
               "⚙️ <b>Configuración</b>",
               f"• <b>Objetivo:</b> {objetivo}",
               (f"• <b>Presupuesto:</b> {cop(p['diario'])} por día × {p['dias']} días = {cop(p['total'])} total"
                if p.get("modo") == "diario" and p.get("diario") else
                f"• <b>Presupuesto:</b> {cop(p['total'])} total · ~{cop(p['total'] / p['dias'])}/día"),
               f"• <b>Días:</b> {p['dias']} (desde que apruebes hasta el {fin:%d/%m})",
               f"• <b>Mínimo de TikTok:</b> {cop(TT_MINIMO_DIA)} por día "
               f"(con {p['dias']} días, {cop(TT_MINIMO_DIA * p['dias'])} en total)",
               "• <b>Público:</b> Colombia · todas las edades · hombres y mujeres",
               "• <b>Dónde:</b> solo TikTok, con la cuenta de Eva (Spark Ad)",
               f"📊 <b>Referencia:</b> {referencia}"]
    if p.get("mediana") and p["vistas"] < p["mediana"]:
        lineas.append("⚠️ Este video va por debajo de lo normal; promocionarlo suele salir más caro.")
    lineas += resumen_recomendacion(p)
    if not estado_tt_probado():
        lineas.append("\n🧪 Primera pauta de TikTok creada por el bot: revísala en TikTok Ads "
                      "Manager apenas se cree.")
    lineas.append("\n🔒 Objetivo, plata y días: los que escogiste. Dale ✅ para revisar y confirmar."
                  if p.get("bloqueado") else "\nCambia lo que quieras con los botones y dale ✅.")
    return "\n".join(lineas)


def teclado_propuesta_tt(pid, p):
    def marca(texto, elegido):
        return f"• {texto} •" if elegido else texto
    diario = p.get("modo") == "diario"
    if p.get("bloqueado"):  # plata, días y objetivo ya escogidos antes
        return {"inline_keyboard": [[{"text": "✅ Aprobar", "callback_data": f"tt_ok:{pid}"},
                                     {"text": "❌ Rechazar", "callback_data": f"tt_no:{pid}"}]]}
    return {"inline_keyboard": [
        [{"text": marca("Presupuesto total", not diario), "callback_data": f"tt_m:{pid}:total"},
         {"text": marca("Presupuesto por día", diario), "callback_data": f"tt_m:{pid}:diario"}],
        ([{"text": marca(f"{cop(v)}/día", v == p.get("diario")), "callback_data": f"tt_y:{pid}:{v}"}
          for v in TT_OPCIONES_DIARIO] if diario else
         [{"text": marca(cop(v), v == p["total"]), "callback_data": f"tt_t:{pid}:{v}"}
          for v in sorted({TT_MINIMO_DIA * p["dias"], *[x for x in TT_OPCIONES_TOTAL
                                                      if x >= TT_MINIMO_DIA * p["dias"]]})][:4]),
        [{"text": marca(f"{d} días", d == p["dias"]), "callback_data": f"tt_d:{pid}:{d}"}
         for d in TT_OPCIONES_DIAS],
        [{"text": "✅ Aprobar", "callback_data": f"tt_ok:{pid}"},
         {"text": "❌ Rechazar", "callback_data": f"tt_no:{pid}"}],
    ]}


def estado_tt_probado():
    """True si el bot ya creó al menos una pauta en TikTok (para avisar en la primera)."""
    try:
        return bool(leer_estado().get("tt_promos"))
    except Exception:
        return False


def proponer_tt(estado, video, chat_ids, plan=None):
    """plan: lo que decidió /pauta (objetivo, presupuesto, por qué...). Sin plan, alcance base."""
    pid = video["video_id"][-12:]
    estado.setdefault("tt_vistos", []).append(video["video_id"])
    p = {**video, "texto": video["texto"][:200], "total": TT_OPCIONES_TOTAL[0], "dias": 3,
         "objetivo": "alcance", **(plan or {})}
    estado.setdefault("tt_propuestas", {})[pid] = p
    guardar_estado(estado)
    for chat_id in chat_ids:
        tg("sendMessage", chat_id=chat_id, text=texto_propuesta_tt(p), parse_mode="HTML",
           disable_web_page_preview=False, reply_markup=teclado_propuesta_tt(pid, p))


def aprobar_tt(estado, pid, quien):
    p = estado.get("tt_propuestas", {}).get(pid)
    if not p:
        return "Esa propuesta ya no está vigente."
    if promo_tt_activa(estado):
        return "Ya hay una promoción de TikTok activa. Una a la vez."
    if p["total"] / p["dias"] < 20000:
        return "TikTok pide mínimo $20.000 por día. Sube el presupuesto o baja los días."
    objetivo = p.get("objetivo") if p.get("objetivo") in TT_OBJETIVOS else "alcance"
    obj = TT_OBJETIVOS[objetivo]
    identidad = identidad_tiktok_eva(estado)
    inicio = datetime.now(timezone.utc) + timedelta(minutes=15)
    fin = inicio + timedelta(days=p["dias"])
    # 1. Una campaña por promoción (sin presupuesto propio; va en el grupo), para que el bot
    #    aprenda de cada una por separado al terminar.
    campana = str(tiktok_api("campaign/create/", {
        "advertiser_id": EVA_TIKTOK_ADS,
        "campaign_name": f"EVA_Bot_TT_{obj['etiqueta'].split()[0]}_{inicio.astimezone(TZ_BOGOTA):%Y%m%d}",
        "objective_type": obj["campaign"], "budget_mode": "BUDGET_MODE_INFINITE"})["campaign_id"])
    # 2. Grupo de anuncios APAGADO: Colombia, presupuesto total y fechas. Copia la configuración
    #    de las campañas hechas a mano que funcionaron (Zunzuncito seguidores, Xpressa alcance).
    nombre = f"Eva bot TT · {p['texto'][:30]} · {inicio.astimezone(TZ_BOGOTA):%d-%m}"
    grupo = str(tiktok_api("adgroup/create/", {
        "advertiser_id": EVA_TIKTOK_ADS, "campaign_id": campana, "adgroup_name": nombre,
        "promotion_type": "WEBSITE_OR_DISPLAY",
        "placement_type": "PLACEMENT_TYPE_NORMAL", "placements": ["PLACEMENT_TIKTOK"],
        "location_ids": [TT_COLOMBIA], "gender": "GENDER_UNLIMITED",
        **({"budget_mode": "BUDGET_MODE_DAY", "budget": p["diario"]}
           if p.get("modo") == "diario" and p.get("diario") else
           {"budget_mode": "BUDGET_MODE_TOTAL", "budget": p["total"]}),
        "schedule_type": "SCHEDULE_START_END",
        "schedule_start_time": inicio.strftime("%Y-%m-%d %H:%M:%S"),  # UTC
        "schedule_end_time": fin.strftime("%Y-%m-%d %H:%M:%S"),
        "bid_type": "BID_TYPE_NO_BID", "pacing": "PACING_MODE_SMOOTH",
        "operation_status": "DISABLE", **obj["grupo"]})["adgroup_id"])
    try:
        # 3. Spark Ad con el video ya publicado de Eva.
        creativo = {"ad_name": nombre, "ad_format": "SINGLE_VIDEO",
                    "identity_type": identidad["identity_type"],
                    "identity_id": identidad["identity_id"], "tiktok_item_id": p["video_id"]}
        if identidad.get("identity_authorized_bc_id"):
            creativo["identity_authorized_bc_id"] = identidad["identity_authorized_bc_id"]
        anuncio = tiktok_api("ad/create/", {"advertiser_id": EVA_TIKTOK_ADS, "adgroup_id": grupo,
                                            "creatives": [creativo]})
        # 4. Todo listo: se enciende la campaña (por si se pausó antes) y el grupo.
        tiktok_api("campaign/status/update/", {"advertiser_id": EVA_TIKTOK_ADS,
                                               "campaign_ids": [campana], "operation_status": "ENABLE"})
        tiktok_api("adgroup/status/update/", {"advertiser_id": EVA_TIKTOK_ADS,
                                              "adgroup_ids": [grupo], "operation_status": "ENABLE"})
    except Exception:
        try:
            tiktok_api("adgroup/status/update/", {"advertiser_id": EVA_TIKTOK_ADS,
                                                  "adgroup_ids": [grupo], "operation_status": "DISABLE"})
        except Exception:
            pass
        raise
    estado.setdefault("tt_promos", []).append({
        "campaign_id": campana, "adgroup_id": grupo, "ad_ids": (anuncio.get("ad_ids") or []),
        "video_id": p["video_id"], "texto": p["texto"], "total": p["total"],
        "objetivo": objetivo, "proposito": p.get("proposito"), "inicio": inicio.timestamp(),
        "fin": fin.timestamp(), "aprobo": quien})
    estado["tt_propuestas"].pop(pid, None)
    guardar_estado(estado)
    return (f"✅ TikTok ({obj['etiqueta']}) creada: {cop(p['total'])} en {p['dias']} días, hasta el "
            f"{fin.astimezone(TZ_BOGOTA):%d/%m %H:%M}. TikTok la revisa antes de mostrarla "
            "(suele tardar de minutos a unas horas). Te mando el resultado cada mañana.")


def atender_boton(estado, consulta):
    chat_id = str(consulta["message"]["chat"]["id"])
    quien = str(consulta["from"]["id"])
    tg("answerCallbackQuery", callback_query_id=consulta["id"])
    if quien not in AUTORIZADOS | CUENTAS_IG["pahubi"]["aprobadores"]:
        return
    accion, _, dato = consulta.get("data", "").partition(":")
    mensaje = consulta["message"]["message_id"]
    if accion in ("ig_o", "ig_t", "ig_d", "ig_a", "ig_l", "ig_m", "ig_y", "ig_r"):
        # ajustes de la propuesta de Instagram / Facebook
        pid, _, valor = dato.rpartition(":")
        p = estado.get("ig_propuestas", {}).get(pid)
        if not p:
            enviar(chat_id, "Esa propuesta ya no está vigente.")
            return
        campo = {"ig_o": "objetivo", "ig_t": "total", "ig_d": "dias", "ig_a": "publico",
                 "ig_l": "producto", "ig_m": "modo", "ig_y": "diario", "ig_r": "redes"}[accion]
        p[campo] = int(valor) if campo in ("total", "dias", "diario") else valor
        if p.get("modo") == "diario":  # presupuesto por día: el total sale de día × días
            p.setdefault("diario", IG_OPCIONES_DIARIO[2])
            p["total"] = p["diario"] * p["dias"]
        if campo in ("objetivo", "total", "dias", "publico", "modo", "diario", "redes"):
            p.pop("estimado", None)  # el estimado de Claude ya no aplica; se recalcula con costos
        guardar_estado(estado)
        tg("editMessageText", chat_id=chat_id, message_id=mensaje, text=texto_propuesta_ig(p),
           parse_mode="HTML", disable_web_page_preview=False,
           reply_markup=teclado_propuesta_ig(pid, p))
        return
    if accion in ("corte_p", "corte_s"):  # avisos de corte: la persona decide, el bot solo ejecuta
        tg("editMessageReplyMarkup", chat_id=chat_id, message_id=mensaje,
           reply_markup={"inline_keyboard": []})
        if accion == "corte_s":
            enviar(chat_id, "👍 Listo, la dejo seguir. No te vuelvo a avisar por esta regla.")
            return
        plataforma, cuenta, cid = dato.split(":", 2)
        if quien not in destinatarios(cuenta) or (
                cuenta == "pahubi" and quien not in CUENTAS_IG["pahubi"]["aprobadores"]):
            enviar(chat_id, "No puedes pausar campañas de esta cuenta.")
            return
        if plataforma == "meta":
            accion_meta(cuenta, "pause_campaign", {"campaign_id": cid})
        else:
            windsor_mcp("execute_action", {"connector": "tiktok", "account": EVA_TIKTOK_ADS,
                                           "action": "pause_campaign", "params": {"campaign_id": cid}})
        enviar(chat_id, f"⏸ Campaña pausada (la pausó {html.escape(consulta['from'].get('first_name', quien))}).")
        return
    if accion.startswith("tt_") and quien not in AUTORIZADOS:
        return
    if accion.startswith("pl_"):  # pregunta previa de plata y días, y reparto
        pid, _, valor = dato.partition(":")
        p = estado.get("planes", {}).get(pid)
        if not p:
            enviar(chat_id, "Esa consulta ya no está vigente; vuelve a tocar el botón del menú.")
            return
        if accion in ("pl_m", "pl_v", "pl_n", "pl_back"):
            if accion == "pl_m":
                p["modo"] = valor
            elif accion == "pl_v":
                p["diario" if p["modo"] == "diario" else "total"] = int(valor)
            elif accion == "pl_n":
                p["dias"] = int(valor)
            guardar_estado(estado)
            tg("editMessageText", chat_id=chat_id, message_id=mensaje, text=texto_plan(p),
               parse_mode="HTML", reply_markup=teclado_plan(pid, p))
            return
        base = "/pauta " + ATAJOS_PAUTA[p["comando"]] + (
            f" Indicaciones: {p['extra']}" if p.get("extra") else "")
        if accion == "pl_bot":
            tg("editMessageReplyMarkup", chat_id=chat_id, message_id=mensaje,
               reply_markup={"inline_keyboard": []})
            comando_pauta(chat_id, base, estado)
            return
        t, d = total_plan(p), p["dias"]
        if accion == "pl_go" and p["comando"] in ATAJOS_EVA:
            p["opciones"] = opciones_reparto(t, d, p["comando"])
            guardar_estado(estado)
            if not p["opciones"]:
                enviar(chat_id, f"Con {cop(t)} en {d} días no alcanza para ninguna red. "
                                f"Mínimo: {cop(IG_MINIMO_DIA * d)} en Instagram o "
                                f"{cop(TT_MINIMO_DIA * 2)} en TikTok.")
                return
            tg("editMessageText", chat_id=chat_id, message_id=mensaje, text=texto_opciones(p),
               parse_mode="HTML", reply_markup=teclado_opciones(pid, p))
            return
        objetivo = ("seguidores" if "seguidor" in p["comando"] else
                    "alcance" if p["comando"] in ("/visibilidad_eva", "/eva_pahubi") else None)
        if accion == "pl_go":  # Pahubi: solo Meta, con la plata y los días que puso la persona
            fijo = {"cuenta": "pahubi", "objetivo": objetivo,
                    "ig": ({"modo": "diario", "diario": p["diario"], "dias": d, "total": t}
                           if p["modo"] == "diario" else {"modo": "total", "total": t, "dias": d})}
        else:  # pl_o: una opción de reparto de Eva
            o = p["opciones"][int(valor)]
            fijo = {"cuenta": "eva", "objetivo": objetivo, "tt": o.get("tt"), "ig": o.get("ig")}
        tg("editMessageReplyMarkup", chat_id=chat_id, message_id=mensaje,
           reply_markup={"inline_keyboard": []})
        enviar(chat_id, f"👍 {html.escape(texto_reparto(fijo))}. Escogiendo la mejor publicación…")
        comando_pauta(chat_id, base, estado, fijo=fijo)
        return
    if accion in ("tt_t", "tt_d", "tt_m", "tt_y"):  # ajustes de la propuesta de TikTok
        pid, _, valor = dato.rpartition(":")
        p = estado.get("tt_propuestas", {}).get(pid)
        if not p:
            enviar(chat_id, "Esa propuesta ya no está vigente.")
            return
        campo = {"tt_t": "total", "tt_d": "dias", "tt_m": "modo", "tt_y": "diario"}[accion]
        p[campo] = valor if campo == "modo" else int(valor)
        if p.get("modo") == "diario":  # por día: el total sale de día × días
            p.setdefault("diario", TT_OPCIONES_DIARIO[0])
            p["diario"] = max(p["diario"], TT_MINIMO_DIA)
            p["total"] = p["diario"] * p["dias"]
        elif p["total"] < TT_MINIMO_DIA * p["dias"]:  # total muy bajo para esos días: se sube
            p["total"] = TT_MINIMO_DIA * p["dias"]
            enviar(chat_id, f"ℹ️ TikTok pide mínimo {cop(TT_MINIMO_DIA)} por día: con {p['dias']} "
                            f"días el mínimo es {cop(p['total'])}. Lo ajusté.")
        guardar_estado(estado)
        tg("editMessageText", chat_id=chat_id, message_id=mensaje, text=texto_propuesta_tt(p),
           parse_mode="HTML", disable_web_page_preview=False,
           reply_markup=teclado_propuesta_tt(pid, p))
        return
    if accion in ("ig_ok", "ig_si"):
        p = estado.get("ig_propuestas", {}).get(dato)
        if p and quien not in CUENTAS_IG[p["cuenta"]]["aprobadores"]:
            enviar(chat_id, f"No puedes aprobar promociones de {CUENTAS_IG[p['cuenta']]['nombre']}.")
            return
    if accion in ("eva_p", "eva_d", "eva_a"):  # ajustes: se edita la propuesta en el mismo mensaje
        post_fb, _, valor = dato.rpartition(":")
        p = estado.get("eva_propuestas", {}).get(post_fb)
        if not p:
            enviar(chat_id, "Esa propuesta ya no está vigente.")
            return
        if accion == "eva_p":
            p["presupuesto"] = int(valor)
        elif accion == "eva_d":
            p["dias"] = int(valor)
        else:
            p["publico"] = valor
        guardar_estado(estado)
        tg("editMessageText", chat_id=chat_id, message_id=mensaje, text=texto_propuesta(p),
           parse_mode="HTML", disable_web_page_preview=True,
           reply_markup=teclado_propuesta(post_fb, p))
        return
    # Quitar los botones para que no se pueda aprobar dos veces.
    tg("editMessageReplyMarkup", chat_id=chat_id, message_id=mensaje,
       reply_markup={"inline_keyboard": []})
    if accion == "eva_ok":
        enviar(chat_id, "Creando la promoción en Meta…")
        enviar(chat_id, aprobar_eva(estado, dato, quien))
    elif accion == "eva_no":
        estado.get("eva_propuestas", {}).pop(dato, None)
        guardar_estado(estado)
        enviar(chat_id, "Listo, no se promociona.")
    elif accion == "eva_pausa":
        enviar(chat_id, pausar_eva(estado, dato))
    elif accion == "ig_ok":  # paso 1: resumen de lo que se va a crear, para confirmar del todo
        p = estado.get("ig_propuestas", {}).get(dato)
        if not p:
            enviar(chat_id, "Esa propuesta ya no está vigente.")
            return
        tg("sendMessage", chat_id=chat_id, text=resumen_confirmar_ig(p), parse_mode="HTML",
           disable_web_page_preview=True, reply_markup=teclado_confirmar("ig", dato))
    elif accion == "ig_si":  # paso 2: confirmado, se crea
        tg("editMessageReplyMarkup", chat_id=chat_id, message_id=mensaje,
           reply_markup={"inline_keyboard": []})  # evita que un doble toque cree dos pautas
        enviar(chat_id, "Creando la pauta…")
        enviar(chat_id, aprobar_ig(estado, dato, quien))
    elif accion in ("ig_volver", "tt_volver"):
        tg("deleteMessage", chat_id=chat_id, message_id=mensaje)
        enviar(chat_id, "Listo, no se creó nada. Cambia lo que quieras con los botones de la "
                        "propuesta y vuelve a darle ✅.")
    elif accion == "ig_no":
        estado.get("ig_propuestas", {}).pop(dato, None)
        guardar_estado(estado)
        enviar(chat_id, "Listo, no se promociona.")
    elif accion == "ig_pausa":
        cuenta, _, conjunto = dato.partition(":")
        enviar(chat_id, pausar_ig(estado, cuenta, conjunto))
    elif accion == "tt_ok":  # paso 1: resumen para confirmar del todo
        p = estado.get("tt_propuestas", {}).get(dato)
        if not p:
            enviar(chat_id, "Esa propuesta ya no está vigente.")
            return
        tg("sendMessage", chat_id=chat_id, text=resumen_confirmar_tt(p), parse_mode="HTML",
           disable_web_page_preview=True, reply_markup=teclado_confirmar("tt", dato))
    elif accion == "tt_si":  # paso 2: confirmado, se crea
        tg("editMessageReplyMarkup", chat_id=chat_id, message_id=mensaje,
           reply_markup={"inline_keyboard": []})
        enviar(chat_id, "Creando la pauta en TikTok…")
        enviar(chat_id, aprobar_tt(estado, dato, quien))
    elif accion == "tt_no":
        estado.get("tt_propuestas", {}).pop(dato, None)
        guardar_estado(estado)
        enviar(chat_id, "Listo, no se promociona en TikTok.")
    elif accion == "eva_ttpausa":
        for promo in estado.get("tt_promos", []):
            if dato in (promo.get("campaign_id"), estado.get("tt_campana")):
                promo["pausada"] = True
        guardar_estado(estado)
        windsor_mcp("execute_action", {"connector": "tiktok", "account": EVA_TIKTOK_ADS,
                                       "action": "pause_campaign", "params": {"campaign_id": dato}})
        enviar(chat_id, "⏸ Campaña de TikTok pausada.")


# ---------- Comandos ----------

AYUDA = (
    "<b>Pahubi Métricas</b>\n"
    "<b>Pautas</b> (primero te pregunto plata y días; en Eva te muestro cómo repartirlo entre "
    "TikTok e Instagram; escojo la publicación, la configuro y tú apruebas con ✅):\n"
    "/vender – Pahubi: vender en pahubi.com (puedes agregar: /vender papel con $100 mil)\n"
    "/seguidores_pahubi – Pahubi: ganar seguidores en Instagram\n"
    "/seguidores_eva – Eva: ganar seguidores (TikTok o Instagram)\n"
    "/visibilidad_eva – Eva: que mucha gente la vea (TikTok o Instagram)\n"
    "/eva_pahubi – Eva × Pahubi: que el público de Eva conozca Pahubi\n"
    "/pauta – dime el propósito y te armo la pauta en Meta con botón Aprobar. Ej.:\n"
    "   /pauta vender papel higiénico en Bogotá con $100 mil\n"
    "   /pauta más seguidores para Eva esta semana\n"
    "   (también puedes escribirlo sin el /pauta)\n"
    "/pautas – todas las pautas activas (también las hechas a mano) y revisa las reglas de corte\n"
    "/propuestas – te propongo ya las pautas de la semana (si no, llegan cada lunes)\n"
    "/pahubi – métricas de los últimos 7 días\n"
    "/hoy – lo que va de hoy\n"
    "/recomendaciones – ideas para ampliar el público (tarda ~1 min)\n"
    "/eva – pauta, seguidores y mejores publicaciones de Eva (7 días)\n"
    "/promo_eva – propone promocionar en Instagram el mejor post reciente de Eva\n"
    "/promo_pahubi – lo mismo para Pahubi (lleva a pahubi.com con UTM)\n"
    "   Puedes pegar el link: /promo_pahubi https://www.instagram.com/reel/…\n"
    "Cada día a las {h}:00 te envío el resumen de ayer.\n"
    "Te aviso al momento cuando un pedido se paga, falla o se cancela.\n"
    "Cada día a las 10:00 reviso Eva: si una publicación despegó, te propongo "
    "promocionarla (botón Aprobar/Rechazar)."
)


def atender(chat_id, texto, estado):
    hoy = datetime.now(TZ_BOGOTA).date()
    comando = texto.split()[0].split("@")[0].lower() if texto else ""
    if comando == "/pahubi":
        enviar(chat_id, "Consultando…")
        enviar(chat_id, reporte(hoy - timedelta(days=6), hoy, "Pahubi – últimos 7 días"))
    elif comando == "/hoy":
        enviar(chat_id, reporte(hoy, hoy, "Pahubi – hoy"))
    elif comando == "/recomendaciones":
        enviar(chat_id, "Analizando con Claude, dame un momento…")
        enviar(chat_id, recomendaciones())
    elif comando == "/eva":
        enviar(chat_id, "Consultando…")
        enviar(chat_id, reporte_eva(hoy - timedelta(days=6), hoy, "Eva – últimos 7 días", estado))
    elif comando in ("/eva_promo", "/promo_eva"):
        comando_promo(chat_id, "eva", texto, estado)
        video = mejor_tiktok_eva()
        if video and TT_TOKEN and not promo_tt_activa(estado):
            proponer_tt(estado, video, [chat_id])
        elif video:
            enviar(chat_id, texto_tiktok(video))
    elif comando == "/promo_pahubi":
        comando_promo(chat_id, "pahubi", texto, estado)
    elif comando == "/pautas":
        enviar(chat_id, "Revisando todas las pautas…")
        campanas = campanas_todas()
        enviar(chat_id, texto_vigilancia(campanas))
        revisar_cortes(estado, forzar=True)
    elif comando == "/propuestas":
        enviar(chat_id, "Armando las propuestas de la semana (2–4 min)…")
        propuesta_semanal(estado, forzar=True)
    elif comando in ATAJOS_PAUTA:
        # Primero se pregunta plata y días; lo que escriban después (link, ciudad, producto)
        # se guarda como indicación para cuando se arme la pauta.
        iniciar_plan(chat_id, comando, texto.partition(" ")[2].strip(), estado)
    elif comando == "/pauta" or (texto and not texto.startswith("/") and len(texto.split()) >= 3):
        comando_pauta(chat_id, texto, estado)
    else:
        enviar(chat_id, AYUDA.format(h=HORA_RESUMEN))


def leer_estado():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def resumen_diario(estado):
    ahora = datetime.now(TZ_BOGOTA)
    if ahora.hour < HORA_RESUMEN or estado.get("ultimo_resumen") == ahora.date().isoformat():
        return
    ayer = ahora.date() - timedelta(days=1)
    texto = reporte(ayer, ayer, "Resumen de ayer")
    try:
        texto += "\n\n" + texto_vigilancia()
    except requests.RequestException as e:
        texto += f"\n\n⚠️ No pude revisar todas las pautas: {html.escape(str(e)[:120])}"
    for chat_id in AUTORIZADOS:
        enviar(chat_id, texto)
    estado["ultimo_resumen"] = ahora.date().isoformat()
    guardar_estado(estado)


def guardar_estado(estado):
    STATE_FILE.write_text(json.dumps(estado), encoding="utf-8")


def una_sola_copia():
    """Ocupa un puerto local; si ya está ocupado, otra copia del bot está corriendo.
    Windows libera el puerto solo cuando el proceso termina."""
    candado = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        candado.bind(("127.0.0.1", 47653))
    except OSError:
        print("El bot ya está corriendo en otra ventana. Cierro esta copia.")
        raise SystemExit(1)
    return candado


def main():
    # La consola de Windows no imprime tildes ni emojis; sin esto un print de error tumba el bot.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    candado = una_sola_copia()  # noqa: F841 (se mantiene abierto mientras viva el bot)
    print("Bot iniciado. Ctrl+C para detener.")
    try:
        tg("setMyCommands", commands=[{"command": c, "description": d} for c, d in MENU])
    except requests.RequestException as e:
        print("No pude actualizar el menú:", e)
    estado = leer_estado()
    offset = None
    while True:
        try:
            resumen_diario(estado)
            try:
                revisar_pedidos(estado)
            except (requests.RequestException, ValueError, KeyError) as e:
                print("Error revisando pedidos:", e)
            try:
                revisar_eva(estado)
            except Exception as e:  # Eva no debe tumbar el resto del bot
                print("Error revisando Eva:", e)
            try:
                revisar_cortes(estado)
            except Exception as e:
                print("Error revisando reglas de corte:", e)
            try:
                propuesta_semanal(estado)
            except Exception as e:
                print("Error en la propuesta semanal:", e)
            r = tg("getUpdates", offset=offset, timeout=50)
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if u.get("callback_query"):
                    try:
                        atender_boton(estado, u["callback_query"])
                    except Exception as e:
                        chat = str(u["callback_query"]["message"]["chat"]["id"])
                        enviar(chat, f"⚠️ Error: {html.escape(str(e)[:300])}")
                    continue
                msg = u.get("message") or {}
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if not chat_id:
                    continue
                if chat_id not in AUTORIZADOS:
                    enviar(chat_id, f"No autorizado. Tu ID de Telegram es {chat_id}.")
                    print(f"Mensaje de chat no autorizado: {chat_id}")
                    continue
                try:
                    atender(chat_id, msg.get("text", ""), estado)
                except Exception as e:  # el bot no debe caerse por un comando
                    enviar(chat_id, f"⚠️ Error: {html.escape(str(e)[:300])}")
        except requests.RequestException as e:
            print("Error de red:", e)
            time.sleep(10)


if __name__ == "__main__":
    main()
