# Criterios de experto para armar una pauta (todos los propósitos)

El bot lee este archivo en cada pauta (/vender, /seguidores, /pauta, /propuestas). Resume las
skills de marketing del proyecto (`.claude/skills/ads`, `ad-creative`, `cro` y `social`)
aplicadas a Pahubi y Eva.

**Regla de oro:** lo que dice nuestra propia historia (playbook_pautas.md, sección 7 y los datos
reales) pesa más que la regla general de un experto. Si chocan, gana nuestra historia y se dice.

## 0. Cómo escoger la publicación (vale para todo)

- **Siempre una publicación que ya existe.** No se graba nada nuevo para pautar; el bot escoge
  entre todas las publicaciones del último año (`publicaciones`), no solo las recientes.
- **Primero lo que ya probó que sirve para ESE propósito** (sección 7 del manual y `lo que ha
  servido`). Después, lo que la gente ya premió gratis: la pauta amplifica lo que funciona, no
  rescata lo que no (skill ads: "proven content + paid distribution").
- **Señales de que una publicación tiene con qué, de más a menos fuerte:**
  1. ya trajo ventas o seguidores en una pauta anterior;
  2. `compartidos` y `guardados` altos para su alcance (la gente la quiso pasar o volver a ver);
  3. `seg_vista_promedio` alto en reels (retiene);
  4. alcance orgánico por encima de lo normal de la cuenta.
  Un alcance alto por un evento local (llegamos a Pasto, Alkosto) no prueba que venda en otra
  ciudad: tenerlo en cuenta.
- **Que encaje con el propósito:** para vender, que muestre el producto y quite una objeción
  (¿tapa el inodoro?, ¿se deshace?, ¿sirve para adultos?) o sea del ángulo que ya vendió. Para
  seguidores, que dé ganas de ver más de la cuenta (serie, dato sorprendente, animal raro).
  Para alcance, que se entienda sin sonido y en 3 segundos.
- **Primero las que nunca se pautaron (`ya_se_pauto: false`).** Una publicación ya pautada tiene
  vistas y alcance inflados por la pauta y ese público ya la vio. Solo se vuelve a pautar si
  claramente no hay otra comparable sin pautar Y la pauta anterior dio buen costo; en ese caso
  decirlo en `por_que` ("ya se pautó en <fecha/red>, se repite porque…").
- **Vistas altas sin pauta** (`vistas` muy por encima de lo normal y `ya_se_pauto: false`) es la
  mejor señal de que el contenido engancha solo.
- **Ojo con los números:** Windsor (plan de prueba) congela las vistas de cada publicación en
  las del día que la leyó por primera vez. Una publicación que despegó días después aparece
  con números bajos (el colugo: 2.228 en Windsor, ~60 mil reales). Si la persona pega un link,
  esa es la publicación y no se discute; si dice cuántas vistas tiene, se le cree.
- **Reels antes que fotos** cuando hay uno parecido; la foto solo si es claramente mejor.
- **El gancho (3 primeros segundos):** imagen + primera frase + texto en pantalla. Para un
  producto de compra impulsiva, abrir con prueba (el producto funcionando) o una situación muy
  concreta. Que se vea nativo ayuda, pero no es obligatorio: Hombre Rudo está hecho con IA y vendió.
- En `por_que` decir por qué esa publicación y no la segunda mejor, con sus números.
- Si ninguna encaja bien, igual se escoge la menos mala y se dice por qué en el veredicto.

## 1. Chequeo antes de gastar (se responde punto por punto)

Cada punto queda ✅ (cumple), ⚠️ (dudoso o falta un dato) o ❌ (no cumple), con el dato que lo
prueba. Usar los puntos del propósito que corresponda.

### Vender (Pahubi)

1. **¿Se puede medir?** UTM, ficha del producto y ventas visibles en WooCommerce. Si no, no se
   pauta (skill ads: "INVESTIGATE gana sobre todo").
2. **¿La tienda cobra?** `salud_tienda_14_dias`, por cliente. Si menos del 60 % de los clientes
   que intentaron terminan pagando, la fuga está en el pago, no en el público: ❌ y ARREGLAR PRIMERO.
3. **¿La publicación tiene con qué vender?** Ver sección 0. Con ventas probadas (Hombre Rudo) es
   ✅. Sin ventas probadas pero con buenas señales es ⚠️ (PRUEBA BARATA). Un ángulo que ya se
   probó y no vendió (sensoriales, Nube Pañito, Gatoresplandor) es ❌.
4. **¿La ficha continúa la promesa?** Lo que dice el video debe verse arriba en la ficha, en el
   celular, dentro del navegador de Instagram (la E9: 1.985 sesiones, 0,8 % carrito).
5. **¿Alcanza la plata para saber algo?** Una prueba de ventas se juzga cuando gastó ~3 veces el
   costo por venta que podemos pagar. $30.000 solo mide costo por visita y carritos. El objetivo
   Ventas de Meta pide ~50 compras/semana para salir de aprendizaje; nunca llegamos, así que se
   juzga en WooCommerce.
