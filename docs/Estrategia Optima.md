# Estrategia básica de Blackjack

## 1. Cómo leer las tablas

### Acciones

| Símbolo | Acción                                                                              |
|:--------|:------------------------------------------------------------------------------------|
| `H`     | Hit — pedir carta                                                                   |
| `S`     | Stand — plantarse                                                                   |
| `D`     | Double — doblar si está permitido; de lo contrario, hit                             |
| `Ds`    | Double si está permitido; de lo contrario, stand                                    |
| `Y`     | Split — dividir el par                                                              |
| `Y/N`   | Dividir solo si se ofrece **DAS** (Double After Split); de lo contrario, no dividir |
| `N`     | No dividir                                                                          |
| `SUR`   | Surrender — rendirse                                                                |

---
# 2. Hard Totals

**Dealer Upcard**

| Mano | 2   | 3   | 4   | 5   | 6   | 7   | 8   | 9   | 10  | A   |
| :--- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 17   | S   | S   | S   | S   | S   | S   | S   | S   | S   | S   |
| 16   | S   | S   | S   | S   | S   | H   | H   | H   | H   | H   |
| 15   | S   | S   | S   | S   | S   | H   | H   | H   | H   | H   |
| 14   | S   | S   | S   | S   | S   | H   | H   | H   | H   | H   |
| 13   | S   | S   | S   | S   | S   | H   | H   | H   | H   | H   |
| 12   | H   | H   | S   | S   | S   | H   | H   | H   | H   | H   |
| 11   | D   | D   | D   | D   | D   | D   | D   | D   | D   | D   |
| 10   | D   | D   | D   | D   | D   | D   | D   | D   | H   | H   |
| 9    | H   | D   | D   | D   | D   | H   | H   | H   | H   | H   |
| 8    | H   | H   | H   | H   | H   | H   | H   | H   | H   | H   |

------------------------------------------------------------------------

# 3. Soft Totals

**Dealer Upcard**

| Mano | 2   | 3   | 4   | 5   | 6   | 7   | 8   | 9   | 10  | A   |
| :--- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| A,9  | S   | S   | S   | S   | S   | S   | S   | S   | S   | S   |
| A,8  | S   | S   | S   | S   | S   | S   | S   | S   | S   | S   |
| A,7  | Ds  | Ds  | Ds  | Ds  | Ds  | S   | S   | H   | H   | H   |
| A,6  | H   | D   | D   | D   | D   | H   | H   | H   | H   | H   |
| A,5  | H   | H   | D   | D   | D   | H   | H   | H   | H   | H   |
| A,4  | H   | H   | D   | D   | D   | H   | H   | H   | H   | H   |
| A,3  | H   | H   | H   | D   | D   | H   | H   | H   | H   | H   |
| A,2  | H   | H   | H   | D   | D   | H   | H   | H   | H   | H   |

------------------------------------------------------------------------
# 4. Pair Splitting

**Dealer Upcard**

| Par | 2   | 3   | 4   | 5   | 6   | 7   | 8   | 9   | 10  | A   |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| A,A | Y   | Y   | Y   | Y   | Y   | Y   | Y   | Y   | Y   | Y   |
| T,T | N   | N   | N   | N   | N   | N   | N   | N   | N   | N   |
| 9,9 | Y   | Y   | Y   | Y   | Y   | N   | Y   | Y   | N   | N   |
| 8,8 | Y   | Y   | Y   | Y   | Y   | Y   | Y   | Y   | N   | N   |
| 7,7 | Y   | Y   | Y   | Y   | Y   | Y   | N   | N   | N   | N   |
| 6,6 | Y/N | Y   | Y   | Y   | Y   | N   | N   | N   | N   | N   |
| 5,5 | N   | N   | N   | N   | N   | N   | N   | N   | N   | N   |
| 4,4 | N   | N   | N   | Y/N | Y/N | N   | N   | N   | N   | N   |
| 3,3 | Y/N | Y/N | Y   | Y   | Y   | Y   | N   | N   | N   | N   |
| 2,2 | Y/N | Y/N | Y   | Y   | Y   | Y   | N   | N   | N   | N   |

### Regla DAS

`Y/N` significa:

> **Dividir si se permite Double After Split (DAS); de lo contrario, no
> dividir.**

------------------------------------------------------------------------

# 5.  Surrender

**Dealer Upcard**

La tabla de estrategia básica mostrada en la primera imagen indica:

| Mano | 2   | 3   | 4   | 5   | 6   | 7   | 8   | 9   | 10  | A   |
| :--- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 16   | —   | —   | —   | —   | —   | —   | —   | SUR | SUR | SUR |
| 15   | —   | —   | —   | —   | —   | —   | —   | —   | SUR | —   |
| 14   | —   | —   | —   | —   | —   | —   | —   | —   | —   | —   |

------------------------------------------------------------------------

# 6. Insurance / Even Money

La tabla indica explícitamente:

> **INSURANCE OR EVEN MONEY: DON’T TAKE**

Esto significa que **no se toma Insurance como parte de la
estrategia básica**.

------------------------------------------------------------------------

# 7. Bet Spread

La estrategia óptima debe hacer su apuesta basándose en el valor de la True Count y la cantidad de la apuesta mínima.
Cuando la True Count es $\leq$ 0 entonces la estrategia óptima decide apostar la cantidad mínima de la mesa. En caso de que la True Count sea positiva, la estrategia óptima hace $n$ veces la apuesta mínima de la mesa.
Por ejemplo, en un bet spread de 1 - 12 y una apuesta mínima de $50, si la True Count es de 2 entonces la estrategia óptima debe apostar $\$50 * 2 = \$100$.

---
# 8. Prioridad de decisiones

Cuando se implementa esta estrategia en software, conviene considerar
las decisiones en este orden:

1.  **Reglas de la mesa**
    - número de barajas;
    - H17/S17;
    - DAS;
    - surrender;
    - restricciones de double/split;
    - blackjack del dealer.
2.  **Estado de la mano**
    - hard total;
    - soft total;
    - par;
    - posibilidad de surrender.
3.  **Estrategia básica**
    - obtener la acción base.
4.  **True Count**
    - obtener el TC actual.

Esto permite separar claramente la **estrategia básica** de las
**decisiones dependientes del conteo**.

------------------------------------------------------------------------

