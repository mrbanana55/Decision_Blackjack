
# 1. Descripción general

El proyecto consiste en desarrollar una aplicación web local para **simular partidas de Blackjack y comparar el comportamiento de tres entidades de decisión**:

1. **Jev**, un modelo de inteligencia artificial System One accesible mediante API.
2. **Laya**, un modelo similar que se ejecutará localmente.
3. **Estrategia Óptima**, basada en Basic Strategy y complementada con desviaciones según el conteo Hi-Lo y las condiciones específicas de la mesa.

El propósito principal del sistema no es que un usuario juegue Blackjack manualmente, sino **ejecutar experimentos controlados y reproducibles** para observar cómo toman decisiones los distintos jugadores y comparar sus resultados.

Las tres mesas deben partir del mismo estado inicial del shoe y utilizar las mismas reglas. Sin embargo, durante una ronda pueden terminar utilizando cartas distintas debido a que sus decisiones pueden provocar secuencias diferentes de _hit_, _stand_, _double_ o _split_. 

La aplicación será de uso individual y se ejecutará localmente mediante Docker, exponiendo el frontend y backend mediante `localhost`.

---
# 2. Objetivo del sistema

El sistema debe permitir configurar y ejecutar simulaciones de Blackjack bajo un conjunto determinado de reglas y posteriormente **obtener datos suficientes para analizar el desempeño de Jev y Laya frente a una estrategia de referencia matemática**.

El flujo conceptual sería:
```text
Configuración
     ↓
Creación de la simulación
     ↓
Preparación del shoe
     ↓
Generación del estado inicial
     ↓
 ┌──────────┬──────────┬──────────────┐
 ↓          ↓          ↓
 Jev       Laya      Óptima
 ↓          ↓          ↓
 decisiones sincronizadas
 └──────────┴──────────┴──────────────┘
              ↓
       Resolución de ronda
              ↓
        Registro de datos
              ↓
       Siguiente ronda
              ↓
        Siguiente simulación
```

El sistema debe mantener separadas las responsabilidades del **motor de Blackjack**, los **modelos de decisión**, la **persistencia** y la **interfaz gráfica**.

---
# 3. Alcance funcional

Los requisitos funcionales cubren cinco grandes áreas:

| Área           | Responsabilidad                                           |
| -------------- | --------------------------------------------------------- |
| Configuración  | Definir reglas, número de rondas y número de simulaciones |
| Simulación     | Ejecutar las tres entidades bajo las mismas condiciones   |
| Sincronización | Mantener las mesas coordinadas                            |
| Visualización  | Mostrar el estado de las mesas y decisiones               |
| Persistencia   | Guardar y exportar los resultados                         |
El núcleo del sistema no debe depender de la interfaz gráfica. El motor debe poder ejecutar una simulación independientemente de cómo se visualicen posteriormente los datos.

---
# 4. Arquitectura

![[Desicion_BlackJack_Architechture]]
## 4. 1. Decisiones Tecnológicas

* **Frontend:** React + TypeScript + Vite.
* **UI:** Tailwind + shadcn/ui.
* **Formularios:** React Hook Form.
- **Backend:** Python + FastAPI.
- **Gestión de entorno Python:** UV.
- **Base de datos:** PostgreSQL.
- **Contenedores:** Docker + Docker Compose.

---
# 5. Separación de responsabilidades

## 5.1. Frontend

El frontend será responsable exclusivamente de la interacción y representación visual.

Debe encargarse de:
- formulario inicial.
- configuración de la simulación.
- iniciar, pausar y reanudar.
- visualizar las tres mesas.
- mostrar cartas.
- mostrar apuestas.
- mostrar bankroll.
- mostrar ronda actual.
- mostrar decisiones.
- mostrar confianza.
- mostrar comparación contra la estrategia óptima.
- mostrar métricas.
- mostrar gráficas.
- permitir descargar resultados.

No debería contener la [[Reglas de BlackJack|lógica]] fundamental de Blackjack.

Por ejemplo, el navegador **no** debería decidir si una mano es un Blackjack, calcular el resultado de una apuesta o determinar cuándo debe pedir carta el dealer. Esto pertenece al motor del backend.

---
# 6. Motor de Blackjack

