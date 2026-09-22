#!/usr/bin/env python3
"""
Synchrony 40-day synthetic transaction dataset generator.

Produces ONE Excel workbook with 40 daily sheets (2026-09-22 → 2026-10-31),
the SAME 1,000 persistent customers across all sheets, exactly the 24 required
columns, and NO fraud-label column. Fraud is embedded as multi-day / multi-txn
behavioral sequences that follow the Synchrony Fraud Taxonomy.

Also emits (outside the workbook, for the pipeline — not part of the deliverable schema):
  - synchrony_40day_events.jsonl   chronological event log for Kafka replay
  - synchrony_40day_ground_truth.csv   (transaction_id, fraud_vector, actor) for scoring
  - dataset_summary.json

Fraud is discoverable ONLY from behavior in the workbook; the ground-truth file is
separate and optional (delete it if you want a blind test).
"""

import csv
import json
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import xlsxwriter

random.seed(2026)

OUT = Path(__file__).resolve().parent
N_ACCOUNTS = 1000
DAYS = 40
# Last 40 days ending TODAY (2026-09-22): 2026-08-14 → 2026-09-22 inclusive
END = date(2026, 9, 22)
START = END - timedelta(days=DAYS - 1)
DATES = [START + timedelta(days=i) for i in range(DAYS)]

COLUMNS = [
    "transaction_id", "account_id", "masked_pan", "bin", "amount", "event_time",
    "merchant_id", "merchant_name", "mcc", "terminal_id", "acquirer_country",
    "entry_method", "card_present", "channel", "cvv_result", "avs_result", "status",
    "auth_id", "promo_financing", "promo_type", "gift_card_amount", "three_ds",
    "device_fingerprint", "ip_address",
]

# ─────────────────────────────────────────────────────────────
# Merchants (US). (name, mcc, industry, tag)
# ─────────────────────────────────────────────────────────────
MERCHANT_DEFS = [
    ("Lowe's Home Center", "5211", "home_improvement", "retail"),
    ("Ashley HomeStore", "5712", "home_furnishings", "resale"),
    ("Mattress Firm", "5712", "home_furnishings", "retail"),
    ("TJX Rewards Store", "5651", "apparel", "retail"),
    ("American Eagle", "5651", "apparel", "retail"),
    ("Old Navy", "5311", "apparel", "retail"),
    ("Discount Tire", "5533", "automotive", "retail"),
    ("Shell Gas #4471", "5541", "automotive", "gas"),
    ("QuickFuel Pump 12", "5541", "automotive", "gas"),
    ("Best Buy", "5732", "electronics", "resale"),
    ("MicroCenter Tech", "5732", "electronics", "resale"),
    ("Verizon Store", "5732", "electronics", "resale"),
    ("Bright Smile Dental", "8021", "health", "carecredit"),
    ("Valley Vision Optometry", "8042", "health", "carecredit"),
    ("Paws & Claws Vet", "0742", "health", "carecredit"),
    ("Lakeside Dental Group", "8021", "health", "carecredit"),
    ("PayPal Digital Goods", "5815", "digital", "digital"),
    ("AppStore Media", "5816", "digital", "digital"),
    ("SkyHigh Airlines", "4511", "travel", "travel"),
    ("Comfort Inn Downtown", "7011", "travel", "travel"),
    ("Dick's Sporting Goods", "5941", "lifestyle", "retail"),
    ("Amazon Marketplace", "5942", "digital", "ecom"),
    ("DealBazaar Online", "5999", "retail", "ecom"),
    ("Walmart Supercenter", "5411", "grocery", "retail"),
    ("Target", "5310", "retail", "retail"),
    # fraud-relevant
    ("GiftCard Mall", "5947", "lifestyle", "giftcard"),
    ("QuickMart Convenience", "5411", "grocery", "weak"),
    ("MoneyGram Center", "4829", "financial", "cashlike"),
    ("CryptoATM Kiosk", "6051", "financial", "cashlike"),
    ("QuasiCash Services", "6540", "financial", "cashlike"),
    ("Wellness Clinic LLC", "8011", "health", "fake_provider"),
    ("BargainHub Store", "5999", "retail", "collusive"),
]


def build_merchants():
    ms = []
    for name, mcc, industry, tag in MERCHANT_DEFS:
        ms.append({
            "merchant_id": "MER-" + uuid.uuid4().hex[:8],
            "merchant_name": name, "mcc": mcc, "industry": industry, "tag": tag,
        })
    return ms


