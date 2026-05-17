import os
import json

TRACKER_FILE = "docs/pillar_tracker.json"
PILLARS = ["AI", "Cloud", "Cybersecurity", "DevOps", "Automation"]

def get_next_pillar():
    """Returns the next pillar in rotation and saves the state."""
    os.makedirs("docs", exist_ok=True)

    # Load current state
    current_index = 0
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE) as f:
                data = json.load(f)
                current_index = data.get("next_index", 0)
        except:
            current_index = 0

    # Get current pillar
    pillar = PILLARS[current_index % len(PILLARS)]

    # Save next index
    with open(TRACKER_FILE, "w") as f:
        json.dump({
            "last_pillar": pillar,
            "next_index": (current_index + 1) % len(PILLARS),
            "run_count": current_index + 1,
        }, f, indent=2)

    return pillar

def get_three_pillars():
    """Returns 3 consecutive pillars starting from current position."""
    os.makedirs("docs", exist_ok=True)

    current_index = 0
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE) as f:
                data = json.load(f)
                current_index = data.get("next_index", 0)
        except:
            current_index = 0

    # Get 3 consecutive pillars
    pillars = []
    for i in range(3):
        pillars.append(PILLARS[(current_index + i) % len(PILLARS)])

    # Save next index (advance by 3)
    with open(TRACKER_FILE, "w") as f:
        json.dump({
            "last_pillar": pillars[-1],
            "next_index": (current_index + 3) % len(PILLARS),
            "run_count": current_index + 3,
        }, f, indent=2)

    return pillars
