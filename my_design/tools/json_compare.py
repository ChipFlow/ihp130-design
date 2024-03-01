import json
import sys

def main():
    with open(sys.argv[1], "r") as f:
        gold = json.load(f)
    with open(sys.argv[2], "r") as f:
        gate = json.load(f)
    assert len(gold["events"]) == len(gate["events"]), f"mismatch: {len(gold['events'])} events in reference, {len(gate['events'])} in test output"
    for ev_gold, ev_gate in zip(gold["events"], gate["events"]):
        for field in ("peripheral", "event", "payload"):
            assert ev_gold["peripheral"] == ev_gate["peripheral"] and ev_gold["event"] == ev_gate["event"] and ev_gold["payload"] == ev_gate["payload"], \
                f"reference event {ev_gold} mismatches test event {ev_gate} beyond timestamp"
    print("Event logs are identical")


if __name__ == "__main__":
    main()
