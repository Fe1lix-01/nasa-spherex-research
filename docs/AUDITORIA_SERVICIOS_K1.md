# K1 — Auditoría de servicios

## Alcance

Revisar los servicios asignados y proponer correcciones pequeñas,
comprensibles y verificables.

## Catálogo de objetos

### CAT-01 — Manejo inconsistente del registro remoto

- Archivo: apps/science-api/app/routers/objects.py.
- Problema: el listado repetía la captura de RemoteCatalogError y el
  detalle carecía de una captura específica.
- Impacto: el mismo registro inválido producía mensajes diferentes
  entre listado y detalle.
- Solución propuesta: conservar una captura específica por endpoint,
  antes de ValueError.
- Estado: corregido y probado localmente.
- Evidencia: seis casos aprobados que combinan tres registros inválidos
  con los endpoints de listado y detalle.
- Prueba: tests/test_remote_catalog.py::test_registro_invalido.

### CAT-02 — Conteos sin validación de coherencia

- Archivo: apps/science-api/app/schemas/objects.py.
- Problema: los modelos restringen los conteos a valores no negativos,
  pero no comprueban su correspondencia.
- Impacto: pueden aceptar totales contradictorios o diferentes de las
  listas incluidas en la respuesta.
- Solución propuesta:
  - Validar que observation_count sea la suma de los conteos local y remoto.
  - En el detalle, comprobar los conteos contra las listas correspondientes.
  - En ObjectsResponse, comprobar total contra la cantidad de objetos.
  - Revisar los usos existentes y el comportamiento cuando se omiten
    los conteos opcionales antes de introducir las validaciones.
- Estado: corregido y probado localmente.
- Evidencia: 47 casos aprobados entre las pruebas de esquemas,
  catálogo de objetos y registro remoto.
- Archivos modificados: app/schemas/objects.py y
  tests/test_objects_schemas.py.
- Evidencia: los modelos aceptaron un resumen con total 9 y subtotales
  cero, un detalle con una observación declarada y lista vacía, y un
  listado con total 3 y lista vacía.

### CAT-03 — Detectores sin restricción en el resumen

- Archivo: apps/science-api/app/schemas/objects.py.
- Problema: detectors utiliza list[str] y acepta valores como D9.
  El modelo de observaciones locales restringe el detector a D1–D6.
- Impacto: el contrato del resumen permite detectores que las
  observaciones locales no admiten.
- Solución propuesta: reutilizar el tipo de detector del modelo existente
  o acordar una definición compartida y comprobar su compatibilidad
  con las observaciones remotas.
- Estado: corregido y probado localmente.
- Solución aplicada: se definió Detector en app/schemas/observations.py
  y se reutilizó en AstronomicalObjectSummary.
- Evidencia: 57 casos aprobados entre esquemas, catálogo y registro remoto.
  Incluyen aceptación de D1–D6 y rechazo de detectores no admitidos.
- Evidencia: AstronomicalObjectSummary aceptó detectors=["D9"].

### CAT-04 — Identidad inconsistente entre variantes de mayúsculas

- Archivo: apps/science-api/app/services/objects.py.
- Problema: M101 y m101 se agrupaban como objetos distintos.
- Impacto: duplicación de objetos e identificadores.
- Solución aplicada: agrupar mediante casefold y elegir de forma
  determinista el nombre entre las variantes presentes.
- Compatibilidad: una única escritura conserva su ID. Los IDs de las
  variantes locales presentes permiten consultar el objeto agrupado.
- Limitación: los identificadores de variantes eliminadas del catálogo
  requieren un registro histórico para garantizar su conservación.
- Estado: corregido y probado localmente, pendiente de revisión.
- Evidencia: 64 pruebas relacionadas aprobadas, incluidas agrupación,
  independencia del orden y compatibilidad de identificadores.

  ### CAT-05 — Disponibilidad conjunta de las fuentes del catálogo

- Archivos: app/services/objects.py y app/services/remote_catalog.py.
- Comportamiento: el directorio local es obligatorio. El registro remoto
  es opcional, pero debe ser válido cuando está presente.
