# API & Schema Contracts: Laya System One Integration

**Feature**: `005-laya-agent-integration`
**Target Endpoint**: `POST /v1/systemone` & `GET /health`

All requests and responses strictly adhere to the TypeSafe System One JSON specifications described in [`docs/Laya_Example_Body.md`](file:///Users/andresdelgado/Documents/Coding/Decision_Blackjack/docs/Laya_Example_Body.md).

---

## 1. Health Probe Contract

### `GET /health`
Probe to verify that the local Laya inference engine is up and running.

#### Response `200 OK`
```json
{
  "status": "ok",
  "loaded": [
    "english",
    "multilingual",
    "typed-decisions"
  ],
  "revisions": {
    "english": "7b928d828b7b0e022f929d9bd2e44165aa270148",
    "multilingual": "7b928d828b7b0e022f929d9bd2e44165aa270148",
    "typed-decisions": "7b928d828b7b0e022f929d9bd2e44165aa270148"
  },
  "device": "mps",
  "device_is_preference": false,
  "checkpoint_devices": {
    "english": "mps",
    "multilingual": "mps",
    "typed-decisions": "mps"
  },
  "cpu_fallbacks": {
    "english": {"count": 0, "last_reason": null},
    "multilingual": {"count": 0, "last_reason": null},
    "typed-decisions": {"count": 0, "last_reason": null}
  }
}
```

---

## 2. Situational Decision Contracts (`POST /v1/systemone`)

### Contract 1A: Initial Paired Hand (Split Eligible, Surrender Disabled)

**Condition**: Hand has 2 equal rank cards (e.g. 8-8 or A-A), bankroll $\ge$ current bet, split limit not reached, and table rules have surrender disabled (`allow_late_surrender = False`).

#### Request Payload
```json
{
  "state": "You are playing blackjack. Round 5, Hand 1. Player holds [8 of Spades, 8 of Diamonds] (Pair of 8s, Total: 16, Hard). Dealer Upcard: 7 of Hearts. Bankroll: $1,000. True Count: +0.5. Current Bet: $50. Surrender: Disabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the paired hand given the dealer upcard and table rules.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "split": "Separate pair of 8s into two independent hands with matching wager of $50"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "action": {
      "choice": "split",
      "confidence": 0.97,
      "distribution": {
        "split": 0.97,
        "hit": 0.02,
        "stand": 0.01
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 44,
    "latency_ms": 30.2
  }
}
```

---

### Contract 1B: Initial Paired Hand (Split Eligible, Surrender Enabled)

**Condition**: Hand has 2 equal rank cards (e.g. 8-8 vs Dealer 10/Ace), bankroll $\ge$ current bet, split limit not reached, and table rules have late surrender enabled (`allow_late_surrender = True`).

#### Request Payload
```json
{
  "state": "You are playing blackjack. Round 7, Hand 1. Player holds [8 of Spades, 8 of Diamonds] (Pair of 8s, Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $1,000. True Count: +0.0. Current Bet: $50. Surrender: Enabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the paired hand given the dealer upcard and table rules (surrender is allowed).",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "split": "Separate pair of 8s into two independent hands with matching wager of $50",
        "surrender": "Forfeit half the initial wager ($25) and retire the hand"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "action": {
      "choice": "surrender",
      "confidence": 0.91,
      "distribution": {
        "surrender": 0.91,
        "split": 0.06,
        "hit": 0.02,
        "stand": 0.01
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 50,
    "latency_ms": 33.5
  }
}
```

---

### Contract 2A: Initial Standard Hand (Double Eligible, Surrender Disabled, No Split)

**Condition**: Hand has 2 non-matching cards (e.g. 5+6 = 11 or 10+6 = 16), bankroll $\ge$ current bet, no pair, and surrender is disabled (`allow_late_surrender = False`).

#### Request Payload
```json
{
  "state": "You are playing blackjack. Round 12, Hand 1. Player holds [5 of Diamonds, 6 of Clubs] (Total: 11, Hard). Dealer Upcard: 6 of Spades. Bankroll: $850. True Count: +2.0. Current Bet: $50. Surrender: Disabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the player hand given the dealer upcard and table state.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "double": "Double the initial wager to $100, receive exactly one card, and stand"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "action": {
      "choice": "double",
      "confidence": 0.98,
      "distribution": {
        "double": 0.98,
        "hit": 0.015,
        "stand": 0.005
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 42,
    "latency_ms": 28.1
  }
}
```

---

### Contract 2B: Initial Standard Hand (Double & Surrender Enabled, No Split)

**Condition**: Hand has 2 non-matching cards (e.g. 10+6 = 16 vs Dealer 10/Ace, or 9+6 = 15 vs 10), bankroll $\ge$ current bet, no pair, and table rules have late surrender enabled (`allow_late_surrender = True`).

#### Request Payload
```json
{
  "state": "You are playing blackjack. Round 15, Hand 1. Player holds [10 of Spades, 6 of Hearts] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $950. True Count: +1.0. Current Bet: $50. Surrender: Enabled.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the player hand given the dealer upcard and table state (surrender is allowed).",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "double": "Double the initial wager to $100, receive exactly one card, and stand",
        "surrender": "Forfeit half the initial wager ($25) and retire the hand"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "action": {
      "choice": "surrender",
      "confidence": 0.94,
      "distribution": {
        "surrender": 0.94,
        "hit": 0.04,
        "stand": 0.015,
        "double": 0.005
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 48,
    "latency_ms": 31.0
  }
}
```

---

### Contract 3: Multi-Card Draw Hand (Post-Hit / 3+ Cards)

**Condition**: Hand has $\ge 3$ cards after hitting. Game rules strictly prohibit double, split, and surrender on multi-card hands regardless of table rules.

#### Request Payload
```json
{
  "state": "You are playing blackjack. Round 12, Hand 1. Player holds [10 of Spades, 3 of Hearts, 3 of Clubs] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $800. True Count: +1.5. Current Bet: $50.",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the multi-card hand given the dealer upcard and table state.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "action": {
      "choice": "hit",
      "confidence": 0.76,
      "distribution": {
        "hit": 0.76,
        "stand": 0.24
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 36,
    "latency_ms": 24.5
  }
}
```

---

### Contract 4: Insurance Phase Decision

**Condition**: Dealer's upcard is an Ace before player hand play begins.

#### Request Payload
```json
{
  "state": "You are playing blackjack. Dealer exposed upcard is Ace. Player holds [King of Hearts, 7 of Clubs] (Total: 17). Bankroll: $1,200. True Count: +1.0. Insurance cost: $25.",
  "questions": {
    "insurance": {
      "type": "choice",
      "instructions": "Decide whether to accept or decline the insurance side bet against a possible dealer Blackjack.",
      "criteria": {
        "accept": "Pay insurance wager of $25 to protect against dealer natural Blackjack (pays 2:1)",
        "decline": "Decline insurance side bet and proceed to normal hand resolution"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "insurance": {
      "choice": "decline",
      "confidence": 0.95,
      "distribution": {
        "decline": 0.95,
        "accept": 0.05
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 34,
    "latency_ms": 22.0
  }
}
```

---

### Contract 5: Round Betting Phase (Pre-Deal Wager Sizing)

**Condition**: Start of round before initial deal. Sized using table minimum bet ($M = \text{rules.min\_bet}$, e.g. $50).

#### Request Payload
```json
{
  "state": "You are playing blackjack. Round 8. Table Rules Minimum Bet: $50. Current Bankroll: $1,150. Shoe True Count: +3.0. Cards Seen: 168/312.",
  "questions": {
    "bet_sizing": {
      "type": "choice",
      "instructions": "Select the opening wager level for the upcoming round given the shoe count and current bankroll.",
      "criteria": {
        "1x": "1 unit ($50) - Base table minimum wager",
        "2x": "2 units ($100) - Moderate count advantage wager",
        "4x": "4 units ($200) - Elevated count advantage wager",
        "8x": "8 units ($400) - High count maximum spread wager"
      }
    }
  }
}
```

#### Response Payload `200 OK`
```json
{
  "answers": {
    "bet_sizing": {
      "choice": "4x",
      "confidence": 0.88,
      "distribution": {
        "4x": 0.88,
        "2x": 0.08,
        "1x": 0.03,
        "8x": 0.01
      }
    }
  },
  "meta": {
    "model": "typed-decisions",
    "device": "mps",
    "tokens": 40,
    "latency_ms": 26.8
  }
}
```

---

## 3. Error Responses & Fault Contract

When Laya returns HTTP 4xx, 5xx, or request times out:
```json
{
  "detail": "request body must be an object with a 'questions' field"
}
```
`LayaClient` captures the HTTP status or connection exception, packages the diagnostics into `AgentFaultError`, and the simulation orchestrator initiates graceful session pausing without data loss.