El motor de Blackjack constituye el núcleo determinista del sistema.
Debe ser responsable de:
- construir el shoe.
- barajar.
- quemar cartas.
- repartir.
- calcular valores de manos.
- manejar Ases.
- detectar Blackjack natural.
- ejecutar turnos.
- procesar _hit_, _stand_, _double_, _split_, etc.
- controlar el dealer.
- aplicar pagos.
- actualizar bankroll.
- detectar bancarrota.
- controlar penetración.
- realizar el reshuffle.

Las [[Reglas de BlackJack|reglas]] proporcionadas establecen, entre otras cosas, que las cartas del 2 al 9 conservan su valor, las figuras y el 10 valen 10 y el As puede valer 1 u 11 dependiendo de la mano. También distinguen un Blackjack natural de un 21 obtenido después de dividir.
La regla del dealer también es determinista: pide mientras tenga menos de 17 y se planta con 17 duro o superior. En el caso del 17 suave, se considera una regla modificable si el dealer debe pedir en 17 suave o si se puede plantar.

---
# 7. Modelo de las tres mesas

Aunque visualmente existen tres mesas, conceptualmente conviene tratarlas como **tres instancias aisladas del jugador dentro de una simulación común**.

![[Desicion_BlackJack_tables.excalidraw]]
Cada una debe tener:
- bankroll.
- mano.
- apuesta.
- decisiones.
- historial.
- estado de turno.

Pero compartirán:
- configuración.
- shoe inicial.
- mezcla inicial.
- estado inicial del experimento.

La frase "mismo deck" no significa que las mesas deban consumir físicamente una misma secuencia de cartas. Lo establecido es que parten del mismo shoe mezclado; a partir de ahí cada decisión puede hacer que sus cartas posteriores sean diferentes.

---
# 8. Sincronización de las mesas

Este es uno de los aspectos más importantes de la arquitectura.
Las mesas no deben ejecutarse como tres simulaciones completamente independientes.

El sistema necesita un orquestador que controle el turno:

```text
Ronda N
   │
   ├── Estado inicial
   │
   ├── Jev decide
   │
   ├── Laya decide
   │
   ├── Óptima decide
   │
   ├── resolver acciones adicionales
   │
   ├── esperar a mesas incompletas
   │
   ├── dealer
   │
   └── resolver resultados
```

Además, si Jev está esperando una respuesta, Laya y Óptima también deben esperar. Si una mesa falla, se detienen las tres. 
Por tanto, será necesario un concepto de **estado global de la simulación**.
Por ejemplo, conceptualmente:

```
CREATED
RUNNING
PAUSED
WAITING_FOR_JEV
RESOLVING
COMPLETED
ERROR
```

Esto no es código, sino una definición conceptual necesaria para el diseño.

---

# 9. Integración de Jev

Jev será un componente externo al motor de Blackjack.

Su comunicación se realiza mediante una solicitud HTTP síncrona y respuesta correspondiente. 

La arquitectura debería evitar que el motor de Blackjack conozca detalles de HTTP.

Conceptualmente:

```text
Motor Blackjack
      │
      ▼
Jev Adapter
      │
      ▼
API TypeSafe
      │
      ▼
Respuesta
      │
      ▼
Jev Adapter
      │
      ▼
Motor Blackjack
```

Esto permite que el motor simplemente pregunte:

> "Dado este estado, ¿qué decisión toma Jev?"

en lugar de conocer cómo funciona la API.

La API key debe permanecer exclusivamente en el backend y el endpoint será configurable mediante `.env`, no desde la interfaz.

---
# 10. Laya

Laya tiene una función similar a Jev, pero su ejecución será local. 

Por ello conviene que ambos estén detrás de una interfaz conceptual común:

```text
             Decision Provider
                  │
        ┌─────────┼─────────┐
        │         │         │
       Jev       Laya    Estrategia
                          Óptima
```

Los tres recibirían un estado de juego y producirían una decisión.

Esto es especialmente útil porque permite posteriormente añadir otros modelos sin modificar el motor de Blackjack.

---
# 11. Estrategia Óptima

La tercera entidad no debe considerarse simplemente una tabla fija. Estará basada en:
- Basic Strategy.
- número de barajas.
- cartas restantes.
- composición del mazo.
- conteo Hi-Lo.
- deck penetration.
- cartas quemadas.
- reglas de la mesa.
- desviaciones ocasionadas por el _true count_.

Por lo tanto, conceptualmente sería:

