Dentro de blackjack existen diferentes reglas que cambian la forma en la que se juega el blackjack. Las reglas que cambian se muestran en [[Reglas de BlackJack]].
Aún así, el flujo de una ronda de blackjack suele suceder de una forma similar 
independientemente de las reglas cambiantes.

---
# Etapas de una Ronda

1. **Apuesta inicial**: La mesa se abre para que los jugadores puedan hacer su apuesta. La apuesta que los jugadores pueden hacer es individual y debe estar dentro del rango que establece la mesa (Ejemplo: un jugador apuesta $100 en una mesa con un rango de $50 - $1000). 
2. **Repartición de cartas**: Después de hacer las apuestas, la mesa se cierra y el dealer comienza a repartir las cartas. Para repartir las cartas, el dealer va de su izquierda a derecha entregando una carta a la vez por jugador y para él. Por ejemplo, en una mesa con un solo jugador, el dealer le da una carta al jugador, se da una carta a si mismo, le da otra carta al jugador y finalmente se da su segunda carta el dealer. Es importante mencionar que las cartas del jugador se entregan de forma que se vea lo que tiene y que inicialmente, las cartas del dealer se encuentran tapadas, pero una vez que se entregan todas las cartas entonces el dealer destapa la primera carta que se entregó a si mismo.
3. **Juego**: Durante esta etapa los jugadores pueden tomar decisiones según las cartas que tengan y para superar el valor de las cartas del dealer sin pasarse de 21. Con el mismo orden que se repartieron las cartas es que los jugadores irán tomando sus decisiones, empezando por el que esté más a la izquierda del dealer y terminando con el que esté a la derecha. También es importante decir que el hecho de que un jugador se pase o pierda no hace que los demás jugadores pierdan instantáneamente. Las decisiones que cada jugador puede hacer son:
	1. **Hit**: El jugador pide una carta. Esta acción se puede hacer las veces que sean mientras no se pase de 21.
	2. **Stand**: El jugador se queda con las cartas que tiene. Esta acción se puede hacer una sola vez e indica el fin de turno del jugador. Se puede hacer desde un inicio, sin tener que pedir cartas.
	3. **Double**: Al recibir sus dos cartas iniciales, el jugador puede doblar su apuesta y recibir una sola carta más. Esta última carta que se le entrega se suele poner de forma horizontal. Si un jugador hace double se le entrega una última carta y termina su turno.
	4. **Split**: Cuando un jugador recibe dos cartas iguales (ejemplo: dos 8 de corazones) puede o no hacer split. Esto consiste en dividir su mano en dos nuevas manos independientes, apostando otra vez la cantidad que apostó originalmente (si apostó $50 e hizo split, entonces debe apostar otros $50). Al hacer split, el jugador empieza a jugar una de las dos manos y luego la otra. En cada mano puede hacer las mismas acciones que como si no hubiera hecho split a menos de que las reglas digan lo contrario. Si el jugador pierde una de las dos manos, la otra mano continua y en caso de ganar se le paga lo correspondiente a cada mano.
	5. **Surrender**: Al recibir sus cartas, el jugador puede rendirse y recuperar la mitad de su apuesta. Existen reglas variables que permiten hacer esto después de pedir cartas (late surrender) o que no permiten rendirse.
	6. **Insurance**: Cuando la carta descubierta del dealer es un As, entonces los jugadores tienen la oportunidad de hacer una apuesta secundaria por la mitad de su apuesta. En caso de que el dealer tenga blackjack, los jugadores que aseguraron ganan esa apuesta secundaria y se paga 2:1. En algunos casos, en cuanto se cierran los seguros el dealer revisa si tiene blackjack y si sí lo tiene termina la ronda y paga los seguros. En otros casos el juego continua y al finalizar la ronda el dealer revisa si tiene blackjack, y en caso de que sí entonces paga los seguros. Si el dealer no tiene blackjack entonces los jugadores pierden los seguros.
4. **Pagos**: Una vez que todos los jugadores pasaron, el dealer destapa su segunda carta y pide o se queda quieto de acuerdo a las reglas. Existen distintos casos que provocan que el dealer pague o no a los jugadores.
	1. Un jugador gana cuando hace blackjack, supera al dealer en su cuenta de cartas obtenidas o si el dealer se pasa de 21.
	2. Un jugador pierde cuando se pasa de 21 o cuando el dealer obtiene una cuenta mayor que él.
	3. Los jugadores empatan con el dealer si obtienen el mismo valor, en este caso no pierden su apuesta pero tampoco ganan nada. Un blackjack vs blackjack es empate.