- Impacto: un directorio local ausente o un registro remoto inválido
  bloquean tanto el listado como el detalle, incluso si la otra fuente
  contiene datos utilizables.
- Decisión propuesta: conservar este comportamiento para la entrega
  actual y documentarlo explícitamente.
- Justificación: el servicio mantiene una respuesta de error cuando
  no puede construir el catálogo con sus fuentes configuradas.
- Estado: comportamiento confirmado y documentado para revisión.
- Evidencia: cinco casos aprobados que comprueban registro remoto
  ausente, directorio local ausente con registro remoto válido y
  registro remoto inválido con archivos locales disponibles.
- Corrección de código: ninguna; se añadieron pruebas de la política.

### CAT-06 — Alcance del conteo de observaciones

- Archivos: app/services/objects.py y app/schemas/observations.py.
- Comportamiento: observation_count suma los registros locales y remotos
  asociados al objeto.
- Limitación: los archivos locales carecen del identificador de procedencia
  IRSA necesario para detectar coincidencias entre ambas fuentes.
- Impacto: el total es coherente con las listas, pero puede contar dos
  registros relacionados con el mismo producto científico.
- Decisión propuesta: conservar el conteo de registros y documentar
  su significado.
- Solución futura, si se requiere unicidad: registrar la procedencia
  de los archivos locales y definir la correspondencia con product_id
  antes de aplicar una deduplicación.
- Estado: alcance confirmado y documentado para revisión.
- Evidencia: test_integracion_remota_sin_duplicar_objeto comprueba la
  suma local/remota; las validaciones de CAT-02 comprueban su coherencia.
- Corrección de código: ninguna en este punto.

### CAT-07 — Especialización de la vista científica de M101

- Archivos: app/services/objects.py, app/services/remote_catalog.py,
  app/schemas/remote_catalog.py y app/routers/science_preview.py.
- Comportamiento: el registro remoto admite M101 y el catálogo asocia
  una vista científica del canal 63.
- Impacto: incorporar otros objetos o canales requiere cambios de código.
  La presencia de science_preview describe una operación soportada,
  pero no garantiza que el FITS esté disponible en ese momento.
- Decisión propuesta: conservar la especialización para el alcance
  actual y documentar el significado de science_preview.
- Configuración existente: M101_FITS_PATH permite indicar la ubicación
  local del cubo.
- Solución futura, si se amplía el alcance: separar la configuración
  de productos y canales de la lógica general del catálogo.
- Estado: comportamiento revisado y documentado para revisión del equipo.
- Evidencia: el catálogo asocia la vista por nombre; el endpoint comprueba
  la configuración y existencia del FITS. Las pruebas de science_preview
  cubren los casos de configuración y archivo ausentes.
- Corrección de código: ninguna en este punto.

## Consultas IRSA

### IRSA-01 — Construcción de la fecha fuera de la validación final

- Archivo: apps/science-api/app/services/irsa.py.
- Problema: normalize_observations construye IrsaObservation con
  start_utc="pendiente" y después lo modifica con model_copy(update=...).
  Esa actualización omite la validación de Pydantic.
- Impacto: el objeto final no se valida completo en una única construcción.
  El modelo start_utc también acepta cualquier cadena.
- Solución aplicada: se calcula start_utc antes de construir
  IrsaObservation y se elimina model_copy(update=...).
- Estado: construcción corregida y probada localmente.
- Evidencia: 20 pruebas de tests/test_irsa.py aprobadas.
- Alcance pendiente de revisión: start_utc continúa declarado como str.
  Una validación adicional de su formato debe conservar la compatibilidad
  con las fechas astronómicas generadas por Astropy.

  ### IRSA-02 — Lógica HTTP repetida entre TAP y SIA

- Archivos: app/clients/irsa.py y app/clients/sia.py.
- Problema: ambos clientes repiten el bucle de solicitudes, clasificación
  de errores, reintentos y esperas.