```text
Estado del juego
       │
       ├── reglas
       ├── mano jugador
       ├── carta dealer
       ├── shoe restante
       ├── running count
       └── true count
                 │
                 ▼
        Estrategia Óptima
                 │
                 ▼
          Acción recomendada
```

Esto la convierte en el **referente de comparación**, pero también en un jugador completo de su propia mesa.

---
# 12. Semillas y reproducibilidad

La utilización de una semilla configurable es una decisión particularmente importante.
Cada simulación comienza con:
- bankroll inicial.
- shoe nuevo.
- misma configuración.
- semilla aleatoria nueva. 
A su vez, se estableció que el usuario puede definir una `seed`.
Esto permite dos conceptos:
* **Ejecución experimental:** `Seed = aleatoria`
* **Ejecución reproducible:** `Seed = 123456`

Una ejecución reproducible sería fundamental para comprobar errores y comparar modificaciones del sistema bajo exactamente las mismas condiciones.

---
# 13. Configuración

La pantalla inicial debe concentrarse en los parámetros que realmente modifican el comportamiento del juego.
A partir del documento de [[Reglas de BlackJack#^65d10d|reglas]], existen configuraciones relacionadas con:
- Soft 17.
- pago de Blackjack.
- Blackjack después de dividir Ases.
- Peek/ENHC.
- Insurance.
- Surrender.
- DAS.
- límite de resplit.
- RSA.
- cartas posteriores a dividir Ases.
- número de barajas.
- penetración.
- cartas quemadas.
- bankroll.
- apuesta mínima y máxima. 
La interfaz deberá distinguir claramente entre reglas modificables y reglas fijas. No tendría sentido presentar al usuario las reglas fijas como parámetros editables.

---
# 14. Apuestas

Las apuestas pueden cambiar entre rondas y deben respetar un mínimo y máximo configurable.
La cantidad que apostada la decide cada jugador. Es decir:
* Jev decide su apuesta.
* Laya decide su apuesta.
* La estrategia óptima decide su apuesta.
No existe una estrategia de apuestas común. Jev y Laya deciden su apuesta basados en la situación en la que se encuentren, mientras que la estrategia óptima utiliza la cuenta Hi-Lo y un bet spread de 1-12.

---
# 15. Bancarrota y Finalización
las [[Reglas de BlackJack]] establecen una condición de bancarrota: si el bankroll de un jugador cae por debajo del mínimo de la mesa.
Si un jugador entra en bancarrota entonces la simulación continua en las otras mesas hasta que las tres mesas entren en bancarrota o termine la simulación.
Por ejemplo:

![[Decision_Blackjack_simulacion.excalidraw]]

---
# 16. Pausa y reanudación

La pausa no debe interpretarse como simplemente detener una animación en React.

Debe ser una **pausa real del motor**.

Se ha establecido que:

- se pausa después de terminar la acción actual;
- una solicitud pendiente de Jev no se cancela inmediatamente;
- se espera su respuesta;
- se ejecuta esa decisión;
- posteriormente se pausa. 

Por lo tanto, la pausa necesita ser controlada desde el backend/orquestador.

Esto además evita perder el estado de una ronda.

---
# 17. Manejo de errores

RNF-02 determina un comportamiento importante:
> Si Jev responde con error HTTP o no responde, se debe pausar y preservar los datos.

Además, posteriormente se indicó que si Jev está esperando una respuesta, las otras mesas también esperan, y si existe un error se detienen todas. 
Por ello, un error de Jev debe tratarse como un **error de simulación**, no como un simple error aislado de una petición HTTP.
El sistema debería conservar al menos:
* Configuración.
* Estado de la simulación.
* Ronda actual.
* Estado de las mesas.
* Datos registrados hasta el error Información del error.

La interfaz debería poder comunicar claramente:

```text
Simulación pausada

Jev API
HTTP 503
La respuesta no estuvo disponible.

[Reintentar]
[Salir]
```

Después del error se debe permitir al usuario ya sea volver a intentar mandar la petición a Jev o Salir de la simulación y volver al inicio de la aplicación.

---
# 18. Visualización

La interfaz no pretende ser una simulación gráfica compleja de un casino. El objetivo es mostrar de manera clara el estado de las tres mesas.

Cada panel debería contener conceptualmente:
```text
┌─────────────────────────────────┐
│ JEV                             │
│                                 │
│ Dealer                          │
│ [K♦] [7♣]                       │
│                                 │
│ Player                          │
│ [10♠] [5♥] [2♦]                 │
│                                 │
│ Bet: $50                        │
│ Bankroll: $1,250                │
│ Round: 183                      │
│                                 │
│ Decision: HIT                   │
│ Confidence: 87%                 │
│ Optimal: HIT            ✓       │
└─────────────────────────────────┘
```

Y equivalentes para Laya y Óptima.
La identificación visual de las tres mesas debe ser inequívoca.
En el caso de Óptima, esta no requiere tener un parámetro de *confidence*, pues es totalmente determinista.

---
# 19. Métricas y telemetría

Las métricas solicitadas inicialmente son:
- Profit/Loss;
- ROI;
- Agreement with Optimal Strategy;
- victorias/derrotas;
- confianza de Jev. 

Conviene diferenciar dos tipos de información.
### Estado instantáneo
Cambian constantemente:

```
Ronda
Bankroll
Apuesta
Cartas
Decisión
Confianza
Estado
```
### Estadísticas acumuladas
Se calculan a partir de muchas rondas:
```
Wins
Losses
Pushes
Profit/Loss
ROI
Agreement
```

Esto debe reflejarse posteriormente en la arquitectura de datos y en la interfaz.

---
# 20. Registro de cada ronda

El sistema debe guardar mucho más que el resultado final.
Cada ronda debe registrar:
- identificador de mesa/modelo.
- número de ronda.
- cartas iniciales.
- cartas del dealer.
- todas las cartas que aparezcan.
- todas las decisiones.
- confianza.
- resultado.
- bankroll resultante.
- respuesta completa de Jev/Laya. 

Una estructura conceptual podría ser:

```text
Run
 └── Simulation
      └── Round
           └── Table/Model
                ├── Initial state
                ├── Cards
                ├── Decisions
                ├── AI response
                ├── Result
                └── Financial state
```

Esto permitirá realizar análisis posteriormente sin tener que volver a ejecutar el experimento.

---
# 21. PostgreSQL

Aunque el RF-12 menciona CSV o JSON para exportación, la persistencia principal será PostgreSQL.
Por tanto, CSV no debería ser la fuente primaria.
La base de datos debe representar al menos conceptualmente:
* Run.
* Simulation.
* Round.
* Table / Player.
* Decision.
* Card / Hand data.
* AI Response.
* Result.
* Configuration.

Cada mesa tendrá su propia entidad de ronda. Conceptualmente se puede pensar como:

```text
Round
 ├── Jev
 ├── Laya
 └── Optimal
```

---
# 22. Persistencia por bloques

El requisito de almacenamiento por bloques significa que no debemos acumular decenas o cientos de miles de registros en memoria. Se usa un batching independiente a la cantidad de rondas.
Conceptualmente:

```
Rondas
  ↓
Buffer
  ↓
Batch
  ↓
PostgreSQL
  ↓
Limpiar buffer
  ↓
Siguiente batch
```

Esto permite soportar el rango esperado de 10,000 a 100,000 rondas sin depender de almacenar toda la ejecución en memoria.

---
# 23. Exportación
Aunque PostgreSQL será la persistencia primaria, el usuario necesita poder obtener los datos para analizarlos externamente.
El formato seleccionado como principal es **JSON**.

---
# 24. Estructura de Ejecución
Una ejecución completa puede representarse así:

```
Run
│
├── Configuration
│
├── Simulation 1
│   ├── Seed
│   ├── Shoe
│   ├── Round 1
│   │   ├── Jev
│   │   ├── Laya
│   │   └── Optimal
│   ├── Round 2
│   └── ...
│
├── Simulation 2
│   ├── Seed
│   ├── New Shoe
│   └── ...
│
└── ...
```

Cada simulación reinicia:
- bankroll.
- shoe.
- seed.
- pero mantiene la misma configuración.

---
# 25. Comunicación frontend-backend

La aplicación necesita dos tipos de comunicación.
### Comandos
Desde frontend hacia backend:

```
Crear simulación
Iniciar
Pausar
Reanudar
Cancelar
Exportar
```
### Estado
Desde backend hacia frontend:

```
Nueva ronda
Nueva carta
Nueva decisión
Cambio de bankroll
Cambio de estado
Error
Fin de simulación
```

Debido a que el sistema es interactivo y debe actualizarse continuamente, se opta por usar WebSocket como canal de telemetría.

---
# 26. Rendimiento

RNF-01 establece una latencia visual menor a **200 ms después de recibir la respuesta de inferencia**. Esto es diferente a exigir que Jev responda en menos de 200 ms.

La interpretación correcta para el diseño es:

```
Jev responde
     ↓
Backend procesa
     ↓
Evento de actualización
     ↓
Frontend
     ↓
Render
```

El tiempo máximo entre la respuesta ya recibida y su reflejo visual debe mantenerse por debajo de 200 ms.
El tiempo que tarde la API externa no queda cubierto por ese requisito.

---
# 27. Seguridad

Como será un sistema local de usuario único:
- no se necesita autenticación.
- no se necesita sistema de roles.
- no se necesita gestión de múltiples usuarios.
Pero la API key de Jev sigue siendo información sensible.
Por tanto:

```
.env
  ↓
Backend
  ↓
Jev API
```

y nunca:

```
.env
  ↓
Frontend
```

La configuración del endpoint también permanece fuera de la interfaz.

---
# 28. Docker

La solución tendrá al menos los siguientes servicios conceptuales:

```
Docker Compose
│
├── frontend
│   └── React/Vite
│
├── backend
│   └── FastAPI/Python
│
└── database
    └── PostgreSQL
```

Esto permite que el entorno completo pueda levantarse de forma consistente en una computadora nueva.

---
# 29. Estructura conceptual del proyecto

Sin entrar todavía en código, la separación debería parecerse conceptualmente a:

```
Proyecto
│
├── frontend
│   ├── UI
│   ├── pages
│   ├── components
│   ├── forms
│   └── visualization
│
├── backend
│   ├── API
│   ├── simulation
│   ├── blackjack
│   ├── strategies
│   ├── models
│   ├── persistence
│   └── integrations
│
├── database
│
├── docker
│
└── documentation
```

La idea importante es que `blackjack`, `simulation`, `strategies`, `integrations` y `persistence` no se mezclen entre sí.

---
# 30. Flujo principal de una ronda

El flujo conceptual más importante del sistema sería:

```
1. Crear ronda
       ↓
2. Determinar estado inicial
       ↓
3. Determinar apuesta de cada jugador
       ↓
4. Repartir cartas iniciales
       ↓
5. Detectar Blackjack / condiciones especiales
       ↓
6. Solicitar decisión de Jev
       ↓
7. Recibir decisión
       ↓
8. Registrar decisión
       ↓
9. Ejecutar acción
       ↓
10. Repetir mientras corresponda
       ↓
11. Ejecutar Laya
       ↓
12. Ejecutar Óptima
       ↓
13. Esperar a que las tres mesas terminen
       ↓
14. Ejecutar dealer de cada mesa
       ↓
15. Calcular resultados
       ↓
16. Actualizar bankroll
       ↓
17. Registrar ronda
       ↓
18. Emitir actualización al frontend
       ↓
19. Comprobar bancarrota / penetración / fin
       ↓
20. Pasar a siguiente ronda
```

Este flujo todavía requiere refinamiento porque algunas reglas especiales —split, insurance, surrender, etc.— pueden alterar el orden de ciertas operaciones.

---
# 31. Estados globales y estados de mesa

Una distinción importante para el diseño será separar:

**Estado de la simulación/global**
```
RUNNING
PAUSED
ERROR
COMPLETED
```

de:

**Estado de cada mesa**
```
WAITING
BETTING
PLAYER_TURN
WAITING_FOR_MODEL
DEALER_TURN
RESOLVING
FINISHED
```

Esto permitirá representar correctamente situaciones como:
```
Simulación: RUNNING

Jev       → WAITING_FOR_MODEL
Laya      → WAITING
Optimal   → WAITING
```

o:
```
Simulación: PAUSED

Jev       → PLAYER_TURN
Laya      → PLAYER_TURN
Optimal   → PLAYER_TURN
```

---
# 32. Puntos críticos de diseño

### 32.1. Sincronización

La comparación pierde utilidad si las tres entidades no están evaluando el mismo experimento. La sincronización debe ocurrir a nivel de ronda y de turno.
### 32.2. Reproducibilidad

La combinación de `seed + configuración + shoe` debe permitir reconstruir una ejecución.
### 32.3. Separación del motor

El motor de Blackjack debe permanecer independiente de Jev, Laya y la interfaz.
### 32.4. Registro detallado

Como el objetivo es analizar modelos, debemos almacenar las decisiones y respuestas, no solamente victorias y derrotas.