# Manual de pautas: lo que el bot sigue al armar una pauta con propósito

El bot lee este archivo cada vez que alguien le pide una pauta (`/pauta ...`).
Si aprenden algo nuevo, agréguenlo aquí; no hay que reiniciar el bot.

## 1. Escoger según el propósito

| Propósito | Cuenta | Objetivo del bot | Destino |
|---|---|---|---|
| Vender en pahubi.com | Pahubi | `ventas` (píxel, compra) o `trafico` | Ficha del producto, nunca /tienda/ ni el inicio |
| Seguidores para Eva | Eva | `seguidores` (TikTok, o visitas al perfil de IG) | Perfil de Eva |
| Seguidores para Pahubi | Pahubi | `seguidores` (visitas al perfil de IG) | Perfil @pahubi.colombia |
| Eva × Pahubi (que el público de Eva conozca Pahubi) | Eva | `alcance` (TikTok o IG) | Ninguno; no es pauta de ventas |
| Que mucha gente vea algo (marca, lanzamiento) | La que corresponda | `alcance` | Ninguno |
| Comentarios y "me gusta" en un post | Eva | `interaccion` | El mismo post |

- **Eva no vende.** Su público quiere ver contenido, no comprar. La pauta del plástico (Eva×Pahubi, nov 2026) trajo 179 sesiones con 3 % de interacción y 0 carritos. Si el propósito es vender, se usa la cuenta Pahubi.
- **Para vender:** `ventas` le pide a Meta compradores, y desde el 4 nov 2026 el píxel cuenta bien las compras (9 compras frente a unos 10 pedidos pagados). Aun así, **la venta real se mide en WooCommerce por UTM**, nunca con lo que dice Meta. `trafico` solo trae visitas: úsalo si no hay plata para una prueba de ventas (la de ventas necesita ~$200.000 en 5 días o más para aprender).
- **Para seguidores:** `seguidores` (visitas al perfil) sí trae seguidores. `alcance` no: Xpressa con alcance llegó a 89 mil personas y dejó unos 8 seguidores.

## 2. Qué publicación usar

- Siempre una publicación orgánica que ya exista. El bot no crea contenido nuevo.
- **Eva:** gana la que despegó sola: un animal pequeño o raro de Colombia con una pregunta sorprendente al inicio (oso hormiguero, zunzuncito). Las de películas, IA, Halloween y productos rinden por debajo de lo normal.
- **Pahubi:** el ángulo adulto/hombre ("Hombre Rudo") es el único con ventas reales. Los videos sensoriales, Nube Pañito y Gatoresplandor no vendieron.
- Si ninguna publicación sirve para el propósito, el bot lo dice y propone qué grabar, sin forzar una.

## 3. Público

- **Pahubi:** las 6 ciudades con bodega (Bogotá, Medellín, Cali, Barranquilla, Cartagena y Pasto), 25 a 54 años. Con poca plata, solo Bogotá y la Sabana: allí paga el 88 % de los pedidos, contra el 46 % fuera de Bogotá, porque el envío afuera sorprende ($18.700 a $32.700).
- **Eva:** Colombia, todas las edades. LatAm solo si el contenido no es local.
- Hombres de 18 a 44 años dan los clics más baratos en Meta; las mujeres de 25 a 34 son las más caras.
- **Solo Instagram:** trae mejor tráfico que Facebook. En la E9, el 81 % de los clics cargaron la página en IG, frente al 60 % en Facebook.

## 4. Presupuesto (costos de referencia)

| Qué | Costo |
|---|---|
| Visita a pahubi.com (Hombre Rudo) | ~$40 |
| Visita a pahubi.com (videos sensoriales) | ~$105 |
| Seguidor de Eva en Instagram (oct 2026) | ~$350 |
| Seguidor de Eva en TikTok (nov 2026) | ~$150 |
| Visita al perfil de IG (nov 2026) | ~$300 |
| Visita al perfil de IG (oct 2026) | ~$67 |
| Ticket promedio de un pedido | ~$60.000 |

- Margen por combo: **falta** (Ivan no ha pasado los costos). Sin ese dato no hay un costo máximo por venta, así que hay que decirlo.
- Primero una prueba corta (3 a 5 días). No se sube más del 20 % de una vez.
- Una promoción del bot a la vez por cuenta.

## 5. Cómo se mide y cuándo se corta