MERCHANTS = build_merchants()
BY_TAG = {}
for m in MERCHANTS:
    BY_TAG.setdefault(m["tag"], []).append(m)
RETAIL = BY_TAG["retail"]
RESALE = BY_TAG["resale"]
CARECREDIT = BY_TAG["carecredit"]
ECOM = BY_TAG["ecom"] + BY_TAG["digital"]

# ─────────────────────────────────────────────────────────────
# Accounts — persistent identity + behavioral profile
# ─────────────────────────────────────────────────────────────
BIN_BY_PRODUCT = {
    "private_label": ["603571", "521000"],
    "co_branded":    ["414720", "546616"],
    "carecredit":    ["601160"],
    "promotional":   ["603572"],
}
PROFILES = ["in_store_regular", "online_shopper", "wallet_user", "mixed"]


def rand_device():
    return "dev_" + uuid.uuid4().hex[:12]


def rand_ip():
    return f"{random.randint(11,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def build_accounts():
    accts = []
    for i in range(1, N_ACCOUNTS + 1):
        product = random.choices(
            ["private_label", "co_branded", "carecredit", "promotional"],
            weights=[40, 35, 10, 15])[0]
        bin_ = random.choice(BIN_BY_PRODUCT[product])
        profile = random.choices(PROFILES, weights=[45, 25, 15, 15])[0]
        freq_tier = random.choices(["low", "med", "high", "vhigh"], weights=[40, 40, 15, 5])[0]
        amt_mean = random.choice([45, 60, 80, 120, 180, 250])
        home = random.sample(RETAIL + RESALE, k=random.randint(2, 4))
        if product == "carecredit":
            home = random.sample(CARECREDIT, k=1) + random.sample(RETAIL, k=1)
        accts.append({
            "account_id": f"ACC-{i:06d}",
            "bin": bin_,
            "masked_pan": f"{bin_}xxxxxx{random.randint(1000,9999)}",
            "product": product,
            "profile": profile,
            "freq_tier": freq_tier,
            "amt_mean": amt_mean,
            "amt_std": amt_mean * 0.35,
            "home": home,
            "usual_device": rand_device(),
            "usual_ip": rand_ip(),
            "promo_user": product in ("promotional", "private_label") and random.random() < 0.5,
            "giftcard_occasional": random.random() < 0.12,
        })
    return accts


ACCOUNTS = build_accounts()
ACCT_BY_ID = {a["account_id"]: a for a in ACCOUNTS}

# ─────────────────────────────────────────────────────────────
# Transaction builder (enforces field consistency)
# ─────────────────────────────────────────────────────────────
DAY_HOURS = list(range(7, 23))
DAY_WEIGHTS = [2, 3, 4, 5, 6, 6, 5, 5, 6, 7, 8, 7, 6, 5, 4, 3]


def rand_time(d, at=None):
    if at is not None:
        h, m, s = at
    else:
        h = random.choices(DAY_HOURS, weights=DAY_WEIGHTS)[0]
        m, s = random.randint(0, 59), random.randint(0, 59)
    return f"{d.isoformat()}T{h:02d}:{m:02d}:{s:02d}"


def promo_type_code():
    return f"{random.randint(1, 12):04d}"


