# Traspaso del proyecto Pautas Automáticas

Escrito el 11 de noviembre de 2026 por Andres (sistemas@pahubi.com), que sale de Pahubi el **13 de noviembre de 2026**. Es para la persona que retome el bot y para Ivan.

Si solo va a leer una parte, lea la **sección 1**: hay cuentas que hoy dependen de Andres y que se caen cuando él se vaya.

---

## 1. Urgente antes del 13 de noviembre: cuentas que hay que pasar a nombre de Pahubi

El bot usa varias cuentas. Si alguna está a nombre de Andres y se cierra, esa parte del bot deja de funcionar. Hay que revisar cada una con Andres **antes de que se vaya**.

| # | Cuenta | Para qué la usa el bot | Qué hacer |
|---|---|---|---|
| 1 | **Claude** (el "cerebro") | Escoge la publicación y arma la pauta en /vender, /seguidores_eva, etc. | Hoy usa Claude Code con la suscripción de **sistemas@pahubi.com, que vence alrededor del 14 nov**. **Recomendado:** pasar a la API de Anthropic (pago por uso, sin suscripción de nadie). Ver la sección 1.1. |
| 2 | **Bot de Telegram** @metricas_pahubi_bot | Todo el bot | Lo controla quien lo creó en @BotFather. Si fue Andres, pasarlo: BotFather → /mybots → el bot → *Transfer ownership* a Ivan. |
| 3 | **Windsor.ai** (cuenta animacion.pahubi@gmail.com) | Lee Meta, Instagram, TikTok y GA4, y crea y pausa pautas en Meta | **La prueba gratis termina el 21 nov 2026.** El plan gratis que sigue solo permite 1 fuente y 1 cuenta, y con eso **el bot deja de funcionar**. Ver la sección 1.3. |
| 4 | **WooCommerce: llave de API de solo lectura** | Ventas reales, pedidos y alertas | La llave pertenece a un usuario de WordPress. **Si se borra el usuario de Andres, la llave muere.** Crear una llave nueva de *solo lectura* con un usuario de Pahubi (WooCommerce → Ajustes → Avanzado → API REST) y cambiarla en el .env. |
| 5 | **TikTok for Business Developers**: app "Pahubi Metricas Bot" (ID 7706642148078125077) | Crear Spark Ads de Eva y leer TikTok | Está en la cuenta "pahubi sas" (correo @pahubi.com). Confirmar que Ivan tenga acceso a ese correo. |
| 6 | **Mercado Libre**: app "Pahubi Metricas" (solo lectura) | Leer pedidos de Mercado Libre (todavía no se usa en el bot) | Está en la cuenta PAHUBI SAS. Nada urgente. |
| 7 | **Meta Business** (cuentas de anuncios de Pahubi y Eva) | El bot entra por Windsor, no directo | Ivan es el dueño. Quitar el acceso de Andres si corresponde. |
| 8 | **El archivo `.env`** (en el PC, en `bot-metricas/`) | Guarda todas las llaves | **No está en GitHub, a propósito.** Copiarlo a un lugar seguro de la empresa (no por chat ni correo). Si se pierde, hay que sacar las llaves otra vez (sección 4). |

> Después de cambiar cualquier llave en el .env hay que **reiniciar el bot** (sección 3).

### 1.1 Pasar el "cerebro" a la API de Claude (antes del 14 nov)

El bot ya sabe usar la API: si en el `.env` existe `ANTHROPIC_API_KEY`, la usa en vez de Claude Code.

1. Ivan (o quien maneje los pagos) crea una cuenta en **https://console.anthropic.com** con un correo de la empresa.
2. **Billing:** agregar tarjeta y cargar saldo (por ejemplo USD 10). Conviene poner un límite mensual de gasto (*Limits*), por ejemplo USD 15.
3. **API Keys → Create Key** con el nombre `bot-pautas`. Copiarla una sola vez.
4. En `bot-metricas/.env`, poner `ANTHROPIC_API_KEY=` seguido de la llave, y opcionalmente `CLAUDE_API_MODELO=`.
5. Reiniciar el bot y probar con `/vender` (solo propone, no crea nada).

