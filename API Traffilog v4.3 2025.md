# Traffiiog 





## Contenido 

|Introducción ........................................................................................................................... 3|
|---|
|Métodos.................................................................................................................................. 5|
|Login ............................................................................................................................... 5|
|Vehículos ............................................................................................................................ 6|
|Get data .......................................................................................................................... 6|
|Viajes ................................................................................................................................... 9|
|Vehicle trips .................................................................................................................... 9|
|Trip locations ................................................................................................................ 11|
|Trip events .................................................................................................................... 13|
|Vehicle Trips Extended ................................................................................................. 15|
|Eventos ............................................................................................................................. 19|
|Incremental events ....................................................................................................... 19|
|Parámetros ....................................................................................................................... 22|
|Get parameters ............................................................................................................. 22|
|Get parameter values ................................................................................................... 23|
|Geocercas ......................................................................................................................... 25|
|Get layers ...................................................................................................................... 25|
|Get geometry ................................................................................................................ 26|
|Conductores...................................................................................................................... 29|
|Get drivers .................................................................................................................... 29|
|Políticas de uso ..................................................................................................................... 32|





2 





### Introducción 

La presente documentación contiene descripciones, sintaxis y ejemplos de uso para cada una de las acciones. 

La API de Traffilog utiliza solicitudes HTTP tipo POST con argumentos y respuestas en formato JSON. Cada solicitud debe incluir un token de sesión válido. El token de sesión se obtiene al hacer una llamada al método de Login. 

No existe una interfaz web para acceder a API. El endpoint de la API, la dirección URL a la cual deben enviarse las solicitudes, es la siguiente. 

<u>https://api.traflog.mx/clients/json</u> 

#### Encabezados 

Cada solicitud debe incluir el siguiente encabezado: 

_Content-Type: application/json_ 

#### Formato de Fecha y Hora 

Todas las fechas de la API están dadas en UTC o en UTC + DST (Daylight Saving Time) según se indique en la descripción del campo y están en la notación dada por la norma ISO 8601. 

yyyy-mm-ddThh:mi:ss.mmm _(2015-05-15T15:50:38.000)_ 

#### Unidades 

Los campos de velocidad y distancia de cada respuesta están dados en la unidad de medida establecida en las preferencias de la cuenta de usuario en la plataforma Traffilog. 

_Velocidad -km/h -MPH Distancia -KM -Millas_ 



3 

Trafti/oHalleck 

@) Numaris; 

> ayo 





### Métodos 

##### Login 

Esta solicitud proporciona el token de sesión que se debe enviar como parámetro en todas las solicitudes subsecuentes. 

Estructura: 

```
{
    "action": {
        "name": "user_login",
        "parameters": {
            "login_name": "<<usuario>>",
            "password": "<<contraseña>>"
        }
    }
}
```

Si el inicio de sesión es exitoso, esta será la respuesta devuelta por el servidor. 

```
{
    "response": {
        "properties": {
            "action_name": "user_login",
            "data": [{
                "session_token": "E2AD2F5E8CXXXXXX64",
                "profile_name": "default",
                "user_language": "",
                "application_url": "",
                "map_type": "google"
            }],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```



5 





#### Vehículos 

Get data 

Esta solicitud proporciona la información de geolocalización más reciente de toda la flota o de una unidad específica dependiendo de los parámetros enviados. 

```
{
    "action": {
        "name": "api_get_data",
        "parameters": [{
            "last_time": "",
            "license_nmbr": "",
            "group_id": "",
            "version": "4"
        }],
        "session_token": "<<session token>>"
    }
}
```

###### Parámetros de la solicitud: 

|Parámetro<br>last_time|Tipo<br>datetime|Atributo<br>Opcional|Descripción<br>La fecha y hora deben darse en el formato<br>de fecha especificado en la página 1 de<br>este documento.|
|---|---|---|---|
||||Para solicitar información de una unidad<br>|
|license_nmb<br>r|string|Opcional|específica. Si se deja en blanco, la<br>respuesta incluirá información de toda la<br>flota asociada a la cuenta.|
|group_id|number|Opcional|Para solicitar información de un grupo<br>específico.|
|version|number|Obligatorio|Indica la versión de la API y se debe incluir<br>especificando la versión 4. Si este campo se<br>deja en blanco, el servidor asumirá la<br>versión 1 por default, que se mantiene<br>activa por motivos de retrocompatibilidad<br>pero que presenta diferencias respecto a<br>los parámetros y sintaxis del presente<br>documento.|





6 





La estructura de la respuesta es la siguiente. 

```
{
    "response": {
        "properties": {
            "action_name": "api_get_data",
            "data": [
                {
                    "vehicle_id": "222222",
                    "unit_id": "111111",
                    "group_id": "40000",
                    "group_name": "PASAJE",
                    "client_id": "15555",
                    "client_name": "TRAFFILOG",
                    "unit_serial": "0000000007000009",
                    "license_nmbr": "TA-9999",
                    "chassis_number": "3HSXXXXX0XXXXXXXX",
                    "last_communication_time": "2021-01-04T21%3A46%3A20.897",
                    "last_position_time": "2021-01-04T21%3A45%3A59",
                    "latitude": "20.5739880",
                    "longitude": "-100.2669030",
                    "speed": "0.00",
                    "direction": "0",
                    "status": "2",
                    "last_event_time": "2021-01-04T21%3A28%3A27",
                    "last_event_type": "Ignition%20ON",
                    "current_driver": "306442",
                    "current_driver_number": "",
                    "driver_name": "1635",
                    "worker_id": "",
                    "current_drive": "57149923308",
                    "last_mileage": "663322.81"
                },
                {
                    …
                }
],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```

