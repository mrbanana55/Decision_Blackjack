"""Interactive terminal game to try out the Core Blackjack Engine."""

import sys
from pathlib import Path

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.engine import (
    Action,
    BlackjackRound,
    HandStatus,
    RoundPhase,
    Shoe,
    TableRules,
)


def format_card(card) -> str:
    """Format card with symbols and colors."""
    rank_str = card.rank.value
    rank_map = {
        "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
        "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        "jack": "J", "queen": "Q", "king": "K", "ace": "A",
    }
    r = rank_map.get(rank_str.lower(), rank_str.upper())
    suit_map = {
        "hearts": "♥",
        "diamonds": "♦",
        "clubs": "♣",
        "spades": "♠",
    }
    s = suit_map.get(card.suit.value.lower(), card.suit.value)
    return f"[{r}{s}]"


def print_table(state, current_bankroll: float, show_all_dealer: bool = False):
    print("\n" + "=" * 45)
    print(f"💰 BANKROLL: ${current_bankroll:.2f}")
    print("-" * 45)

    # Dealer display
    dealer = state.dealer_hand
    if show_all_dealer or dealer.is_revealed:
        cards_str = " ".join(format_card(c) for c in dealer.cards)
        print(f"🃏 DEALER ({dealer.total} pts): {cards_str}")
    else:
        upcard_str = format_card(dealer.upcard) if dealer.upcard else "[?]"
        print(f"🃏 DEALER: {upcard_str} [🂠]")

    print("-" * 45)
    # Player hands display
    for idx, hand in enumerate(state.player_hands):
        cards_str = " ".join(format_card(c) for c in hand.cards)
        active_marker = "👉 " if idx == state.active_hand_index and state.phase == RoundPhase.PLAYER_TURNS else "   "
        status_info = f"({hand.status.value})" if hand.status != HandStatus.ACTIVE else ""
        soft_info = " (soft)" if hand.is_soft else ""
        print(f"{active_marker}Hand {idx + 1} [Bet: ${hand.bet:.2f}]: {cards_str} -> {hand.total} pts{soft_info} {status_info}")
    print("=" * 45 + "\n")


def main():
    print("♠️ ♥️  WELCOME TO DECISION BLACKJACK  ♦️ ♣️")
    print("Powered by the Core Deterministic Engine\n")

    rules = TableRules(min_bet=10.0, max_bet=500.0)
    shoe = Shoe(num_decks=6)
    bankroll = 1000.0

    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=bankroll)

    while True:
        if engine.current_bankroll < rules.min_bet:
            print("💸 You are out of funds! Thanks for playing.")
            break

        print(f"Current Bankroll: ${engine.current_bankroll:.2f}")
        bet_input = input(f"Place your bet (${rules.min_bet} - ${rules.max_bet}) [default: 50, 'q' to quit]: ").strip()
        if bet_input.lower() == "q":
            print("Thanks for playing! Goodbye.")
            break

        try:
            bet = float(bet_input) if bet_input else 50.0
        except ValueError:
            print("Invalid amount. Using default $50.")
            bet = 50.0

        if bet > engine.current_bankroll:
            print(f"❌ You cannot bet more than your bankroll (${engine.current_bankroll:.2f}).")
            continue

        if not rules.validate_bet(bet):
            print(f"❌ Bet must be between ${rules.min_bet} and ${rules.max_bet}.")
            continue

        # Start Round
        try:
            state = engine.start_round(bet=bet)
        except Exception as e:
            print(f"Error starting round: {e}")
            continue

        print_table(state, engine.current_bankroll)

        # 1. Insurance Offer
        if state.phase == RoundPhase.INSURANCE_OFFERED:
            ins_cost = bet / 2.0
            print(f"🔔 Dealer shows an Ace! Insurance costs ${ins_cost:.2f}.")
            take_ins = input("Take insurance? (y/n) [default: n]: ").strip().lower() == "y"
            state = engine.submit_insurance(accept=take_ins)
            print_table(state, engine.current_bankroll)

        # 2. Player Turns
        action_map = {
            "h": Action.HIT,
            "s": Action.STAND,
            "d": Action.DOUBLE,
            "p": Action.SPLIT,
            "r": Action.SURRENDER,
        }

        action_names = {
            Action.HIT: "Hit (h)",
            Action.STAND: "Stand (s)",
            Action.DOUBLE: "Double (d)",
            Action.SPLIT: "Split (p)",
            Action.SURRENDER: "Surrender (r)",
        }

        while state.phase == RoundPhase.PLAYER_TURNS:
            legal = engine.get_legal_actions()
            if not legal:
                break

            opts = [action_names[a] for a in legal if a in action_names]
            prompt = f"Choose action [{' | '.join(opts)}]: "
            choice = input(prompt).strip().lower()

            action = action_map.get(choice)
            if not action or action not in legal:
                # Try full name
                try:
                    action = Action(choice)
                except ValueError:
                    action = None

            if not action or action not in legal:
                print("❌ Invalid or illegal action. Try again.")
                continue

            state = engine.submit_action(action)
            print_table(state, engine.current_bankroll)

        # 3. Dealer Turn
        if state.phase == RoundPhase.DEALER_TURN:
            print("🤖 Dealer is playing...")
            state = engine.play_dealer_to_end()
            print_table(state, engine.current_bankroll, show_all_dealer=True)

        # 4. Settlement
        if state.phase == RoundPhase.SETTLEMENT:
            settlement = engine.settle()
            print_table(state, engine.current_bankroll, show_all_dealer=True)

            print("🏆 ROUND RESULTS:")
            for h in settlement.hand_outcomes:
                status_emoji = "✅" if h.net_profit > 0 else ("🤝" if h.net_profit == 0 else "❌")
                print(f"  {status_emoji} Hand {h.hand_index + 1}: {h.description} (Net: ${h.net_profit:+.2f}, Return: ${h.payout:.2f})")

            if settlement.insurance_bet > 0:
                ins_status = "✅ Won" if settlement.insurance_payout > 0 else "❌ Lost"
                print(f"  Insurance: {ins_status} (Payout: ${settlement.insurance_payout:.2f})")

            print(f"  Net Round PnL: ${settlement.net_profit:+.2f}")
            print(f"  New Bankroll: ${settlement.final_bankroll:.2f}\n")

        # Play another?
        again = input("Play another round? (y/n) [default: y]: ").strip().lower()
        if again == "n":
            print(f"🏁 Final bankroll: ${engine.current_bankroll:.2f}. Thanks for playing!")
            break


if __name__ == "__main__":
    main()