**Costo estimado** (cada propuesta lee unos 50.000 tokens y escribe unos 2.000):

| Modelo (`CLAUDE_API_MODELO`) | Precio (entrada / salida, por millón de tokens) | Por propuesta | 20–40 propuestas al mes |
|---|---|---|---|
| `claude-opus-5-5` (por defecto, el mejor) | USD 4 / USD 20 | ~USD 0,25–0,35 | **~USD 6–14** |
| `claude-sonnet-5-5` (el que usa hoy Claude Code) | USD 2 / USD 10 | ~USD 0,12–0,18 | **~USD 3–7** |

Las propuestas semanales automáticas (2 cada lunes) entran en esa cuenta.

**Alternativa:** otra persona de Pahubi con suscripción de Claude inicia sesión en Claude Code en el PC (`claude` → `/login`). Así funciona igual que hoy, pero vuelve a depender de la cuenta de una persona.

### 1.2 Darle acceso al bot a Ivan (y a quien siga)

1. La persona le escribe cualquier cosa a **@metricas_pahubi_bot** en Telegram. El bot le contesta *"No autorizado. Tu ID de Telegram es …"*.
2. En `bot-metricas/.env`, agregar ese número a `ALLOWED_CHAT_IDS`, separado por coma de los demás.
3. Para que **pueda aprobar pautas de Pahubi**, agregarlo también a `PAHUBI_APROBADORES`.
4. Reiniciar el bot.
5. **Control total del bot:** en @BotFather → /mybots → @metricas_pahubi_bot → *Transfer ownership*, pasárselo a Ivan. Así él puede cambiar el token si algún día hace falta.
6. Cuando Andres se vaya: quitar su ID de `ALLOWED_CHAT_IDS` y de `PAHUBI_APROBADORES`.

### 1.3 Windsor después del 21 de noviembre

| Plan | Precio | ¿Le sirve al bot? |
|---|---|---|
| Free (después de la prueba) | USD 0 | **No.** Solo 1 fuente y 1 cuenta. El bot necesita Meta Ads (Pahubi y Eva), Instagram (Pahubi y Eva), TikTok orgánico de Eva y GA4. |
| **Basic** | **USD 23/mes** (USD 19/mes si se paga el año) | **Sí, con un ajuste:** 3 fuentes y 75 cuentas, 10 años de historia, MCP y acciones incluidas. Se escogen **Facebook Ads, Instagram y TikTok orgánico**. GA4 sale, y lo de TikTok Ads ya lo lee el bot directo por su API. Antes hay que hacer un pequeño cambio en el bot: la regla de "visitas sin carritos" usa GA4 y se puede cambiar por las visitas que reporta Meta. |
| Standard | USD 118/mes | Sí, sin cambios (7 fuentes). Es caro para este uso. |

Bonus del plan pago: se acaban dos límites de la prueba, el de "solo 30 días de historia" y probablemente el de "vistas congeladas" de Instagram.

**A futuro (USD 0):** conectar el bot directo a la API de Meta, como ya se hizo con TikTok. Ivan tendría que crear una app de Meta y un "usuario del sistema" en Business Manager. Es más trabajo de programación, pero elimina Windsor.

---

## 2. Cómo funciona por dentro

```
Telegram (usted)
   │  botones y comandos
   ▼
bot-metricas/bot.py   ← corre en el PC de la oficina, una sola copia
   ├─ Claude Code (claude -p)  → escoge la publicación y arma la pauta
   │      lee: playbook_pautas.md + criterios_venta.md + datos reales
   ├─ Windsor.ai (API + MCP)   → lee Meta/IG/TikTok/GA4; crea y pausa pautas en Meta
   ├─ API de TikTok            → crea Spark Ads de Eva; lee y pausa
   ├─ API de WooCommerce       → pedidos pagados (la venta real), alertas de pedidos
   └─ estado.json              → memoria del bot (propuestas, pautas creadas). No se sube.
```

**Archivos importantes en `bot-metricas/`:**