A continuación, se describen los parámetros incluidos en la respuesta. 

|Parámetro|Tipo|Descripción|
|---|---|---|
|vehicle_id|number|ID único del vehículo.|
|unit_id|number|ID único del dispositivo del vehículo.|
|group_id|number|ID único del grupo definido por Traffilog.|





7 





|group_name|string|Nombre del grupo correspondiente al ID.|
|---|---|---|
|client_id|number|ID único de cliente.|
|client_name|string|Nombre del cliente|
|unit_serial|string|Número de serie del dispositivo.|
|license_nmbr|string|Número económico del vehículo.|
|chassis_number|string|VIN del vehículo.|
|last_communication_time|datetime|Hora y fecha de la última recepción de<br>información del vehículo en UTC.|
|last_position_time|datetime|Hora y fecha de la última posición reportada por<br>el vehículo en GMT + DST.|
|latitude|number|Latitud de última posición.|
|longitude|number|Longitud de última posición.|
|speed|number|Última velocidad reportada.|
|direction|number|Rumbo / ángulo GPS.|
|status|number|Estatus posibles:<br>0 – Vehículo apagado.<br>1 – Vehículo encendido.|
|||2 – Vehículo encendido, motor en ralentí.|
|last_event_time|datetime|Hora y fecha del último evento reportado en<br>GMT + DST.|
|last_event_type|string|Descripción del último evento.|
|current_driver|number|ID del chofer actual (si el vehículo cuenta con<br>servicio de identificación de conductor).|
|current_driver_number|string|Código del chofer actual (si el vehículo cuenta<br>con servicio de identificación de conductor).|
|driver_name|string|Nombre del chofer actual (si el vehículo cuenta<br>con servicio de identificación de conductor).|
|worker_id|number|Nombre<br>del<br>empleado<br>(si<br>se<br>encuentra<br>registrado en los sistemas de Traffilog).|
|current_drive|number|Si el vehículo se encuentra actualmente en un<br>_viaje_.<br>|
|last_mileage|number|Última lectura recibida del odómetro.|





8 





#### Viajes 

##### Vehicle trips 

Esta solicitud proporciona la información sobre los viajes de un vehículo específico. 

```
 {
    "action": {
        "name": "get_vehicle_trips",
        "parameters": [{
            "vehicle_id": "-1",
            "license_number": "1017119",
            "from_date": "2016-12-27",
            "to_date": "2016-12-28",
        }],
        "session_token": "<<session token>>"
    }
}
```

Estos son los parámetros que pueden incluirse en la solicitud. 

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|vehicle_id|number|Condicional|ID único del vehículo. Al menos uno de<br>estos tres parámetros debe introducirse:<br>_vehicle_id_,_license_numbe_r o_driver_id_.|
|license_number|string|Condicional|Número económico del vehículo. Al menos<br>uno de estos tres parámetros debe<br>introducirse:_vehicle_id_,_license_number_o<br>_driver_id_.|
|driver_id|number|Condicional|ID del chofer. Si solamente se proporciona<br>este número, la respuesta puede incluir<br>viajes de más de un vehículo. Si este<br>parámetro se proporciona en combinación|
||||con<br>_vehicle_id_<br>_o_<br>_license_number_,<br>la<br>respuesta solamente incluirá viajes del<br>chofer en ese vehículo específico.|
|from_date|date|Opcional|Fecha de inicio de la consulta en formato<br>YYYY-MM-DD. Si no se proporciona una<br>fecha, la respuesta asumirá la fecha actual.|
|to_date|date|Opcional|Fecha final de la consulta en formato<br>YYYY-MM-DD. Si no se proporciona una<br>fecha, la respuesta asumirá la fecha actual.|





9 





La respuesta a esta petición tiene la siguiente estructura. 

```
{
    "response": {
        "properties": {
            "action_name": "get_vehicle_trips",
            "data": [{
                "vehicle_id": "134535",
                "license_number": "123RTR56",
                "driver_id": "",
                "start_time": "2016-12-27T17:12:26",
                "end_time": "2016-12-27T17:16:46",
                "start_location": "Hyldegårdsvej 11D, 23 Charlottenlund, Denmark",
                "end_location": "Rosavej 1A, 2930 Klampenborg, Denmark",
                "drive_id": "111222333",
                "distance": "01.77",
                "start_latitude": "55.7610283",
                "start_longitude": "12.5758896",
                "end_latitude": "55.7664948",
                "end_longitude": "12.5939608"
            }, {
                "vehicle_id": "134535",
                "driver_id": "",
                "start_time": "2016-12-27T17:38:55",
                "end_time": "2016-12-27T17:39:56",
                "start_location": "Emiliekildevej 25, Klampenborg, Denmark",
                "end_location": "Emiliekildevej 13B, Klampenborg, Denmark",
                "drive_id": "1423",
                "distance": "00.24",
                "start_latitude": "55.7688713",
                "start_longitude": "12.5903263",
                "end_latitude": "55.7698326",
                "end_longitude": "12.5928764"
            }],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```



10 





###### A continuación, se describen los parámetros incluidos en la respuesta. 