- Impacto: una corrección de esa política puede aplicarse a un cliente
  y quedar pendiente en el otro.
- Solución propuesta: después de cubrir ambos clientes con pruebas,
  evaluar la extracción de la política HTTP compartida, conservando
  las consultas y los parsers específicos de TAP y SIA.
- Estado: duplicación confirmada, propuesta pendiente de revisión.
- Evidencia: comparación de fetch_observations_csv y fetch_observations.
- Corrección de código: ninguna en esta etapa.

### IRSA-03 — Cobertura HTTP pendiente del cliente TAP

- Archivos: app/clients/irsa.py y tests/test_irsa.py.
- Problema: las pruebas actuales cubren transformación, parámetros,
  estructura y documentación, pero no ejecutan los reintentos y errores
  HTTP del cliente TAP.
- Impacto: un cambio en el cliente podría alterar esos comportamientos
  sin ser detectado por las pruebas actuales.
- Solución propuesta: utilizar un servidor HTTP local para comprobar
  éxito, error no reintentable, error transitorio, recuperación y timeout.
- Estado: cobertura añadida y probada localmente.
- Solución aplicada: servidor HTTP local controlado para ejecutar
  solicitudes reales del cliente TAP.
- Evidencia: 29 pruebas de tests/test_irsa.py aprobadas.
  Incluyen nueve casos HTTP nuevos de éxito, errores permanentes,
  errores transitorios, recuperación y timeout.
- Archivos modificados: app/clients/irsa.py y tests/test_irsa.py.

### IRSA-04 — Timeouts definidos dentro del método

- Archivo: app/clients/irsa.py.
- Comportamiento: fetch_observations_csv crea internamente timeouts
  de conexión, lectura, escritura y pool.
- Impacto: ajustar esos tiempos o probarlos requiere modificar
  la construcción interna del cliente.
- Solución propuesta: permitir una configuración explícita y validada,
  conservando los valores actuales como predeterminados.
- Alcance: documentar que estos timeouts corresponden a operaciones
  de red. La política actual no define un plazo total para la consulta
  completa con todos sus reintentos.
- Solución aplicada: IrsaClient acepta un httpx.Timeout opcional.
  Al omitirlo conserva los tiempos predeterminados anteriores.
- Estado: configuración desde código implementada y comprobada
  para el timeout de lectura.
- Limitación: sigue sin definirse un plazo total para todos los intentos.

### SIA-01 — Coherencia entre consulta y respuesta

- Archivo: `apps/science-api/app/schemas/sia.py`.
- Problema: SiaResponse validaba los conteos, pero permitía que la
  colección de la respuesta o la colección y banda de las observaciones
  no coincidieran con la consulta.
- Impacto: otros consumidores del modelo podían construir respuestas
  inconsistentes, aunque el servicio actual realizaba esas comprobaciones.
- Solución aplicada: validar que la colección de la respuesta y la
  colección y banda de cada observación coincidan con la consulta.
- Verificación: cinco pruebas nuevas, sin consultas externas, para una
  respuesta válida y cuatro escenarios inconsistentes.
- Resultado: las 28 pruebas de tests/test_sia.py aprobaron.
- Estado: corregido y probado localmente; pendiente de revisión del equipo.

### SIA-02 — Manejo de valores externos inválidos

- Archivo revisado: `apps/science-api/app/services/sia.py`.
- Riesgo revisado: recibir fechas, coordenadas, identificadores,
  enlaces o formatos inválidos desde el proveedor.
- Impacto potencial: aceptar metadatos inválidos o propagar
  excepciones sin controlar.
- Resultado: los ocho escenarios probados producen IrsaResponseError.
- Solución: no fue necesario modificar el servicio; se añadieron
  pruebas de regresión en `tests/test_sia.py`.
- Verificación: 8 casos aprobados, sin consultas externas.
- Verificación conjunta: las 36 pruebas de tests/test_sia.py aprobaron.
- Estado: comportamiento comprobado para los escenarios probados.

### SIA-03 — Configuración del timeout y política HTTP compartida