| Archivo | Qué es | ¿Se puede editar a mano? |
|---|---|---|
| `bot.py` | Todo el bot (~3.000 líneas de Python) | Sí, con cuidado. Hay que reiniciar después. |
| `playbook_pautas.md` | Manual de pautas. El bot lo lee en cada propuesta y **escribe solo la sección 7** cuando termina una pauta. | **Sí**, sin reiniciar. Es la forma más fácil de enseñarle algo al bot. |
| `criterios_venta.md` | Criterios de experto para escoger publicación y configurar (resumen de las skills de marketing) | **Sí**, sin reiniciar. |
| `publicaciones_pautadas.json` | Publicaciones que ya se pautaron, para no repetirlas | **Sí**: agregar el código del link de IG (lo que va después de `/reel/`) o el id del video de TikTok. |
| `.env` | Llaves. **Nunca a GitHub.** | Sí. Hay que reiniciar después. |
| `iniciar.bat` | Prende el bot (doble clic) | — |
| `tiktok_token.py` | Saca la llave de TikTok (se usa una vez, o cuando la llave vence) | — |
| `mercadolibre_token.py` | Conecta Mercado Libre (una vez) | — |
| `woo_lectura.py` | Consultas de solo lectura a WooCommerce para auditorías | — |

**Reglas de diseño que no hay que romper:**
- El bot **nunca pausa solo** ni gasta sin que una persona toque ✅ **y** "Confirmar y crear".
- La venta se mide en WooCommerce por la UTM de cada pauta, nunca con el Pixel.
- Siempre se pauta una publicación que ya existe (así los likes quedan en la publicación real).
- Solo puede correr **una copia** del bot. Si hay dos, los mensajes salen dobles. El bot lo impide con un candado interno.

---

## 3. Prenderlo, apagarlo y reiniciarlo

**En el PC de la oficina (donde está hoy):**
- **Prender:** doble clic en `bot-metricas/iniciar.bat`. Se abre una ventana negra: **déjela abierta, no la cierre**.
- **Apagar:** cerrar esa ventana.
- **Reiniciar** (después de cambiar el .env o `bot.py`): cerrar la ventana y abrir `iniciar.bat` otra vez.
- **Saber si está prendido:** en Telegram, mandar `/hoy`. Si responde, está prendido.
- ⚠️ **Solo funciona mientras el PC esté encendido y con internet.** Si el PC se reinicia, hay que volver a abrir `iniciar.bat` (ver la sección 7 para que arranque solo o para tenerlo 24/7).

**En un PC nuevo, desde cero:**
1. Instalar **Python 3.11 o más nuevo** (python.org; marcar "Add to PATH").
2. Instalar **Node.js** (nodejs.org) y luego Claude Code: `npm install -g @anthropic-ai/claude-code`. Abrir una terminal, escribir `claude` e iniciar sesión con la cuenta de Pahubi.
3. Bajar este repositorio (`git clone ...`).
4. En `bot-metricas/`: `pip install -r requirements.txt`.
5. Copiar `.env.example` como `.env` y llenar las llaves (o traer el `.env` guardado).
6. Abrir `iniciar.bat`. Si dice que no encuentra Python, editar la línea `set "PY=..."` con la ruta de Python de ese PC.
7. En Telegram, mandar `/hoy` para probar.

---

## 4. De dónde sale cada llave del .env

| Variable | Dónde se saca |
|---|---|
| `TELEGRAM_TOKEN` | Telegram → @BotFather → /mybots → @metricas_pahubi_bot → API Token |
| `ALLOWED_CHAT_IDS` | IDs de Telegram de quienes usan el bot. Para saber el suyo: escribirle a @userinfobot |
| `PAHUBI_APROBADORES` | IDs que pueden aprobar pautas de Pahubi (Ivan). Si se deja vacío, cualquiera de los autorizados |
| `WINDSOR_API_KEY` | windsor.ai → cuenta → API key |
| `ANTHROPIC_API_KEY` | Opcional. console.anthropic.com → API Keys. Si está, el bot usa la API en vez de Claude Code |
| `WOO_KEY`, `WOO_SECRET` | pahubi.com/wp-admin → WooCommerce → Ajustes → Avanzado → API REST → Agregar clave, permiso **Lectura** |
| `TIKTOK_SECRET` | business-api.tiktok.com/portal → My Apps → Pahubi Metricas Bot → Secret |
| `TIKTOK_ACCESS_TOKEN` | Abrir el "Advertiser authorization URL" de la app, autorizar la cuenta **Eva Solarte_adv**, copiar el `auth_code` de la dirección a la que lo manda, y correr `python tiktok_token.py EL_CODIGO` |
| `ML_*` | Ver las instrucciones al inicio de `mercadolibre_token.py` |

