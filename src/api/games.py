"""
=====================================================================
 FINFLUENT · JUEGOS MULTIJUGADOR   POST /api/games/<familia>/<accion>

   trade   state | pick | offer | cancel | preview | accept     (CREAR Market)
   shop    state | join | leave | open | pay                    (CREAR Shop)
   fair    list  | publish | invest                             (Ferias / Shark Arena)
   global  list  | publish | order                              (Global Showcase)
   team    state | create | join | save                         (Equipos 11°)
   qb      list  | save | rate                                  (Question Forge)
   bs      state | create | join | fire | pass                  (Battleship)
   lb      list  | save                                         (Hall of Fame)

 Es la misma lógica del Apps Script, pero:
   · el estudiante sale del token (nadie puede jugar a nombre de otro)
   · todo se filtra por colegio (school_id)
   · el LockService se reemplaza por un candado de Postgres por colegio+juego
=====================================================================
"""
import base64
import hashlib
import json
import random
import re
import zlib
from datetime import datetime, timezone

from flask import jsonify
from sqlalchemy import text
from sqlalchemy.orm import joinedload

from api.auth import auth_required, find_user_by_key
from api.models import (db, User, Trading, TradeCode, ShopPlayer, ShopOrder,
                        FairCompany, FairInvestment, GlobalStore, GlobalOrder,
                        Team, Question, BattleRoom, LeaderboardEntry, utcnow)
from api.routes import api, body


# ---------------------------------------------------------------------
#  Helpers comunes
# ---------------------------------------------------------------------
def err(message):
    return {"status": "error", "message": message}


def sch(model, user):
    """Filtro por colegio (los usuarios sin colegio comparten un espacio 'demo')."""
    return model.school_id == user.school_id if user.school_id else model.school_id.is_(None)


def lock(user, family):
    """Candado por colegio + juego hasta el commit (equivale al LockService de Apps Script)."""
    if db.engine.dialect.name == "postgresql":
        k = zlib.crc32(f"{family}:{user.school_id or 0}".encode())
        db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": k})


def school_user(user, key):
    """Busca a un compañero del MISMO colegio por su Student_Key."""
    other = find_user_by_key(key)
    if not other or other.school_id != user.school_id:
        return None
    return other


def two_names(name):
    return " ".join(str(name or "").split(" ")[:2])


def first_name(name):
    return str(name or "").split(" ")[0]


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


LETTERS = "ABCDFGHJKLMNPQRSTUVWXYZ"
CHARS = LETTERS + "23456789"


def new_code(taken):
    """4 caracteres, empieza con letra."""
    while True:
        code = random.choice(LETTERS) + "".join(random.choice(CHARS) for _ in range(3))
        if code not in taken:
            return code


def num(v, default=0.0):
    try:
        n = float(v)
        return n if n == n and n not in (float("inf"), float("-inf")) else default
    except Exception:
        return default


# =====================================================================
#  CREAR MARKET (Periodo 1 · trueque con códigos)
# =====================================================================
TRADE_VALUES = {"clip": 1, "pencil": 3, "notebook": 8, "bottle": 12, "ball": 20, "book": 25,
                "headphones": 35, "skateboard": 50, "bike": 120, "tablet": 200}
TRADE_VALUES_10 = {"clip": 1, "pen": 3, "cap": 8, "calc": 15, "ball": 18, "speaker": 30, "sneakers": 45,
                   "skate": 55, "guitar": 70, "console": 110, "bike": 130, "scooter": 180}


def tv(g):
    return TRADE_VALUES_10 if str(g) == "10" else TRADE_VALUES


def trade_state(user, grado):
    rows = Trading.query.options(joinedload(Trading.user)).filter(sch(Trading, user)).all()
    me_row = next((r for r in rows if r.user_id == user.id), None)
    me = None
    if me_row and me_row.object_id:
        me = {"object": me_row.object_id, "start": me_row.start_object, "trades": me_row.trades or 0,
              "partners": me_row.partners or [], "history": me_row.history or []}

    last = (TradeCode.query.filter(TradeCode.from_user_id == user.id, TradeCode.status.in_(["open", "used"]))
            .order_by(TradeCode.id.desc()).first())
    my_code = {"code": last.code, "status": last.status} if last else None

    g = str(grado or (me_row.scope if me_row else "") or "")
    values = tv(g)
    board = [{
        "name": two_names(r.user.full_name if r.user else ""),
        "object": r.object_id,
        "trades": r.trades or 0,
        "partners": len(r.partners or []),
        "me": r.user_id == user.id,
    } for r in rows if r.object_id and (not g or r.scope == g)]
    board.sort(key=lambda b: (-(values.get(b["object"], 0)), -b["trades"]))
    return {"status": "success", "me": me, "myCode": my_code, "board": board}