- Archivo: apps/science-api/app/clients/sia.py.
- Comportamiento: SiaClient utiliza directamente la constante
  SIA_TIMEOUT. No permite configurar el timeout por instancia.
- Impacto: consumidores que necesiten otros tiempos deben modificar
  la configuración global del módulo. Las pruebas de timeout actuales
  también sustituyen esa constante.
- Solución propuesta: permitir un httpx.Timeout opcional en el
  constructor, conservando SIA_TIMEOUT como valor predeterminado.
- Duplicación relacionada: el bucle HTTP repite la política del cliente
  TAP, descrita en IRSA-02. Cualquier extracción compartida debe
  conservar los parámetros y parsers específicos de cada protocolo.
- Limitación: los timeouts de red no establecen un plazo total para
  todos los intentos y sus esperas.
- Estado: hallazgo confirmado; propuesta pendiente de revisión.
- Corrección de código: ninguna en este punto.

### REM-01 — Errores de lectura del registro remoto

- Archivos: app/services/remote_catalog.py y app/routers/objects.py.
- Riesgo revisado: registro con codificación UTF-8 inválida o una
  carpeta situada donde se espera el archivo JSON.
- Impacto potencial: excepciones sin controlar o exposición de rutas locales.
- Resultado: el servicio produce RemoteCatalogError y los endpoints
  de listado y detalle responden con HTTP 503 y un mensaje genérico.
  Las respuestas comprobadas no incluyen la ruta del registro.
- Solución: conservar el comportamiento existente y añadir pruebas
  de regresión en tests/test_remote_catalog.py.
- Verificación: cuatro casos aprobados, sin consultas externas.
- Verificación conjunta: las 25 pruebas de tests/test_remote_catalog.py aprobaron.
- Estado: comportamiento comprobado para los escenarios probados.
- Corrección del servicio: ninguna.
### REM-02 — Validaciones repetidas entre modelos

- Archivos: app/schemas/remote_catalog.py y app/schemas/sia.py.
- Problema: RemoteCatalogSnapshot repetía las comprobaciones de
  colección y banda realizadas por su modelo anidado SiaResponse.
- Impacto: mantener las mismas reglas en dos lugares podía generar
  diferencias al modificar únicamente una de ellas.
- Solución aplicada: centralizar la coherencia de colección y banda
  en SiaResponse. RemoteCatalogSnapshot conserva la comprobación
  de productos duplicados.
- Verificación: cuatro pruebas nuevas comprueban el rechazo de
  registros incoherentes. La prueba existente de duplicados se conserva.
- Resultado: las pruebas de SIA y del registro remoto aprobaron.
- Estado: corregido y probado localmente; pendiente de revisión del equipo.

### REM-03 — Clasificación amplia de errores de previsualización

- Archivos: app/services/remote_previews.py y
  app/services/frame_images.py.
- Problema: render_cutout_png captura cualquier Exception durante
  la lectura, validación y generación del PNG, convirtiéndola
  en IrsaResponseError.
- Impacto: un fallo interno al generar el PNG podría clasificarse
  como un problema del recorte externo.
- Solución propuesta: separar los errores esperados de lectura y
  validación de los fallos internos de generación. Conservar el
  rechazo controlado de imágenes sin datos finitos.
- Verificación: las 12 pruebas de test_remote_previews.py aprobaron.
  Cubren parámetros, productos inexistentes, PNG válido y recortes
  inválidos.
- Limitación: estas pruebas no reproducen un fallo interno del
  codificador PNG; su clasificación no está verificada.
- Decisión para esta auditoría: conservar el comportamiento actual
  y entregar la mejora propuesta para revisión.
- Corrección de código: ninguna.

### REM-04 — Clasificación de URLs malformadas

- Archivo: app/clients/irsa_cutouts.py.
- Problema: urlsplit podía lanzar ValueError ante una URL malformada.
  El router podía clasificarlo como un problema del catálogo.