|Parámetro|Tipo|Descripción|
|---|---|---|
|vehicle_id|number|ID único del vehículo.|
|license_number|string|Número económico del vehículo.|
|driver_id|number|ID del chofer actual (si el vehículo cuenta con servicio de<br>identificación de conductor).|
|start_time|datetime|Hora y fecha de inicio del viaje.|
|end_time|datetime|Hora y fecha del final del viaje.|
|start_location|string|Ubicación de inicio del viaje.|
|end_location|string|Ubicación de final del viaje.|
|drive_id|number|ID único del viaje.|
|distance|number|Distancia total del viaje.|
|start_latitude|number|Latitud inicial del viaje.|
|start_longitude|number|Longitud inicial del viaje.|
|end_latitude|number|Latitud inicial del viaje.|
|end_longitude|number|Longitud inicial del viaje.|



Una vez identificado el viaje que nos interesa de la lista anterior, es posible obtener un histórico de ubicaciones y eventos de este con los siguientes comandos. 

Trip locations 

Esta es la estructura de la solicitud. 

```
{
    "action": {
        "name": "get_trip_locations",
        "parameters": [{
            "drive_id": "<<trip_id>>"
        }],
        "session_token": "<<session_token>>"
    }
}
```

Parámetro Tipo Atributo Descripción drive_id number Obligatorio ID único del viaje. Este valor puede ser obtenido del con el comando _get_vehicle_trips_ mencionado en la página 7 de este documento. 



11 





Esta es la estructura de la respuesta a esta solicitud. 

```
{
    "response": {
        "properties": {
            "action_name": "get_trip_locations",
            "data": [{
                "trip_id": "895043958",
                "vehicle_id": "123123",
                "license_number": "LF9-F6",
                "time": "2016-12-27T17:44:38",
                "latitude": "55.7664660",
                "longitude": "12.5940150",
                "direction": "0",
                "speed": "00.00",
                "mileage": "256.27",
                "vehicle_status": "0"
            }, {
                "trip_id": "895043958",
                "vehicle_id": "123123",
                "license_number": "LF9-F6",
                "time": "2016-12-27T17:44:39",
                "latitude": "55.7664700",
                "longitude": "12.5940100",
                "direction": "0",
                "speed": "00.00",
                "mileage": "256.27",
                "vehicle_status": "0"
            }],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```

|Parámetro|Tipo|Descripción|
|---|---|---|
|trip_id|number|ID único del viaje.|
|vehicle_id|number|ID único del vehículo.|
|license_number|string|Número económico del vehículo.|
|time|datetime|Fecha y hora de la localización GPS.|
|latitude|number|Latitud de posición.|
|longitude|number|Longitud de posición.|
|direction|number|Rumbo / ángulo GPS.|
|speed|number|Velocidad reportada al momento del evento.|
|mileage|number|Lectura del odómetro.|
|vehicle_status|number|Estatus posibles:<br>0 – Vehículo apagado.<br>1 – Vehículo encendido.|



2 – Vehículo encendido, motor en ralentí. 



12 





##### Trip events 

La solicitud de eventos de un viaje debe tener la siguiente estructura. 

```
{
    "action": {
        "name": "get_trip_events",
        "parameters": [{
            "drive_id": "1000",
            "version": "2"
        }],
        "session_token": "<<session token>>"
    }
}
```

Parámetro Tipo Atributo Descripción drive_id number Obligatorio ID único del viaje. Este valor puede ser obtenido del con el comando _get_vehicle_trips_ mencionado en la página 7 de este documento. version number Obligatorio Indica la versión de la API y se debe incluir especificando la versión 2. Si este campo se deja en blanco, el servidor asumirá la versión 1 por default. 

###### La respuesta a esta solicitud tendrá la siguiente estructura. 

```
{
    "response": {
        "properties": {
            "action_name": "get_trip_events",
            "data": [{
                "trip_id": "895043958",
                "event_id": "895043958",
                "vehicle_id": "123123",
                "license_number": "LN-45T",
                "time": "2016-12-27T17:44:34",
                "event_type_id": "32",
                "event_type_description": "ignition on",
                "event_category": "5",
                "event_category_description": "Other",
                "latitude": "55.7664642",
                "longitude": "12.5940228",
                "speed": "00.00",
                "direction": "0",
```



13 





```
                "driver_id": "12345",
                "driver_name": "Test Driver",
                "driver_code": "1245600188,ED55D7DD",
                "worker_id": "132456"
            }, {
                "trip_id": "895043958",
                "event_id": "895044007",
                "vehicle_id": "123123",
                "license_number": "LN-45T",
                "time": "2016-12-27T17:44:50",
                "event_type_id": "33",
                "event_type_description": "ignition off",
                "event_category": "5",
                "event_category_description": "Other",
                "latitude": "55.7664490",
                "longitude": "12.5940351",
                "speed": "00.00",
                "direction": "0",
                "driver_id": "12345",
                "driver_name": "Test Driver",
                "driver_code": "1245600188,ED55D7DD",
                "worker_id": "132456"
            }],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```

|Parámetro|Tipo|Descripción|
|---|---|---|
|trip_id<br>|number<br>|ID único del viaje.<br>|
|event_id|number|ID único del evento.<br>|
|vehicle_id|number|ID único del vehículo.|
|license_number|string|Número económico del vehículo.|
|time|datetime|Fecha y hora del evento.|
|event_type_id|number|ID único del tipo de evento.|
|event_type_description|string|Descripción del tipo de evento.|
|event_category|number|ID único de la categoría del evento.|
|event_category_description|string|Descripción de la categoría del evento.|
|latitude|number|Latitud de posición.|
|longitude|number|Longitud de posición.|
|speed|number|Velocidad reportada al momento del evento.|
|direction|number|Rumbo / ángulo GPS.|
|ajádriver_id|number|ID del chofer actual (si el vehículo cuenta con<br>servicio de identificación de conductor).|
|driver_name|string|Nombre del chofer actual (si el vehículo cuenta<br>con servicio de identificación de conductor).|
|driver_code|string|Código del chofer actual (si el vehículo cuenta con<br>servicio de identificación de conductor).|