def apply_trade(rec, new_object, partner_name, now):
    partners = list(rec.partners or [])
    if partner_name not in partners:
        partners.append(partner_name)
    history = list(rec.history or [])
    history.append({"gave": rec.object_id, "got": new_object, "with": partner_name, "at": now_iso()})
    rec.object_id = new_object
    rec.trades = (rec.trades or 0) + 1
    rec.partners = partners
    rec.history = history
    rec.updated_at = now


def handle_trade(user, p):
    grado = str(p.get("grado") or "")
    action = p["action"]
    if action == "trade_state":
        return trade_state(user, grado)

    lock(user, "trade")
    me = Trading.query.filter_by(user_id=user.id).first()

    # ---- Abrir la caja sorpresa (solo una vez) ----
    if action == "trade_pick":
        if me and me.object_id:
            return trade_state(user, grado)
        pick = random.choice(list(tv(grado).keys()))
        if not me:
            me = Trading(user_id=user.id, school_id=user.school_id)
            db.session.add(me)
        me.scope, me.object_id, me.start_object = grado, pick, pick
        me.trades, me.partners, me.history, me.updated_at = 0, [], [], utcnow()
        db.session.flush()
        return trade_state(user, grado)

    if not me or not me.object_id:
        return err("Open your mystery box first.")

    # ---- Crear o cancelar mi oferta ----
    if action in ("trade_offer", "trade_cancel"):
        TradeCode.query.filter_by(from_user_id=user.id, status="open").update({"status": "cancelled"})
        if action == "trade_offer":
            open_codes = {c.code for c in TradeCode.query.filter(sch(TradeCode, user), TradeCode.status == "open").all()}
            db.session.add(TradeCode(school_id=user.school_id, code=new_code(open_codes), from_user_id=user.id,
                                     object_id=me.object_id, status="open"))
        db.session.flush()
        return trade_state(user, grado)

    # ---- Ver la oferta de un código / aceptar el cambio ----
    if action in ("trade_preview", "trade_accept"):
        code = str(p.get("code") or "").strip().upper()
        offer = TradeCode.query.filter(sch(TradeCode, user), TradeCode.code == code, TradeCode.status == "open").first()
        if not offer:
            return err("This code is not valid or it was already used.")
        if offer.from_user_id == user.id:
            return err("That's your own code! Give it to a classmate.")
        other = Trading.query.options(joinedload(Trading.user)).filter_by(user_id=offer.from_user_id).first()
        if not other or other.object_id != offer.object_id:
            offer.status = "cancelled"
            return err("This offer is old. Ask your classmate for a new code.")
        other_name = other.user.full_name if other.user else ""
        if action == "trade_preview":
            return {"status": "success", "preview": {"partner": other_name, "theirObject": other.object_id, "myObject": me.object_id}}

        now = utcnow()
        mine_obj, theirs_obj = me.object_id, other.object_id
        apply_trade(me, theirs_obj, other_name or other.user.student_key, now)
        apply_trade(other, mine_obj, user.full_name or user.student_key, now)
        offer.status, offer.to_user_id = "used", user.id
        db.session.flush()
        st = trade_state(user, grado)
        st["traded"] = {"gave": mine_obj, "got": theirs_obj, "with": other_name}
        return st

    return err("Unknown market action.")


# =====================================================================
#  CREAR SHOP (Periodo 2 · pagos digitales)
# =====================================================================
SHOP_CATALOG = {
    "pencil": {"n": "Pencil", "e": "✏️", "p": 2000}, "notebook": {"n": "Notebook", "e": "📓", "p": 6000},
    "juice": {"n": "Juice", "e": "🧃", "p": 3500}, "cookie": {"n": "Cookie", "e": "🍪", "p": 2500},
    "chips": {"n": "Chips", "e": "🥔", "p": 3000}, "sticker": {"n": "Sticker", "e": "⭐", "p": 1000},
    "bracelet": {"n": "Bracelet", "e": "📿", "p": 5000}, "keychain": {"n": "Keychain", "e": "🔑", "p": 4000},
    "comic": {"n": "Comic book", "e": "📖", "p": 8000}, "ball": {"n": "Ball", "e": "⚽", "p": 12000},
    "slime": {"n": "Slime", "e": "🟢", "p": 4500}, "lemonade": {"n": "Lemonade", "e": "🍋", "p": 2000},
    "cupcake": {"n": "Cupcake", "e": "🧁", "p": 3500}, "crayons": {"n": "Crayons", "e": "🖍️", "p": 7000},
    "yoyo": {"n": "Yo-yo", "e": "🪀", "p": 6000},
}
SHOP_START_BALANCE = 50000