---

## 5. Operación del día a día

**Cada mañana** el bot manda el resumen: ventas de ayer, pautas activas y cómo van.

**Para pautar:** botón del menú → plata y días → (en Eva) escoger reparto → revisar la ficha → ✅ → revisar el resumen → **Confirmar y crear**.
- Para pautar **una publicación específica**, pegar el link después del comando. Ejemplo: `/seguidores_eva https://www.instagram.com/reel/DfckgWaD3m3/`.
- Pahubi: **con el OK de Ivan.**

**Cuando llega un aviso de corte** (⚠️ con botón ⏸): leer el motivo y decidir. ⏸ pausa la campaña en Meta o TikTok. "Dejarla seguir" no hace nada y no vuelve a avisar por esa regla.

**Después de crear una pauta,** conviene mirarla en Ads Manager:
- Meta: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2071312623652434 (Pahubi) o `act=1805850660019527` (Eva).
- Al entrar a editar un anuncio, Meta crea un borrador. **No darle "Publicar".** Dar "Cerrar" y, si queda "Revisar y publicar (1)" con solo ese anuncio, "Descartar borradores".

**Qué mirar para saber si una pauta sirvió:**
- **Pahubi:** pedidos **pagados** en WooCommerce con la UTM de la pauta. El bot los cruza solo.
- **Eva, seguidores:** costo por seguidor. Referencia: TikTok ~$130, Instagram ~$286 la visita al perfil. Se corta si pasa de $500.
- **Alcance:** costo por cada 1.000 personas. TikTok ~$380, Instagram ~$725.

---

## 6. Problemas conocidos y cómo se resuelven

| Problema | Por qué pasa | Qué hacer |
|---|---|---|
| El bot no responde | El PC se reinició o se cerró la ventana | Abrir `iniciar.bat` |
| Mensajes repetidos | Hay dos copias del bot | Cerrar todas las ventanas negras del bot y abrir solo una |
| El bot no "ve" que un post nuevo despegó | Windsor (plan de prueba) congela las vistas de cada post en las del día que lo leyó por primera vez | Pegar el link del post después del comando: el bot lo usa sin discutir |
| "TikTok pide mínimo $20.000 por día" | Regla de TikTok | El bot ya no deja escoger menos. Para repartir entre TikTok e Instagram todos los días hacen falta $25.000/día |
| Windsor responde "confirmation_token" | Windsor pide confirmar lo que gasta plata | Ya está resuelto en el bot: confirma solo después del ✅ humano |
| La llave de TikTok deja de funcionar | Puede vencer o revocarse | Volver a correr `tiktok_token.py` (sección 4) |
| El bot dice "Claude Code falló" | Claude Code no tiene sesión iniciada o se acabó el cupo | `claude` → `/login`, o poner `ANTHROPIC_API_KEY` |
| La app de TikTok no tiene el permiso "TikTok accounts" | Se quitó para que aprobaran la app | El bot saca la identidad de Eva de los anuncios existentes. Si un día falla, agregar ese permiso en la app y reenviarla a revisión |

---

## 7. Lo que quedó pendiente (en orden de importancia)