---
# Diagrama de una Ronda
```mermaid
flowchart TD
    A([Inicio de la ronda]) --> B[Abrir mesa para apuestas]

    B --> C[Cada jugador realiza su apuesta]
    C --> D{¿Apuesta dentro del rango de la mesa?}

    D -- No --> C
    D -- Sí --> E[Realizar reparto inicial]

    E --> F[Dealer reparte una carta a cada jugador<br/>de izquierda a derecha]
    F --> G[Dealer recibe su primera carta]
    G --> H[Dealer reparte segunda carta a cada jugador]
    H --> I[Dealer recibe su segunda carta]
    
    I --> J[Jugador muestra sus cartas]
    J --> K[Dealer destapa su primera carta]
    K --> L{¿Carta descubierta del dealer es As?}

    L -- Sí --> M[Ofrecer Insurance a los jugadores]
    L -- No --> P[Iniciar turno de jugadores]
    M --> N[Jugadores deciden si toman Insurance]
    N --> O{¿Regla de la mesa revisa<br/>blackjack del dealer ahora?}

    O -- Sí --> Q{¿Dealer tiene Blackjack?}
    O -- No --> P

    Q -- Sí --> R[Pagar Insurance 2:1]
    R --> S([Fin de la ronda])
    Q -- No --> P

    P --> T[Comenzar con el jugador más a la izquierda]
    T --> U{¿Jugador tiene Blackjack?}

    U -- Sí --> V[Finalizar turno del jugador]
    U -- No --> W{¿Qué acción elige?}

    W -->|Hit| X[Recibir una carta]
    X --> Y{¿Jugador supera 21?}
    Y -- Sí --> Z[Jugador pierde]
    Y -- No --> W

    W -->|Stand| AA[Finalizar turno del jugador]

    W -->|Double| AB[Duplicar apuesta]
    AB --> AC[Recibir una sola carta]
    AC --> AD{¿Jugador supera 21?}
    AD -- Sí --> Z
    AD -- No --> AA

    W -->|Split| AE[Crear dos manos<br/>y realizar apuesta adicional]
    AE --> AF[Jugar primera mano]
    AF --> AG{¿Termina primera mano?}
    AG -- No --> W
    AG -- Sí --> AH[Jugar segunda mano]
    AH --> AI{¿Termina segunda mano?}
    AI -- No --> W
    AI -- Sí --> AJ[Finalizar turno del jugador]

    W -->|Surrender| AK[Jugador recupera la mitad de su apuesta]
    AK --> AL[Finalizar turno del jugador]

    V --> AM{¿Quedan jugadores por jugar?}
    AA --> AM
    Z --> AM
    AJ --> AM
    AL --> AM

    AM -- Sí --> AN[Pasar al siguiente jugador]
    AN --> T

    AM -- No --> AO[Dealer destapa su segunda carta]
    AO --> AP{¿Dealer tiene Blackjack?}

    AP -- Sí --> AQ[Resolver pagos contra Blackjack]
    AP -- No --> AR{¿Dealer supera 21?}

    AR -- Sí --> AS[Dealer pierde<br/>Jugadores que no se pasaron ganan]
    AR -- No --> AT{¿Dealer debe pedir carta?}

    AT -- Sí --> AU[Dealer recibe una carta]
    AU --> AV{¿Dealer supera 21?}
    AV -- Sí --> AS
    AV -- No --> AT

    AT -- No --> AW[Dealer se queda con sus cartas]

    AW --> AX[Comparar cada mano válida<br/>contra el dealer]

    AX --> AY{¿Resultado de la comparación?}
    AY -->|Jugador mayor| AZ[Jugador gana]
    AY -->|Dealer mayor| BA[Jugador pierde]
    AY -->|Mismo valor| BB[Empate: se devuelve la apuesta]

    AQ --> BC[Resolver resultados y pagos]
    AS --> BC
    AZ --> BC
    BA --> BC
    BB --> BC

    BC --> S([Fin de la ronda])
```