def shop_hash(user, pin):
    return base64.b64encode(hashlib.sha256(f"{user.id}:{pin}".encode()).digest()).decode()


def shop_products(rec):
    return [{"id": i, **SHOP_CATALOG.get(i, {"n": i, "e": "❓", "p": 0})} for i in (rec.products or [])]


def shop_state(user, grado):
    rows = ShopPlayer.query.options(joinedload(ShopPlayer.user)).filter(sch(ShopPlayer, user)).all()
    rec = next((r for r in rows if r.user_id == user.id), None)
    me = None
    if rec and rec.role:
        me = {
            "role": rec.role, "shopName": rec.shop_name, "shopCode": rec.shop_code or "",
            "products": shop_products(rec) if rec.role == "seller" else [],
            "balance": rec.balance or 0, "spent": rec.spent or 0, "purchases": rec.purchases or 0,
            "salesTotal": rec.sales_total or 0, "salesCount": rec.sales_count or 0,
            "history": (rec.history or [])[-10:],
        }
    g = str(grado or (rec.scope if rec else "") or "")
    board = [{
        "name": two_names(r.user.full_name if r.user else ""), "shop": r.shop_name,
        "sales": r.sales_total or 0, "count": r.sales_count or 0, "me": r.user_id == user.id,
    } for r in rows if r.role == "seller" and (not g or r.scope == g)]
    board.sort(key=lambda b: (-b["sales"], -b["count"]))
    return {"status": "success", "me": me, "board": board}


def handle_shop(user, p):
    grado = str(p.get("grado") or "")
    action = p["action"]
    if action == "shop_state":
        return shop_state(user, grado)

    lock(user, "shop")
    me = ShopPlayer.query.filter_by(user_id=user.id).first()

    # ---- Elegir rol: vendedor o comprador ----
    if action == "shop_join":
        if me and me.role:
            return shop_state(user, grado)
        role = "seller" if p.get("role") == "seller" else "buyer"
        if role == "buyer" and not re.fullmatch(r"\d{4}", str(p.get("pin") or "")):
            return err("Your PIN must have 4 numbers.")
        if not me:
            me = ShopPlayer(user_id=user.id, school_id=user.school_id)
            db.session.add(me)
        me.scope, me.role = grado, role
        me.balance = me.spent = me.sales_total = 0
        me.purchases = me.sales_count = 0
        me.history, me.updated_at = [], utcnow()
        if role == "seller":
            ids = list(SHOP_CATALOG.keys())
            random.shuffle(ids)
            used = {r.shop_code for r in ShopPlayer.query.filter(sch(ShopPlayer, user)).all() if r.shop_code}
            me.shop_name = str(p.get("shop_name") or "My Shop")[:28]
            me.shop_code = new_code(used)
            me.products = ids[:5]
        else:
            me.pin_hash = shop_hash(user, p.get("pin"))
            me.balance = SHOP_START_BALANCE
        db.session.flush()
        return shop_state(user, grado)

    # ---- Cambiar de rol (borra la tienda o la billetera) ----
    if action == "shop_leave":
        if me:
            db.session.delete(me)
            db.session.flush()
        st = shop_state(user, grado)
        st["me"] = None
        return st

    if not me or not me.role:
        return err("Choose your role first.")

    # ---- Entrar a una tienda con su código / pagar ----
    if action in ("shop_open", "shop_pay"):
        code = str(p.get("code") or "").strip().upper()
        seller = (ShopPlayer.query.options(joinedload(ShopPlayer.user))
                  .filter(sch(ShopPlayer, user), ShopPlayer.role == "seller", ShopPlayer.shop_code == code).first())
        if not seller or not code:
            return err("This shop code does not exist. Check it with the seller.")
        if seller.user_id == user.id:
            return err("That's your own shop!")
        products = shop_products(seller)
        seller_full = seller.user.full_name if seller.user else ""

        if action == "shop_open":
            return {"status": "success", "shop": {"code": code, "name": seller.shop_name,
                                                  "seller": two_names(seller_full), "products": products}}

        if me.role != "buyer":
            return err("Only buyers can pay. Change your role.")
        if shop_hash(user, p.get("pin")) != me.pin_hash:
            return err("❌ Wrong PIN. Try again — and remember, never share it!")
        method = p.get("method") if p.get("method") in ("card", "qr", "wallet") else "card"
        items = []
        for it in (p.get("items") or []):
            pr = next((x for x in products if x["id"] == (it or {}).get("id")), None)
            qty = int(max(0, min(5, num((it or {}).get("qty")))))
            if pr and qty:
                items.append({**pr, "qty": qty})
        if not items:
            return err("Your cart is empty.")
        total = sum(it["p"] * it["qty"] for it in items)
        balance = me.balance or 0
        if total > balance:
            return err("Not enough money in your wallet.")

        now = utcnow()
        summary = ", ".join(f"{it['qty']}× {it['n']}" for it in items)
        me.history = ((me.history or []) + [{"with": seller.shop_name, "items": summary, "total": total,
                                             "method": method, "at": now_iso()}])[-30:]
        me.balance, me.spent, me.purchases, me.updated_at = balance - total, (me.spent or 0) + total, (me.purchases or 0) + 1, now

        seller.history = ((seller.history or []) + [{"with": first_name(user.full_name), "items": summary, "total": total,
                                                     "method": method, "at": now_iso()}])[-30:]
        seller.sales_total, seller.sales_count, seller.updated_at = (seller.sales_total or 0) + total, (seller.sales_count or 0) + 1, now

        db.session.add(ShopOrder(school_id=user.school_id, shop_code=code, seller_id=seller.user_id, buyer_id=user.id,
                                 items=[{"id": it["id"], "qty": it["qty"], "p": it["p"]} for it in items],
                                 total=total, method=method))
        db.session.flush()
        st = shop_state(user, grado)
        st["receipt"] = {"shop": seller.shop_name, "seller": first_name(seller_full), "items": items, "total": total,
                         "method": method, "balance": balance - total, "at": now_iso()}
        return st

    return err("Unknown shop action.")