def make_txn(acct, d, *, channel=None, merchant=None, amount=None, event_time=None,
             device=None, ip=None, entry_method=None, cvv_result=None, avs_result=None,
             status=None, promo=None, gift_card_amount=None, three_ds=None):
    if channel is None:
        channel = {
            "in_store_regular": random.choices(["in_store", "e_commerce", "mobile"], weights=[8, 1, 1])[0],
            "online_shopper":   random.choices(["e_commerce", "in_store", "mobile"], weights=[7, 2, 1])[0],
            "wallet_user":      random.choices(["mobile", "in_store", "e_commerce"], weights=[6, 3, 1])[0],
            "mixed":            random.choices(["in_store", "e_commerce", "mobile"], weights=[5, 3, 2])[0],
        }[acct["profile"]]

    if merchant is None:
        if channel == "e_commerce":
            merchant = random.choice(acct["home"] + ECOM)
        else:
            merchant = random.choice(acct["home"])

    if amount is None:
        amount = max(1.0, random.gauss(acct["amt_mean"], acct["amt_std"]))
    amount = round(amount, 2)

    card_present = (channel == "in_store")
    if entry_method is None:
        entry_method = "chip" if channel == "in_store" else ("token" if channel == "mobile" else "cnp")

    if card_present:
        dev, ipa, tds = "", "", ""
        cvv = cvv_result or "not_provided"
        avs = avs_result or ""
        terminal = "TERM-" + uuid.uuid4().hex[:6]
    else:
        dev = device if device is not None else acct["usual_device"]
        ipa = ip if ip is not None else acct["usual_ip"]
        tds = three_ds if three_ds is not None else (
            random.choice(["authenticated", "attempted", "not_enrolled"]) if channel == "e_commerce" else "")
        cvv = cvv_result or "match"
        avs = avs_result or "Y"
        terminal = ""

    st = status or "approved"
    auth = f"{random.randint(100000, 999999)}" if st == "approved" else ""

    if promo is None:
        promo = acct["promo_user"] and channel == "in_store" and amount > 150 and random.random() < 0.4
    ptype = promo_type_code() if promo else ""

    gca = round(gift_card_amount, 2) if gift_card_amount else 0.0

    return {
        "transaction_id": str(uuid.uuid4()),
        "account_id": acct["account_id"],
        "masked_pan": acct["masked_pan"],
        "bin": acct["bin"],
        "amount": amount,
        "event_time": event_time or rand_time(d),
        "merchant_id": merchant["merchant_id"],
        "merchant_name": merchant["merchant_name"],
        "mcc": merchant["mcc"],
        "terminal_id": terminal,
        "acquirer_country": "US",
        "entry_method": entry_method,
        "card_present": card_present,
        "channel": channel,
        "cvv_result": cvv,
        "avs_result": avs,
        "status": st,
        "auth_id": auth,
        "promo_financing": bool(promo),
        "promo_type": ptype,
        "gift_card_amount": gca,
        "three_ds": tds,
        "device_fingerprint": dev,
        "ip_address": ipa,
    }


# ─────────────────────────────────────────────────────────────
# Baseline legitimate history for all accounts
# ─────────────────────────────────────────────────────────────
FREQ_LAMBDA = {"low": 0.4, "med": 1.2, "high": 3.0, "vhigh": 5.0}


def daily_count(tier):
    lam = FREQ_LAMBDA[tier]
    # Poisson-ish via sum of randoms; keep small
    n = 0
    p = 2.718281828 ** (-lam)
    cum, k = p, 0
    r = random.random()
    while r > cum and k < 12:
        k += 1
        p *= lam / k
        cum += p
    n = k
    return n


def generate_baseline():
    txns = []
    for acct in ACCOUNTS:
        for d in DATES:
            for _ in range(daily_count(acct["freq_tier"])):
                t = make_txn(acct, d)
                # occasional legit gift card
                if acct["giftcard_occasional"] and random.random() < 0.05:
                    gc = random.choice(BY_TAG["giftcard"])
                    t = make_txn(acct, d, channel="in_store", merchant=gc,
                                 amount=random.choice([25, 50, 100]),
                                 gift_card_amount=random.choice([25, 50, 100]))
                txns.append(t)
    return txns


# ─────────────────────────────────────────────────────────────
# Fraud scenario injectors  (append txns + record ground truth)
# ─────────────────────────────────────────────────────────────
GT = []  # ground truth: (transaction_id, vector, actor)


def tag(t, vector, actor):
    GT.append((t["transaction_id"], vector, actor))
    return t


def pick_accounts(n, pred=None, exclude=None):
    exclude = exclude or set()
    pool = [a for a in ACCOUNTS if a["account_id"] not in exclude and (pred is None or pred(a))]
    return random.sample(pool, min(n, len(pool)))


def inj_card_testing(txns):
    weak = BY_TAG["weak"][0]
    for _ in range(4):
        victim = random.choice(ACCOUNTS)
        d = random.choice(DATES[3:])
        atk_dev, atk_ip = rand_device(), rand_ip()
        h = random.randint(0, 22)
        base_m, base_s = random.randint(0, 55), 0
        for i in range(random.randint(15, 24)):
            s = base_s + i * random.randint(2, 6)
            mm, ss = base_m + s // 60, s % 60
            declined = random.random() < 0.8
            t = make_txn(victim, d, channel="e_commerce", merchant=weak,
                         amount=random.choice([0.50, 0.75, 1.00, 1.25, 2.00]),
                         device=atk_dev, ip=atk_ip,
                         cvv_result="no_match" if declined else "match",
                         avs_result="N",
                         status="declined" if declined else "approved",
                         event_time=rand_time(d, (h, (mm) % 60, ss)))
            txns.append(tag(t, "CB-2", "3P"))


