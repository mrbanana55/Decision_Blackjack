# Interface Contract: Jev System One API & Diagnostic Endpoints

**Feature Branch**: `006-jev-agent-integration`  
**Date**: 2026-10-12  
**Status**: Completed  

---

## 1. Remote System One HTTP Interface (`POST /v1/systemone`)

### Request Headers
```http
POST /v1/systemone HTTP/1.1
Host: api.typesafe.ai
Authorization: Bearer <TYPESAFE_API_KEY>
Content-Type: application/json
```

### Request Body Specification
```json
{
  "state": "<Observable game and table context string>",
  "model": "jev-latest",
  "questions": {
    "<question_id>": {
      "type": "choice",
      "instructions": "<Decision prompt for model>",
      "criteria": {
        "<option_key>": "<Description of candidate action>"
      }
    }
  }
}
```

---

## 2. Situational Hand Payloads

### Situation 1A: Paired Hand (Split Eligible, Surrender Disabled)
```json
{
  "state": "You are playing blackjack. Round 3, Hand 1. Player holds [8 of Spades, 8 of Diamonds] (Pair of 8s) (Total: 16, Hard). Dealer Upcard: 7 of Hearts. Bankroll: $1,000.00. True Count: +0.5. Surrender: Disabled. Table Minimum Bet: $50.00. Legal actions: hit, stand, split.",
  "model": "jev-latest",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the paired hand given the dealer upcard and table rules.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "split": "Separate pair of cards into two independent hands with matching wager"
      }
    }
  }
}
```

### Situation 1B: Paired Hand (Split Eligible, Surrender Enabled)
```json
{
  "state": "You are playing blackjack. Round 3, Hand 1. Player holds [8 of Spades, 8 of Diamonds] (Pair of 8s) (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $1,000.00. True Count: +0.0. Surrender: Enabled. Table Minimum Bet: $50.00. Legal actions: hit, stand, split, surrender.",
  "model": "jev-latest",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the paired hand given the dealer upcard and table rules (surrender is allowed).",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "split": "Separate pair of cards into two independent hands with matching wager",
        "surrender": "Forfeit half the initial wager and retire the hand"
      }
    }
  }
}
```

### Situation 2A: Standard Hand (Double Eligible, Surrender Disabled)
```json
{
  "state": "You are playing blackjack. Round 5, Hand 1. Player holds [5 of Diamonds, 6 of Clubs] (Total: 11, Hard). Dealer Upcard: 6 of Spades. Bankroll: $1,000.00. True Count: +2.0. Surrender: Disabled. Table Minimum Bet: $50.00. Legal actions: hit, stand, double.",
  "model": "jev-latest",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the player hand given the dealer upcard and table state.",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "double": "Double the initial wager, take exactly one card, and stand"
      }
    }
  }
}
```

### Situation 2B: Standard Hand (Double & Surrender Enabled)
```json
{
  "state": "You are playing blackjack. Round 7, Hand 1. Player holds [10 of Spades, 6 of Hearts] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $1,000.00. True Count: +1.0. Surrender: Enabled. Table Minimum Bet: $50.00. Legal actions: hit, stand, double, surrender.",
  "model": "jev-latest",
  "questions": {
    "action": {
      "type": "choice",
      "instructions": "Select the optimal action for the player hand given the dealer upcard and table state (surrender is allowed).",
      "criteria": {
        "hit": "Request an additional card from the dealer",
        "stand": "Conclude turn and maintain current hand total",
        "double": "Double the initial wager, take exactly one card, and stand",
        "surrender": "Forfeit half the initial wager and retire the hand"
      }
    }
  }
}
```

### Situation 3: Multi-Card Draw (Post-Hit / 3+ Cards)
```json
{
  "state": "You are playing blackjack. Round 8, Hand 1. Player holds [10 of Spades, 3 of Hearts, 3 of Clubs] (Total: 16, Hard). Dealer Upcard: 10 of Clubs. Bankroll: $950.00. True Count: +1.5. Legal actions: hit, stand.",
  "model": "jev-latest",
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

### Situation 4: Insurance Offer (Dealer Upcard is Ace)
```json
{
  "state": "You are playing blackjack. Dealer exposed upcard is Ace. Player holds [King of Spades, 7 of Diamonds] (Total: 17). Bankroll: $1,000.00. True Count: +3.0. Insurance cost: $25.00.",
  "model": "jev-latest",
  "questions": {
    "insurance": {
      "type": "choice",
      "instructions": "Decide whether to accept or decline the insurance side bet against a possible dealer Blackjack.",
      "criteria": {
        "accept": "Pay insurance wager of $25.00 to protect against dealer natural Blackjack (pays 2:1)",
        "decline": "Decline insurance side bet and proceed to normal hand resolution"
      }
    }
  }
}
```

### Situation 5: Pre-Deal Round Wager Sizing
```json
{
  "state": "You are playing blackjack. Round 14. Table Rules Minimum Bet: $50.00. Current Bankroll: $1,250.00. Shoe True Count: +2.5. Cards Seen: 142/312.",
  "model": "jev-latest",
  "questions": {
    "bet_sizing": {
      "type": "choice",
      "instructions": "Select the opening wager level for the upcoming round given the shoe count and current bankroll.",
      "criteria": {
        "1x": "1 unit ($50.00) - Base table minimum wager",
        "2x": "2 units ($100.00) - Moderate count advantage wager",
        "4x": "4 units ($200.00) - Elevated count advantage wager",
        "8x": "8 units ($400.00) - High count maximum spread wager"
      }
    }
  }
}
```

---

## 3. Remote Response Specifications

### Successful Response (HTTP 200)
```json
{
  "model": "jev-1.13.0",
  "answers": {
    "action": {
      "type": "choice",
      "choice": "hit",
      "probabilities": {
        "hit": 0.88,
        "stand": 0.12
      },
      "confidence": 0.81
    }
  },
  "usage": {
    "input_tokens": 142,
    "output_tokens": 24
  }
}
```

### Error Responses
- **HTTP 401 Unauthorized**: Missing or invalid API key. Triggers immediate pause with configuration alert.
- **HTTP 422 Unprocessable Entity**: Malformed payload. Triggers agent fault and capture of debug payload.
- **HTTP 429 Too Many Requests**: Rate limit reached. Triggers exponential backoff retry.
- **HTTP 529 Overloaded**: Cloud service overloaded. Triggers backoff retry.

---

## 4. Backend Diagnostic API (`GET /health/jev`)

### Success (HTTP 200)
```json
{
  "status": "ok",
  "provider": "typesafe",
  "model": "jev-latest",
  "endpoint": "https://api.typesafe.ai/v1/systemone",
  "has_api_key": true
}
```

### Unavailable (HTTP 200)
```json
{
  "status": "unavailable",
  "provider": "typesafe",
  "error": "Missing TYPESAFE_API_KEY in environment configuration",
  "has_api_key": false
}
```
