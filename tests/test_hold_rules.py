from prorealtime_v2.strategies.hold_rules import should_buy, should_sell, should_vad_buy, should_vad_sell


def base_signal():
    return {
        "MARKET": "US",
        "Day": "Entry >>",
        "Week": "Entry >",
        "Month": "Entry",
        "Quarter": "Entry",
        "D OPP": "Opp",
        "W OPP": "Opp",
        "M OPP": "Opp",
        "dTS": 1,
        "dKS": 1,
        "dCloud": 2,
        "wTS": 1,
        "wKS": 1,
        "wCloud": 2,
        "mTS": 1,
        "mKS": 1,
        "mCloud": 2,
        "SENS": 20,
    }


def test_buy_requires_no_position():
    assert should_buy(0, base_signal()) is True
    assert should_buy(10, base_signal()) is False


def test_buy_rejected_when_sens_too_high():
    signal = base_signal()
    signal["SENS"] = 80
    assert should_buy(0, signal) is False


def test_sell_for_long_position_requires_daily_ts_and_ks_negative():
    signal = base_signal()
    signal["Day"] = "Exit >>"
    signal["dTS"] = -1
    signal["dKS"] = -1
    assert should_sell(5, signal) is True
    assert should_sell(0, signal) is False


def test_vad_sell_rejected_for_european_markets():
    signal = base_signal()
    signal.update({"MARKET": "EUROPE", "Day": "Exit", "Week": "Exit", "Month": "Exit", "W OPP": "VAD Opp", "dTS": -1, "dKS": -1, "wTS": -1, "wKS": -1, "dCloud": -2, "wCloud": -2, "SENS": 10})
    assert should_vad_sell(0, signal) is False


def test_vad_buy_requires_short_position():
    signal = base_signal()
    signal["dTS"] = 1
    assert should_vad_buy(-3, signal) is True
    assert should_vad_buy(0, signal) is False
