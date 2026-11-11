---
name: "pahubi-meta-ads-whatsapp-number"
description: "Use when creating, editing, publishing, or auditing Meta (Facebook/Instagram) ads for Pahubi — verifies the ad's WhatsApp/call destination number is correct (visually, as the customer sees it) so it never silently reverts to the old wrong number."
---

# Pahubi — Verificación del número de WhatsApp en anuncios de Meta

Responder siempre en español. Versión actualizada el 13 oct 2026.

## Por qué existe esta skill
- **Septiembre 2026:** cerca de una semana de inversión se perdió porque varios anuncios (entre ellos "[Estrategia 3] Flushable — Top 10 ciudades") abrían WhatsApp en **+57 312 6062630** en vez del número real.
- **13 octubre 2026:** la campaña "[Estrategia 8] Nube Pañito" mostró en vivo el 312 6062630 (captura de Ivan en el celular) aunque el editor mostraba "Pañitos Pahubi +57 300 5060274". Se pausó E8.
- **Origen real encontrado el 13 oct:** el 312 6062630 estaba guardado como **número principal de WhatsApp de la Página de Facebook "Pahubi Colombia"** (Configuración de la Página → Cuentas vinculadas → WhatsApp; la Página tenía 3 números: el 312 como principal y el 300 5060274 dos veces). Meta ofrece los números conectados a la Página como "perfiles" en el selector del anuncio ("Conectar perfil"). Se puso el 300 5060274 como principal y se **eliminó el 312** (Meta avisa que pausa los anuncios de clic a WhatsApp de ese número). Business Suite → Cuentas de WhatsApp solo tiene "Pañitos Pahubi +57 300 5060274" (WABA 2201335723604041); el 312 no estaba ahí.
- Lección: **el editor no es lo que ve el cliente.** Leer el texto de la pantalla (get_page_text/find) solo lista opciones, no la selección real. La verificación debe ser visual, como cliente.

## Números
- **Correcto (ventas):** Pañitos Pahubi — **+57 300 5060274** (`wa.me/573005060274`).
- **Asesoría comercial:** +57 304 3900861.
- **NUNCA:** **+57 312 6062630** (viejo/huérfano) y **+57 300 5060272** (contacto desactualizado de la Página).

## Lugares donde el número puede estar mal (revisar TODOS; son independientes)
1. El anuncio en Ads Manager (sección Identidad: "Número de teléfono de WhatsApp" y "Llamar").
2. **Configuración de la Página → Cuentas vinculadas → WhatsApp:** el número principal debe ser +57 300 5060274; no debe existir el 312 6062630; limpiar el duplicado.
3. Botón de contacto de Instagram @pahubi.colombia y la sección "Información" de la Página.
4. Business Suite → Configuración → Cuentas de WhatsApp (solo debe existir Pañitos Pahubi).
5. Catálogo de Meta.
6. El widget de WhatsApp del sitio: plantilla "Elementor Header #2208" (asignada a "Entire site"); apunta a `wa.me/573005060274`.

## Checklist al crear O editar un anuncio
1. Abrir "Identidad" y, aunque parezca seleccionado, abrir el desplegable y confirmar "Pañitos Pahubi +57 300 5060274".
2. Si hay campo "Llamar": +57 300 5060274 (o 304 3900861 si es de asesoría).
3. Publicar (editar este campo en un anuncio activo no exige pausarlo).
4. Reabrir el editor y confirmar que quedó guardado.
5. **Verificación como cliente (obligatoria):** ver el anuncio publicado en el celular o en el navegador de Instagram/Facebook, tocar el botón y capturar el número o el enlace `wa.me/573005060274`. Sin captura no está verificado.
6. Seguir la puerta `pahubi-meta-ads-puerta-antes-de-publicar` antes de activar.

## Auditoría periódica (semanal mientras haya campañas activas)
Abrir CADA anuncio activo en modo edición (el número no se ve en la tabla), revisar el campo, verificar como cliente, y revisar los lugares 2–6 de arriba. Corregir al instante y reportar a Ivan cuántos anuncios se revisaron y cuántos se corrigieron.

## Si algo sale mal
Si un anuncio en vivo muestra un número equivocado: pausar esa campaña de inmediato (reversible), capturar, avisar a Ivan o Jhoana y buscar el origen en los 6 lugares. Si no se puede resolver, preguntar a Ivan o a Jhoana (administradora de Pahubi); no activar con dudas.
