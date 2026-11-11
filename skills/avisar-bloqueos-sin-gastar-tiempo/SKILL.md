---
name: "avisar-bloqueos-sin-gastar-tiempo"
description: "Usar siempre que una tarea técnica (compilar, desplegar, conectar una herramienta, hacer push, etc.) tropiece con un obstáculo — avisar rápido y ofrecer alternativas, en vez de reintentar en silencio."
---

# Avisar bloqueos rápido, sin gastar tiempo/créditos en silencio

## Contexto real que motivó esto
En una sesión de trabajo en el proyecto ReadShadow, Claude se quedó varios minutos intentando
compilar un proyecto Android dentro de su propio entorno en la nube (que no tiene acceso a los
servidores de Google/Android), probando distintas soluciones una tras otra (generar un wrapper
de Gradle a mano, compilar el módulo aislado, etc.) sin decirle nada al usuario mientras tanto.
El usuario notó el silencio y la lentitud antes de que Claude dijera una palabra, y preguntó
"por qué no procedes, te quedaste bloqueado?" y luego "cuánto demoras? siento que ha sido más
demorado que con Android Studio". La alternativa correcta (usar GitHub Actions, que sí tiene
internet completo, para compilar y probar) ya era conocida, pero no se usó de inmediato.

## Regla
1. Si una acción técnica falla, reintentar como máximo 2-3 veces con variaciones razonables.
   Si en esos intentos no se resuelve, DETENERSE ahí mismo y avisar al usuario de inmediato —
   no seguir probando una cuarta, quinta o sexta variante en silencio.
2. El aviso debe decir, en una o dos frases: (a) qué se intentó, (b) por qué no funcionó (la
   causa raíz, si se conoce — ej. "este entorno no tiene acceso a los servidores de Android"),
   y (c) qué alternativas concretas hay (ej. "puedo verificarlo con GitHub Actions en vez de
   compilarlo aquí", "puedes intentar X en tu PC", "puedo seguir sin esta verificación y avisar
   si algo falla después").
3. Nunca dejar pasar más de ~1 minuto de llamadas a herramientas (compilaciones, búsquedas,
   reintentos de red) sin que el usuario vea al menos una línea de texto explicando qué está
   pasando. Si una tarea va a tomar tiempo real (ej. esperar un CI), decirlo ANTES de esperar,
   no después de que el usuario pregunte.
4. Preferir de inmediato la alternativa que ya se sabe que funciona, en vez de insistir en la
   que está fallando. Ejemplo real: en vez de insistir en compilar Android dentro del entorno
   de Claude (sin internet completo hacia Maven/Google), usar GitHub Actions (que sí tiene
   internet completo) para compilar y correr las pruebas.
5. Si de verdad no hay alternativa y hay que esperar (ej. un build de CI en curso), decirlo
   explícitamente ("esto va a tomar unos X minutos, reviso en breve") en vez de callar.

## Señales de que hay que parar y avisar
- Vas por el segundo o tercer intento fallido de lo mismo (misma causa de error).
- Llevas más de ~1 minuto de llamadas a herramientas sin haber compartido un mensaje de texto
  con el usuario.
- Descubres una limitación estructural (sin acceso a internet completo, sin credenciales, sin
  una herramienta necesaria) — eso no se arregla reintentando, hay que decirlo y ofrecer el
  rodeo o alternativa disponible.

## Ajuste para Pahubi (oct 2026)
En el trabajo de Pahubi, "parar y avisar" NO significa abandonar la tarea: significa preguntar. Ante una duda, un bloqueo o una decisión que no es tuya, escribe a **Ivan Cordoba (dueño) o a Jhoana (administradora de Pahubi)** con una pregunta concreta (qué intentaste, qué falló, qué alternativas ves) y mientras esperas continúa con las partes de la tarea que sí son seguras (lecturas, preparación, documentación). Ver la skill `pahubi-contactos-y-escalamiento`.