# =====================================================================
#  FERIAS (Young Entrepreneurs Fair, Shark Arena, Pre-order Fair, Gallery…)
# =====================================================================
FAIR_BUDGET = 100
FAIR_CATS = ["clarity", "useful", "creative", "responsible"]


def fair_state(user, grado):
    g = str(grado or "")
    cq = FairCompany.query.options(joinedload(FairCompany.user)).filter(sch(FairCompany, user))
    iq = FairInvestment.query.filter(sch(FairInvestment, user))
    if g:
        cq, iq = cq.filter(FairCompany.scope == g), iq.filter(FairInvestment.scope == g)
    invs = iq.all()
    totals = {}
    for r in invs:
        t = totals.setdefault((r.company_user_id, r.scope), {"total": 0, "cats": {}})
        t["total"] += r.amount or 0
        t["cats"][r.category or ""] = t["cats"].get(r.category or "", 0) + (r.amount or 0)

    key_by_id = {}
    companies = []
    for r in cq.all():
        k = r.user.student_key if r.user else ""
        key_by_id[r.user_id] = k
        t = totals.get((r.user_id, r.scope), {"total": 0, "cats": {}})
        companies.append({"key": k, "nombre": r.user.full_name if r.user else "", "company": r.company or {},
                          "total": t["total"], "cats": t["cats"]})

    mine_rows = [r for r in invs if r.investor_id == user.id]
    missing = {r.company_user_id for r in mine_rows} - set(key_by_id)
    if missing:
        for u in User.query.filter(User.id.in_(missing)).all():
            key_by_id[u.id] = u.student_key
    mine = [{"company": key_by_id.get(r.company_user_id, ""), "amount": r.amount or 0, "category": r.category} for r in mine_rows]
    spent = sum(m["amount"] for m in mine)
    return {"status": "success", "companies": companies, "mine": mine, "left": max(0, FAIR_BUDGET - spent)}


def handle_fair(user, p):
    grado = str(p.get("grado") or "")
    action = p["action"]
    if action == "fair_list":
        return fair_state(user, grado)

    lock(user, "fair")

    # ---- Abrir / actualizar mi stand ----
    if action == "fair_publish":
        company = p.get("company") or {}
        if len(json.dumps(company)) > 45000:
            return err("Your company card is too long. Make some texts shorter.")
        me = FairCompany.query.filter_by(user_id=user.id, scope=grado).first()
        if not me:
            me = FairCompany(user_id=user.id, school_id=user.school_id, scope=grado)
            db.session.add(me)
        me.company_name = str(company.get("name") or "My Company")[:40]
        me.company, me.updated_at = company, utcnow()
        db.session.flush()
        return fair_state(user, grado)

    # ---- Invertir monedas en una empresa ----
    if action == "fair_invest":
        target_key = str(p.get("company_key") or "").strip()
        amount = int(round(num(p.get("amount"))))
        cat = str(p.get("category")) if str(p.get("category")) in FAIR_CATS else "useful"
        if not target_key:
            return err("Choose a company.")
        target = school_user(user, target_key)
        if target and target.id == user.id:
            return err("You cannot invest in your own company! 😉")
        if amount <= 0 or amount % 10 != 0:
            return err("Invest 10, 20, 30 or 50 coins.")
        if not target or not FairCompany.query.filter_by(user_id=target.id, scope=grado).first():
            return err("That stand is closed.")
        spent = sum(r.amount or 0 for r in FairInvestment.query.filter_by(investor_id=user.id, scope=grado).all())
        if spent + amount > FAIR_BUDGET:
            return err(f"You only have {FAIR_BUDGET - spent} coins left.")
        db.session.add(FairInvestment(school_id=user.school_id, investor_id=user.id, company_user_id=target.id,
                                      amount=amount, category=cat, note=str(p.get("note") or "")[:300], scope=grado))
        db.session.flush()
        return fair_state(user, grado)

    return err("Unknown fair action.")


