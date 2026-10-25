"""Conservative EVCC projections of the charger's observed session status."""

# A session can be authorized while the vehicle or charger suspends energy flow.
SESSION_ENABLED = {0: False, 1: False, 4: True, 5: True, 6: True, 8: False}
IEC_STATUS = {0: "A", 1: "B", 2: "B", 4: "B", 5: "B", 6: "C", 7: "B", 8: "B"}
