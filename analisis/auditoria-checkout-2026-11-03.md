# Auditoría checkout pahubi.com: 3 nov 2026

Auditor: agente `auditor-woocommerce`, en modo solo lectura. Fuentes: API de WooCommerce (solo GET, 71 pedidos del 5 sep al 3 nov 2026, con sus notas), `payment_gateways`, `shipping/zones`, `settings`, `webhooks`, `system_status`, el HTML público de inicio, tienda, ficha, carrito y finalizar compra (con un celular Android simulado) y los datos de la pauta E9 que entregó el usuario. No se incluyen datos personales: los clientes se agruparon por un hash del teléfono.

## Resumen (3 líneas)
1. En 60 días se crearon **71 pedidos y solo se pagaron 33 (46 %)**. Contando personas, 48 intentaron comprar, **32 pagaron y 16 (33 %) se fueron sin pagar**. El último intento de esas 16 personas suma unos **$992.000**.
2. La caída se concentra **fuera de Bogotá urbana**: allí paga el 46 % de los clientes, contra el 88 % en Bogotá urbana. El envío que se anuncia ("desde $11.100" y "$12.000") no es el que se cobra fuera de Bogotá ($18.695 a $32.760). Además, **28 de los 38 pedidos caídos nunca generaron una transacción en Wompi**.
3. La E9 gastó $222.626 y dejó 1 pedido creado (#4053, que no se pagó) y 0 pagados. Mandó la gente a `/tienda/`, la página genérica. **No se recomienda más pauta** hasta resolver los puntos 🔴.

## Embudo con números (visitas → carrito → checkout → pedido creado → pagado)

**Pauta Estrategia 9 (24–31 oct 2026, Meta, tráfico, UTM `estrategia9_video_sensorial`)**
| Paso | Cantidad | Fuente |
|---|---|---|
| Gasto | $222.626 | Meta (dato del usuario) |
| Impresiones | 54.155 | Meta |
| Clics al enlace | 2.793 | Meta |
| Visitas (página cargada) | ~1.897 (68 % de los clics) | Meta |
| Agregar al carrito | **FALTA** (no hay embudo en GA4/Jetpack accesible; CartBounty podría tenerlo) | — |
| Llegada a finalizar compra | **FALTA** (al menos 1, la del #4053) | — |
| Pedido creado con UTM E9 | **1** (#4053, 31 oct, Pereira, Combo Sachets papel, $46.595 de los cuales $18.695 son envío "Envío Nacional 1") | Woo |
| Pedido pagado con UTM E9 | **0**. El #4053 se canceló por límite de tiempo 117 min después, sin ninguna transacción en Wompi | Woo |

- Recorrido del #4053: un clic en Instagram llevó a `/tienda/` con el UTM. De ahí pasó a `finalizar-compra` (2 páginas en la sesión) y el pedido se creó 2 minutos después de llegar.
- Toda la tienda del 24 al 31 oct: 5 pedidos creados (#4049–#4053) y 3 pagados por **$192.189** (#4050, #4051, #4052, ninguno con UTM de E9).
  - #4050: Instagram, enlace en la biografía. Es el reintento del #4049, que había sido DECLINED.
  - #4051: referido de l.instagram.com.
  - #4052: tráfico directo, de un cliente que ya había comprado en sep con el UTM de Hombre Rudo.
- No hay pedidos nuevos del 1 al 3 nov. El último es el #4053.

**Tienda completa, 60 días (5 sep – 3 nov):** visitas FALTA → carrito FALTA → checkout FALTA → **71 pedidos creados** → **33 pagados ($1.974.731)**. Ticket promedio de los pagados: $59.840.

**30 días (4 oct – 3 nov):** 21 pedidos creados → 10 pagados ($701.036), 7 por tiempo agotado ($427.005) y 4 DECLINED ($194.396).

## Por qué se caen los pagos (60 días)

| Motivo (según las notas del pedido) | Pedidos | Monto | Clientes únicos que nunca pagaron | Último intento de esos clientes |
|---|---|---|---|---|
| Pagado (completed) | 33 | $1.974.731 | — | — |
| **Tiempo agotado**: "Pedido no pagado cancelado: límite de tiempo alcanzado", **sin ninguna transacción Wompi registrada** | 28 | $2.016.388 | 11 | $720.526 |
| **Rechazo**: "Wompi payment DECLINED" (el plugin pasa el pedido directo a *Cancelado*) | 10 | $528.040 | 5 | $271.960 |
| Cancelación manual / otro | 0 | $0 | — | — |
| **Total caído** | **38** | **$2.544.428** | **16** | **$992.486** |

Cómo leer la tabla:
- **El monto de pedidos inflado.** Un solo cliente de Ibagué creó 12 pedidos por tiempo agotado en dos días (17–18 sep y 7 oct, de $82.527 y $50.891, en computador y en Android). Suman $958.688, pero es una sola venta perdida. Otro cliente de Pasto lo intentó 4 veces (3 por tiempo y 1 DECLINED) y uno de Sabana/Cundinamarca 3 veces. Por eso se cuentan clientes únicos.
- **Reintentos exitosos: 5 clientes.**
  - #4049 → #4050 (DECLINED, pagó 51 min después).
  - #4043 → #4044 (tiempo agotado, pagó 2 h después).
  - #4026 → #4027 (DECLINED, 2 h).
  - #3980 → #3981 (DECLINED, 12 min).
  - #3969 → #4013 (DECLINED, 20 días después).
  - En todos, el cliente tuvo que llenar otra vez el formulario completo.
- **Tiempo hasta el pago:** 32 de 33 pedidos pagados se pagaron entre 1,4 y 8,3 minutos después de creados (mediana de unos 3 min). El #3981 se pagó a los 78,5 min, después de vencida la retención de 60 min; se salvó porque el cron todavía no había pasado.
- **Tiempo hasta el rechazo:** los DECLINED llegan entre 4 y 25 min. Los pedidos por tiempo agotado se cancelan entre 64 y 118 min, según cuándo pase el cron.
- **Método (Nequi, PSE, tarjeta, Daviplata):** **FALTA.** Ni las notas ni la metadata del pedido guardan el medio que se eligió dentro de Wompi. Solo se ve en el panel de Wompi.

**Cruces (hechos):**
| Corte | Pagaron | No pagaron | Tasa de pago |
|---|---|---|---|
| Clientes con envío urbano en Bogotá ("Local Bogotá" o "JAMV", $12.000) | 21 | 3 | **88 %** |
| Clientes con envío fuera de Bogotá urbana | 11 | 13 | **46 %** |
| Pedidos con "Envío Nacional 1" ($18.695–$25.240) | 3 | 16 | 16 % |
| Pedidos con "otras zonas" ($32.760) | 0 | 3 | 0 % |
| Pedidos desde celular | 24 | 18 (8 DECLINED) | 57 % |
| Pedidos desde computador | 9 | 20 (12 del cliente de Ibagué) | 31 % |
| Pedidos con UTM de Meta | 8 | 6 | 57 % |
| Pedidos directos (typein) | 11 | 23 | 32 % |
| Pedidos de Google orgánico | 8 | 6 | 57 % |

- Envío promedio: $13.576 en los pedidos pagados y $19.882 en los cancelados.
- Ajuste "Mantener inventario": **60 minutos** (`woocommerce_hold_stock_minutes = 60`). Con los datos no se ve que sea corto: casi todos pagan en menos de 9 min. Los pedidos por tiempo agotado no tienen ninguna transacción iniciada en Wompi, así que no son PSE lentos, sino gente que no llegó a pagar.

## Hallazgos

### 🔴 Crítico

- **Problema:** el costo de envío que se anuncia no es el que se cobra fuera de Bogotá, y aparece de sorpresa en el último paso.
  - **Evidencia:**
    - La tienda y las fichas dicen "+ envío desde $11.100", pero ninguna tarifa configurada baja de $12.000.
    - El carrito muestra por defecto "Envío Local: $12.000, Envío a Bogotá D.C." antes de que el cliente elija ciudad (`default_customer_address = base`).
    - En el checkout, al elegir la ciudad, el envío sube:
      - Envío Nacional 1: $18.713 para menos de 2 kg y $25.240 entre 2 y 5 kg.
      - Otras zonas: $32.760.
      - Envío zonal: $24.688 a $37.999.
      - Envío especial: $45.265.
    - Los combos pesan 1.460 g (pañitos), 1.693 g (mixto) y 1.926 g (papel), así que **2 combos pasan de 2 kg y suben de escalón en todas las zonas fuera de Bogotá** (Pasto pasa de $12.000 a $15.000; Nacional, de $18.713 a $25.240). La frase del contexto "mismo envío para 1 o 2 combos" solo es cierta en Bogotá y en "Envío urbano 24 h".
    - Resultado: 88 % de pago en Bogotá urbana contra 46 % fuera, y 3 de 19 pedidos pagados con Envío Nacional 1.
  - **Impacto:** 13 de los 16 clientes que se perdieron eran de fuera de Bogotá urbana. La pauta E9 apuntaba a 6 ciudades y su único pedido fue de Pereira, con $18.695 de envío sobre $27.900 de producto.
  - **Arreglo:**
    1. Quitar o corregir el "+ envío desde $11.100".
    2. Poner en la ficha y en el carrito una tabla corta de envío por zona (Bogotá $12.000; las 5 ciudades satélite $12.000; resto del país desde $18.713, y $25.240 con 2 combos).
    3. Que el carrito pida la ciudad antes de mostrar un costo, en vez de dar Bogotá por defecto.
    4. La tarifa fuera de Bogotá, por ejemplo cobrar el mismo valor por 1 o 2 combos, es **decisión de Ivan**. No se promete envío gratis.
  - **Quién/aprueba:** textos, Daniel o quien administre WordPress; tarifas, Ivan. **Esfuerzo:** bajo para los textos, medio para la tarifa.

- **Problema:** 28 pedidos (11 clientes únicos) se crean y nunca llegan a tener una transacción en Wompi. Hay un cliente que lo intentó 12 veces sin que se registrara ni un intento de pago.
  - **Evidencia:**
    - En los pedidos pagados o rechazados siempre aparece una nota "Wompi payment APPROVED/DECLINED. TRANSACTION ID …".
    - Los 28 pedidos por tiempo agotado solo tienen la nota de retención de inventario y la cancelación automática.
    - El cliente de Ibagué repitió el pedido de $82.527 desde computador y desde Android en dos días seguidos, sin ninguna transacción.
  - **Impacto:** es el motivo n.º 1 de pérdida, con 11 clientes y unos $720.000. No se sabe si el cliente se arrepiente al ver el total en Wompi o si la ventana o la redirección de Wompi falla en algunos casos.
  - **Arreglo:**
    1. Exportar del panel de Wompi todas las transacciones del 5 sep al 3 nov, incluidas las PENDING, ERROR y VOIDED, y cruzarlas por referencia con estos pedidos.
    2. Leer el registro del plugin en WooCommerce → Estado → Registros → `wompi-*`. El registro está activo (`logging = yes`).
    3. Hacer el guion de prueba manual de abajo.
  - **Quién/aprueba:** Andres y Jhoana, porque es solo lectura. **Esfuerzo:** bajo.

- **Problema:** cuando un pago se cae, nadie de Pahubi se entera a tiempo para recuperar la venta.
  - **Evidencia:**
    - Los correos "Pedido cancelado" y "Pedido fallido" para la tienda van a direcciones de Findcor, la agencia que implementó el sitio, no al equipo de ventas.
    - El webhook 31 "Qubit Suite Pedidos" (WhatsApp) está **desactivado desde el 30 oct**. WooCommerce desactiva un webhook después de varios envíos fallidos.
    - Las notas de los pedidos no muestran ningún contacto de recuperación, salvo uno manual en #3969, que el cliente pagó 20 días después.
  - **Impacto:** 16 clientes y unos $992.000 en 60 días. Llamar o escribir por WhatsApp a la gente que ya dio ciudad, producto y teléfono es la recuperación más barata posible. Los 5 reintentos exitosos que hubo los hizo el cliente por su cuenta.
  - **Arreglo:**
    1. Agregar el correo de ventas de Pahubi como destinatario de "Pedido cancelado" y "Pedido fallido".
    2. Reactivar el webhook 31 después de confirmar con Qubit que su URL responde. **Rotar el token**, que hoy va en texto plano dentro de la URL y lo puede leer cualquiera con la llave de lectura.
    3. Fijar una rutina diaria: los pedidos cancelados del día reciben un WhatsApp desde el +57 300 5060274.
    4. Revisar si CartBounty (activo) envía recordatorios.
  - **Quién/aprueba:** Ivan aprueba; lo hacen Andres y Jhoana. **Esfuerzo:** bajo.

### 🟠 Alto

- **Problema:** un pago DECLINED cancela el pedido de inmediato y el cliente tiene que llenar todo otra vez.
  - **Evidencia:** en los 10 DECLINED la nota dice "Wompi payment DECLINED" y en el mismo minuto el estado pasa de "Pago pendiente" a **Cancelado**, no a "Fallido". Hay 0 pedidos en estado failed en 60 días. Con un pedido cancelado, WooCommerce ya no deja "Pagar" desde el enlace del pedido.
  - **Impacto:** 5 de los 10 clientes con DECLINED no volvieron. Los que reintentaron llenaron otra vez 10 campos obligatorios.
  - **Arreglo:**
    1. Ver si el plugin Wompi (3.2.0; ya existe la 3.2.1) permite dejar el pedido como "Fallido" o "Pendiente", con un mensaje de "intenta con otro medio (Nequi o PSE)" y un botón para reintentar.
    2. Si no lo permite, pedirlo a soporte de Wompi.
    3. Actualizar el plugin solo después de leer el registro de cambios y con una copia de seguridad.
  - **Quién/aprueba:** Ivan. **Esfuerzo:** medio.

- **Problema:** la pauta llega a la tienda genérica, no al producto del anuncio.
  - **Evidencia:** las URL de entrada con el UTM de E9 (y de E7 y E4) son `pahubi.com/tienda/?utm_…`. El aprendizaje del 29 oct ya registró que "mandar tráfico frío a /tienda/ no vende". E9 tuvo 1.897 visitas y 1 pedido creado (0,05 %).
  - **Impacto:** toda la inversión en tráfico.
  - **Arreglo:** cuando se reanude la pauta, y solo después de arreglar lo 🔴, mandar a la ficha del combo que muestra el anuncio, con UTM, y con el envío por zona visible en esa ficha.
  - **Quién/aprueba:** Ivan. **Esfuerzo:** bajo.

- **Problema:** el formulario es largo y empieza por lo más pesado.
  - **Evidencia** (HTML del checkout con 1 producto en el carrito):
    - Hay **10 campos obligatorios**: tipo de documento, número de identificación, nombres, apellidos, país (solo Colombia), departamento, ciudad, dirección, teléfono y correo.
    - Hay 2 opcionales (razón social y código postal), más casilla de boletín, "¿Crear una cuenta?", "¿Cliente recurrente?" y la casilla obligatoria de términos.
    - El documento es lo primero que se pide.
    - El departamento trae opciones inventadas, "Bogotá Alrededores y Sabana (Chía, Cajicá, Soacha, Cota, etc.)" y "Bogotá D.C. (Solo Perímetro Urbano)", y además un aviso ⚠️ que explica cómo elegir.
    - Lo bueno: departamento y ciudad son listas, y se puede comprar sin cuenta.
    - Si las validaciones son en línea o solo al enviar: **FALTA**, porque requiere JavaScript; queda en la prueba manual.
  - **Impacto:** en el carrito el 63 % compra desde celular. El cliente lo dijo por WhatsApp: "no es fácil comprar".
  - **Arreglo** (con Checkout Field Editor, ya instalado):
    1. Pasar el documento al final, después del correo, o quitarlo si la facturación electrónica no lo exige; eso lo decide Jhoana.
    2. Ocultar "País", porque solo hay Colombia.
    3. Quitar razón social y código postal.
    4. Ocultar "¿Cliente recurrente?" (`checkout_login_reminder`).
  - **Quién/aprueba:** Ivan y Jhoana. **Esfuerzo:** bajo.

- **Problema:** la velocidad móvil sigue lenta. Los videos pesados siguen igual que el 26 oct.
  - **Evidencia:**
    - Tiempo de respuesta del servidor (TTFB) medido hoy desde Colombia con un celular Android simulado: inicio 2,5 s, tienda 1,8 s, ficha 1,9 s, carrito 1,7–2,2 s y checkout 2,2–3,0 s.
    - Cloudflare responde `cf-cache-status: DYNAMIC` en todo.
    - En el inicio siguen `DesintegracionC.mp4` (**23,4 MB**) y `SacarPanitosC.mp4` (**16,3 MB**) con reproducción automática.
    - El inicio carga además PNG de 0,5 a 1,9 MB (Blog-010.png, Perfil-010.png y otros).
    - PageSpeed: **FALTA** (la API respondió 429, cuota agotada).
  - **Impacto:** las visitas de pauta se pierden antes de que cargue la página. De 2.793 clics solo 68 % se volvieron visitas.
  - **Arreglo** (sin caché de página, que el equipo descartó):
    1. Recomprimir los videos a menos de 2 MB, con una imagen de portada y sin reproducción automática en celular.
    2. Convertir los PNG a WebP.
    3. Que Cloudflare guarde en caché solo los archivos estáticos (imágenes, CSS, JS).
    4. Probar la caché de objetos de Hostinger (Redis o Memcached), que no es caché de página.
    5. Quitar `cart-fragments` en las páginas que no son de tienda.
  - **Quién/aprueba:** Daniel (medios), Andres (técnico) e Ivan. **Esfuerzo:** medio.

### 🟡 Medio
- **Hay dos plugins de Meta activos:** `facebook-for-woocommerce` 3.7.8 y `official-facebook-pixel` 5.2.2, además de un "Meta CAPI Purchase" en las notas.
  - El CAPI Purchase solo aparece en los 33 pedidos pagados, así que el lado servidor está bien.
  - La inflación de unas 30 veces del Pixel se origina, como hipótesis, en el lado del navegador: dos plugins, o Purchase al recargar la página de gracias.
  - Arreglo: dejar uno solo y verificar con Events Manager → Probar eventos.
  - Aprueba Ivan.
- **Webhooks de ecartapi duplicados:** dos juegos (1 y 2, y 28, 29 y 30) para order.created y order.updated. Puede duplicar la sincronización con marketplaces o el inventario. Hay que confirmarlo con quien usa ecartapi.
- **Ciudades que están en dos métodos de envío a la vez.** Cali, Cartago, Jamundí y Palmira están en "Envío Nacional 1" y en "urbano 24 h" o "municipal/regional"; Pasto está en "Envío Local Pasto" y en "urbano 24 h"; Arauca y Florencia, en "Nacional 1" y en "otras zonas". El cliente puede ver precios contradictorios. Hay que depurar las listas de `filters_by_cities_shipping_method`.
- **Plugins desactualizados:**
  - Wompi 3.2.0 → 3.2.1
  - Flexible Shipping 6.13.3 → 6.13.7
  - MailPoet 5.42 → 5.45
  - Elementor 4.3.5 → 4.3.6
  - Pro Elements 4.3.0 → 4.3.2
  - OceanWP 4.2.7 → 4.2.8
  - Site Kit, Yoast, WPCode, All-in-One Migration y otros, menores
  
  Además, el mu-plugin "Hostinger Smart Auto Updates" puede actualizar sin pruebas y romper el checkout. Conviene una ventana de actualización con copia de seguridad.
- **Avisos de inventario** van a un correo de Findcor, no a Pahubi.
- **Retención de 60 min:** se puede dejar. Si se quiere evitar casos como el #3981, que pagó a los 78 min, se puede subir a 90–120 min sin costo real, porque el inventario sobra.

### 🟢 Bajo
- El checkout solo muestra el logo de Wompi. Agregar los logos de Nequi, PSE y Bancolombia junto al botón ayudaría a la confianza.
- Hay 2.396 revisiones guardadas en la base de datos. Conviene limpiarlas.
- El registro del plugin Wompi está activo. Está bien para diagnosticar ahora; después conviene apagarlo.
- El precio del contexto de marketing ($32.178 / $28.644) no coincide con el de la tienda ($32.200 / $28.700). Es un tema de redondeo con IVA: actualizar `product-marketing.md`.

## Lo que está bien
- WooCommerce 11.2.1 (al día), WordPress 7.1.4, PHP 8.2, HPOS activo y la atribución de pedidos activa. Los pedidos sí guardan `_wc_order_attribution_utm_*`, la URL de entrada, el dispositivo y las páginas de la sesión.
- El checkout es **clásico (shortcode)**, no por bloques, y es compatible con el Checkout Field Editor.
- El tema no tiene plantillas desactualizadas (`has_outdated_templates: false`). Los overrides de OceanWP (content-single-product, title, product-image, loop-start) están al día, y el mini-cart de Pro Elements no declara versión.
- Wompi está en modo producción (testmode no). Su descripción menciona Nequi, PSE, Daviplata, Bancolombia y tarjeta. El botón dice "Pagar de forma segura". La contraentrega y la transferencia están desactivadas, según la política de la empresa.
- La integración con Wompi funciona: los pagos aprobados se registran en 1 a 8 minutos.
- Se puede comprar sin crear cuenta. Departamento y ciudad son listas. Los términos están plegados.
- Carrito y checkout no van en caché (`no-cache, no-store, private`). LiteSpeed Cache está inactivo, como decidió el equipo.
- En inicio, tienda, ficha, carrito y checkout solo aparece el WhatsApp correcto, **+57 300 5060274**. No se encontró 312 6062630 ni 300 5060272.
- El envío local de Bogotá cuesta $12.000 hasta 5 kg, es decir, el mismo para 1 o 2 combos.

## Guion de prueba manual (celular Android con datos móviles, sin pagar)
Para hacer en Chrome y también dentro del navegador de Instagram, porque los compradores de E9 llegaron desde la app.
1. Abrir el enlace de un anuncio de E9, o `pahubi.com/tienda/?utm_source=meta&utm_medium=paid_social&utm_campaign=prueba`. Cronometrar cuánto tarda en verse el primer producto.
2. Agregar un Combo Pañitos e ir al carrito. Anotar qué envío muestra antes de elegir ciudad.
3. Cambiar la dirección a Ibagué, Pereira, Pasto y Chía, una por una. Anotar el envío y si aparecen 1 o 2 opciones. Repetir con 2 combos.
4. Ir a finalizar compra:
   - Contar cuánto hay que bajar hasta el botón.
   - Comprobar que el teclado sea numérico en cédula y teléfono.
   - Dejar el correo mal escrito y ver si avisa al salir del campo o solo al tocar el botón.
   - Elegir "Bogotá Alrededores y Sabana" y ver qué ciudades salen.
5. Tocar "Pagar de forma segura" con datos de prueba reales del empleado (no de un cliente):
   - Anotar si se abre la ventana o página de Wompi, cuánto tarda y si el total coincide.
   - **No pagar.** Cerrar Wompi y volver a la tienda: anotar qué mensaje ve el cliente, si hay un botón para reintentar o elegir otro medio, y si llega algún correo o WhatsApp en los siguientes 120 min.
6. Repetir el paso 5 eligiendo PSE y Nequi dentro de Wompi, hasta la pantalla del banco o de la app, sin aprobar. Anotar si da algún error.
7. Opcional, solo si Ivan lo aprueba: hacer un pago real con el monto mínimo (sachet individual) y luego un DECLINED a propósito, por ejemplo con una tarjeta sin cupo. Ver qué pantalla queda y si se puede reintentar sin llenar todo otra vez.
8. Con Meta Pixel Helper o Events Manager → Probar eventos, contar cuántos `Purchase` y `InitiateCheckout` se disparan en el paso 5 y en la página de gracias del paso 7.

Los pedidos de prueba del paso 5 quedan "Pendientes" y se cancelan solos. Hay que avisarle a Jhoana para que no los gestione.

## Hechos / Hipótesis / Datos que faltan
**Hechos (API de Woo y HTML público):**
- Pedidos: 71 creados, 33 pagados, 28 por tiempo agotado sin transacción y 10 DECLINED. Los clientes pagan en un 88 % en Bogotá urbana y en un 46 % fuera. Hubo 5 reintentos exitosos.
- Configuración: la retención de inventario es de 60 min, los DECLINED se cancelan de inmediato y el webhook 31 está desactivado. Los avisos de cancelación van a Findcor. El texto "+ envío desde $11.100" no coincide con ninguna tarifa. Los combos pesan entre 1,46 y 1,93 kg.
- Pauta y velocidad: E9 aterriza en `/tienda/`. Los videos de 23,4 MB y 16,3 MB siguen en el inicio y el TTFB va de 1,7 a 3,0 s.

**Hipótesis (por verificar):**
- El envío fuera de Bogotá, que se ve por primera vez en el checkout o en Wompi, es la causa principal del abandono fuera de Bogotá.
- Parte de los pedidos por tiempo agotado vienen de una falla al abrir Wompi, por el caso de 12 intentos sin transacción.
- La inflación del Pixel viene del doble plugin de Meta o de Purchase en el navegador.
- El checkout largo afecta más en celular.

**Datos que faltan (FALTA):**
- Visitas, carrito y checkout por día y por fuente: GA4 (Site Kit `GT-MKRZ285S`), Jetpack WooCommerce Analytics o CartBounty. Hay que pedir acceso o una captura.
- Transacciones de Wompi con su medio (Nequi, PSE, tarjeta o Daviplata) y el motivo del rechazo.
- Registro del plugin Wompi.
- PageSpeed móvil (la API dio 429). Hay que repetirlo mañana o con una llave de API.
- Si CartBounty envía recordatorios.
- Si el cliente recibe el correo "Tu pedido fue cancelado". La plantilla está activa, pero las notas no lo distinguen del aviso a la tienda.
- Qué ve el cliente al volver de Wompi.
- Si la cédula es obligatoria para la facturación electrónica.

Nota de transparencia: para leer el formulario real del checkout, se agregó 1 Combo Pañitos a un carrito anónimo con una petición GET normal de visitante. No se llenó ningún formulario ni se creó ningún pedido. Ese carrito puede aparecer en CartBounty como carrito anónimo y como un AddToCart en Meta o GA4 el 3 nov alrededor de las 15:15.

## Orden recomendado: las 5 cosas a arreglar primero
1. **Diagnosticar los pedidos que no llegan a Wompi** (bajo esfuerzo, solo lectura): exportar las transacciones de Wompi del 5 sep al 3 nov, leer el registro del plugin y hacer los pasos 1 a 6 del guion en Android y en el navegador de Instagram.
2. **Hacer visible y coherente el envío** (bajo para los textos, Ivan para la tarifa): corregir "desde $11.100", poner la tabla por zona en la ficha y el carrito, y pedir la ciudad antes de mostrar el costo. Ivan decide la tarifa fuera de Bogotá para 1 o 2 combos.
3. **Recuperar pedidos caídos todos los días** (bajo): avisos de cancelado y fallido al correo de Pahubi, reactivar el webhook de Qubit con un token nuevo, y que ventas escriba desde el +57 300 5060274 a cada pedido caído del día. Con los datos de 60 días, recuperar 1 de cada 3 equivaldría a unos 5 clientes y $330.000.
4. **Dejar reintentar el pago sin volver a llenar el formulario** (medio): que un DECLINED quede como pedido fallido con botón "intentar con otro medio", y acortar el formulario (documento al final o fuera, sin país, código postal ni razón social).
5. **Ajustar la página de aterrizaje y el peso del inicio antes de volver a pautar** (medio): anuncios a la ficha del combo, no a `/tienda/`; videos de menos de 2 MB y PNG en WebP. **No subir pauta** hasta cerrar los puntos 1 a 3.
