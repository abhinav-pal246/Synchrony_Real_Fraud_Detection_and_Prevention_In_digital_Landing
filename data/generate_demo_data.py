#!/usr/bin/env python3
"""
Synthetic demo-data generator for the Synchrony Real-Time Fraud Detection system.

Produces three JSON files:
  - merchants.json      reference data (MCC, industry, partner)
  - accounts.json       customer accounts (with PII used for graph linking)
  - transactions.json   >1000 transaction events matching the Kafka payload (§7b),
                        each with a ground-truth _label {is_fraud, fraud_vector, actor}

Design notes
------------
* Mostly-legitimate baseline with embedded fraud scenarios covering the 8 product
  lines, 4 actor types (B / 3P / S / M), and a representative slice of the 45 vectors.
* Fraud rate is intentionally inflated (~20%) so the demo has plenty to show;
  real-world fraud is <1% (documented in data/README.md).
* Every record is tagged phase = "history" (seed → Postgres) or "live" (replay → Kafka),
  so the same file drives both the batch seed and the real-time stream.
* Ring / synthetic-identity accounts deliberately SHARE device/phone/address so the
  graph lane (Lane B) has real clusters to find.

Stdlib only — runs on the project's Python without extra dependencies.
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)  # reproducible

OUT_DIR = Path(__file__).resolve().parent
NOW = datetime(2026, 9, 21, 18, 0, 0, tzinfo=timezone.utc)
HISTORY_START = NOW - timedelta(days=90)
LIVE_START = NOW - timedelta(hours=2)  # the "demo window" that gets replayed live

# ─────────────────────────────────────────────────────────────
# Reference pools
# ─────────────────────────────────────────────────────────────
FIRST_NAMES = ["James", "Maria", "David", "Linda", "Robert", "Patricia", "John", "Jennifer",
               "Michael", "Elizabeth", "William", "Sarah", "Carlos", "Aisha", "Wei", "Priya",
               "Diego", "Fatima", "Kenji", "Olga", "Ahmed", "Grace", "Tyler", "Nina"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Patel", "Nguyen", "Kim", "Chen", "Ali", "Okafor", "Rossi", "Novak"]
CITIES = [("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Chicago", "IL", "60601"),
          ("Houston", "TX", "77001"), ("Phoenix", "AZ", "85001"), ("Philadelphia", "PA", "19101"),
          ("Dallas", "TX", "75201"), ("Miami", "FL", "33101"), ("Seattle", "WA", "98101"),
          ("Atlanta", "GA", "30301"), ("Denver", "CO", "80201"), ("Boston", "MA", "02101")]
STREETS = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Elm St", "Pine Rd", "Washington Blvd",
           "Lake View Dr", "Sunset Ave", "Highland Rd"]

# Merchants by industry: (name, mcc, industry, partner)
MERCHANT_DEFS = [
    # Retail & Apparel
    ("TJX Rewards Store", "5651", "Retail & Apparel", "TJX"),
    ("American Eagle", "5651", "Retail & Apparel", "AEO"),
    ("Old Navy Outlet", "5311", "Retail & Apparel", "Gap"),
    # Home Improvement
    ("Lowe's Home Center", "5211", "Home Improvement", "Lowe's"),
    ("Ashley HomeStore", "5712", "Home Furnishings", "Ashley"),
    ("Mattress Firm", "5712", "Home Furnishings", "MattressFirm"),
    # Automotive
    ("Discount Tire", "5533", "Automotive", "DiscountTire"),
    ("Shell Gas #4471", "5541", "Automotive", "Shell"),
    ("QuickFuel Pump 12", "5541", "Automotive", "QuickFuel"),
    # Health & Wellness (CareCredit providers)
    ("Bright Smile Dental", "8021", "Health & Wellness", "CareCredit"),
    ("Valley Vision Optometry", "8042", "Health & Wellness", "CareCredit"),
    ("Paws & Claws Vet", "0742", "Health & Wellness", "CareCredit"),
    ("Lakeside Dental Group", "8021", "Health & Wellness", "CareCredit"),
    # Electronics
    ("Best Buy Electronics", "5732", "Electronics", "BestBuy"),
    ("MicroCenter Tech", "5732", "Electronics", "MicroCenter"),
    ("Verizon Store", "5732", "Electronics", "Verizon"),
    # Digital
    ("PayPal Digital Goods", "5815", "Digital", "PayPal"),
    ("AppStore Media", "5816", "Digital", "Digital"),
    # Travel
    ("SkyHigh Airlines", "4511", "Travel", "SkyHigh"),
    ("Comfort Inn Downtown", "7011", "Travel", "ComfortInn"),
    # Lifestyle
    ("Dick's Sporting Goods", "5941", "Lifestyle", "Dicks"),
    ("GiftCard Mall", "5947", "Lifestyle", "GiftMall"),          # gift-card heavy (PL-2)
    ("QuickMart Convenience", "5411", "Retail & Apparel", "QuickMart"),  # weak merchant (card testing)
    # Cash-like / quasi-cash (CB-3)
    ("MoneyGram Center", "4829", "Financial", "MoneyGram"),
    ("CryptoATM Kiosk", "6051", "Financial", "CryptoATM"),
    # Marketplace / e-commerce
    ("Amazon Marketplace", "5942", "Digital", "Amazon"),
    ("DealBazaar Online", "5999", "Retail & Apparel", "DealBazaar"),   # triangulation storefront
    # Fraud-specific
    ("Wellness Clinic LLC", "8011", "Health & Wellness", "CareCredit"),  # fake provider (CC-5)
]

PRODUCT_LINES = [
    "real_time_credit_application", "private_label", "co_branded", "promotional_financing",
    "pos_installment", "carecredit", "digital_wallet", "ecommerce",
]
# Card product an account holds (channels like wallet/ecommerce are derived per-txn)
ACCOUNT_PRODUCTS = ["private_label", "co_branded", "promotional_financing", "pos_installment", "carecredit"]

CHANNELS = ["in_store", "online", "mobile_app", "phone", "digital_wallet"]
ENTRY_METHODS = ["chip", "contactless", "swipe", "manual", "cnp", "token"]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def rid(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def rand_email(name):
    base = name.lower().replace(" ", ".")
    return f"{base}{random.randint(1, 999)}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'proton.me'])}"


def rand_phone():
    return f"+1{random.randint(200, 989)}{random.randint(200, 989)}{random.randint(1000, 9999)}"


def rand_device():
    return "dev_" + uuid.uuid4().hex[:12]


def rand_ip():
    return f"{random.randint(11, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def rand_address():
    city, state, zip_ = random.choice(CITIES)
    return {
        "street": f"{random.randint(10, 9999)} {random.choice(STREETS)}",
        "city": city, "state": state, "zip": zip_, "country": "US",
    }


def masked_pan(bin6):
    return f"{bin6}xxxxxx{random.randint(1000, 9999)}"


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def phase_for(dt):
    return "live" if dt >= LIVE_START else "history"


# ─────────────────────────────────────────────────────────────
# Build merchants
# ─────────────────────────────────────────────────────────────
def build_merchants():
    merchants = []
    for name, mcc, industry, partner in MERCHANT_DEFS:
        merchants.append({
            "merchant_id": rid("MER"),
            "merchant_name": name,
            "merchant_category_code": mcc,
            "industry": industry,
            "partner": partner,
            "onboarding_date": iso(HISTORY_START - timedelta(days=random.randint(30, 900))),
        })
    return merchants


def m_by_industry(merchants, industry):
    return [m for m in merchants if m["industry"] == industry]


def m_by_name(merchants, name_substr):
    return next(m for m in merchants if name_substr in m["merchant_name"])


# ─────────────────────────────────────────────────────────────
# Build accounts (incl. ring / synthetic / mule flags)
# ─────────────────────────────────────────────────────────────
def build_accounts():
    accounts = []

    def make_account(product=None, **overrides):
        name = overrides.get("holder_name", rand_name())
        addr = overrides.get("_addr", rand_address())
        bin6 = random.choice(["411111", "531000", "601100", "379100"])
        acct = {
            "account_id": rid("ACC"),
            "masked_pan": masked_pan(bin6),
            "product_type": product or random.choice(ACCOUNT_PRODUCTS),
            "holder_name": name,
            "email": overrides.get("email", rand_email(name)),
            "phone": overrides.get("phone", rand_phone()),
            "device_fingerprint": overrides.get("device_fingerprint", rand_device()),
            "home_street": addr["street"], "home_city": addr["city"],
            "home_state": addr["state"], "home_zip": addr["zip"],
            "balance": 0.0,
            "credit_limit": random.choice([1000, 2500, 5000, 7500, 10000]),
            "account_age_days": overrides.get("account_age_days", random.randint(30, 2000)),
            "promo_plan_id": None, "promo_plan_type": None,
            "days_past_due": 0, "status": "active",
            "opened_at": iso(NOW - timedelta(days=overrides.get("account_age_days", random.randint(30, 2000)))),
            "_risk_profile": overrides.get("_risk_profile", "legit"),  # generator hint, not shipped to model
        }
        accounts.append(acct)
        return acct

    # ~150 ordinary legit accounts
    for _ in range(150):
        make_account()

    # 1 synthetic-identity RING of 5 accounts sharing device + phone + address (APP-2 / X-2 / graph)
    ring_device = rand_device()
    ring_phone = rand_phone()
    ring_addr = rand_address()
    ring = []
    for _ in range(5):
        a = make_account(
            product="co_branded",
            device_fingerprint=ring_device, phone=ring_phone, _addr=ring_addr,
            account_age_days=random.randint(120, 210),  # "nurtured" months
            _risk_profile="synthetic_ring",
        )
        ring.append(a)

    # 4 bust-out accounts (long clean history then max-out)
    for _ in range(4):
        make_account(product=random.choice(["private_label", "promotional_financing"]),
                     account_age_days=random.randint(150, 400), _risk_profile="bustout")

    # 6 accounts that will be ATO victims
    for _ in range(6):
        make_account(account_age_days=random.randint(400, 1800), _risk_profile="ato_victim")

    return accounts, ring


def accts_by_profile(accounts, profile):
    return [a for a in accounts if a["_risk_profile"] == profile]


def legit_accounts(accounts):
    return [a for a in accounts if a["_risk_profile"] == "legit"]


# ─────────────────────────────────────────────────────────────
# Transaction builder
# ─────────────────────────────────────────────────────────────
def base_txn(account, merchant, when, amount, *, channel="in_store", entry="chip",
             txn_type="purchase", status="approved", label=None, **extra):
    """Assemble a Kafka-shaped transaction event (§7b) + ground-truth label + product_line."""
    home_addr = {"street": account["home_street"], "city": account["home_city"],
                 "state": account["home_state"], "zip": account["home_zip"], "country": "US"}
    wallet = extra.get("wallet_provider")
    txn = {
        "transaction_id": str(uuid.uuid4()),
        "account_id": account["account_id"],
        "masked_pan": account["masked_pan"],
        "event_time": iso(when),
        "amount": round(amount, 2),
        "currency": "USD",
        "merchant_id": merchant["merchant_id"],
        "merchant_name": merchant["merchant_name"],
        "merchant_category_code": merchant["merchant_category_code"],
        "terminal_id": extra.get("terminal_id", rid("TERM")),
        "transaction_type": txn_type,
        "channel": channel,
        "entry_method": entry,
        "card_present": channel in ("in_store",),
        "cvv_result": extra.get("cvv_result", "match" if entry != "cnp" else random.choice(["match", "match", "no_match"])),
        "avs_result": extra.get("avs_result", "full"),
        "three_ds_result": extra.get("three_ds_result", "authenticated" if channel == "online" else "not_enrolled"),
        "status": status,
        "decline_reason_code": extra.get("decline_reason_code"),
        "ip_address": extra.get("ip_address", rand_ip() if channel != "in_store" else None),
        "device_fingerprint": extra.get("device_fingerprint", account["device_fingerprint"] if channel != "in_store" else None),
        "user_agent": extra.get("user_agent"),
        "session_id": extra.get("session_id", rid("SES")),
        "shipping_address": extra.get("shipping_address", home_addr if channel == "online" else None),
        "shipping_name": extra.get("shipping_name", account["holder_name"] if channel == "online" else None),
        "billing_address": home_addr if channel in ("online", "digital_wallet") else None,
        "expedited_shipping": extra.get("expedited_shipping", False),
        "token_id": extra.get("token_id", rid("TOK") if wallet else None),
        "wallet_provider": wallet,
        "token_provisioning_date": extra.get("token_provisioning_date"),
        "promo_plan_id": extra.get("promo_plan_id"),
        "installment_loan_id": extra.get("installment_loan_id"),
        "associate_id": extra.get("associate_id"),
        "store_id": extra.get("store_id"),
        "refund_original_txn_id": extra.get("refund_original_txn_id"),
        # ── demo metadata (NOT part of the real Kafka payload / not fed to the model) ──
        "product_line": derive_product_line(account, merchant, channel, extra),
        "phase": phase_for(when),
        "_label": label or {"is_fraud": False, "fraud_vector": None, "actor_code": None, "note": "legitimate"},
    }
    return txn


def derive_product_line(account, merchant, channel, extra):
    # Precedence: product-defining attributes first, then channel, then card type.
    if extra.get("is_application"):
        return "real_time_credit_application"
    if extra.get("installment_loan_id"):
        return "pos_installment"
    if extra.get("promo_plan_id"):
        return "promotional_financing"
    if merchant["partner"] == "CareCredit":
        return "carecredit"
    if channel == "digital_wallet" or extra.get("wallet_provider"):
        return "digital_wallet"
    if channel == "online":
        return "ecommerce"
    return account["product_type"] if account["product_type"] in ("private_label", "co_branded") else "private_label"


def amount_for(industry):
    ranges = {
        "Retail & Apparel": (15, 250), "Home Improvement": (40, 1200), "Home Furnishings": (200, 3000),
        "Automotive": (25, 400), "Health & Wellness": (150, 2500), "Electronics": (80, 2000),
        "Digital": (5, 120), "Travel": (120, 1500), "Lifestyle": (20, 400), "Financial": (100, 1000),
    }
    lo, hi = ranges.get(industry, (10, 300))
    return random.uniform(lo, hi)


# ─────────────────────────────────────────────────────────────
# Scenario generators (return list of txns)
# ─────────────────────────────────────────────────────────────
def gen_legit(accounts, merchants, n):
    txns = []
    pool = legit_accounts(accounts) + accts_by_profile(accounts, "ato_victim")
    for _ in range(n):
        acct = random.choice(pool)
        # choose a plausible merchant/channel for this card product
        merchant = random.choice(merchants)
        when = HISTORY_START + timedelta(seconds=random.randint(0, int((NOW - HISTORY_START).total_seconds())))
        channel = random.choices(["in_store", "online", "mobile_app", "digital_wallet"], weights=[5, 3, 1, 1])[0]
        entry = {"in_store": random.choice(["chip", "contactless"]), "online": "cnp",
                 "mobile_app": "token", "digital_wallet": "token"}[channel]
        extra = {}
        if channel == "digital_wallet":
            extra["wallet_provider"] = random.choice(["apple", "google", "samsung"])
        if merchant["partner"] == "CareCredit":
            channel, entry = "in_store", "chip"
        amt = amount_for(merchant["industry"])
        txns.append(base_txn(acct, merchant, when, amt, channel=channel, entry=entry, **extra))
    return txns


def gen_card_testing(accounts, merchants):
    """CB-2 / EC-2: bursts of tiny auths across many PANs from one attacker device."""
    txns = []
    weak = m_by_name(merchants, "QuickMart")
    for burst in range(3):
        atk_device = rand_device()
        atk_ip = rand_ip()
        start = LIVE_START + timedelta(minutes=random.randint(0, 90))
        victim = random.choice(legit_accounts(accounts))
        for i in range(random.randint(15, 25)):
            when = start + timedelta(seconds=i * random.randint(2, 6))
            declined = random.random() < 0.8
            txns.append(base_txn(
                victim, weak, when, round(random.uniform(0.2, 2.5), 2),
                channel="online", entry="cnp",
                status="declined" if declined else "approved",
                decline_reason_code="cvv_mismatch" if declined else None,
                cvv_result="no_match" if declined else "match",
                device_fingerprint=atk_device, ip_address=atk_ip,
                label={"is_fraud": True, "fraud_vector": "CB-2", "actor_code": "3P",
                       "note": "card-testing burst: tiny auths, high decline rate, single device/BIN"},
            ))
    return txns


def gen_ato(accounts, merchants):
    """X-1: post-account-takeover high-value purchase from a NEW device/geo."""
    txns = []
    elec = m_by_industry(merchants, "Electronics")
    for acct in accts_by_profile(accounts, "ato_victim"):
        when = LIVE_START + timedelta(minutes=random.randint(0, 110))
        txns.append(base_txn(
            acct, random.choice(elec), when, round(random.uniform(900, 1800), 2),
            channel="online", entry="cnp",
            device_fingerprint=rand_device(),  # NEW device (not the account's)
            ip_address=rand_ip(),
            shipping_address=rand_address(),   # shipped elsewhere
            expedited_shipping=True,
            label={"is_fraud": True, "fraud_vector": "X-1", "actor_code": "3P",
                   "note": "account takeover: new device + new geo + contact change 2d prior + expedited ship"},
        ))
    return txns


def gen_bustout(accounts, merchants):
    """X-2 / PF-1: long clean history (phase=history) then max-out cluster (phase=live)."""
    txns = []
    resale = m_by_industry(merchants, "Electronics") + m_by_industry(merchants, "Home Furnishings")
    everyday = m_by_industry(merchants, "Retail & Apparel") + m_by_industry(merchants, "Automotive")
    for acct in accts_by_profile(accounts, "bustout"):
        # build ~60 days of small legit-looking history
        for d in range(60, 5, -random.randint(2, 5)):
            when = NOW - timedelta(days=d, minutes=random.randint(0, 1000))
            txns.append(base_txn(acct, random.choice(everyday), when, round(random.uniform(20, 120), 2),
                                  channel="in_store", entry="chip"))
        # the bust-out: cluster of high-value resale purchases in the live window
        for _ in range(random.randint(4, 7)):
            when = LIVE_START + timedelta(minutes=random.randint(0, 110))
            txns.append(base_txn(
                acct, random.choice(resale), when, round(random.uniform(1200, 2500), 2),
                channel="in_store", entry="chip",
                promo_plan_id=rid("PROMO"),
                label={"is_fraud": True, "fraud_vector": "PF-1", "actor_code": "B",
                       "note": "promo bust-out: max-out on resale goods after clean history, promo defers first payment"},
            ))
    return txns


def gen_ring_activity(accounts, ring, merchants):
    """APP-2 / X-2: synthetic-identity ring — applications + coordinated spend (shared PII → graph)."""
    txns = []
    elec = m_by_industry(merchants, "Electronics")
    for acct in ring:
        # application event (front door)
        when_app = NOW - timedelta(days=random.randint(150, 200))
        txns.append(base_txn(
            acct, elec[0], when_app, float(acct["credit_limit"]),
            channel="online", entry="cnp", txn_type="auth_only", is_application=True,
            device_fingerprint=acct["device_fingerprint"], ip_address=rand_ip(),
            label={"is_fraud": True, "fraud_vector": "APP-2", "actor_code": "S",
                   "note": "synthetic identity application: shared device/phone/address across ring"},
        ))
        # coordinated bust-out spend in the live window
        for _ in range(random.randint(2, 4)):
            when = LIVE_START + timedelta(minutes=random.randint(0, 110))
            txns.append(base_txn(
                acct, random.choice(elec), when, round(random.uniform(1500, 2400), 2),
                channel="in_store", entry="chip",
                label={"is_fraud": True, "fraud_vector": "X-2", "actor_code": "S",
                       "note": "ring bust-out: coordinated max-out across shared-PII accounts"},
            ))
    return txns


def gen_carecredit_fraud(accounts, merchants):
    """CC-1 / CC-3: provider bills far above peers, repeat patients, first-visit full charge."""
    txns = []
    bad_provider = m_by_name(merchants, "Wellness Clinic")
    patients = random.sample(legit_accounts(accounts), 8)
    for acct in patients:
        for visit in range(random.randint(1, 3)):
            when = HISTORY_START + timedelta(days=random.randint(0, 88), minutes=random.randint(0, 900))
            txns.append(base_txn(
                acct, bad_provider, when, round(random.uniform(2800, 6000), 2),  # >> peer avg
                channel="in_store", entry="chip", associate_id=rid("STAFF"),
                label={"is_fraud": True, "fraud_vector": "CC-1", "actor_code": "M",
                       "note": "provider billing anomaly: ticket >> specialty peers, repeat patients, day-1 full charge"},
            ))
    return txns


def gen_wallet_provisioning(accounts, merchants):
    """DW-1: stolen card provisioned to a new device, immediate high-value spend, geo mismatch."""
    txns = []
    elec = m_by_industry(merchants, "Electronics")
    for acct in random.sample(legit_accounts(accounts), 5):
        prov_time = LIVE_START + timedelta(minutes=random.randint(0, 60))
        when = prov_time + timedelta(minutes=random.randint(1, 20))
        txns.append(base_txn(
            acct, random.choice(elec), when, round(random.uniform(700, 1600), 2),
            channel="digital_wallet", entry="token",
            wallet_provider=random.choice(["apple", "google"]),
            token_provisioning_date=iso(prov_time),
            device_fingerprint=rand_device(), ip_address=rand_ip(),
            label={"is_fraud": True, "fraud_vector": "DW-1", "actor_code": "3P",
                   "note": "stolen-card wallet provisioning: new device, provision→spend minutes apart, geo mismatch"},
        ))
    return txns


def gen_ecommerce_cnp(accounts, merchants):
    """EC-1: card-not-present with stolen data, billing/shipping mismatch, proxy IP."""
    txns = []
    stores = [m_by_name(merchants, "DealBazaar"), m_by_name(merchants, "Amazon Marketplace")]
    for acct in random.sample(legit_accounts(accounts), 8):
        when = LIVE_START + timedelta(minutes=random.randint(0, 115))
        txns.append(base_txn(
            acct, random.choice(stores), when, round(random.uniform(200, 900), 2),
            channel="online", entry="cnp",
            cvv_result=random.choice(["match", "no_match"]), avs_result="no_match",
            device_fingerprint=rand_device(), ip_address=rand_ip(),
            shipping_address=rand_address(), shipping_name=rand_name(),  # differs from cardholder
            expedited_shipping=True,
            label={"is_fraud": True, "fraud_vector": "EC-1", "actor_code": "3P",
                   "note": "CNP stolen card: AVS mismatch, new device, shipping name/address differ from cardholder"},
        ))
    return txns


def gen_triangulation(accounts, merchants):
    """EC-5: one device ships to many unrelated addresses (feeds graph)."""
    txns = []
    store = m_by_name(merchants, "DealBazaar")
    fraud_device = rand_device()
    for acct in random.sample(legit_accounts(accounts), 6):
        when = LIVE_START + timedelta(minutes=random.randint(0, 115))
        txns.append(base_txn(
            acct, store, when, round(random.uniform(120, 500), 2),
            channel="online", entry="cnp",
            device_fingerprint=fraud_device,  # SAME device, many cards/addresses
            ip_address=rand_ip(), shipping_address=rand_address(), shipping_name=rand_name(),
            label={"is_fraud": True, "fraud_vector": "EC-5", "actor_code": "3P",
                   "note": "triangulation: single device fulfilling orders across many unrelated cards/addresses"},
        ))
    return txns


def gen_giftcard_cashout(accounts, merchants):
    """PL-2: private-label account buys many gift cards in a short window."""
    txns = []
    mall = m_by_name(merchants, "GiftCard Mall")
    for acct in random.sample([a for a in accounts if a["product_type"] == "private_label"], 3):
        start = LIVE_START + timedelta(minutes=random.randint(0, 90))
        for i in range(random.randint(4, 8)):
            txns.append(base_txn(
                acct, mall, start + timedelta(minutes=i * 3), round(random.uniform(200, 500), 2),
                channel="in_store", entry="chip",
                label={"is_fraud": True, "fraud_vector": "PL-2", "actor_code": "B",
                       "note": "gift-card cash-out: many gift cards on credit in a short window"},
            ))
    return txns


def gen_quasi_cash(accounts, merchants):
    """CB-3: co-branded card spikes at cash-like MCCs before a bust-out."""
    txns = []
    cashlike = [m_by_name(merchants, "MoneyGram"), m_by_name(merchants, "CryptoATM")]
    for acct in random.sample([a for a in accounts if a["product_type"] == "co_branded"], 3):
        when = LIVE_START + timedelta(minutes=random.randint(0, 110))
        txns.append(base_txn(
            acct, random.choice(cashlike), when, round(random.uniform(400, 900), 2),
            channel="in_store", entry="manual", txn_type="cash_advance",
            label={"is_fraud": True, "fraud_vector": "CB-3", "actor_code": "S",
                   "note": "quasi-cash cash-out: cash-like MCC spike (money transfer / crypto)"},
        ))
    return txns


def gen_skimming(accounts, merchants):
    """CB-1: skimmed co-branded card, magstripe fallback, impossible travel."""
    txns = []
    gas = m_by_name(merchants, "Shell Gas")
    for acct in random.sample([a for a in accounts if a["product_type"] == "co_branded"], 3):
        t0 = LIVE_START + timedelta(minutes=random.randint(0, 60))
        txns.append(base_txn(acct, gas, t0, round(random.uniform(40, 90), 2),
                             channel="in_store", entry="chip"))
        # same card used far away minutes later (impossible travel), magstripe swipe
        txns.append(base_txn(
            acct, gas, t0 + timedelta(minutes=20), round(random.uniform(200, 500), 2),
            channel="in_store", entry="swipe",
            label={"is_fraud": True, "fraud_vector": "CB-1", "actor_code": "3P",
                   "note": "counterfeit/skimmed card: magstripe fallback + impossible travel"},
        ))
    return txns


def gen_installment_fpd(accounts, merchants):
    """IL-1: high-ticket phone loan, new-ish identity, express shipping, never-pay risk."""
    txns = []
    verizon = m_by_name(merchants, "Verizon")
    for acct in random.sample(legit_accounts(accounts), 4):
        when = LIVE_START + timedelta(minutes=random.randint(0, 115))
        txns.append(base_txn(
            acct, verizon, when, round(random.uniform(900, 1400), 2),
            channel="online", entry="cnp",
            installment_loan_id=rid("LOAN"), expedited_shipping=True,
            shipping_address=rand_address(),
            label={"is_fraud": True, "fraud_vector": "IL-1", "actor_code": "3P",
                   "note": "installment first-payment-default risk: high-ticket resale item, express ship, new identity"},
        ))
    return txns


def gen_refund_abuse(accounts, merchants):
    """X-5 / X-4: refund to a different tender / friendly-fraud dispute."""
    txns = []
    retail = m_by_industry(merchants, "Retail & Apparel")
    for acct in random.sample(legit_accounts(accounts), 5):
        m = random.choice(retail)
        buy_time = NOW - timedelta(days=random.randint(2, 20))
        buy = base_txn(acct, m, buy_time, round(random.uniform(150, 600), 2), channel="in_store", entry="chip")
        txns.append(buy)
        refund_time = LIVE_START + timedelta(minutes=random.randint(0, 110))
        txns.append(base_txn(
            acct, m, refund_time, -buy["amount"], channel="in_store", entry="manual",
            txn_type="refund", refund_original_txn_id=buy["transaction_id"],
            label={"is_fraud": True, "fraud_vector": "X-5", "actor_code": "B",
                   "note": "refund abuse: return processed to a different tender than original purchase"},
        ))
    return txns


# ─────────────────────────────────────────────────────────────
# Assemble
# ─────────────────────────────────────────────────────────────
def main():
    merchants = build_merchants()
    accounts, ring = build_accounts()

    txns = []
    txns += gen_legit(accounts, merchants, 780)
    txns += gen_card_testing(accounts, merchants)
    txns += gen_ato(accounts, merchants)
    txns += gen_bustout(accounts, merchants)
    txns += gen_ring_activity(accounts, ring, merchants)
    txns += gen_carecredit_fraud(accounts, merchants)
    txns += gen_wallet_provisioning(accounts, merchants)
    txns += gen_ecommerce_cnp(accounts, merchants)
    txns += gen_triangulation(accounts, merchants)
    txns += gen_giftcard_cashout(accounts, merchants)
    txns += gen_quasi_cash(accounts, merchants)
    txns += gen_skimming(accounts, merchants)
    txns += gen_installment_fpd(accounts, merchants)
    txns += gen_refund_abuse(accounts, merchants)

    # order by event_time so a replay producer can stream chronologically
    txns.sort(key=lambda t: t["event_time"])

    # strip generator-only hints from accounts before writing
    for a in accounts:
        a.pop("_risk_profile", None)

    # ── summary / manifest ──
    fraud = [t for t in txns if t["_label"]["is_fraud"]]
    by_vector, by_actor, by_line, by_phase = {}, {}, {}, {}
    for t in txns:
        by_line[t["product_line"]] = by_line.get(t["product_line"], 0) + 1
        by_phase[t["phase"]] = by_phase.get(t["phase"], 0) + 1
    for t in fraud:
        v = t["_label"]["fraud_vector"]; a = t["_label"]["actor_code"]
        by_vector[v] = by_vector.get(v, 0) + 1
        by_actor[a] = by_actor.get(a, 0) + 1

    summary = {
        "generated_at": iso(NOW),
        "counts": {"merchants": len(merchants), "accounts": len(accounts), "transactions": len(txns),
                   "fraud": len(fraud), "legit": len(txns) - len(fraud),
                   "fraud_rate_pct": round(100 * len(fraud) / len(txns), 1)},
        "by_phase": by_phase,
        "by_product_line": dict(sorted(by_line.items())),
        "fraud_by_vector": dict(sorted(by_vector.items())),
        "fraud_by_actor": dict(sorted(by_actor.items())),
        "ring_accounts": [a["account_id"] for a in ring],
    }

    (OUT_DIR / "merchants.json").write_text(json.dumps(merchants, indent=2))
    (OUT_DIR / "accounts.json").write_text(json.dumps(accounts, indent=2))
    (OUT_DIR / "transactions.json").write_text(json.dumps(txns, indent=2))
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
