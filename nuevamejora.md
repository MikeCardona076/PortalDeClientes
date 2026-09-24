# Nueva mejora: detalle por ruta y retrasos

**Estado:** especificación de la mejora, pendiente de implementación.

## 1. Objetivo

Mejorar el detalle de cada cliente para que permita revisar sus indicadores y el comportamiento de sus rutas dentro de la UDN correspondiente.

La mejora debe mostrar, por ruta, los servicios, retrasos, Nivel de Servicio y Calidad de Ruta. Al seleccionar el número de retrasos, se debe abrir el detalle de los servicios retrasados con sus horarios programados, horarios reales y diferencias.

## 2. Reglas confirmadas

- **UDN:** significa `BusinessUnit`.
- La UDN activa del sistema actualmente es `set_tj2`.
- Todas las plantas, grupos y rutas que se están mostrando pertenecen a `set_tj2`.
- No se debe crear una entidad nueva llamada `Planta` si ese término sólo se refiere a la UDN actual.
- `GrupoCliente` representa el grupo de rutas/cliente recibido desde la API.
- La semana operativa es de **lunes a domingo**.
- Las semanas se deben representar por su calendario ISO y conservar el cruce entre semana 52 y semana 1, incluyendo los días que quedan en el año calendario anterior o posterior.
- Los servicios se asignarán a la semana según la fecha de inicio del servicio.

## 3. Flujo de navegación

1. El usuario entra a la matriz principal, donde ve los clientes organizados por semana.
2. Selecciona una celda de un cliente y una semana.
3. La aplicación abre el detalle de ese cliente, esa semana y la UDN `set_tj2`.
4. En el detalle se muestran los indicadores generales y la tabla de rutas.
5. Si una ruta tiene retrasos, el usuario hace clic en el número de retrasos.
6. Se abre el detalle de los servicios retrasados de esa ruta, cliente, semana y UDN.

Ejemplo de URL de destino:

```text
/cliente/?cliente=FLEX&udn=set_tj2&anio=2026&semana=34&window=14d
```

## 4. Matriz principal

Actualmente la matriz muestra una fila por `Cliente`. Para la operación actual se mantendrá esa estructura, pero se mostrará explícitamente la UDN `set_tj2` para evitar confusión.

La matriz tendrá en cuenta:

- Cliente.
- Semana.
- Total de viajes.
- Nivel de Servicio.
- Calidad de Ruta, según la ventana seleccionada (`7d` o `14d`).
- UDN=`set_tj2`.

Si en el futuro se incorporan otras UDN, la vista deberá permitir filtrar o separar por `BusinessUnit` sin cambiar la lógica de las rutas ni de los retrasos.

## 5. Tabla del detalle del cliente

La tabla actual `Detalle por ruta (IN/N)` se cambiará a:

**Detalle por ruta y servicio (IN/N)**

La tabla tendrá, por cada ruta:

- Ruta.
- Grupo o cliente, cuando sea necesario para distinguir rutas.
- Descripción.
- Número de servicios.
- Entradas elegibles para Nivel de Servicio.
- Número de retrasos.
- Nivel de Servicio por ruta.
- Calidad de Ruta, con la ventana `7d` o `14d` seleccionada.
- Indicador de fuente del dato: API o GPS.

El número de retrasos será un enlace o botón cuando sea mayor que cero. Al pulsarlo, sólo se mostrarán los retrasos de esa ruta y de esa semana.

## 6. Detalle de retrasos

El detalle debe mostrar las siguientes columnas, en este orden:

1. `id`
2. `Fecha inicio`
3. `Fecha fin`
4. `Ruta`
5. `Cliente`
6. `UDN`
7. `Veh`
8. `Operador`
9. `Nómina`
10. `Prog ini`
11. `Real ini`
12. `Dif ini`
13. `Prog fin`
14. `Real fin`
15. `Dif fin`
16. `Diagnóstico Inicio`
17. `Diagnóstico Fin`

El detalle se filtrará obligatoriamente por:

- UDN.
- Cliente.
- Semana.
- Grupo/ruta.
- Servicio marcado como retraso.

No se deben mostrar datos de otra UDN aunque el usuario cambie los parámetros de la URL.

## 7. Mapeo de horarios y diferencias

La fuente principal actual es el reporte `rid=5`, complementado con los datos de `get_trips_eta` cuando sea necesario.

| Columna visible | Campo probable | Uso |
|---|---|---|
| Fecha inicio | `start_date` | Fecha real/inicial del servicio |
| Fecha fin | `end_date` | Fecha final del servicio |
| Ruta | `ID Ruta` o `service_id` | Identificador de ruta |
| Cliente | `group` y `client_base(group)` | Cliente mostrado |
| UDN | `bunit` | BusinessUnit de la sincronización |
| Veh | `car` | Vehículo |
| Prog ini | `start_time` | Hora programada de inicio |
| Real ini | `start_eta` | Hora real de inicio |
| Dif ini | `Real ini - Prog ini` | Diferencia de inicio en minutos |
| Prog fin | `end_time` | Hora programada de llegada |
| Real fin | `end_eta` | Hora real de llegada |
| Dif fin | `Real fin - Prog fin` | Diferencia de llegada en minutos |
| Operador | `operador` | Nombre o identificador del operador |
| Nómina | `no. de nomina` | Número o identificador de nómina |
| Diagnóstico Inicio | Calculado | `Retrasado` si `Δ_ini >= 4 min`; si no, `A tiempo` |
| Diagnóstico Fin | Calculado | `Retrasado` si `Δ_fin >= 4 min`; si no, `A tiempo` |

