import pandas as pd

from prorealtime_v2.strategies.hold_signals import determine_comment_and_opportunity


def test_entry_opportunity_from_negative_histogram_recovery():
    df = pd.DataFrame(
        [
            {"hist": -0.5, "Close": 10, "TS": 11, "KS": 10, "SSA": 9, "SSB": 8, "Evolution_rate": -1},
            {"hist": -0.3, "Close": 11, "TS": 10, "KS": 10, "SSA": 9, "SSB": 8, "Evolution_rate": 2},
            {"hist": -0.1, "Close": 12, "TS": 10, "KS": 10, "SSA": 9, "SSB": 8, "Evolution_rate": 2},
        ]
    )
    signal = determine_comment_and_opportunity(df)
    assert "Entry" in signal.comment
    assert signal.cloud > 0


def test_exit_opportunity_from_histogram_breakdown():
    df = pd.DataFrame(
        [
            {"hist": 0.5, "Close": 12, "TS": 10, "KS": 10, "SSA": 14, "SSB": 13, "Evolution_rate": 1},
            {"hist": 0.2, "Close": 11, "TS": 10, "KS": 10, "SSA": 14, "SSB": 13, "Evolution_rate": -1},
            {"hist": -0.1, "Close": 9, "TS": 10, "KS": 10, "SSA": 14, "SSB": 13, "Evolution_rate": -2},
        ]
    )
    signal = determine_comment_and_opportunity(df)
    assert "Exit" in signal.comment
    assert signal.opportunity == "VAD Opp"
    assert signal.cloud < 0
