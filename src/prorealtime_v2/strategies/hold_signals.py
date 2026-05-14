from __future__ import annotations

import pandas as pd

from prorealtime_v2.domain.models import TimeframeSignal
from prorealtime_v2.utils.parsing import to_float


def _row(df: pd.DataFrame, index: int) -> pd.Series:
    fallback = {"hist": 0, "Close": 0, "TS": 0, "KS": 0, "SSA": 0, "SSB": 0, "Evolution_rate": 0}
    if df.empty:
        return pd.Series(fallback)
    try:
        return df.iloc[index]
    except IndexError:
        return pd.Series(fallback)


def determine_comment_and_opportunity(df: pd.DataFrame) -> TimeframeSignal:
    """Version structurée du moteur historique de commentaire/opportunité.

    Elle conserve les familles de signaux du fichier d'origine :
    Entry, Exit, Opp, VAD Opp, TS, KS et Cloud.
    """
    seuil = 0.0
    w1 = _row(df, -1)
    w2 = _row(df, -2) if len(df) >= 2 else _row(pd.DataFrame(), 0)
    w3 = _row(df, -3) if len(df) >= 3 else _row(pd.DataFrame(), 0)

    h1 = to_float(w1.get("hist"))
    h2 = to_float(w2.get("hist"))
    h3 = to_float(w3.get("hist"))
    c1 = to_float(w1.get("Close"))
    c2 = to_float(w2.get("Close"))
    ts1 = to_float(w1.get("TS"))
    ts2 = to_float(w2.get("TS"))
    ks1 = to_float(w1.get("KS"))
    ks2 = to_float(w2.get("KS"))
    evo1 = to_float(w1.get("Evolution_rate"))

    comment = "Wait"
    opportunity = ""

    if c1 > ts1 and h2 < h1 < seuil and evo1 > 0:
        comment, opportunity = "Entry >>> TS", "Opp"
    elif h3 < seuil < h2 < h1 or seuil < h3 < h2 < h1:
        comment = "Entry >>>"
    elif h2 < h1 and h2 < seuil < h1:
        comment, opportunity = "Entry >>", "Opp"
    elif h3 > h2 and h2 < h1 and h2 < seuil < h1:
        comment, opportunity = "Entry >>", "Opp"
    elif h3 < h2 < h1 < seuil:
        comment, opportunity = "Entry >", "Opp"
    elif h3 > h2 and h2 < h1 < seuil:
        comment, opportunity = "Entry", "Opp"
    elif c1 < ts1 and h2 > h1 > seuil and evo1 < 0:
        comment, opportunity = "Exit >>> TS", "VAD Opp"
    elif seuil > h2 > h1:
        comment = "Exit >>>"
    elif h2 > seuil > h1 or h2 > 0 > h1:
        comment, opportunity = "Exit >>", "VAD Opp"
    elif h3 < h2 and h2 > h1 > seuil:
        comment, opportunity = "Exit", "VAD Opp"
    elif h3 > h2 > h1 > seuil or h2 > h1 > seuil:
        comment, opportunity = "Exit >", "VAD Opp"

    if h3 > h2 and seuil < h2 < h1:
        comment, opportunity = "Entry >>>!", "Opp"
    elif h3 < h2 and seuil > h2 > h1:
        comment, opportunity = "Exit >>>!", "VAD Opp"

    ts = 1 if c1 > ts1 and c2 < ts2 and h2 < h1 and evo1 > 0 else 2 if c1 > ts1 else -1 if c2 > ts2 and h2 > h1 and evo1 < 0 else -2
    ks = 1 if c1 > ks1 and c2 < ks2 and h2 < h1 and evo1 > 0 else 2 if c1 > ks1 else -1 if c2 > ks2 and h2 > h1 and evo1 < 0 else -2

    cloud = 0
    ssa = to_float(w1.get("SSA"))
    ssb = to_float(w1.get("SSB"))
    if "Entry" in comment:
        cloud = int(c1 > ssa) + int(c1 > ssb)
    elif "Exit" in comment:
        cloud = -(int(c1 < ssa) + int(c1 < ssb))

    return TimeframeSignal(comment=comment, opportunity=opportunity, ts=ts, ks=ks, cloud=cloud)
