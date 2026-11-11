---
name: numbered-prompt-log
description: "Numera cada prompt de forma consecutiva con fecha, hora y estado cuando se mantiene un registro de prompts para Claude en Chrome u otro flujo de automatización de navegador de varios pasos."
---

## Trigger

Se activa cuando:
- El usuario pide un nuevo prompt para pegar en Claude en Chrome (o una herramienta de automatización de navegador similar) dentro de un flujo de trabajo que ya tiene prompts anteriores guardados en un archivo.
- Existe (o se está creando) un archivo tipo "registro de prompts" para un proyecto — normalmente un .md con varios bloques de código para copiar y pegar.

## Steps

1. Cada prompt nuevo se agrega como un bloque separado con encabezado `## PROMPT N — Título`, donde N es consecutivo respecto al último prompt del archivo (nunca se reordena ni se reutiliza un número, incluso si un prompt queda obsoleto).
2. El encabezado siempre incluye fecha y hora exactas de cuándo se escribió el prompt (usar la hora real del sistema, zona horaria del usuario si se conoce), y una etiqueta de estado:
   - ⏳ Pendiente de ejecutar
   - 🔄 En progreso / diagnóstico parcial
   - ✅ Ejecutado y confirmado
   - ⚠️ Reemplazado por un prompt posterior (se deja como referencia, no se vuelve a usar)
3. Cuando un prompt existente crece demasiado por tener varias fases internas (Fase 1, Fase 2, Fase 3...) y hay que dar instrucciones para la siguiente fase, esa fase se separa en un PROMPT nuevo con su propio número — no se sigue apilando dentro del mismo bloque. Se deja una nota corta dentro del prompt viejo apuntando al número del prompt nuevo ("⚠️ Ver PROMPT N — esta fase quedó reemplazada").
4. Cuando se resuelve o se descarta un prompt anterior, se actualiza su etiqueta de estado en el encabezado (no se borra el contenido — queda como historial).
5. Cada prompt copiable (el bloque " ``` ") debe incluir, cuando aplique: advertencias de cuidado al inicio (qué NO tocar, cómo revertir si algo sale mal) y un bloque de verificación al final (pasos concretos para confirmar que el cambio funcionó Y que no rompió nada más).
6. Si el archivo no tiene todavía una sección de "Convención de este documento" explicando este esquema, agregarla cerca del inicio la primera vez que se aplique esta skill.

## Verification

- El prompt más reciente que hay que pegar siempre es fácil de identificar: es el de número más alto con estado ⏳ o 🔄.
- Ningún número de prompt se repite ni se reordena en el archivo.
- Cada prompt tiene fecha y hora (no solo fecha) desde que se adoptó esta convención.