# =====================================================================
#  GLOBAL BUSINESS SHOWCASE (Periodo 4 · tiendas + reseñas)
# =====================================================================
GLOBAL_WALLET = 100000


def global_state(user, grado):
    g = str(grado or "")
    orders = GlobalOrder.query.options(joinedload(GlobalOrder.buyer)).filter(sch(GlobalOrder, user)).order_by(GlobalOrder.id).all()
    by_store = {}
    for o in orders:
        b = by_store.setdefault(o.store_user_id, {"sales": 0, "count": 0, "stars": 0, "reviews": []})
        b["sales"] += o.total or 0
        b["count"] += 1
        if (o.stars or 0) > 0:
            b["stars"] += o.stars
            b["reviews"].append({"stars": o.stars, "text": o.review or "", "name": o.buyer.full_name if o.buyer else ""})

    sq = GlobalStore.query.options(joinedload(GlobalStore.user)).filter(sch(GlobalStore, user))
    if g:
        sq = sq.filter(GlobalStore.scope == g)
    key_by_id = {}
    stores = []
    for r in sq.all():
        k = r.user.student_key if r.user else ""
        key_by_id[r.user_id] = k
        b = by_store.get(r.user_id, {"sales": 0, "count": 0, "stars": 0, "reviews": []})
        stores.append({"key": k, "nombre": r.user.full_name if r.user else "", "store": r.store or {},
                       "sales": b["sales"], "count": b["count"],
                       "stars": (b["stars"] / len(b["reviews"])) if b["reviews"] else 0,
                       "reviews": list(reversed(b["reviews"][-8:]))})

    my_orders = [o for o in orders if o.buyer_id == user.id]
    missing = {o.store_user_id for o in my_orders} - set(key_by_id)
    if missing:
        for u in User.query.filter(User.id.in_(missing)).all():
            key_by_id[u.id] = u.student_key
    spent = sum(o.total or 0 for o in my_orders)
    return {"status": "success", "stores": stores, "balance": max(0, GLOBAL_WALLET - spent),
            "orders": [{"store": key_by_id.get(o.store_user_id, ""), "total": o.total or 0} for o in my_orders]}


def handle_global(user, p):
    grado = str(p.get("grado") or "")
    action = p["action"]
    if action == "global_list":
        return global_state(user, grado)

    lock(user, "global")

    # ---- Publicar / actualizar mi tienda ----
    if action == "global_publish":
        store = p.get("store") or {}
        if not store.get("products"):
            return err("Your store needs at least one product.")
        if len(json.dumps(store)) > 45000:
            return err("Your store is too long. Make some texts shorter.")
        me = GlobalStore.query.filter_by(user_id=user.id).first()
        if not me:
            me = GlobalStore(user_id=user.id, school_id=user.school_id)
            db.session.add(me)
        me.scope, me.store_name = grado, str(store.get("name") or "My Store")[:40]
        me.store, me.updated_at = store, utcnow()
        db.session.flush()
        return global_state(user, grado)

    # ---- Comprar en una tienda + reseña con estrellas ----
    if action == "global_order":
        target_key = str(p.get("store_key") or "").strip()
        if not target_key:
            return err("Choose a store.")
        target = school_user(user, target_key)
        if target and target.id == user.id:
            return err("You cannot buy in your own store! 😉")
        rec = GlobalStore.query.filter_by(user_id=target.id).first() if target else None
        if not rec:
            return err("That store is closed.")
        catalog = {str(pr.get("id")): pr for pr in ((rec.store or {}).get("products") or []) if isinstance(pr, dict)}

        total, lines = 0, []
        for it in (p.get("items") or []):
            pr = catalog.get(str((it or {}).get("id")))
            qty = int(max(0, min(20, round(num((it or {}).get("qty"))))))
            if pr and qty > 0:
                price = num(pr.get("price"))
                total += price * qty
                lines.append({"id": pr.get("id"), "name": pr.get("name"), "qty": qty, "price": price})
        if not lines:
            return err("Your cart is empty.")

        stars = int(round(num(p.get("stars"))))
        if stars < 1 or stars > 5:
            return err("Give 1 to 5 stars.")
        review = str(p.get("review") or "").strip()[:200]
        if len(review.split()) < 5:
            return err("Write a review with 5 words or more.")

        spent = sum(o.total or 0 for o in GlobalOrder.query.filter_by(buyer_id=user.id).all())
        if spent + total > GLOBAL_WALLET:
            return err(f"Insufficient balance! You have ${GLOBAL_WALLET - spent:,.0f}.")

        db.session.add(GlobalOrder(school_id=user.school_id, buyer_id=user.id, store_user_id=target.id, items=lines,
                                   total=total, method=str(p.get("method") or "")[:20], stars=stars, review=review, scope=grado))
        db.session.flush()
        return global_state(user, grado)

    return err("Unknown Showcase action.")