- **Pahubi:** pedidos pagados en WooCommerce (processing, completed o delivered) con la UTM de la promo.
  - Corte: si gasta el 50 % sin carritos, o el 100 % sin ventas pagadas, se pausa.
- **Eva, seguidores:** el crecimiento diario de seguidores de la cuenta, porque Windsor no trae los seguidores por anuncio.
  - Corte: si a mitad de presupuesto el costo por seguidor supera $500.
- **Eva, alcance:** costo por cada 1.000 personas.

### Ventas que llegan después, sin UTM (efecto indirecto)

Alguien puede ver la pauta, no comprar, y días después escribir pahubi.com, buscar en Google o entrar por la bio de IG y ahí comprar. Esa venta no trae la UTM de la pauta.

- **Por qué casi no se ve:** quien hace clic dentro de Instagram o TikTok abre la tienda en el navegador de la app. Si después compra desde Chrome, la tienda lo ve como un visitante nuevo.
- **Cómo lo mide el bot:** cuenta las ventas sin UTM de campaña (directo, Google, referidos, bio de IG) durante la pauta y los 7 días siguientes. Las compara con el promedio de las 8 semanas anteriores. Es una señal, no una prueba.
- **Cómo se juzga una pauta de venta:**
  1. Ventas con su UTM.
  2. Si son 0, mirar si las ventas sin UTM subieron claramente: al menos 1,5 veces lo normal y 2 pedidos más.
  3. Si tampoco subieron, la pauta no vendió.
- **Lo visto hasta nov 2026:**
  - E9 (oct 24–31, $222k) y el plástico de Eva (nov 6–10) no movieron las ventas sin UTM: siguieron en 1 a 3 por semana.
  - Las semanas con más ventas directas fueron las de septiembre.
- **Decidido (nov 2026):** no se pregunta "¿cómo nos conociste?" en el pago, porque agrega pasos. Tampoco hay códigos de descuento por pauta, porque Ivan no los aprueba. No proponerlos. Se mide solo con la comparación de ventas sin UTM.

## 6. Reglas que no se rompen

- **Cuentas:** Pahubi 2071312623652434 y Eva 1805850660019527. Nunca las otras.
- **WhatsApp:** solo +57 300 5060274 (ventas) y +57 304 3900861 (asesoría).
- No hay pago contraentrega y no se promete envío gratis.
- **Frases permitidas:** biodegradable, 99 % agua, sin alcohol, INVIMA.
  - "Sin ftalatos/BPA" y "empaque ecológico" solo cuando los certificados estén en `contexto/`.
  - Nunca decir que el plástico causa infertilidad.
- Una pauta de Eva que promueva Pahubi lleva #Publicidad y la etiqueta de colaboración pagada.
- **Aprobaciones:** Ivan aprueba toda pauta de Pahubi y todo presupuesto. El bot solo propone; nada se activa sin el botón ✅.
- **TikTok:** la app de la API se aprobó el 10 nov 2026. El bot crea Spark Ads de Eva (seguidores o alcance) con videos que ya están en su TikTok, siempre con el botón ✅. La primera creación real todavía no se ha probado: revísala en TikTok Ads Manager.

## 7. Aprendizajes automáticos (los escribe el bot)

Cada pauta que termina queda aquí con su resultado real; el bot lo lee al armar la siguiente. Se puede corregir o borrar a mano.

| Fecha | Cuenta | Pauta | Gasto | Resultado | Costo c/u | Ventas Woo | Lectura |
|---|---|---|---|---|---|---|---|
| 2026-10-24 a 2026-10-31 | Pahubi (Meta) | [Estrategia 9] Flushable — Video Sensorial (6 Ciudades) — Tráfico | $222.626 | 1.897 visitas a la web | $117 | 0 pedidos ($0); sin UTM: 5 (lo normal: 7.5) | no vendió, ni directo ni indirecto: no repetir igual |
| 2026-10-31 a 2026-11-05 | Eva (Meta) | EVA_Alcance_Xpressa_IG_Nov26 | $79.990 | 110.281 personas alcanzadas | $725 por 1.000 | — | alcance: no mide seguidores ni ventas |
| 2026-10-31 a 2026-11-05 | Eva (TikTok) | EVA_Alcance_Xpressa_Nov26 | $120.000 | 316.621 personas alcanzadas | $379 por 1.000 | — | alcance: no mide seguidores ni ventas |