14 





|worker_id|number|Nombre del empleado (si se encuentra registrado<br>en los sistemas de Traffilog).|
|---|---|---|



##### Vehicle Trips Extended 

Esta solicitud proporciona un reporte de los viajes de uno o más vehículos determinados, definiendo como viaje al periodo de tiempo que sucede entre el encendido y el apagado del motor de la unidad. 

No todos los campos están disponibles para todos los servicios de telemetría en nuestro catálogo y varios de ellos requieren permisos en la plataforma de Traffilog. Si el usuario no tiene los permisos necesarios para consultar un campo, este regresará sin valor. 

Estructura: 

```
{
   "action": {
      "name": "get_vehicle_trips_extended",
      "parameters": [
         {
            "vehicle_id": "",
            "license_number": "350753",
             "from_date": "2019-09-26",
            "to_date": "2019-09-30",
            "driver_id": "",
            "version": ""
         }
      ],
      "session_token": "489D3B79527F4DAAB00AF5266471D05F4337"
   }
}
```

Parámetros de la solicitud: 

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|vehicle_id|number|Condicional|ID único del vehículo. Este parámetro<br>acepta múltiples valores separados por<br>comas, por ejemplo: “1234,5678”. Al menos<br>uno de estos tres parámetros debe<br>introducirse:_vehicle_id_,_license_numbe_r o<br>_driver_id_.|
|license_number|string|Condicional|Número económico del vehículo. Este<br>parámetro<br>acepta<br>múltiples<br>valores<br>separados<br>por<br>comas,<br>por<br>ejemplo:<br>“A1234,B-5678”. Al menos uno de estos tres|





15 



|Parámetro|Tipo|Atributo|
|---|---|---|
|driver_id|number|Condicional|
|from_date|date|Opcional|
|to_date|date|Opcional|





parámetros debe introducirse: _vehicle_id_ , _license_number_ o _driver_id_ . <mark>Descripción</mark> 

ID del chofer. Si solamente se proporciona este número, la respuesta puede incluir viajes de más de un vehículo. Si este parámetro se proporciona en combinación con _vehicle_id o license_number_ , la respuesta solamente incluirá viajes del chofer en ese vehículo específico. Fecha de inicio de la consulta en formato YYYY-MM-DD. Si no se proporciona una fecha, la respuesta asumirá la fecha actual. Fecha final de la consulta en formato YYYY-MM-DD. Si no se proporciona una fecha, la respuesta asumirá la fecha actual. La diferencia máxima entre estas fechas no podrá superar 30 días. 

La estructura de la respuesta es la siguiente. 

```
{
   "response": {
      "properties": {
         "action_name": "get_vehicle_trips_extended",
         "data": [
            {
               "drive_id": "27538460208",
               "vehicle_id": "173114",
               "license_number": "621",
               "vehicle_group": "abc",
               "parent_group": "",
               "upper_group": "",
               "top_group": "",
               "driver_name": "",
               "driver_code": "",
               "driver_group": "A",
               "worker_id": "1601",
               "start_latitude": "",
               "start_longitude": "",
               "start_mileage": "",
               "end_latitude": "",
               "end_longitude": "",
               "distance": "160.66",
               "drive_duration": "18:54:00",
               "start_fuel_level_percent": "",
               "end_fuel_level_percent": "",
               "fuel_used": "",
               "idle_time": "",
               "total_mileage": "268164.90",
               "engine_hours": "",
               "water_used": "",
```



16 





```
               "driver_id": "286401",
               "start_time": "2018-09-25T01:13:38",
               "end_time": "2018-09-25T20:07:48",
               "start_location": "",
               "end_location": "",
               "chassis_serial": "16-227-12",
               "liter_Per_100_km": "",
               "time_from_prev_drive": "",
               "km_per_1_Liter": "",
               "safety_score": "89",
               "CO2": "211.306",
               "trailer": "929"
            }  ],
         "action_value": "0",
         "description": "",
         "session_token": "E2AD2F5E8CXXXXXX64"
      }
   }
}
```

###### Los parámetros de la respuesta son los siguientes: 

|Parámetro|Tipo|Descripción|
|---|---|---|
|drive_id|number|ID único del viaje.|
|vehicle_id|number|ID único del vehículo.|
|license_number|string|Número económico del vehículo.|
|vehicle_group|string|Grupo del vehículo|
|parent_group|string|Grupo padre en la jerarquía de la plataforma.<br>Requiere permisos especiales.|
|upper_group|string|Requiere permisos especiales.|
|top_group|string|Requiere permisos especiales.|
|driver_name|string|Nombre del conductor.<br>Requiere permisos especiales.|
|||Código del conductor (si el vehículo cuenta con|
|driver_code|string|servicio de identificación de conductor).<br>Requiere permisos especiales.|
|driver_group|string|Grupo del conductor.<br>Requiere permisos especiales.|
|worker_id|string|ID único del empleado.|
|start_latitude|number|Latitud inicial del viaje.|
|start_longitude|number|Longitud inicial del viaje.|
|start_mileage|string|Lectura del odómetro al inicio del viaje.|
|end_latitude|number|Latitud inicial del viaje.|
|end_longitude|number|Longitud inicial del viaje.|
|distance|number|Distancia total del viaje.|
|drive_duration|number|Duración total del viaje. Formato HH:MM:SS|