6. **¿Cuánto podemos pagar por venta?** Margen por pedido: MISSING hasta que Ivan pase costos.
7. **¿Choca con otra pauta?** Una pauta de venta a la vez.
8. **Público:** amplio, que el contenido segmente. Con poca plata, Bogotá y la Sabana: ahí paga
   el 100 % de los clientes (nov 2026); fuera de las 6 ciudades el envío de $18.695 los espanta.

### Seguidores (Eva)

1. **¿La publicación ya demostró que trae gente nueva?** Despegó sola (alcance muy por encima de
   lo normal) o ya trajo seguidores pagada (zunzuncito, oso hormiguero).
2. **¿El perfil convence al llegar?** Las últimas publicaciones son del mismo tipo que la pautada;
   si alguien llega por un animal raro y encuentra otra cosa, no sigue.
3. **¿Objetivo correcto?** `seguidores` (visitas al perfil). `alcance` NO trae seguidores
   (Xpressa: 89 mil personas, ~8 seguidores).
4. **¿Costo dentro de lo normal?** Referencia del manual: IG ~$150–350 por seguidor; cortar si
   pasa de $500 a mitad de presupuesto.
5. **¿Choca con otra pauta de Eva?** Una a la vez por cuenta.

### Seguidores (Pahubi)

1. **¿La publicación da ganas de seguir la cuenta?** Útil o sorprendente (cómo se deshace, la
   duda del inodoro), no un anuncio de punto de venta ni de evento local.
2. **¿El perfil convence al llegar?** Las últimas publicaciones se ven cuidadas y dicen qué es Pahubi.
3. **Costo:** sin historia propia en Pahubi; usar las referencias de Eva y decir que es una prueba.

### Eva × Pahubi

1. **¿La publicación de Eva muestra o menciona a Pahubi?** Si no, NO TODAVÍA.
2. **¿Lleva #Publicidad y la etiqueta de colaboración pagada?** Si no, ⚠️ y decirlo.
3. **Objetivo alcance, no ventas:** el plástico (nov 2026) trajo ~700 visitas y 0 carritos.
4. **Medir:** personas alcanzadas y si suben las visitas o seguidores del perfil de Pahubi.

### Escoger entre TikTok e Instagram (Eva)

- Seguidores: TikTok salió más barato (~$130 por seguidor, frente a ~$286 la visita al perfil de IG).
- Alcance: TikTok ~$380 por 1.000 personas; IG ~$725 (Xpressa, nov 2026).
- En TikTok el mínimo es ~$20.000 por día: la prueba más chica es $60.000 en 3 días.
- Si el mejor video solo está en una de las dos redes, va en esa.
- Un video con `ya_se_pauto: true` tiene vistas infladas por la pauta (Xpressa, zunzuncito): no
  cuentan como éxito orgánico. Se juzga por lo que trajo esa pauta (manual, sección 7). Xpressa es
  de un tercero: no se usa para seguidores ni visibilidad de Eva.

### Alcance o interacción

1. **¿Se entiende sin sonido en 3 segundos?**
2. **¿Para qué sirve ese alcance?** Lanzamiento, marca o colaboración. Si lo que se quiere son
   seguidores o ventas, usar ese objetivo y decirlo.
3. **Costo de referencia:** por cada 1.000 personas (manual, sección 7).

## 2. Veredicto (uno solo, para cualquier propósito)

- **VA:** los puntos clave en ✅ y ninguno en ❌. Se propone la pauta con su prueba corta.
- **PRUEBA BARATA:** nada en ❌, pero hay ⚠️ (publicación sin prueba, datos que faltan). Se
  propone lo mínimo para aprender y qué número decide si se sigue.
- **ARREGLAR PRIMERO:** la medición o la tienda fallan. Se dice qué arreglar.
- **NO TODAVÍA:** ninguna publicación existente encaja bien. Se dice por qué.

**En todos los casos se arma la pauta completa** con la mejor publicación disponible y queda
el botón ✅. El veredicto es la recomendación; quien aprueba decide (el usuario lo pidió así).

## 3. Configuración (lo decide Claude, dentro de las opciones permitidas)

- **Objetivo** según el propósito (manual, sección 1).
- **Presupuesto y días:** primero una prueba corta (3–5 días). Nunca subir más del 20 % de una vez.
  No juzgar antes de ~5 días.
- **Público:** de las opciones permitidas; el más amplio que tenga sentido para el propósito.
- **Producto (venta):** la ficha que corresponde a lo que muestra la publicación.

## 4. Cómo se juzga después

- Leer el embudo por etapas:
  - mucha vista y pocos clics → el gancho;
  - clics sin carritos → la ficha;
  - carritos sin ventas → el pago y el envío.
- Nunca pausar sin con qué reemplazar; si no hay reemplazo, la plata vuelve a lo que funciona.
- Editar un anuncio que funciona reinicia el aprendizaje: mejor lanzar uno nuevo al lado.

## 5. Al responder

Separar **hechos** (con su número), **hipótesis** (lo que creemos y cómo se comprueba) y **datos
que faltan** (MISSING, sin inventarlos).
