---
name: "pahubi-fuentes-de-verdad-y-pixel"
description: "Usar al analizar resultados de pautas de Pahubi, decidir presupuesto o revisar el Pixel de Meta: qué fuentes son confiables y por qué no escalar con las compras que reporta Meta."
---

# Pahubi — Fuentes de verdad y Pixel de Meta

Responder siempre en español.

## Fuentes de verdad (solo estas)
1. **Meta Ads Manager (en Chrome):** gasto, entrega, clics, CTR, CPC.
2. **WooCommerce → Pedidos, columna "Origen":** ventas reales pagadas (estados processing y completed, sin reembolsos).
3. **Ventas y chats de WhatsApp** que lleva Ivan con código por campaña (Woo no los ve).
4. **Events Manager / Pixel ID 1985025489050897:** solo para auditar eventos, no para decidir ventas.
No se usan reportes de intermediarios ni agregadores como fuente de decisión.

## Qué se sabe del Pixel (hasta 13 oct 2026)
- Reportó ~430 Purchase y ~1.700 AddToCart en 28 días, muy por encima de las ventas reales (~$358.593 COP con origen Meta en ~30 días, WooCommerce, 25 sep).
- Tres sistemas envían eventos a la vez: Meta Pixel for WordPress (PageView), Meta for WooCommerce v3.7.6 (oficial, con errores abiertos #4006 y #4047) y snippets propios de WPCode (3916 compra por CAPI, 3918 AddToCart) sin event_id.
- El snippet #3979 apaga el pixel del plugin oficial (confirmado por código que también apaga su envío de servidor; falta verlo en ejecución).
- Plan de revisión completo: documento "plan-definitivo-pixel-pahubi" del proyecto.

## Reglas
- No escalar presupuesto con las "Compras" de Meta hasta que, del 5 al 11 oct, los Purchase deduplicados estén entre 95 % y 105 % de los pedidos pagados de Woo.
- Un costo por compra que baja muchísimo de golpe es sospechoso (se está contando más), no una mejora.
- El costo por pedido de equilibrio se calcula solo con datos que entrega Ivan o Jhoana (precio, costo del producto, envío y comisión real de la pasarela). Si faltan, preguntar; no suponer.
- Cambios en WPCode, plugins o Events Manager: decir qué se cambia y cómo se revierte, esperar el "sí" de Ivan, luego LiteSpeed Purge All y probar como visitante anónimo.