17 





|start_fuel_level_percent|string|Nivel de combustible al inicio del viaje.<br>Requiere permisos especiales.|
|---|---|---|
|end_fuel_level_percent|string|Nivel de combustible al final del viaje.<br>Requiere permisos especiales.|
|fuel_used|string|Combustible consumido durante el viaje.<br>Requiere permisos especiales.|
|idle_time|string|Tiempo de la unidad en ralentí durante el viaje.<br>Requiere permisos especiales.|
|total_mileage|string|Kilometraje total de la unidad.|
|engine_hours|string|Horas de motor del viaje.<br>Requiere permisos especiales.|
|water_used|string|Agua consumida.<br>Requiere permisos especiales.|
|driver_id|number|ID del conductor (si el vehículo cuenta con<br>servicio de identificación de conductor).|
|start_time|datetime|Hora y fecha del inicio del viaje.<br>Formato YYYY-MM-DDTHH:MM:SS|
|end_time|datetime|Hora y fecha del final del viaje.<br>Formato YYYY-MM-DDTHH:MM:SS|
|start_location|string|Descripción de la posición del inicio del viaje.<br>Requiere permisos especiales.|
|end_location|string|Descripción de la posición del final del viaje.<br>Requiere permisos especiales.|
|chassis_serial|string|VIN del vehículo.|
|||Litros de combustible consumidos por cada 100|
|liter_Per_100_km|string|kilómetros.<br>Requiere permisos especiales.|
|time_from_prev_drive|string|Tiempo transcurrido desde el viaje anterior.<br>Requiere permisos especiales.|
|||Kilómetros<br>recorridos<br>por<br>cada<br>litro<br>de|
|km_per_1_Liter|string|combustible.<br>Requiere permisos especiales.|
|safety_score|string|Puntuación de seguridad del viaje en una escala<br>de 0 a 100.|
|CO2|string|Requiere permisos especiales.|
|trailer|string|Número de trailer.|





18 





#### Eventos 

##### Incremental events 

Esta solicitud proporciona una lista de todos los eventos de toda la flota de una lista preconfigurada de eventos disponibles por cliente / vehículo. En la primera llamada a la API, devolverá todos los eventos generados en las últimas 24 horas o los 10,000 eventos más recientes. A partir de entonces, regresará los eventos más nuevos desde la última llamada (con un límite de 10,000 registros). 

Estructura: 

```
{
    "action": {
        "name": "get_incremental_events",
        "parameters": [{
            "event_category_id": "",
            "version": "3",
        }],
        "session_token": "E2AD2F5E8CXXXXXX64"
    }
}
```

Parámetros de la solicitud: 

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|event_category_id|number|Opcional|Filtra por una categoría específica de<br>eventos:|
||||1 – Safety<br>2 – Geographic<br>3 – Mechanic<br>10 – DTC (Data Trouble Code)|
|Version|Number|Opcional|La descripción de este método en el<br>presente documento hace referencia a<br>la versión 3.|





19 





La estructura de la respuesta es la siguiente. 

```
{
    "response": {
        "properties": {
            "action_name": "get_incremental_events",
            "data": [{
                "event_id": "895043958",
                "vehicle_id": "123123",
                "license_number": "LN-45T",
                "vin": "11243256fgd",
                "time": "2016-12-27T17:44:34",
                "event_type_id": "32",
                "event_type_description": "ignition on",
                "event_category_id": "5",
                "event_category_description": "Other",
                "severity": "low",
                "spn": "",
                "fmi": "",
                "fmi_description": "",
                "source": "",
                "start_latitude": "55.7664642",
                "start_llongitude": "12.5940228",
                "end_time": "2016-12-27T17:45:25",
                "end_latitude": "55.7664735",
                "end_longitude": "12.5940226",
                "speed": "00.00",
                "direction": "0",
                "driver_id": "12345",
                "driver_name": "Test Driver",
                "driver_code": "1245600188,ED55D7DD",
                "worker_id": "132456"
            }],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```



20 





Los parámetros de la respuesta son los siguientes: 

|Parámetro|Tipo|Descripción|
|---|---|---|
|event_id|number|ID único del evento.|
|vehicle_id|number|ID único del vehículo.|
|license_number|string|Número económico del vehículo.|
|vin|string|Número de serie del vehículo.|
|time<br>|string<br>|Hora de inicio del evento.<br>|
|event_type_id|string|ID único del tipo de evento.|
|event_type_description|string|Descripción del tipo de evento.|
|event_category_id|string|ID único de la categoría del evento.|
|event_category_description|string|Descripción de la categoría del evento.|
|||Severidad del evento (solamente eventos<br>Safety y DTC).|
|severity|string|1 – baja<br>2 – medio<br>|
|||3 – alto|
|spn|string|Suspect<br>parameter<br>number<br>(solo<br>para<br>eventos DTC).|
|fmi|string|Failure mode indicator number (solo para<br>eventos DTC).|
|fmi_description|number|Descripción del failure mode indicator (solo<br>para eventos DTC).|
|source|number|Fuente del código de error (dirección CAN<br>bus) (solo para eventos DTC).|
|start_latitude|string|Latitud inicial del evento.|
|start_longitude|number|Longitud inicial del evento.|
|end_time|number|Hora final de evento.|
|end_latitude|number|Latitud final del evento.|
|end_longitude|number|Longitud final del evento.|
|speed|string|Velocidad.|
|direction|string|Dirección GPS.|
|driver_id|string|ID único del conductor (requiere validación<br>del conductor activada).|
|driver_name|string|Nombre del conductor (requiere validación<br>del conductor activada).|
|driver_code|string|Código del conductor (requiere validación del<br>conductor activada).|
|||Código de empleado (requiere validación del|
|worker_id|string|conductor activada y lista de empleados<br>registrada con Traffilog).|





