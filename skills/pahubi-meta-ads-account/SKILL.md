---
name: "pahubi-meta-ads-account"
description: "Use when doing anything in Meta Ads Manager, Meta Business Suite, or the Meta Events Manager for pahubi.com — ensures the correct ad account is used and the decoy account is avoided."
---

# Pahubi — cuenta publicitaria de Meta correcta

## La regla

Para pahubi.com, la **única** cuenta publicitaria de Meta que contiene las campañas reales es:

- **Nombre:** Pahubi
- **ID de cuenta publicitaria:** `2071312623652434`
- **Portafolio comercial:** Pahubi SAS
- **Business ID (Meta Business):** `8777151152410064`

Todas las campañas reales usan el prefijo **"[Estrategia N] ..."** (ej. "[Estrategia 5] Gatoresplandor — IA viral", "[Estrategia 4] Raquel — Ventas (Bogotá)", "[Estrategia 3] Hombre Rudo — Top 10 ciudades").

## La trampa a evitar

Cuando se abre el Administrador de anuncios (adsmanager.facebook.com) sin especificar la cuenta, o al usar el selector de cuentas en la esquina superior izquierda, **Facebook puede mostrar por defecto una cuenta distinta: `1189939789598673`**. Esa cuenta también aparece agrupada bajo el mismo portafolio comercial "Pahubi SAS" en el selector, lo cual la hace parecer correcta, pero:

- Solo contiene campañas de prueba/borradores sin publicar (nombres como "Nueva campaña de Interacción", "tráfico web personalizada...").
- NINGUNA campaña real ("[Estrategia N] ...") vive ahí.
- Si se navega directo con un ID de campaña real vía `selected_campaign_ids=...` SIN especificar `act=`, Facebook puede autocompletar `act=1189939789598673` de todas formas (por ser la última cuenta usada), y la tabla mostrará "seleccionado" pero las filas reales nunca cargarán ("No se encontraron campañas", "Aún no creaste anuncios").

Si en cualquier momento el Administrador de anuncios muestra 0 resultados para una campaña que se sabe activa, o solo muestra borradores/campañas desconocidas, es señal de estar en la cuenta equivocada — no seguir intentando ahí.

## Cómo entrar siempre a la cuenta correcta

Navegar directamente con el ID de cuenta explícito en la URL, sin depender del selector:

```
https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2071312623652434
```

Si hace falta confirmar o localizar la cuenta desde cero (por ejemplo, sesión nueva o duda), ir a Business Settings en lugar de fiarse del selector rápido del Ads Manager:

```
https://business.facebook.com/latest/settings/ad_accounts?business_id=8777151152410064
```

Ahí la lista de "Cuentas publicitarias" del negocio muestra el identificador real (`2071312623652434`) de forma inequívoca, sin el agrupamiento confuso del selector de Ads Manager.

## Contactos oficiales de Pahubi (para extensiones de llamada / CTA de WhatsApp)

Algunos flujos de creación de anuncios en Meta Ads Manager piden un número de teléfono obligatorio (por ejemplo, el campo "* Llamar" que aparece junto a la llamada a la acción aunque el destino principal del anuncio sea un sitio web). Usar **siempre** uno de estos dos números verificados directamente por Ivan Cordoba — nunca el que aparece en la sección "Información de contacto" de la página de Facebook "Pahubi Colombia", que está desactualizado/incorrecto (muestra +57 300 5060272, que NO es un número real de Pahubi):

- **Ventas / WhatsApp:** código de país `+57`, número `300 5060274` (es decir, `+57 300 5060274`). Usar este para cualquier extensión de llamada o CTA de un anuncio orientado a compra/venta.
- **Asesoría comercial:** código de país `+57`, número `304 3900861` (es decir, `+57 304 3900861`). Usar este para anuncios o flujos orientados a asesoría/consultas comerciales en vez de venta directa.

Si se necesita un número y no está claro cuál de los dos aplica, usar el de Ventas/WhatsApp por defecto y preguntar solo si hay ambigüedad real.

## Checklist antes de pausar/editar/publicar cualquier campaña de Pahubi en el navegador

1. Confirmar que la URL de la pestaña activa tiene `act=2071312623652434`.
2. Confirmar que el nombre de la campaña visible empieza con "[Estrategia N]".
3. Si algo no carga o aparece "No se encontraron campañas"/"Aún no creaste anuncios" para una campaña que se sabe activa, DETENERSE y revisar el `act=` en la URL antes de seguir haciendo clic — no es un bug de carga, es la cuenta equivocada.
4. Si el formulario pide un número de teléfono (extensión de llamada), usar los contactos verificados de la sección anterior — nunca el de la página de Facebook.