- Solución aplicada: capturar ValueError al interpretar la URL y
  convertirlo en IrsaResponseError, conservando las restricciones
  existentes de origen, ruta, extensión, consulta y fragmento.
  no verifica por sí sola la respuesta HTTP del endpoint.
- Impacto: al utilizar directamente el cliente, una URL malformada
  podía propagar ValueError en lugar de IrsaResponseError.
- Verificación: las 14 pruebas del cliente aprobaron. Dos pruebas
  del endpoint confirmaron HTTP 503 para un registro con URL
  malformada y HTTP 502 para una URL de origen no permitido.
- Alcance: el registro valida access_url con Pydantic antes de llamar
  al cliente. La corrección del cliente protege también su uso directo.
- Estado: corregido y probado localmente; pendiente de revisión del equipo.

## Comunicación entre routers y servicios

### ARQ-01 — Separación de responsabilidades

- Archivos revisados:
  - app/routers/objects.py
  - app/routers/irsa.py
  - app/routers/sia.py
  - app/routers/remote_previews.py
  - app/services/objects.py
  - app/services/irsa.py
  - app/services/sia.py
  - app/services/remote_catalog.py
  - app/services/remote_previews.py
- Resultado: los servicios realizan las operaciones de catálogo,
  consulta y procesamiento. Los routers reciben los parámetros
  HTTP y traducen los errores a respuestas para el consumidor.
- Correspondencias revisadas:
  - Objeto o producto inexistente: HTTP 404.
  - Catálogo o registro no disponible: HTTP 503.
  - Respuesta externa inválida: HTTP 502.
  - Servicio externo no disponible: HTTP 503.
  - Timeout externo: HTTP 504.
- Evidencia: revisión del código y pruebas de endpoints existentes.
  Las 56 pruebas relacionadas con recortes y registros remotos aprobaron.
- Limitación conocida: la clasificación amplia de errores del
  generador PNG está descrita en REM-03.
- Corrección adicional: ninguna.

### ARQ-02 — Dependencias de FastAPI en los servicios

- Archivos: los cinco servicios enumerados en ARQ-01.
- Resultado: no se encontraron importaciones directas de FastAPI
  o Starlette, ni construcción de HTTPException o respuestas HTTP.
- Impacto: estos servicios pueden utilizarse desde scripts y pruebas
  sin depender de una solicitud HTTP.
- Decisión: conservar esta separación al realizar cambios futuros.
- Verificación: inspección de importaciones y del manejo de errores.
- Corrección de código: ninguna.

## Correspondencia de modelos y respuestas

### MOD-01 — Validaciones adicionales entre campos

- Archivos: app/schemas/irsa.py y app/schemas/objects.py.
- Problema: IrsaResponse valida los conteos, pero no comprueba que
  cada observación tenga la banda solicitada. Esa comprobación
  actualmente corresponde al servicio.
  AstronomicalObjectDetail valida las cantidades, pero no exige
  remote_query y remote_association cuando existen registros remotos.
- Impacto: los modelos utilizados directamente pueden aceptar
  combinaciones que los servicios actuales no generan.
- Solución propuesta: definir y probar esas reglas entre campos
  antes de incorporarlas a los modelos.
- Verificación: comparación de los modelos con la construcción
  de respuestas en los servicios.
- Estado: limitaciones identificadas; corrección propuesta para revisión.
- Corrección de código: ninguna.
- Limitación relacionada: start_utc continúa siendo una cadena;
  su validación adicional está descrita en IRSA-01.

### MOD-02 — Tipado genérico del servicio de objetos

- Archivo: app/services/objects.py.
- Problema: list_objects devuelve list[dict] y get_object devuelve
  dict o None, sin describir las claves y tipos del objeto.
- Impacto: las herramientas de análisis estático no pueden detectar
  fácilmente claves incorrectas o campos ausentes entre servicios.
  Los routers sí validan sus respuestas mediante Pydantic.
- Solución propuesta: evaluar TypedDict o modelos internos explícitos,
  conservando la diferencia entre resumen y detalle.
- Estado: hallazgo documentado para revisión.
- Corrección de código: ninguna.