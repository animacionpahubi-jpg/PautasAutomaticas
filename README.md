# Pautas Automáticas · Pahubi y Eva

Bot de Telegram (**@metricas_pahubi_bot**) que arma, vigila y mide las pautas de **Pahubi** (ventas en pahubi.com) y de **Eva** (seguidores y alcance) en Facebook, Instagram y TikTok.

> **Para quien retoma el proyecto:** lea primero [TRASPASO.md](TRASPASO.md). Ahí está cómo prenderlo, qué cuentas hay que pasar a su nombre y qué quedó pendiente.

## Qué hace, en una frase

Usted le dice al bot **para qué** quiere la pauta y **cuánta plata y cuántos días**. El bot escoge la mejor publicación que ya existe, configura todo con lo aprendido en las pautas anteriores y se la muestra lista. **Nada se publica sin que una persona toque ✅ y confirme.**

## Lo que se hace desde Telegram

| Botón | Para qué |
|---|---|
| 💰 `/vender` | Pahubi: pauta para vender en pahubi.com (Facebook + Instagram) |
| 📈 `/seguidores_pahubi` | Pahubi: ganar seguidores en Instagram |
| 📈 `/seguidores_eva` | Eva: ganar seguidores (TikTok o Instagram) |
| 👀 `/visibilidad_eva` | Eva: que mucha gente la vea (TikTok o Instagram) |
| 🤝 `/eva_pahubi` | Que el público de Eva conozca Pahubi |
| `/pautas` | Cómo van todas las pautas activas (incluidas las hechas a mano) |
| `/hoy`, `/pahubi`, `/eva` | Métricas del día, de Pahubi (7 días) y de Eva |

**Así funciona una pauta:**
1. Usted toca el botón y escoge la plata (por día o total) y los días.
2. En Eva, el bot muestra cómo repartirla entre TikTok e Instagram, y explica qué no se puede y por qué (por ejemplo, TikTok pide mínimo $20.000 por día).
3. El bot escoge la publicación con más opción. Mira:
   - lo que ya funcionó en pautas anteriores;
   - las publicaciones que la gente compartió y guardó sin pagar;
   - primero las que nunca se han pautado.
4. Muestra una ficha: la publicación, la configuración, lo estimado, su recomendación y cuándo cortarla.
5. **✅ Aprobar → resumen → ✅ Confirmar y crear.** Solo ahí se crea en Meta o TikTok.

**Además, solo:**
- avisa en Telegram cada pedido pagado, fallido o cancelado de la tienda;
- manda un resumen cada mañana;
- **avisa** cuando una pauta rompe una regla de corte (por ejemplo, mucho gasto sin carritos), con el botón ⏸. **Nunca pausa solo:** la pausa la decide una persona;
- cuando una pauta termina, anota su resultado real en el manual ([bot-metricas/playbook_pautas.md](bot-metricas/playbook_pautas.md)), y así la siguiente propuesta aprende de ella.

## Reglas que el bot respeta siempre

- **Las ventas reales se cuentan en WooCommerce**: solo pedidos pagados, atribuidos por UTM. Nunca con las compras del Pixel, que en su momento las inflaba.
- Cuenta de Meta de Pahubi **2071312623652434** (nunca la 1189939789598673). Cuenta de Eva **1805850660019527** (nunca la 1435739040823706).
- Las pautas se hacen sobre publicaciones que ya existen y siempre llevan UTM a una ficha de pahubi.com.
- WhatsApp solo +57 300 5060274 (ventas) y +57 304 3900861 (asesoría).
- Ivan aprueba toda pauta y todo presupuesto de Pahubi.

## Estado al 11 de noviembre de 2026

| Pauta (creada por el bot) | Red | Plata | Hasta |
|---|---|---|---|
| Pahubi ventas: reel "¿Miedo a tapar el inodoro?" | Facebook + Instagram, 6 ciudades | $30.000/día | 18 nov |
| Eva seguidores: oso hormiguero | TikTok | $20.000/día | 16 nov |
| Eva seguidores: oso hormiguero | Instagram | $40.000 total | 18 nov |

## Dónde está cada cosa

| Carpeta o archivo | Qué es |
|---|---|
| [bot-metricas/](bot-metricas/) | El bot: `bot.py`, el manual de pautas y los criterios |
| [bot-metricas/playbook_pautas.md](bot-metricas/playbook_pautas.md) | Manual que el bot sigue y que él mismo amplía con cada pauta terminada |
| [bot-metricas/criterios_venta.md](bot-metricas/criterios_venta.md) | Criterios de experto (resumen de las skills de marketing) para escoger y configurar |
| [TRASPASO.md](TRASPASO.md) | Guía para retomar: instalar, cuentas, operación y pendientes |
| [docs/historial-y-decisiones.md](docs/historial-y-decisiones.md) | Qué se probó, qué funcionó, qué se decidió y por qué |
| [analisis/](analisis/), [anuncios/](anuncios/), [competencia/](competencia/) | Análisis de públicos, auditoría del checkout, propuestas y competencia |
| [CLAUDE.md](CLAUDE.md) y [.claude/](.claude/) | Contexto e instrucciones para trabajar el proyecto con Claude Code |
| [skills/](skills/) | Reglas propias de Pahubi para Claude: cuentas, WhatsApp, Pixel, contactos |