21 





#### Parámetros 

Get parameters 

Esta solicitud proporciona el valor más reciente para cada uno de los parámetros que el equipo de telemetría está configurado para leer. 

```
{
    "action": {
        "name": "get_parameters",
        "parameters": [{
            "vehicle_id": "17333522"
        }],
        "session_token": "DDFF454545DXXXXX"
    }
}
```

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|vehicle_id|number|Condicional|ID único del vehículo.|



La estructura de la respuesta es la siguiente. 

```
{
    "response": {
        "properties": {
            "action_name": "get_parameters",
            "data": [{
                "vehicle_id": "17333522",
                "license_number": "405-L87-B",
                "parameter_type": "496",
                "parameter_type_description": "Unit Time",
                "last_input_value": "10662.0000000",
                "last_input_time": "2017-01-11T12:24:16"
            }, {
                "vehicle_id": "17333522",
                "license_number": "1017119",
                "parameter_type": "516",
                "parameter_type_description": "OBD Malfunction Indicator Lamp (MIL)",
                "last_input_value": "10.55487",
                "last_input_time": "2017-01-10T13:34:17"
            }],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```



22 





###### A continuación, se describen los parámetros incluidos en la respuesta. 

|Parámetro|Tipo|Descripción|
|---|---|---|
|vehicle_id|number|ID único del vehículo.|
|license_nmbr|string|Número económico del vehículo.|
|parameter_type|number|ID único del parámetro.|
|parameter_type_description|string|Nombre del parámetro.<br>|
|last_input_value|number|Última lectura registrada del parámetro en<br>UTC.|
|last_input_time|datetime|Hora y fecha de la última lectura registrada<br>en UTC.|



##### Get parameter values 

Esta solicitud proporciona los distintos valores registrados de un parámetro específico en un periodo de tiempo delimitado. Este periodo de tiempo no podrá ser superior a 72 horas. 

```
 {
   "action": {
      "name": "api_get_vehicle_parameter_values",
      "parameters": [
         {
            "vehicle_id": ""
            "param_type": "30275",
            "start_time": "2021-06-10 00:00",
            "end_time": "2021-06-11 23:59",
            "version": ""
         }
      ],
      "session_token": "E2AD2F5E8CXXXXXX64"
   }
}
```

Estos son los parámetros que pueden incluirse en la solicitud. 

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|vehicle_id|number|Condicional|ID único del vehículo.|
|param_type|number|Obligatorio|ID único del parámetro.|
|start_time|datetime|Obligatorio|Fecha y hora de inicio de la consulta en<br>formato YYYY-MM-DD HH:MM:SS en UTC.|
|end_time|datetime|Obligatorio|Fecha y hora final de la consulta en<br>formato YYYY-MM-DD HH:MM:SS en UTC.<br>La diferencia entre ambas fechas no<br>puede ser superior a 72 horas.|





23 





La respuesta a esta petición tiene la siguiente estructura. 

```
{
   "response": {
      "properties": {
         "action_name": "api_get_vehicle_parameter_values",
         "data": [
            {
               "vehicle_id": "13216",
               "parameter_type": "30275",
               "parameter_type_description": "BMU_SOC_MSG_CM (M15-25)",
               "value": "89.2000000",
               "time": "2018-06-11T14:34:32.0000000+00:00"
            },
           {
               "vehicle_id": "13216",
               "parameter_type": "30275",
               "parameter_type_description": "BMU_SOC_MSG_CM (M15-25)",
               "value": "72.4000000",
               "time": "2018-06-11T15:00:33.0000000+00:00"
            }
         ],
         "action_value": "0",
         "description": "",
         "session_token": "E2AD2F5E8CXXXXXX64"
      }
   }
}
```

A continuación, se describen los parámetros incluidos en la respuesta. 

|Parámetro|Tipo|Descripción|
|---|---|---|
|vehicle_id|number|ID único del vehículo.|
|parameter_type|number|ID único del parámetro.|
|parameter_type_description|number|Nombre del parámetro.|
|value|datetime|Valor de lectura del parámetro.|
|time|datetime|Hora y fecha de la lectura del parámetro.|





24 





#### Geocercas 

##### Get layers 

Dentro de la estructura Traffilog, se define como capa a las categorías que agrupan lugares con atributos similares. Cada capa contiene figuras geométricas que definen diferentes áreas en un mapa, llamadas geocercas. Esta API devuelve la lista de capas existentes en la cuenta, las cuales son necesarias para hacer una consulta de geocercas de una capa específica. Existe un límite de 50 capas por respuesta. Cada una de las capas de la respuesta contendrá un número consecutivo, que nos permitirá ejecutar consultas subsecuentes con el resto de las capas. 

###### Estructura **:** 

```
{
    "action": {
       "name": "api_get_layers",
       "parameters": [{
            "layer_name": "<<name>>",
            "last_object_id": "0"
          }],
          "session_token": "E2AD2F5E8CXXXXXX64"
     }
}
```

