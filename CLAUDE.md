# Pautas Pahubi: contexto del proyecto

Responder siempre en español (Colombia), con honestidad y sin rodeos. Hasta el 13 nov 2026 el usuario fue Andres (sistemas@pahubi.com), de Pahubi SAS. Desde entonces lo retoma otra persona: **leer primero `TRASPASO.md`** (cómo prender el bot, cuentas, pendientes) y `docs/historial-y-decisiones.md` (qué se probó y qué se decidió).

## Personas
- **Ivan Cordoba:** dueño. Aprueba cualquier cambio en producción, en presupuestos y en anuncios.
- **Jhoana:** administración.
- **Daniel:** diseño.

## Marcas y dónde está su contexto
- **Pahubi:** pañitos y papel higiénico húmedo biodegradable. Objetivo: **ventas** en pahubi.com. Contexto: `.claude/product-marketing.md`.
- **Eva (eva_eco_d):** contenido de divulgación ambiental. Objetivo: **alcance y seguidores**. Contexto: `.claude/eva-marketing.md`.
- Análisis de públicos y anuncios: `analisis/`. Competencia: `competencia/swipe-file.md`. Textos de anuncios: `anuncios/`.

## Reglas que no se rompen
- **Cuenta de Meta de Pahubi:** act 2071312623652434. Nunca usar la 1189939789598673.
- **Cuenta de Meta de Eva:** 1805850660019527 ("Eva Daferu"). Nunca usar la 1435739040823706.
- **WhatsApp:** solo +57 300 5060274 (ventas) y +57 304 3900861 (asesoría). Nunca 312 6062630 ni 300 5060272.
- **Anuncios:** se hacen sobre publicaciones orgánicas existentes. Antes de activar, verificar como si fuera un cliente.
- **Ventas reales:** solo pedidos pagados en WooCommerce. Cuentan los estados processing, completed y delivered, atribuidos por UTM. **No decidir con las compras del Pixel**, que las infla unas 30 veces.
- **Toda campaña lleva UTM y manda a pahubi.com.** Si no, no se puede medir.
- No hay pago contraentrega y no se promete envío gratis sin la decisión de Ivan.
- **El agente lee, compara, redacta y recomienda.** Publicar, pausar o cambiar presupuestos solo con aprobación explícita.

## Herramientas
- **Bot de Telegram** (@metricas_pahubi_bot): `bot-metricas/`. Corre en el PC de la oficina con una sola copia y lee las llaves de `.env` (no está en git; plantilla en `.env.example`). Arma pautas con Claude Code (`claude -p`) siguiendo `playbook_pautas.md` y `criterios_venta.md`; nunca crea ni pausa nada sin el ✅ y la confirmación de una persona. Al reiniciarlo, cerrar también su ventana vieja para que no queden dos copias.
- **TikTok Marketing API:** app "Pahubi Metricas Bot" (aprobada el 10 nov 2026). El bot crea Spark Ads de Eva directo por la API.
- **Windsor.ai:** datos de Meta, Instagram, TikTok y Facebook. Las acciones también pasan por Windsor.
- **WooCommerce:** se lee directo con llaves de solo lectura, porque Windsor está bloqueado por IP.
- **Skills de marketing** en `.claude/skills/`: ads, ad-creative, ad-swipe-file, ad-account-diagnostic, competitors, cro, social. No van en git (son de terceros); reinstalar con `skills-lock.json`.

## Carpeta `contexto/`
Lo que el equipo deje aquí (costos, reportes de ventas de WhatsApp, Alkosto o Rappi, guía de marca, conversaciones) se lee antes de analizar o proponer algo.