En la API de `rid=5`, `time` es el horario programado y `eta` el horario real. El código actual `end_eta - end_time` ya calcula `Real - Prog`: positivo significa tardío y coincide con el `Diagnostico Viaje` de la API, por lo que el KPI de retrasos se mantiene como hoy.

Las diferencias se calculan con la hora y un ajuste de medianoche; los valores desconocidos se muestran como `—`, no como `0`.

## 8. Persistencia y sincronización

Actualmente el reporte `rid=5` se agrega por cliente y luego se descartan las filas individuales (`apps/sync/services.py:214-231`). Para soportar el drilldown se requiere persistir los servicios normalizados.

La implementación debería separar:

- **Servicio de ruta:** una fila por servicio reportado, con sus horarios, ruta, vehículo, operador, diagnóstico y estado de retraso.
- **Resumen por ruta:** servicios, entradas, retrasos, NS y CR por UDN, cliente, grupo, ruta y semana.
- **CR por ruta:** se conserva `CRRutaSemana`, pero siempre asociado a la UDN y grupo correctos.
- **Resumen del cliente:** se conserva para la matriz, pero se calcula por la UDN seleccionada.

La sincronización debe ser idempotente: al repetir una semana, los servicios que ya no devuelve la API deben actualizarse o eliminarse, no permanecer como retrasos antiguos.

Los datos históricos que actualmente sólo existen como agregados requerirán un backfill desde la API para poder mostrar el detalle de retrasos.

## 9. Calendario ISO y cruce 52/1

`Semana.inicio` debe ser la fuente principal para ordenar y filtrar el histórico.

Se deben corregir especialmente:

- Consultas que sólo filtran por `year` y `week`.
- Históricos que ordenan únicamente por número de semana.
- Cálculo de 14 días, que debe comenzar exactamente siete días antes del lunes de la semana actual.
- Semanas que comienzan en diciembre pero pertenecen a la semana 1 del año ISO siguiente.

El número de semana que se muestre debe conservar la pertenencia ISO del día, aunque la fecha calendario pertenezca al año anterior.

## 10. Alcance por UDN

Todas las consultas del detalle deben filtrar por `BusinessUnit=set_tj2` de forma explícita, aunque actualmente sea la única UDN activa.

La matriz, el detalle, la tabla de rutas, el histórico y el drilldown de retrasos deben utilizar el mismo contexto de UDN.

## 11. Criterios de aceptación

- La matriz y el detalle identifican claramente `UDN: set_tj2`.
- La tabla se titula `Detalle por ruta y servicio (IN/N)`.
- Cada ruta muestra servicios, retrasos, NS y CR.
- El número de retrasos abre únicamente los servicios retrasados de la ruta seleccionada.
- El detalle contiene todas las columnas solicitadas.
- `Prog ini` y `Prog fin` muestran la programación; `Real ini` y `Real fin` muestran lo ejecutado.
- Las diferencias se calculan en minutos y muestran correctamente el signo.
- Los horarios desconocidos se muestran como `—`.
- Los servicios que cruzan medianoche conservan sus fechas correctas.
- El cruce de semana 52/1 no pierde días.
- Los datos de otra UDN nunca aparecen en el detalle de `set_tj2`.
- Un usuario sin autorización para la UDN o cliente no puede consultar sus datos.
- Repetir la sincronización no duplica servicios ni deja retrasos obsoletos.

## 12. Confirmaciones pendientes

Decisiones resueltas:

- Calendario: ISO lunes–domingo; `Sem Via` de Bustrax sólo se usa como referencia informativa.
- `time` = programado y `eta` = real. `Δ = Real − Prog`; positivo significa tardío.
- Operador = `operador`; Nómina = `no. de nomina`.
- `Diagnóstico Inicio` se calcula con `Δ_ini`: `Retrasado` desde 4 minutos.
- `Diagnóstico Fin` se calcula con `Δ_fin`: `Retrasado` desde 4 minutos.
- El detalle de retrasos se abre en un modal dentro de la página.
- El KPI de retrasos se mantiene como hoy (`record_quality == 1`); el modal muestra todos los `Δ >= 4 min`, incluyendo los que no tienen `record_quality`.
- La UDN activa es `set_tj2`.

Pendientes para después:

- Rotar tokens de Bustrax/Traffilog sólo si el escaneo de secretos los encuentra.
- Evaluar el reseteo masivo de contraseñas de usuarios.
- Ajustar umbrales o reglas si la validación con datos reales lo requiere.