###### Parámetros de la solicitud: 

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|layer_name|string|Opcional|Devuelve la información de  una capa en<br>específico.<br>Si se deja<br>en<br>blanco,<br>devuelve<br>las<br>primeras<br>50<br>capas<br>existentes.|
|last_object_id|number|Opcional|Número consecutivo de capa en la<br>respuesta. En caso de que el número de<br>capas exceda 50, se deberá introducir el<br>último id del objeto de la capa (50, 100,<br>150, etc) para recibir las siguientes 50<br>capas de la lista.|





25 





La estructura de la respuesta es la siguiente. 

```
{
    "response": {
        "properties": {
            "action_name": "api_get_layers",
            "data": [{
                 "object_id": "93",
                 "layer_id": "140463",
                 "layer_name": "layer4",
                 "count_geometries_in_layer": "10",
                 "created_date": "2019-04-10T12:55:12.0000000+00:00",
                 "created by": "",
                 "last_updated_date": ""
             }],
             "action_value": "0",
             "description": "",
             "session_token": "E2AD2F5E8CXXXXXX64"
          }
     }
}
```

Los parámetros de la respuesta son los siguientes: 

|Parámetro|Tipo|Descripción|
|---|---|---|
|object_id|number|Número consecutivo de la capa (relevante<br>para más de 50 capas).|
|layer_id|number|ID único de la capa en el sistema Traffilog.|
|layer_name|string|Nombre de la capa.|
|count_geometries_in_layer|number|Número de geocercas contenidas en la capa.|
|created_date|datetime|Fecha de creación de capa.|
|created_by|string|Usuario que creó la capa.|
|last_updated_date|datetime|Fecha de la última modificación de la capa.|



Get geometry 

Esta API devuelve la lista de geocercas existentes en una capa determinada o de una geocerca específica. 

Existe un límite de 50 geocercas por respuesta y se deben hacer solicitudes subsecuentes para recuperar un número más alto dentro de una capa. 



26 





Estructura: 

```
{
    "action": {
       "name": "api_get_geometry",
       "parameters": [{
            "layer_id":"138019",
            "layer_name": "<<name>>",
            "geometry_name": "<<geometry_name>>",
            "geometry_type": "2",
            "last_object_id": "0",
          }],
          "session_token": "E2AD2F5E8CXXXXXX64"
     }
}
```

###### Parámetros de la solicitud: 

|Parámetro|Tipo|Atributo|Descripción|
|---|---|---|---|
|layer_id|number|Opcional|ID único de la capa en el sistema<br>Traffilog. Este valor es obligatorio si no<br>se especifican valores para layer_name<br>o geometry_name.|
|layer_name|string|Opcional|Nombre de la capa. Este valor es<br>obligatorio si no se especifican valores<br>para layer_id o geometry_name.|
|geometry_name|string|Opcional|Nombre de la geocerca. Si se incluye<br>este valor, la respuesta solamente<br>devolverá<br>la<br>información<br>de<br>una<br>geocerca específica.|
|last_object_id|number|Opcional|Número consecutivo de geocerca en la<br>respuesta. En caso de que el número de<br>geocercas<br>exceda<br>50,<br>se<br>deberá<br>introducir el último id del objeto de la<br>última geocerca (50, 100, 150, etc) para<br>recibir las siguientes 50 geocercas de la<br>lista.|



La estructura de la respuesta es la siguiente. 

```
{
    "response": {
        "properties": {
            "action_name": "api_get_geometry",
            "data": [{
                 "object_id": "42",
```



27 





```
 "layer_id": "132321",
         "layer_name": "layer4",
                 "geometry_id": "132320",
                 "geometry_name": "geo4",
                 "geometry_type":"1",
                 "geometry_type_descr": "circle",
                 "shape_coordinates": "31.86808203013619,34.74597930908203",
                 "radius": "00.05",
                 "image": "",
                 "created_date": "2019-04-10T12:55:12.0000000+00:00",
                 "created_by": ""
             }],
             "action_value": "0",
             "description": "",
             "session_token": "E2AD2F5E8CXXXXXX64"
          }
     }
}
```

Los parámetros de la respuesta son los siguientes: 

|Parámetro|Tipo|Descripción|
|---|---|---|
|object_id|number|Número consecutivo de la geocerc (relevante<br>para más de 50 geocercas).|
|layer_id|number|ID único de la capa en el sistema Traffilog.|
|layer_name|string|Nombre de la capa.|
|geometry_id|number|ID único de la geocerca en el sistema<br>Traffilog.|
|geometry_name|number|Nombre de la geocerca.|
|||ID del tipo de geocerca. Los tipos disponibles<br>son:|
|geometry_type|number|1. Círculo<br>2. Polilínea|
|||3. Polígono|
|||Descripción del tipo de geocerca. Los valores<br>posibles correspondientes a la lista anterior|
|geometry_type_description|string|son:<br>1. circle*<br>2. polyline*<br>3. polygon*|
|geometry_coordinates|string|Coordenadas geométricas de la geocerca.|
|radius|number|Radio de la geocerca si es de tipo 1 (círculo).|
|image|string|Campo sin uso actualmente.|
|created_date|datetime|Fecha y hora de creación de la geocerca.|
|created_by|string|Usuario que creó la geocerca.|





28 





#### Conductores 

##### Get drivers 

Esta solicitud proporciona una lista de todos los conductores asignados a la flota o bien, filtrando por un conductor específico o un grupo de conductores. 

