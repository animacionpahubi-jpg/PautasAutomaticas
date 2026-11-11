---
name: notify-on-blocker
description: "Enviar una notificación push cuando algo necesite aprobación del usuario, ayuda manual, o cuando se pierda la conexión con Claude en Chrome u otra herramienta de automatización mientras trabaja en segundo plano."
---

## Trigger

Se activa durante cualquier tarea de varios pasos (especialmente las que involucran Claude en Chrome, un agente en segundo plano, o cualquier herramienta que pueda quedar bloqueada) cuando ocurre alguna de estas situaciones:

- Se necesita una decisión o aprobación explícita del usuario para continuar (por ejemplo: "¿activo este snippet o no?", "¿procedo con la Fase 2?").
- Un agente conectado (Claude en Chrome, un dispositivo remoto, etc.) reporta que perdió la conexión, se quedó atascado en un diálogo nativo del navegador, o necesita una interacción manual que solo el usuario puede dar (un clic, un pago, una confirmación de identidad).
- Un paso requiere que el usuario haga algo fuera del alcance de las herramientas disponibles (ej. completar un pago real, aprobar un cambio riesgoso).

## Steps

1. Antes de quedarse esperando en silencio, llamar a `PushNotification` con `status: "proactive"` y un mensaje de menos de 200 caracteres, una línea, sin markdown, que lidere con lo accionable (ej. "Claude en Chrome atascado en un diálogo de wp-admin — necesita tu clic" en vez de "hay una actualización").
2. No notificar por progreso rutinario, por confirmar algo que el usuario acaba de pedir hace segundos y sigue claramente mirando la conversación, ni por tareas rápidas que se completan solas.
3. Si el bloqueo se resuelve solo o el usuario ya respondió antes de que se pudiera notificar, no reenviar una notificación redundante.
4. Cuando la herramienta reporte que la notificación "no se envió" (por ejemplo porque el usuario está activo en la terminal), tratarlo como esperado — no es un error, solo significa que ya lo iba a ver de todas formas.

## Verification

- El usuario recibe aviso (sonido/push) específicamente en los momentos en que una tarea quedó esperando algo de él, sin necesidad de estar revisando la conversación activamente.
- No se generan notificaciones por progreso rutinario o por cosas que el usuario ya está viendo en vivo.

## Ajuste para Pahubi (oct 2026)
El aviso de bloqueo debe dirigirse a quien pueda resolverlo: Ivan Cordoba (dueño) o Jhoana (administradora de Pahubi). Ver `pahubi-contactos-y-escalamiento`.