def inj_ato(txns):
    for acct in pick_accounts(12):
        d = random.choice(DATES[20:])
        t = make_txn(acct, d, channel="e_commerce",
                     merchant=random.choice(RESALE),
                     amount=random.uniform(900, 1900),
                     device=rand_device(), ip=rand_ip(),
                     avs_result="N", cvv_result="match",
                     three_ds="attempted")
        txns.append(tag(t, "X-1", "3P"))


def inj_bustout(txns):
    for acct in pick_accounts(8, pred=lambda a: a["product"] in ("promotional", "private_label")):
        # escalating trajectory across the 40 days
        schedule = [(2, 80), (6, 120), (11, 150), (16, 220), (22, 300),
                    (27, 900), (30, 1400), (33, 1800), (36, 2200), (38, 2400)]
        for day_idx, amt in schedule:
            d = DATES[day_idx]
            resale = random.choice(RESALE)
            promo = amt > 500
            t = make_txn(acct, d, channel="in_store", merchant=resale,
                         amount=amt * random.uniform(0.9, 1.1), promo=promo)
            txns.append(tag(t, "PF-1", "B") if amt > 500 else t)


def inj_ring(txns):
    ring = random.sample(ACCOUNTS, 5)
    dev, ipa = rand_device(), rand_ip()
    for acct in ring:
        acct["usual_device"], acct["usual_ip"] = dev, ipa  # shared PII
        for _ in range(random.randint(3, 6)):
            d = random.choice(DATES[15:])
            t = make_txn(acct, d, channel="e_commerce",
                         merchant=random.choice(RESALE),
                         amount=random.uniform(800, 2000),
                         device=dev, ip=ipa, avs_result="N")
            txns.append(tag(t, "APP-2", "S"))


def inj_carecredit(txns):
    provider = BY_TAG["fake_provider"][0]
    patients = random.sample(ACCOUNTS, 10)
    for acct in patients:
        for _ in range(random.randint(1, 3)):
            d = random.choice(DATES)
            t = make_txn(acct, d, channel="in_store", merchant=provider,
                         amount=random.uniform(2800, 6000), entry_method="chip")
            txns.append(tag(t, "CC-1", "M"))


def inj_wallet(txns):
    for acct in pick_accounts(6):
        d = random.choice(DATES[10:])
        t = make_txn(acct, d, channel="mobile", merchant=random.choice(RESALE),
                     amount=random.uniform(700, 1600),
                     device=rand_device(), ip=rand_ip())
        txns.append(tag(t, "DW-1", "3P"))


def inj_cnp(txns):
    stores = BY_TAG["ecom"]
    for acct in pick_accounts(10):
        d = random.choice(DATES[5:])
        t = make_txn(acct, d, channel="e_commerce", merchant=random.choice(stores),
                     amount=random.uniform(250, 950),
                     device=rand_device(), ip=rand_ip(),
                     cvv_result="no_match", avs_result="N", three_ds="failed")
        txns.append(tag(t, "EC-1", "3P"))


def inj_giftcard(txns):
    mall = BY_TAG["giftcard"][0]
    for acct in pick_accounts(5, pred=lambda a: a["product"] == "private_label"):
        d = random.choice(DATES)
        h = random.randint(9, 20)
        for i in range(random.randint(4, 8)):
            amt = random.choice([200, 300, 500])
            t = make_txn(acct, d, channel="in_store", merchant=mall,
                         amount=amt, gift_card_amount=amt,
                         event_time=rand_time(d, (h, (i * 3) % 60, 0)))
            txns.append(tag(t, "PL-2", "B"))


def inj_quasicash(txns):
    cashlike = BY_TAG["cashlike"]
    for acct in pick_accounts(4, pred=lambda a: a["product"] == "co_branded"):
        d = random.choice(DATES)
        t = make_txn(acct, d, channel="in_store", merchant=random.choice(cashlike),
                     amount=random.uniform(400, 900), entry_method="manual")
        txns.append(tag(t, "CB-3", "S"))