# =====================================================================
#  GRADO 11 · EQUIPOS
# =====================================================================
def team_out(r):
    return {"code": r.code, "name": r.name or "", "members": r.members or [], "data": r.data or {}}


def handle_team(user, p):
    key = user.student_key
    nombre = user.full_name
    grado = str(p.get("grado") or "11")
    action = p["action"]
    teams_q = Team.query.filter(sch(Team, user))

    def is_member(t):
        return any(str((m or {}).get("key")) == key for m in (t.members or []))

    def find(code):
        if code:
            return teams_q.filter(Team.code == code).first()
        return next((t for t in teams_q.all() if is_member(t)), None)

    code = str(p.get("code") or "").strip().upper()

    if action == "team_state":
        rec = find(code)
        if not rec:
            return err("Team not found.")
        return {"status": "success", "team": team_out(rec)}

    lock(user, "team")
    now = utcnow()
    all_teams = teams_q.all()

    def leave_others(except_code):
        for t in all_teams:
            if t.code == except_code:
                continue
            if is_member(t):
                t.members = [m for m in (t.members or []) if str((m or {}).get("key")) != key]
                t.updated_at = now

    if action == "team_create":
        name = str(p.get("name") or "").strip()[:28]
        if len(name) < 3:
            return err("Write a team name (3+ letters).")
        new = Team(school_id=user.school_id, code=new_code({t.code for t in all_teams}), name=name, scope=grado,
                   members=[{"key": key, "name": nombre}], data={}, created_at=now, updated_at=now)
        leave_others(new.code)
        db.session.add(new)
        db.session.flush()
        return {"status": "success", "team": team_out(new)}

    if action == "team_join":
        rec = next((t for t in all_teams if t.code.upper() == code), None)
        if not rec:
            return err("That team code does not exist. Check the 4 letters.")
        mem = list(rec.members or [])
        if not is_member(rec):
            if len(mem) >= 6:
                return err("This team is full (6 founders).")
            mem.append({"key": key, "name": nombre})
        leave_others(rec.code)
        rec.members, rec.updated_at = mem, now
        db.session.flush()
        return {"status": "success", "team": team_out(rec)}

    if action == "team_save":
        rec = next((t for t in all_teams if t.code.upper() == code), None) if code else next((t for t in all_teams if is_member(t)), None)
        if not rec:
            return err("Team not found.")
        if not is_member(rec):
            return err("You are not a member of this team.")
        data = dict(rec.data or {})
        for k, v in (p.get("data") or {}).items():
            data[k] = v
            data[k + "_by"] = nombre
        if len(json.dumps(data)) > 45000:
            return err("Team data is too long.")
        rec.data, rec.updated_at = data, now
        db.session.flush()
        return {"status": "success", "team": team_out(rec)}

    return err("Unknown team action.")


