# Reglas del Juego
## Reglas Modificables

^65d10d

### Dealer y Mesa
- **Regla del 17 suave (Soft 17):** Dealer planta en soft 17 (**S17**) vs. pide carta (**H17**).
- **Pago por Blackjack natural:** 3:2, 6:5, 1:1.
- **Blackjack tras dividir Ases:** ¿Paga 1:1 o paga bono de Blackjack?
- **Regla de O/U (Peek / Hole Card):**
    - _American Style (Peek):_ El dealer revisa blackjack antes de que el jugador actúe.
    - _European No Hole Card (ENHC):_ El dealer no toma segunda carta hasta el final (el jugador arriesga apuestas dobles/splits si el dealer saca blackjack).
- **Seguro (Insurance):** Permitido / Prohibido; ratio de pago 2:1.
- **Rendición (Surrender):** No permitida, Rendición Temprana (_Early Surrender_), o Rendición Tardía (_Late Surrender_).
### Reglas del Jugador (Doblar y Dividir)
- **Double After Split (DAS):** Permitido o Prohibido doblar tras dividir una mano.
- **Resplit:** Número máximo de manos divididas (usualmente hasta 3 o 4 manos).
- **Resplit de Ases (RSA):** Permitido o prohibido volver a dividir Ases.
- **Carta tras dividir Ases:** ¿Solo una carta obligatoria y plantarse (_Hit Split Aces = False_), o se permite pedir más?
### Zapato, Cartas y Mezclado (Deck & Shoe)
- **Número de barajas:** 1, 2, 4, 6 u 8 mazos.
- **Penetración del mazo (_Cut Card_):** Porcentaje del zapato que se reparte antes de barajar (por ejemplo, 50% a 85%).
- **Quema de cartas (_Burn cards_):** Cuántas cartas descarta el dealer al inicio del zapato o de cada mano (0, 1 o varias).
### Economía, Apuestas y Bankroll
- **Bankroll inicial:** Monto inicial del bot (ej. $1,000, $10,000).
- **Límites de la mesa:** Apuesta mínima ($5, $25) y apuesta máxima ($500, $5,000).
- **Regla de banca rota:** Criterio de parada si el bankroll cae por debajo del mínimo de la mesa.
## Reglas Fijas
### Valores Numéricos de las Cartas
- **Cartas del 2 al 9:** Conservan su valor nominal estricto.
- **Figuras y diez (10, J, Q, K):** Todas valen exactamente 10 puntos.
- **As:** Vale 11 o 1 de forma dinámica. Siempre cuenta como 11 a menos que cause que la mano supere 21, en cuyo caso pasa a valer 1 automáticamente.
### Definición de Mano y Blackjack Natural
- **Total objetivo:** El puntaje máximo sin perder es 21. Si una mano supera 21, pierde la ronda de inmediato.
- **Blackjack Natural:** Se compone **únicamente** de las dos primeras cartas repartidas sumando 21 (un As + cualquier carta de valor 10). Si se dividen 2 Ases y se obtiene un 10 además del As en una o ambas manos, entonces se considera 21 y no blackjack.
- **Jerarquía de 21:** Un Blackjack natural vence a cualquier mano de 21 puntos formada por 3 o más cartas (o tras dividir).
### Orden de Turnos y Resolución Asimétrica
- **El jugador actúa primero:** El dealer no juega hasta que todos los jugadores activos en la mesa hayan completado sus decisiones (o se hayan pasado).
- **Bancarrota simultánea:** Si el jugador se pasa de 21, pierde su apuesta inmediatamente. Si el dealer se pasa más tarde en esa misma ronda, el jugador **no** recupera su dinero ni empata.
### Mecánica Obligatoria del Dealer
- **Cero libre albedrío:** El dealer no toma decisiones estratégicas, no puede doblar, no puede dividir ni puede rendirse. Sigue un algoritmo determinista estricto:
    - Si su puntaje es menor a 17, está obligado a pedir carta (_Hit_).
    - Si su puntaje alcanza 17 duro o más (hasta 21), está obligado a plantarse (_Stand_).
### Condiciones de Victoria y Empate (_Push_)
- **Gana el jugador (pago 1:1):**
    - El jugador no se pasa y su total es mayor que el del dealer.
    - El jugador no se pasa y el dealer se pasa de 21.
- **Gana el dealer (se lleva la apuesta):**
    - El jugador se pasa de 21.
    - El dealer no se pasa y su total es mayor que el del jugador.
- **Empate (_Push_):**
    - Mismo total de puntos entre jugador y dealer (o ambos con Blackjack natural). La apuesta se devuelve íntegra.

