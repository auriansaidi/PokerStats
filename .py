import pandas as pd
from collections import defaultdict
from os import listdir
from os.path import isfile, join

# Load logs
path_to_logs = "logs"  # Directory containing poker log files
files = [f for f in listdir(path_to_logs) if isfile(join(path_to_logs, f))]
logs = []

# Read and reverse log files
for file in files:
    df = pd.read_csv(f"{path_to_logs}/{file}")
    logs.extend(reversed(df["entry"]))

# Split logs into individual hands
hands = []
current_hand = []
in_hand = False

for log in logs:
    if log.startswith("-- ending"):  # Detect the end of a hand.
        in_hand = False
        hands.append(current_hand)
        current_hand = []
    elif log.startswith("-- starting"):  # Detect the start of a hand.
        in_hand = True
    if in_hand:
        current_hand.append(log)

# Define actions for preflop and postflop stages
preflop_actions = ["folds", "calls", "raises"]
flop_actions = ["bets", "checks", "folds", "calls", "raises"]

# Buckets for categorizing hands by the number of active players
hand_buckets = {
    "short-handed": [],  # 1-3 players
    "medium-handed": [],  # 4-6 players
    "full-ring": []  # 7-9 players
}

# Categorize hands into buckets based on the number of active players
for hand in hands:
    players_in_hand = set()
    for log in hand:
        if any(action in log for action in preflop_actions + flop_actions):
            player = log[1:log.index(" @")].lower()  # Extract player name.
            players_in_hand.add(player)

    player_count = len(players_in_hand)
    if player_count <= 3:
        hand_buckets["short-handed"].append(hand)
    elif 4 <= player_count <= 6:
        hand_buckets["medium-handed"].append(hand)
    elif 7 <= player_count <= 9:
        hand_buckets["full-ring"].append(hand)

# Function to calculate statistics for a given set of hands
def calculate_stats(hands):
    """Calculate poker statistics for the given hands."""
    # Initialize data structures for statistics
    preflop = defaultdict(lambda: {action: 0 for action in preflop_actions})
    threebets = defaultdict(lambda: {action: 0 for action in preflop_actions})
    cbets = defaultdict(lambda: {action: 0 for action in flop_actions})
    fourbets = defaultdict(int)  # Track 4-bets
    showdown_counts = defaultdict(lambda: {"participated": 0, "showdown": 0})  # Track showdown participation
    can_3bet = defaultdict(int)  # Opportunities to 3-bet

    # Analyze each hand
    for hand in hands:
        raise_count = 0  # Number of raises in preflop
        street = "preflop"  # Current stage of the hand
        fourbettor = None  # Player who made a 4-bet
        showdown_reached = False  # Whether the hand went to showdown
        participants = set()  # Players involved in the hand

        for log in hand:
            # Update current street based on log content
            if log.startswith("Flop"):
                street = "flop"
            elif log.startswith("Turn"):
                street = "turn"
            elif log.startswith("River"):
                street = "river"
            elif "shows" in log or "wins" in log:
                showdown_reached = True

            # Analyze preflop actions
            if street == "preflop":
                for action in preflop_actions:
                    if action in log:
                        player = log[1:log.index(" @")].lower()
                        participants.add(player)
                        if raise_count == 1:  # Track 3-bet opportunities
                            can_3bet[player] += 1
                        if action == "raises":
                            raise_count += 1
                            if raise_count == 3:  # Identify 4-bettor
                                fourbettor = player
                                fourbets[player] += 1

        # Update showdown stats
        for player in participants:
            showdown_counts[player]["participated"] += 1
            if showdown_reached:
                showdown_counts[player]["showdown"] += 1

    # Calculate statistics for each player
    stats = {}
    for player, actions in preflop.items():
        num_hands = sum(actions.values())
        vpip = round(100 * (actions["calls"] + actions["raises"]) / num_hands)
        pfr = round(100 * actions["raises"] / num_hands)
        threebet = round(100 * threebets[player]["raises"] / can_3bet[player]) if can_3bet[player] > 0 else 0
        fourbet = round(100 * fourbets[player] / num_hands) if num_hands > 0 else 0
        went_to_showdown = (
            round(100 * showdown_counts[player]["showdown"] / showdown_counts[player]["participated"])
            if showdown_counts[player]["participated"] > 0
            else 0
        )

        stats[player] = {
            "vpip": vpip,
            "pfr": pfr,
            "3bet": threebet,
            "4bet": fourbet,
            "went to showdown": went_to_showdown,
        }
    return stats

# Calculate stats for each bucket
bucket_stats = {bucket: calculate_stats(hands) for bucket, hands in hand_buckets.items()}

# Output statistics for each bucket
for bucket, stats in bucket_stats.items():
    print(f"\n{bucket.capitalize()} Stats:")
    for player, stat in stats.items():
        print(player, stat)