# =====================================================================
#  GRADO 11 · BANCO DE PREGUNTAS (Question Forge)
# =====================================================================
def handle_qb(user, p):
    grado = str(p.get("grado") or "11")
    action = p["action"]
    base = Question.query.filter(sch(Question, user), Question.scope == grado)

    if action == "qb_list":
        out = []
        for r in base.options(joinedload(Question.user)).all():
            if (r.bad or 0) >= 3 and (r.bad or 0) > (r.good or 0):     # reportadas por la clase: se ocultan
                continue
            q = r.q or {}
            if not q.get("q") or not isinstance(q.get("options"), list) or len(q["options"]) != 4:
                continue
            out.append({"id": str(r.id), "t": r.topic or "", "lv": r.level or 2, "q": q.get("q"), "options": q["options"],
                        "correct": int(num(q.get("correct"))), "by": r.user.full_name if r.user else "",
                        "mine": r.user_id == user.id})
        return {"status": "success", "questions": out}

    lock(user, "qb")

    if action == "qb_save":
        lst = (p.get("questions") or [])[:5]
        if len(lst) < 5:
            return err("Send 5 questions.")
        for i, x in enumerate(lst):
            x = x or {}
            opts = [str(s or "").strip() for s in (x.get("options") or [])]
            if not x.get("q") or len(str(x.get("q")).strip().split()) < 6:
                return err(f"Question {i + 1} is too short.")
            if len(opts) != 4 or any(not s for s in opts):
                return err(f"Question {i + 1} needs 4 options.")
            c = num(x.get("correct"), -1)
            if not (0 <= c <= 3):
                return err(f"Question {i + 1} needs a correct option.")
        base.filter(Question.user_id == user.id).delete(synchronize_session=False)   # reemplaza las anteriores
        for x in lst:
            db.session.add(Question(
                school_id=user.school_id, user_id=user.id, scope=grado, topic=str(x.get("t") or "")[:30],
                level=int(max(1, min(3, num(x.get("lv"), 2) or 2))),
                q={"q": str(x["q"]).strip()[:300], "options": [str(s).strip()[:140] for s in x["options"]],
                   "correct": int(num(x.get("correct")))}, good=0, bad=0))
        db.session.flush()
        return {"status": "success", "saved": len(lst)}

    if action == "qb_rate":
        try:
            rec = base.filter(Question.id == int(p.get("id"))).first()
        except Exception:
            rec = None
        if not rec:
            return err("Question not found.")
        if rec.user_id == user.id:
            return {"status": "success"}
        if p.get("rate") == "good":
            rec.good = (rec.good or 0) + 1
        if p.get("rate") in ("wrong", "hard"):
            rec.bad = (rec.bad or 0) + 1
        return {"status": "success"}

    return err("Unknown question-bank action.")


# =====================================================================
#  GRADO 11 · BATTLESHIP ONLINE  (6×6 · barcos de 3, 2, 2 y 1)
# =====================================================================
CELL = re.compile(r"^[0-5],[0-5]$")


def bs_valid_board(board):
    if not isinstance(board, list) or len(board) != 4:
        return False
    if sorted(len(s) if isinstance(s, list) else 0 for s in board) != [1, 2, 2, 3]:
        return False
    seen = set()
    for ship in board:
        for c in ship:
            k = str(c)
            if not CELL.match(k) or k in seen:
                return False
            seen.add(k)
    return True


def bs_out(r, user):
    me = "A" if r.a_user_id == user.id else "B"
    my_ships, op_ships = (r.a_board, r.b_board) if me == "A" else (r.b_board, r.a_board)
    my_shots, their_shots = (r.a_shots, r.b_shots) if me == "A" else (r.b_shots, r.a_shots)
    my_ships, op_ships, my_shots, their_shots = my_ships or [], op_ships or [], my_shots or {}, their_shots or {}
    their_sunk = [s for s in op_ships if all(my_shots.get(k) == "hit" for k in s)]   # solo barcos ya hundidos
    return {"code": r.code, "me": me, "turn": r.turn or "A", "winner": r.winner or "",
            "names": {"A": r.a_name or "", "B": r.b_name or ""},
            "ready": {"A": bool(r.a_board), "B": bool(r.b_board)},
            "myShips": my_ships, "myShots": my_shots, "theirShots": their_shots, "theirSunk": their_sunk}


