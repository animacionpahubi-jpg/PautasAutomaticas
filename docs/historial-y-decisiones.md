# Historial y decisiones (oct–nov 2026)

Qué se probó, qué funcionó y qué se decidió, para no repetir errores. Las cifras son las reales de cada fecha.

## Pautas de Pahubi (ventas)

| Pauta | Ángulo | Gasto | Resultado real (WooCommerce) | Lectura |
|---|---|---|---|---|
| E3 "Hombre Rudo" | Adulto/hombre | $363.431 | 8.969 visitas (~$40 c/u), **4 pedidos pagados** ($208.662) | El único ángulo con ventas reales |
| E4 Flushable / Raquel | Ventas, Bogotá | — | 3 pedidos | Objetivo Ventas: impresiones muy caras |
| E7 + E9 "Video sensorial" | Sensorial, 6 ciudades | $474.000 | **0 pedidos**; 1.985 sesiones, 0,8 % de carrito | No repetir igual |
| Nube Pañito, Gatoresplandor | Varios | — | 0 pedidos | No vendieron |
| **Bot · reel "¿Miedo a tapar el inodoro?"** (11 nov) | Objeción del inodoro, Ventas, FB+IG, 6 ciudades | $30.000/día × 7 | En curso | Primera pauta creada por el bot |

Aprendizajes:
- **Medir solo con WooCommerce.** El Pixel llegó a inflar las compras unas 30 veces. Se corrigió el 4 de noviembre (snippets WPCode 3979 y 3916), y aun así la decisión se toma con WooCommerce.
- **Ventas que llegan después, sin UTM** (vieron la pauta y compraron días después entrando directo o desde Google). El bot las compara con el promedio de 8 semanas. Ni la E9 ni la pauta del plástico subieron esas ventas.
- **Dónde se paga:** en Bogotá y la Sabana paga casi todo el que intenta comprar. Fuera de las 6 ciudades con bodega, el envío ($18.700–$32.700) espanta.
- **Instagram trae mejor tráfico que Facebook:** en la E9, el 81 % de los clics cargaron la página en IG, contra el 60 % en FB.
- **Decidido:** no se pregunta "¿cómo nos conociste?" en el pago (agrega pasos) y no hay códigos de descuento por pauta (Ivan no los aprueba).

## Pautas de Eva (seguidores y alcance)

| Pauta | Red | Gasto | Resultado | Lectura |
|---|---|---|---|---|
| Xpressa (colaboración pagada) | TikTok | $120.000 | 316.621 personas (~$379 por cada 1.000) | El alcance no trae seguidores |
| Xpressa | Instagram | $79.990 | 110.281 personas (~$725 por cada 1.000) | TikTok rinde el doble en alcance |
| Zunzuncito, seguidores | TikTok | $72.952 | 557 seguidores (~$131 c/u) | **La forma más barata de ganar seguidores** |
| Zunzuncito, seguidores | Instagram | $35.823 | ~240 seguidores (~$150 c/u) | Bien |
| Plástico Eva × Pahubi, tráfico | TikTok + IG | $95.711 | ~713 visitas a pahubi.com, **0 carritos, 0 ventas** | **El público de Eva no compra.** Eva × Pahubi se hace como alcance |
| **Bot · oso hormiguero, seguidores** (11 nov) | TikTok $20k/día × 5 días + IG $40k | — | En curso | Primeras pautas de TikTok creadas por la API |

Aprendizajes:
- **Lo que despega en Eva:** un animal pequeño o raro con una pregunta al inicio (tití pigmeo, oso hormiguero, zunzuncito, colugo). Películas, IA, Halloween y productos rinden por debajo de lo normal.
- **Las publicaciones ya pautadas tienen las vistas infladas** por la pauta. El bot prefiere las que nunca se pautaron (`bot-metricas/publicaciones_pautadas.json`).
- La pauta de Eva que promueve Pahubi lleva #Publicidad y la etiqueta de colaboración pagada. Nunca decir que el plástico causa infertilidad. "Sin ftalatos/BPA" solo cuando los certificados estén en `contexto/`.

## Tienda y checkout

- Auditoría del 3 de noviembre (`analisis/auditoria-checkout-2026-11-03.md`): en 60 días, solo el 46 % de los pedidos creados terminaron pagados. Wompi es el único medio de pago, y la contraentrega está desactivada (activarla es decisión de Ivan).
- Arreglos ya hechos:
  - correo de recordatorio de pago a la 1 h y a las 20 h;
  - inventario retenido 24 h;
  - recompra por correo a los 30 días;
  - textos de envío ("+ envío $12.000 en ciudades principales");
  - zona "Bogotá Alrededores y Sabana".
- 11 de noviembre: de 7 clientes que intentaron comprar en 14 días, pagaron 4. Los que no pagaron: tarjeta rechazada dos veces (Pasto) y dos que no entraron a pagar con envío de $18.695 (Pereira e Ibagué).
- Pendiente: reactivar el webhook de Qubit (WhatsApp de pedidos) con un token nuevo. El de ahora va en texto plano dentro de la URL.

## Otros canales

- **Mercado Libre:** Pahubi vende ahí desde junio (34 pedidos, ~$2,39 M). **0 ventas desde el 26 de septiembre**, con la reputación en rojo por despachos tardíos. Primero hay que arreglar los despachos.
- **Propuesta de marketplaces** (`analisis/propuesta-marketplaces-2026-11-05.html`): Mercado Libre primero, luego Éxito. Sin integrador por ahora. Pendiente de Ivan.
- **Plan de 30–50 ventas al día** (`analisis/plan-30-50-diarias.html`): escalera de metas 3 → 10 → 30 → 50 al día, repartida por canales. Hace falta una persona comercial para droguerías y mayoristas.
- **Competencia** (`competencia/swipe-file.md`): Pequeñín empuja el ángulo adulto/gimnasio y manda a Rappi; Familia empuja kits, envío gratis desde $150k y contraentrega.

## Decisiones sobre el bot

- **26 oct:** bot en el PC de la oficina con Claude Code (no se paga la API). WooCommerce se lee directo porque Windsor está bloqueado por IP.
- **7 nov:** `/pauta` con propósito. Claude lee el manual y los datos y propone. El bot valida contra listas permitidas.
- **10 nov:** el bot vigila **todas** las pautas (también las hechas a mano), **avisa** el corte pero **nunca pausa solo**, aprende de cada pauta terminada y propone cada lunes.
- **10–11 nov:**
  - botones por propósito;
  - criterios de experto para cualquier propósito;
  - siempre arma una pauta aprobable (la recomendación es solo un aviso);
  - ficha con la configuración primero;
  - presupuesto por día o total, y Facebook + Instagram;
  - confirmación en dos pasos;
  - primero pregunta la plata y los días, y en Eva propone repartos entre TikTok e Instagram que cumplan los mínimos.
- **10 nov:** la app de TikTok Marketing API se aprobó al tercer intento. El perfil de desarrollador quedó como "Direct Advertiser" con correo @pahubi.com, y la app con permisos solo de anuncios y reportes.
- **11 nov:** se crearon las primeras pautas reales desde el bot (Pahubi en Meta, Eva en TikTok e IG).
