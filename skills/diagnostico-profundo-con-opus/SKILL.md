---
name: "diagnostico-profundo-con-opus"
description: "Usar cuando un problema lleva días o varias sesiones sin cerrarse, un arreglo no da prueba directa o el usuario reclama pérdida de tiempo. Delega el diagnóstico a Opus y deja un plan exacto para Sonnet."
---

# Diagnóstico profundo con Opus, ejecución con el modelo estándar

Responder siempre en español.

## Cuándo activarla (basta una señal)
- El mismo problema aparece en 2 o más sesiones, o lleva más de 2 días.
- Ya se aplicó un arreglo y el síntoma sigue, o "mejoró" pero sin prueba directa.
- El usuario dice cosas como "perdiendo tiempo", "otra vez lo mismo", "ya van X días", "cómo sabes que no te pasa lo mismo", o pide certeza.
- El mismo dato o configuración puede vivir en varias capas (sitio, plugin, caché, servidor, anuncio, conjunto de anuncios, cuenta, perfil personal).
- Se está acumulando costo real (gasto en anuncios, horas de trabajo).

No activarla para tareas nuevas simples ni para errores de primera vez.

## Regla de oro
Esta skill DIAGNOSTICA, no ejecuta cambios en producción. Opus investiga y decide; el modelo estándar (Sonnet) ejecuta el plan. El subagente Opus trabaja en modo solo lectura: no modifica, no publica, no envía mensajes.

## Pasos

1. **Frenar.** No ejecutar más cambios. Avisar al usuario en 2 líneas: "Voy a hacer una revisión profunda con Opus antes de tocar nada más".

2. **Armar el expediente** (lo hace Sonnet) con documentos del proyecto, memoria e historial:
   - Síntoma exacto, desde cuándo y costo acumulado.
   - Cronología de lo intentado y el resultado de cada intento.
   - Dos listas separadas: VERIFICADO (prueba directa: conteo de eventos, pedidos reales, solicitudes de red, capturas) e INFERIDO (métricas agregadas, lectura de código, suposiciones).
   - Restricciones: qué no se puede tocar, qué accesos hay (¿navegador conectado?) y qué permisos faltan.

3. **Delegar a Opus.** Usar la herramienta Agent con model "opus" (tipo general-purpose). El subagente no ve la conversación, así que el prompt debe ser autocontenido: pegar el expediente completo y exigir:
   a. **Mapa de capas:** listar TODOS los lugares donde el mismo dato o configuración puede vivir o ser sobrescrito. Lección aprendida: verificar una sola capa y asumir las demás causó el error del número de WhatsApp equivocado (se revisó el sitio pero no cada anuncio).
   b. **Investigación externa** con URLs: documentación oficial, repositorios e issues, changelogs, foros. Distinguir fuente oficial de opinión.
   c. **Hipótesis ordenadas por probabilidad**, cada una con la prueba concreta que la refutaría.
   d. **Autocrítica:** qué evidencia haría falsa la conclusión y qué falta por verificar.
   e. **Solo lectura.**

4. **Revisión cruzada** (Sonnet): cada afirmación de Opus debe tener fuente o prueba; marcar lo no verificado. Si contradice algo verificado antes, resolverlo antes de seguir. Si el costo de equivocarse es alto, lanzar un segundo agente Opus como abogado del diablo.

5. **Plan de ejecución** (entregable). Guardarlo en el doc del proyecto o en un archivo, y resumirlo al usuario. Formato:
   - Causa raíz (o las 2 más probables) con certeza: Confirmada, Probable o Hipótesis.
   - Pasos numerados. Cada uno con: acción exacta, herramienta, ruta, URL o valor, riesgo, cómo revertir y criterio de éxito con prueba directa.
   - Orden: primero lecturas y pruebas, luego cambios, luego verificación.
   - Qué se necesita del usuario (accesos, decisiones).
   - Condiciones de parada: cuándo dejar de intentar y avisar.
   - Criterio de cierre: qué resultado da el problema por terminado.

6. **Traspaso.** Sonnet ejecuta el plan paso a paso, sin improvisar fuera de él. Si un paso falla o aparece un dato que contradice el diagnóstico, parar y avisar (ver skill avisar-bloqueos-sin-gastar-tiempo); no reintentar en silencio. Volver a llamar a Opus solo si el diagnóstico queda invalidado.

7. **Cierre.** No declarar "resuelto" con señales indirectas (métricas agregadas, "la página cargó bien"). Solo con la prueba directa definida en el plan. Además, tras cualquier cambio en un sitio web, purgar cachés y verificar como visitante anónimo. Reportar al usuario en pocas líneas: qué se encontró, qué se hizo y qué queda.

## Límites de tiempo y costo
- Una pasada Opus por problema, más una revisión adversarial si el riesgo es alto.
- Si falta acceso (por ejemplo, navegador desconectado), Opus diagnostica lo que pueda con fuentes externas y el plan marca qué pasos esperan ese acceso.

## Notas
- Esta skill no cambia el modelo de la sesión; Opus se usa solo dentro del subagente y el resto sigue en el modelo estándar.
- Si el parámetro model no acepta "opus", usar el modelo más capaz disponible y decírselo al usuario.