def handle_bs(user, p):
    grado = str(p.get("grado") or "11")
    action = p["action"]
    code = str(p.get("code") or "").strip().upper()
    rooms = BattleRoom.query.filter(sch(BattleRoom, user))

    def in_room(r):
        return user.id in (r.a_user_id, r.b_user_id)

    if action == "bs_state":
        rec = rooms.filter(BattleRoom.code == code).first()
        if not rec or not in_room(rec):
            return err("Battle not found.")
        return {"status": "success", "room": bs_out(rec, user)}

    lock(user, "bs")
    now = utcnow()

    if action == "bs_create":
        if not bs_valid_board(p.get("board")):
            return err("Invalid fleet. Move your ships again.")
        taken = {r.code for r in rooms.with_entities(BattleRoom.code).all()}
        row = BattleRoom(school_id=user.school_id, code=new_code(taken), scope=grado, a_user_id=user.id,
                         a_name=user.full_name, b_name="", a_board=p.get("board"), b_board=[], a_shots={}, b_shots={},
                         turn="A", winner="", updated_at=now)
        db.session.add(row)
        db.session.flush()
        return {"status": "success", "room": bs_out(row, user)}

    rec = rooms.filter(BattleRoom.code == code).with_for_update().first()
    if not rec:
        return err("That battle code does not exist.")

    if action == "bs_join":
        if in_room(rec):
            return {"status": "success", "room": bs_out(rec, user)}       # volver a entrar
        if rec.b_user_id:
            return err("This battle already has two captains.")
        if not bs_valid_board(p.get("board")):
            return err("Invalid fleet. Move your ships again.")
        rec.b_user_id, rec.b_name, rec.b_board, rec.updated_at = user.id, user.full_name, p.get("board"), now
        db.session.flush()
        return {"status": "success", "room": bs_out(rec, user)}

    if not in_room(rec):
        return err("You are not in this battle.")
    me = "A" if rec.a_user_id == user.id else "B"
    op = "B" if me == "A" else "A"
    if rec.winner:
        return {"status": "success", "room": bs_out(rec, user)}
    if not rec.b_board:
        return err("Wait for your rival to join.")
    if rec.turn != me:
        return err("It's not your turn.")

    if action == "bs_pass":
        rec.turn, rec.updated_at = op, now
        return {"status": "success", "room": bs_out(rec, user)}

    if action == "bs_fire":
        cell = str(p.get("cell") or "")
        if not CELL.match(cell):
            return err("Invalid cell.")
        shots = dict((rec.a_shots if me == "A" else rec.b_shots) or {})
        if shots.get(cell):
            return err("You already fired there.")
        op_ships = (rec.b_board if me == "A" else rec.a_board) or []
        shots[cell] = "hit" if any(cell in s for s in op_ships) else "miss"
        if me == "A":
            rec.a_shots = shots
        else:
            rec.b_shots = shots
        if all(all(shots.get(k) == "hit" for k in s) for s in op_ships):
            rec.winner = me
        rec.turn, rec.updated_at = op, now
        db.session.flush()
        return {"status": "success", "room": bs_out(rec, user)}

    return err("Unknown battle action.")


# =====================================================================
#  GRADO 11 · HALL OF FAME
# =====================================================================
LB_LOWER_IS_BETTER = {"vault", "vault2"}     # tiempo de escape: menos es mejor
LB_ADD_UP = {"bs"}                           # Battleship: suma victorias


def handle_lb(user, p):
    grado = str(p.get("grado") or "11")
    action = p["action"]

    if action == "lb_list":
        boards = {}
        rows = (LeaderboardEntry.query.options(joinedload(LeaderboardEntry.user))
                .filter(sch(LeaderboardEntry, user), LeaderboardEntry.scope == grado).all())
        for r in rows:
            boards.setdefault(r.game, []).append({"name": r.user.full_name if r.user else "", "score": r.score or 0,
                                                  "mine": r.user_id == user.id})
        for g, lst in boards.items():
            lst.sort(key=lambda x: x["score"] if g in LB_LOWER_IS_BETTER else -x["score"])
            boards[g] = lst[:10]
        return {"status": "success", "boards": boards}

    if action == "lb_save":
        lock(user, "lb")
        game = str(p.get("game") or "")[:12]
        score = num(p.get("score"), None)
        if not game or score is None:
            return err("Invalid score.")
        rec = LeaderboardEntry.query.filter_by(user_id=user.id, game=game, scope=grado).first()
        extra = p.get("extra") if isinstance(p.get("extra"), dict) else {}
        if not rec:
            db.session.add(LeaderboardEntry(school_id=user.school_id, user_id=user.id, scope=grado, game=game,
                                            score=score, extra=extra))
            return {"status": "success"}
        old = rec.score or 0
        if game in LB_ADD_UP:
            nxt = old + max(0, score)
        elif game in LB_LOWER_IS_BETTER:
            nxt = min(old, score) if old > 0 else score
        else:
            nxt = max(old, score)
        rec.score, rec.extra, rec.updated_at = nxt, extra, utcnow()
        return {"status": "success"}

    return err("Unknown leaderboard action.")


# ---------------------------------------------------------------------
#  Despachador
# ---------------------------------------------------------------------
FAMILIES = {"trade": handle_trade, "shop": handle_shop, "fair": handle_fair, "global": handle_global,
            "team": handle_team, "qb": handle_qb, "bs": handle_bs, "lb": handle_lb}


@api.route('/games/<family>/<action>', methods=['POST'])
@auth_required()
def games(user, family, action):
    handler = FAMILIES.get(family)
    if not handler:
        return jsonify(err("Unknown game.")), 404
    p = body()
    p["action"] = f"{family}_{action}"
    try:
        out = handler(user, p)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(out), 200