```
{
    "action": {
       "name": "get_user_drivers",
       "parameters": [{
            "driver_id": "",
            "active_drivers": "",
            "group_id": "",
            "version": ""
          }],
          "session_token": "45DD800DFFBA433581A9B134979AE9314492370289"
     }
}
```

La estructura de la respuesta es la siguiente. 

```
{
    "response": {
        "properties": {
            "action_name": "get_user_drivers",
            "data": [
                {
                    "driver_id": "374XXX",
                    "worker_id": "2200XXXX",
                    "driver_name": "LOPEZ%20NAVA%20JUAN",
                    "active_flag": "1",
                    "driver_code": "121212",
                    "client_group": "3039",
                    "group_name": "GRUPO%20CONDUCTORES",
                    "parent_group": "12345",
                    "parent_group_name": "GRUPO%20MAESTRO",
                    "driver_cell_phone": "1102948567",
                    "driver_main_vehicle_id": "",
                    "driver_main_vehicle_license_number": "",
                    "customer_contact_person": "DIANA%20LOPEZ",
                    "contact_person_phone_number": "9947208465",
                    "driver_email": "",
                    "last_event_id": "7532XXXXXX",
                    "last_event_time": "2022-12-30T15%3A28%3A12",
                    "last_event_type": "33",
                    "last_event_type_desc": "Ignition%20Off",
```



29 





```
                    "last_event_vehicle": "2294XXX",
                    "last_event_licence_number": "0123",
                    "last_event_location": "",
                    "last_event_latitude": "25.1233456",
                    "last_event_longitude": "-99.1234567",
                    "last_event_direction": ""
```

```
                } ],
            "action_value": "0",
            "description": "",
            "session_token": "E2AD2F5E8CXXXXXX64"
        }
    }
}
```

###### Los parámetros de la respuesta son los siguientes: 

|Parámetro|Tipo|Descripción|
|---|---|---|
|driver_id|number|ID único del conductor.|
|worker_id|number|Código de empleado.|
|driver_name|string|Nombre del conductor.|
|||Estatus del conductor en el sistema:|
|active_flag|number|0 - Inactivo<br>1 - Activo|
|||Código de DMAS del conductor|
|driver_code|string|(requiere validación del conductor<br>activada).|
|client_group|string|ID del grupo del conductor.|
|group_name|string|Nombre del grupo del conductor.|
|parent_group|string|ID del grupo superior del conductor.|
|parent_group_name|string|Nombre del grupo superior del<br>conductor.|
|driver_cell_phone|string|Número celular del conductor.|
|||ID del vehículo al que está asignado|
|driver_main_vehicle_id|string|el<br>conductor<br>como<br>operador|
|||principal.|
|||Número económico del vehículo al|
|driver_main_vehicle_license_number|string|que está asignado el conductor como<br>operador principal.|
|customer_contact_person|number|Persona de contacto del cliente.|
|contact_person_phone_number|number|Teléfono de contacto del cliente.|
|driver_email|string|Correo electrónico del conductor.|
|last_event_id|number|ID del último evento detonado por el<br>conductor.|
|last_event_time|number|Hora del último evento detonado por<br>el conductor.|





30 





|last_event_type|number|ID<br>del<br>tipo<br>del<br>último<br>evento<br>detonado por el conductor.<br>|
|---|---|---|
|last_event_type_desc|number|Descripción del tipo del último<br>evento detonado por el conductor.|
|||ID único del vehículo en el cual fue|
|last_event_vehicle|string|registrado el último evento detonado<br>por el conductor.|
|||Número económico del vehículo en|
|last_event_licence_number|string|el cual fue registrado el último evento<br>detonado por el conductor.|
|last_event_location|string|Ubicación del lugar en donde se<br>registró el último evento detonado<br>por el conductor (requiere permiso<br>especial).|
|||Latitud del lugar en donde se registró|
|last_event_latitude|string|el último evento detonado por el<br>conductor.|
|||Longitud del lugar en donde se|
|last_event_longitude|string|registró el último evento detonado<br>por el conductor.|
|||Rumbo / ángulo GPS del vehículo|
|last_event_direction|string|cuando se registró el último evento<br>detonado por el conductor.|





31 





### Políticas de uso 

Esta sección define las normas de uso de todas las APIs y servicios web para clientes Traffilog. Su correcto seguimiento nos ayudará a asegurar un flujo constante y exitoso de la información a todos los clientes y/o consumidores del servicio. 

A menos que se especifique lo contrario para un servicio determinado, todos las APIs y otros servicios web de Traffilog deberán seguir los siguientes lineamientos. 

- Un usuario de la API debe iniciar sesión usando el método correspondiente y recibir un token de sesión. Este token es válido por las siguientes 24 horas y en la medida de lo posible deberá usarse durante ese periodo sin solicitar uno nuevo para cada conexión independiente. 

- Un usuario solamente puede mantener 64 tokens de sesión activos al mismo tiempo, descartando los primeros tokens generados al superar este número, independientemente del tiempo de vida restante. 

- Los servicios web no deben ser consumidos con una frecuencia mayor a 30 segundos por llamada, incluyendo todos los métodos utilizados por el mismo usuario. Por regla general, la información de telemetría disponible en la API no se actualizará con una frecuencia mayor a este periodo.  Para información histórica de extensos periodos de tiempo, es recomendable usar alguna de las otras opciones disponibles con esta información, como repositorios online, reportes calendarizados, etcétera. Favor de contactar a su ejecutivo de cuenta para conocer estas soluciones alternas. 



32 