def inj_skimming(txns):
    gas = [m for m in MERCHANTS if m["tag"] == "gas"]
    for acct in pick_accounts(4, pred=lambda a: a["product"] == "co_branded"):
        d = random.choice(DATES)
        h = random.randint(8, 18)
        t1 = make_txn(acct, d, channel="in_store", merchant=random.choice(gas),
                      amount=random.uniform(35, 80), entry_method="chip",
                      event_time=rand_time(d, (h, 5, 0)))
        txns.append(t1)
        t2 = make_txn(acct, d, channel="in_store", merchant=random.choice(gas),
                      amount=random.uniform(200, 500), entry_method="swipe",
                      event_time=rand_time(d, (h, 25, 0)))
        txns.append(tag(t2, "CB-1", "3P"))


def inj_collusive(txns):
    merch = BY_TAG["collusive"][0]
    for acct in random.sample(ACCOUNTS, 20):
        for _ in range(random.randint(1, 2)):
            d = random.choice(DATES[10:25])
            t = make_txn(acct, d, channel="e_commerce", merchant=merch,
                         amount=random.uniform(150, 600),
                         device=rand_device(), ip=rand_ip())
            txns.append(tag(t, "CB-4", "M"))


# ─────────────────────────────────────────────────────────────
# Assemble, partition by day, write outputs
# ─────────────────────────────────────────────────────────────
def main():
    txns = generate_baseline()
    for inj in (inj_card_testing, inj_ato, inj_bustout, inj_ring, inj_carecredit,
                inj_wallet, inj_cnp, inj_giftcard, inj_quasicash, inj_skimming, inj_collusive):
        inj(txns)

    # sort chronologically
    txns.sort(key=lambda t: t["event_time"])

    # partition by day
    by_day = {d.isoformat(): [] for d in DATES}
    for t in txns:
        by_day[t["event_time"][:10]].append(t)

    # ── Excel workbook: 40 sheets ──
    xlsx_path = OUT / "Synchrony_40_Day_Fraud_Dataset.xlsx"
    wb = xlsxwriter.Workbook(str(xlsx_path), {"constant_memory": True})
    hdr = wb.add_format({"bold": True, "bg_color": "#1E2A45", "font_color": "white"})
    for idx, d in enumerate(DATES, 1):
        ws = wb.add_worksheet(f"Day_{idx:02d}_{d.isoformat()}")
        for c, col in enumerate(COLUMNS):
            ws.write(0, c, col, hdr)
        for r, t in enumerate(by_day[d.isoformat()], 1):
            for c, col in enumerate(COLUMNS):
                ws.write(r, c, t[col])
    wb.close()

    # ── JSONL event log (for Kafka replay) ──
    with (OUT / "synchrony_40day_events.jsonl").open("w") as f:
        for t in txns:
            f.write(json.dumps(t) + "\n")

    # ── CSV: combined + one file per day (CSV has no sheets → one file = one day) ──
    import zipfile
    csv_dir = OUT / "csv_by_day"
    csv_dir.mkdir(exist_ok=True)
    with (OUT / "synchrony_40day_all.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for t in txns:
            w.writerow(t)
    for idx, d in enumerate(DATES, 1):
        with (csv_dir / f"Day_{idx:02d}_{d.isoformat()}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            for t in by_day[d.isoformat()]:
                w.writerow(t)
    with zipfile.ZipFile(OUT / "synchrony_40day_csv_by_day.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for idx, d in enumerate(DATES, 1):
            fn = csv_dir / f"Day_{idx:02d}_{d.isoformat()}.csv"
            z.write(fn, fn.name)

    # ── ground truth (separate, NOT in workbook) ──
    with (OUT / "synchrony_40day_ground_truth.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id", "fraud_vector", "actor"])
        w.writerows(GT)

    # ── summary ──
    by_vector, by_actor = {}, {}
    for _, v, a in GT:
        by_vector[v] = by_vector.get(v, 0) + 1
        by_actor[a] = by_actor.get(a, 0) + 1
    summary = {
        "accounts": N_ACCOUNTS,
        "days": DAYS,
        "date_range": [DATES[0].isoformat(), DATES[-1].isoformat()],
        "total_transactions": len(txns),
        "fraud_transactions": len(GT),
        "fraud_rate_pct": round(100 * len(GT) / len(txns), 2),
        "fraud_by_vector": dict(sorted(by_vector.items())),
        "fraud_by_actor": dict(sorted(by_actor.items())),
        "txns_per_day_min": min(len(v) for v in by_day.values()),
        "txns_per_day_max": max(len(v) for v in by_day.values()),
    }
    (OUT / "dataset_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