1. **Las cuentas de la sección 1.** Antes del 13 de noviembre.
2. **Tenerlo prendido 24/7 sin depender del PC.** Opciones evaluadas:
   - **Lo más simple:** que el PC lo arranque solo al encender (tarea programada de Windows). Gratis, 10 minutos.
   - **Cloudflare Workers:** reescribir el bot en el formato de Workers. Todo cabe en el plan gratis menos "el cerebro", que tendría que usar Claude por API (~USD 3–6 al mes) o pedirle al PC que piense. Antes hay que probar que WooCommerce deje entrar desde Cloudflare (Hostinger ya bloqueó a Windsor por IP).
   - **Un servidor:** Oracle Cloud gratis (pide tarjeta para verificar) o uno de ~USD 5 al mes, con Claude Code instalado allá.
3. **Resultados de las 3 pautas activas** (cierran el 16 y el 18 de noviembre). El bot las anota solo en el manual. Comparar:
   - Pahubi: ¿hubo ventas pagadas con la UTM `bot_ig_pahubi_ventas_20261111_83196`?
   - Eva: ¿el oso hormiguero repetido en Instagram rindió igual que la primera vez? ¿cuánto costó el seguidor en TikTok frente a Instagram?
4. **Costos por combo** (los tiene Ivan). Sin eso no se sabe cuánto se puede pagar por venta. El bot lo marca como "MISSING".
5. **Hombre Rudo:** es el único ángulo con ventas reales en Pahubi, pero no aparece en el Instagram de Pahubi (puede estar solo en Facebook). Buscar el link en Ads Manager → [Estrategia 3] y pautarlo pegando el link.
6. **Mercado Libre:** reputación en rojo por despachos tardíos y 0 ventas desde el 26 de septiembre. Arreglar los despachos antes de abrir más marketplaces (ver `analisis/propuesta-marketplaces-2026-11-05.html`).
7. **Checkout:** cerca de 4 de cada 10 clientes que intentan comprar no terminan de pagar (tarjeta rechazada, o envío caro fuera de las 6 ciudades). Ver `analisis/auditoria-checkout-2026-11-03.md`.
8. Ideas para el bot que no se alcanzaron:
   - avisos de pedidos de Mercado Libre;
   - botón para cambiar la publicación dentro de la ficha;
   - botón de edad.

---

## 8. Trabajar el proyecto con Claude Code

Abrir una terminal en la carpeta del proyecto y escribir `claude`. Claude lee [CLAUDE.md](CLAUDE.md) con las reglas y el contexto.

**Lo que Claude "sabe" de la empresa no está guardado en la cuenta de Claude.** Está en archivos:
- **En este repositorio:** `CLAUDE.md`, `TRASPASO.md`, `docs/historial-y-decisiones.md`, `.claude/product-marketing.md`, `.claude/eva-marketing.md`, el manual y los criterios del bot, y los análisis. Cualquiera que abra Claude Code en esta carpeta, con cualquier cuenta, arranca con todo eso.
- **La "memoria" de Claude Code** (notas detalladas de cada tema) **solo está en el PC de la oficina**, en `C:\Users\PC\.claude\projects\c--Users-PC-Desktop-Trabajo-Pahubi-Pautas-Pahubi\memory\`. No se subió a GitHub porque el repositorio es público. Pertenece al usuario de Windows y a la carpeta, no a la cuenta de Claude: quien use Claude Code **en ese PC y en esta carpeta** la tiene disponible aunque inicie sesión con otra cuenta. Si se trabaja desde otro PC, copiar esa carpeta al mismo lugar.
- La conversación larga con Andres no se traspasa. Todo lo importante quedó en los archivos de arriba.

- Las skills de marketing (ads, ad-creative, cro, social, competitors…) **no se suben** porque son de terceros. Para reinstalarlas, usar `skills-lock.json` o pedirle a Claude que las instale. El bot **no las necesita para funcionar**: su resumen ya está en `bot-metricas/criterios_venta.md`.
- Las reglas propias de Pahubi están en `skills/` (cuentas, WhatsApp, Pixel, contactos). Ver `skills/LEEME-INSTALAR.md`.
- El agente `.claude/agents/auditor-woocommerce.md` audita la tienda en modo solo lectura.
- Siempre: el agente **lee, compara, redacta y recomienda**. Publicar, pausar o cambiar presupuestos, solo con aprobación de Ivan.
