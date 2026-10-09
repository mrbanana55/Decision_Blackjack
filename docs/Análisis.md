## Requisitos Funcionales
### Configuración e Inicialización

- **RF-01:** El sistema **debe** aplicar las reglas de juego establecidas en [[Reglas de BlackJack]].
- **RF-02:** **Cuando** el usuario inicie la aplicación, el sistema **debe** presentar un formulario interactivo para modificar los parámetros de las [[Reglas de BlackJack#Reglas Modificables|reglas modificables]] del juego.
- **RF-03:** **Cuando** el usuario configure la simulación, el sistema **debe** permitir establecer la cantidad total de rondas a disputar dentro de un rango entero de 1 a N (N≥1, admitiendo simulación continua/indefinida).
- **RF-04:** El sistema **debe** importar la API key desde un archivo *.env* así como validar los endpoints requeridos para la API del modelo Jev.
- **RF-05:** **Cuando** el usuario configure la simulación, el sistema **debe** permitir realizar una cantidad total de simulaciones con la misma configuración dentro de un rango entero de 1 a N (N≥1, permitiendo simulaciones continuas/indefinidas).

### Motor de Simulación y Ejecución

- **RF-06:** El sistema **debe** ejecutar cada entidad (modelo Jev, modelo Laya y Estrategia Óptima) en una mesa de juego independiente y aislada, evitando interacción o interferencia entre sus manos.
- **RF-07:** **Mientras** la simulación esté en ejecución, **cuando** el usuario active el comando de pausa, el sistema **debe** suspender temporalmente el juego de todas las mesas conservando el estado exacto de la ronda actual.
- **RF-08:** **Mientras** la simulación esté en estado de pausa, **cuando** el usuario active el comando de reanudación, el sistema **debe** continuar la ejecución desde el último turno registrado.

### Visualización y Telemetría en Tiempo Real

- **RF-09:** **Mientras** la simulación se encuentre activa, el sistema **debe** renderizar en tiempo real el progreso de cada mesa (cartas del crupier, cartas del jugador, bankroll actual y conteo de rondas).
- **RF-10:** **Mientras** un modelo (Jev o Laya) evalúe su turno, el sistema **debe** desplegar gráficamente la decisión tomada, el porcentaje de confianza asociado y la comparación visual contra la decisión que dictaría la estrategia óptima.

### Registro, Persistencia y Exportación

- **RF-11:** **Cuando** finalice cada ronda en cualquiera de las mesas, el sistema **debe** almacenar un registro estructurado que incluya: identificador de mesa/modelo, número de ronda, cartas iniciales del jugador, cartas del crupier, decisiones tomadas, porcentaje de confianza, resultado de la ronda y bankroll resultante.
- **RF-12:** **Cuando** el usuario solicite la descarga de los datos de juego, el sistema **debe** exportar los registros históricos en un formato tabular estructurado (CSV o JSON) listo para su análisis comparativo.

## Requisitos No Funcionales

### Rendimiento y Tiempo Real

- **RNF-01:** **Mientras** la simulación esté en curso, el sistema **debe** reflejar los cambios de estado y las decisiones de los modelos en la interfaz visual con una latencia menor a **200 ms** tras recibir la respuesta de inferencia.
- **RNF-02:** **Cuando** la API de Jev no responda o devuelva un código de error HTTP (5xx/4xx), el sistema **debe** pausar la mesa afectada, notificar el incidente al usuario en pantalla y preservar los datos recolectados hasta ese instante sin colapsar la aplicación.

### Persistencia y Acceso a Datos

- **RNF-03:** El sistema **debe** organizar los archivos de registro generados en una estructura de directorios predecible y accesible en el sistema local/servidor (`/data/runs/[timestamp]`), garantizando que sean localizables sin depender exclusivamente del panel web.
- **RNF-04:** **Mientras** se procesen simulaciones de alto volumen (más de 10,000 rondas), el sistema **debe** registrar las transacciones en disco en bloques (_batch_) para no saturar la memoria RAM del navegador/servidor.

### Usabilidad y Compatibilidad

- **RNF-05:** El sistema **debe** ser completamente operativo desde navegadores web modernos basados en Chromium, WebKit y Gecko sin requerir extensiones de terceros.
- **RNF-06:** La interfaz gráfica **debe** distinguir de manera clara e inequívoca las tres mesas de análisis (Jev, Laya y Estrategia Óptima) mediante esquemas de color o paneles diferenciados para facilitar la comparación simultánea.
