from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# Imports estándar
import os
import json
import logging
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

# ──────────────────────────────────────────────────────────────────────────────
# Imports de terceros
from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, jsonify, redirect,
    render_template, request, session, url_for
)
from flask_login import (
    LoginManager, current_user, login_required,
    login_user, logout_user
)
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

# ──────────────────────────────────────────────────────────────────────────────
# Imports locales
from forms import RegisterForm
from models import User, Post
from extensions import db, bcrypt
from football_api import player_info as football_pi
from basket_api import player_info as basket_pi
from wa_scraper import player_info as wa_scraper
from formula1_api import driver_info as f1_pi
from mma_api import player_info as mma_pi
from routes import bp as posts_bp

# ──────────────────────────────────────────────────────────────────────────────
# Configuración de entorno y logging
load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("app")

# ──────────────────────────────────────────────────────────────────────────────
# Creación de la app y configuración de extensiones
app = Flask(__name__)
app.config.update({
    "SECRET_KEY": os.getenv("SECRET_KEY", "changeme-please"),
    "SQLALCHEMY_DATABASE_URI": (
        f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASS')}"
        f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/"
        f"{os.getenv('MYSQL_DB', 'sportstats')}?charset=utf8mb4"
    ),
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "SPORTS_LIST": [
        "Atletismo",
        "NBA",
        "Fútbol",
        "Fórmula 1",
        "MMA",
    ],
})
db.init_app(app)
bcrypt.init_app(app)

# ──────────────────────────────────────────────────────────────────────────────
# Login manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


# ──────────────────────────────────────────────────────────────────────────────
# Servicio de estadísticas por deporte
SERVICE_MAP = {
    0: wa_scraper,
    1: basket_pi,
    2: football_pi,
    3: f1_pi,
    4: mma_pi,
}

# ──────────────────────────────────────────────────────────────────────────────
# Rutas de autenticación y sesión

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if not user or not user.check_pw(request.form["password"]):
            abort(401, "Credenciales inválidas")
        fav = int(request.form.get("fav_sport", 0))
        session['fav_sport'] = fav
        user.fav_sport = fav
        db.session.commit()
        login_user(user)
        return redirect(request.args.get("next") or url_for("index"))
    return render_template("login.html", sports=app.config["SPORTS_LIST"])


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.route("/register_user", methods=["GET", "POST"])
def register_user():
    form = RegisterForm()
    if form.validate_on_submit():
        uname = form.username.data.strip()
        email = form.email.data.strip()
        pwd   = form.password.data
        fav   = int(form.fav_sport.data)

        if User.query.filter_by(username=uname).first():
            flash("El nombre de usuario ya existe", "danger")
            return redirect(url_for("register_user"))
        if User.query.filter_by(email=email).first():
            flash("Ese email ya existe", "danger")
            return redirect(url_for("register_user"))

        user = User(username=uname, email=email, fav_sport=fav)
        user.set_password(pwd)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            flash("Ese email ya existe", "danger")
            return redirect(url_for("register_user"))

        flash("Usuario creado. Ya puedes iniciar sesión", "success")
        return redirect(url_for("login"))

    return render_template("register_user.html", form=form)


# ──────────────────────────────────────────────────────────────────────────────
# JSON legacy de deportistas

BASE_DIR       = Path(__file__).resolve().parent
DATA_FILE      = BASE_DIR / "players.json"
PRECHARGE_FILE = BASE_DIR / "precharge_players.json"

def load_players() -> List[Dict[str, Any]]:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text("utf-8"))
        except json.JSONDecodeError:
            pass
    return []

def save_players(players: List[Dict[str, Any]]) -> None:
    DATA_FILE.write_text(json.dumps(players, indent=4, ensure_ascii=False), "utf-8")

def load_precharge() -> List[Dict[str, Any]]:
    if PRECHARGE_FILE.exists():
        try:
            return json.loads(PRECHARGE_FILE.read_text("utf-8"))
        except json.JSONDecodeError:
            pass
    return []

def save_precharge(pre_list: List[Dict[str, Any]]) -> None:
    PRECHARGE_FILE.write_text(json.dumps(pre_list, indent=4, ensure_ascii=False), "utf-8")

def _strip(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn').lower()

def _find_player(name: str):
    key = _strip(name)
    for pl in load_players():
        if _strip(pl["DatosPersonales"]["name"]) == key:
            return pl
    return None

def create_player_data(form: Dict[str, str]) -> Dict[str, Any]:
    personal = {k: form.get(k, "").strip() for k in (
        "id", "name", "FirstName", "LastName", "Gender",
        "placeofbirth", "bio", "about"
    )}
    personal["age"] = int(form.get("age", 0) or 0)
    sport = {
        "sport": form.get("sport", "0"),
        "sportLevel": form.get("sportLevel", "").strip(),
        "sportIndexList": [s.strip() for s in form.get("sportIndexList","").split(",") if s.strip()],
        "Position": form.get("Position","").strip(),
        "Side": form.get("Side","").strip(),
        "SportSituation": form.get("SportSituation","").strip(),
        "StartPlayer": form.get("StartPlayer","").strip(),
        "athlete_id": form.get("athlete_id","").strip(),
        "jersey": form.get("jersey","").strip(),
        "games": [],
    }
    return {"DatosPersonales": personal, "DeporteYHabilidades": sport}

def generate_next_id() -> str:
    players = load_players()
    if not players:
        return "1"
    max_id = 0
    for p in players:
        try:
            nid = int(p["DatosPersonales"].get("id", "0"))
            max_id = max(max_id, nid)
        except ValueError:
            continue
    return str(max_id + 1)

def _stats_for_player(player: dict) -> dict:
    idx = int(player["DeporteYHabilidades"]["sport"])
    svc = SERVICE_MAP.get(idx)
    if not svc:
        return {}
    name = player["DatosPersonales"]["name"]
    try:
        if idx == 0:
            aid = player["DeporteYHabilidades"].get("athlete_id") or None
            return svc(name, athlete_id=aid)
        if idx == 1:
            api_id  = int(player["DeporteYHabilidades"].get("athlete_id") or 0)
            season  = player.get("season")
            game_id = player.get("game_id")
            if not (api_id and season and game_id):
                return {}
            return svc(api_id, season=season, game_id=game_id)
        return svc(name)
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Rutas de gestión de deportistas

@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        new_id = generate_next_id()
        name = request.form.get("name", "").strip()
        if not name:
            flash("El 'Nombre completo' es obligatorio.", "danger")
            return render_template("register.html", sports=app.config["SPORTS_LIST"])
        player = create_player_data(request.form)
        player["DatosPersonales"]["id"] = new_id
        players = load_players()
        players.append(player)
        save_players(players)
        flash(f"Deportista '{player['DatosPersonales']['name']}' creado con ID {new_id}.", "success")
        return redirect(url_for("list_players"))
    return render_template("register.html", sports=app.config["SPORTS_LIST"])


@app.route("/players")
@login_required
def list_players():
    players = load_players()
    players.sort(key=lambda p: int(p["DeporteYHabilidades"]["sport"]))
    return render_template("users.html", players=players, sports=app.config["SPORTS_LIST"])


@app.route("/player/<pid>")
@login_required
def player_detail(pid: str):
    players = load_players()
    pl = next((p for p in players if p["DatosPersonales"]["id"] == pid), None)
    if not pl:
        abort(404)
    season  = request.args.get("season", type=int)
    game_id = request.args.get("game", type=int)
    updated = False
    if season and pl.get("season") != season:
        pl["season"] = season
        updated = True
    if game_id and pl.get("game_id") != game_id:
        pl["game_id"] = game_id
        updated = True
    if updated:
        save_players(players)
    api_data = _stats_for_player(pl)
    if (pl["DeporteYHabilidades"]["sport"] == '1'
        and season and game_id and request.args.get("save")):
        row = (api_data.get("response") or [{}])[0]
        games = pl["DeporteYHabilidades"].setdefault("games", [])
        if not any(g["season"] == season and g["game_id"] == game_id for g in games):
            if row.get("points") is not None:
                games.append({
                    "season": season,
                    "game_id": game_id,
                    "pts": row.get("points", 0),
                    "reb": row.get("totReb", 0),
                    "ast": row.get("assists", 0),
                })
                save_players(players)
    return render_template(
        "player_detail.html",
        player=pl,
        api_data=api_data,
        sports=app.config["SPORTS_LIST"]
    )


@app.route("/player/<pid>/edit", methods=["GET", "POST"])
@login_required
def edit_player(pid: str):
    players = load_players()
    pl = next((p for p in players if p["DatosPersonales"]["id"] == pid), None)
    if not pl:
        abort(404)
    if request.method == "POST":
        updated = create_player_data(request.form)
        updated["DatosPersonales"]["id"] = pid
        players = [updated if p["DatosPersonales"]["id"] == pid else p for p in players]
        save_players(players)
        return redirect(url_for("player_detail", pid=pid))
    return render_template("edit_player.html", player=pl, sports=app.config["SPORTS_LIST"])


@app.route("/player/<pid>/delete", methods=["POST"])
@login_required
def delete_player(pid: str):
    current_favs = load_players()
    jugador = next((p for p in current_favs if p["DatosPersonales"]["id"] == pid), None)
    if not jugador:
        abort(404, "Deportista no encontrado en favoritos")
    new_favs = [p for p in current_favs if p["DatosPersonales"]["id"] != pid]
    save_players(new_favs)
    pre_list = load_precharge()
    if not any(p["DatosPersonales"]["id"] == pid for p in pre_list):
        pre_list.append(jugador)
        save_precharge(pre_list)
    flash(f"«{jugador['DatosPersonales']['name']}» devuelto a pre-cargados.", "info")
    return redirect(url_for("list_players"))


# ──────────────────────────────────────────────────────────────────────────────
# Micro-feed y Posts

@app.route("/posts", methods=["GET", "POST"])
@login_required
def posts():
    if request.method == "POST":
        body = request.form["body"].strip()
        if body:
            db.session.add(Post(content=body, author=current_user))
            db.session.commit()
        return redirect(url_for("posts"))
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("posts.html",
                           posts=all_posts,
                           sports=app.config["SPORTS_LIST"],
                           user=current_user)


# ──────────────────────────────────────────────────────────────────────────────
# Página de inicio y ranking

@app.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    return render_template("index.html", sports=app.config["SPORTS_LIST"])


@app.route("/ranking")
@login_required
def ranking():
    players = load_players()
    by_sport: Dict[str, List] = {s: [] for s in app.config["SPORTS_LIST"]}

    for p in players:
        idx        = int(p["DeporteYHabilidades"]["sport"])
        sport_name = app.config["SPORTS_LIST"][idx]

        try:
            stats = _stats_for_player(p) or {}
        except Exception as e:
            log.warning("stats error: %s", e)
            stats = {}

        rank: dict[str, Any] = {"edad": p["DatosPersonales"]["age"]}

        # ─── CÁLCULO DE MÉTRICAS SEGÚN DEPORTE ────────────────────────────────
        if idx == 0:
            # Atletismo: mostramos la primera marca personal
            pbs = stats.get("pbs", [])
            if pbs:
                best = pbs[0]
                rank["prueba"] = best.get("discipline", "")
                rank["marca"]   = best.get("performance", "")
            else:
                rank["prueba"] = ""
                rank["marca"]   = ""
        elif idx == 1:
            # NBA: puntos, rebotes, asistencias, minutos
            resp = stats.get("response", []) or []
            if resp:
                st = resp[0]
                rank.update({
                    "pts": st.get("points", 0),
                    "reb": st.get("totReb",  0),
                    "ast": st.get("assists", 0),
                    "min": st.get("min",     0),
                })
        elif idx == 2:
            # Fútbol: resumimos la última temporada
            seasons   = stats.get("seasons", []) or []
            stats_map = stats.get("stats", {})   or {}
            if seasons:
                last = seasons[-1]
                lsts = stats_map.get(last, []) or []
                suma = {
                    "goles":  0,
                    "asis":   0,
                    "ga":     0,
                    "min":    0,
                    "yellow": 0,
                    "red":    0,
                }
                for st in lsts:
                    goles  = st.get("goals",{}).get("total", 0)
                    asis   = st.get("goals",{}).get("assists",0)
                    mins   = st.get("games",{}).get("minutes",0)
                    yellow = st.get("cards",{}).get("yellow",0)
                    red    = st.get("cards",{}).get("red",0)
                    suma["goles"]  += goles
                    suma["asis"]   += asis
                    suma["ga"]     += (goles + asis)
                    suma["min"]    += mins
                    suma["yellow"] += yellow
                    suma["red"]    += red
                rank.update(suma)
        elif idx == 3:
            # Fórmula 1: mundiales, podios, puntos de carrera
            resp = stats.get("response", []) or []
            if resp:
                drv = resp[0]
                rank.update({
                    "mund": drv.get("world_championships", 0),
                    "pod":  drv.get("podiums",             0),
                    "pts":  drv.get("career_points",       0),
                })
        elif idx == 4:
            # MMA: altura, peso, reach
            resp = stats.get("response", []) or []
            if resp:
                f = resp[0]
                rank.update({
                    "altura": f.get("height", ""),
                    "peso":    f.get("weight", ""),
                    "reach":   f.get("reach", ""),
                })
        p["rank"] = rank
        by_sport[sport_name].append(p)

    for lst in by_sport.values():
        lst.sort(key=lambda j: j["rank"]["edad"], reverse=True)

    return render_template("ranking.html", ranking=by_sport)



# ──────────────────────────────────────────────────────────────────────────────
# Endpoints AJAX / API

@app.get("/api/player-info/<name>")
@login_required
def api_player_info(name: str):
    sport = request.args.get("sport", default=0, type=int)
    pl    = _find_player(name)
    if not pl:
        return jsonify({"ok": False, "error": "Deportista no encontrado"}), 404
    svc = SERVICE_MAP.get(sport)
    if not svc:
        return jsonify({"ok": False, "error": "Deporte no soportado"}), 400
    try:
        if sport == 0:
            aid = pl["DeporteYHabilidades"].get("athlete_id") or None
            data = svc(name, athlete_id=aid)
        elif sport == 1:
            api_id  = int(request.args.get("id", 0)) or int(pl["DeporteYHabilidades"].get("athlete_id") or 0)
            season  = request.args.get("season", type=int) or pl.get("season")
            game_id = request.args.get("game", type=int) or pl.get("game_id")
            if not (api_id and season and game_id):
                return jsonify({"ok": False, "error": "Faltan filtros season o game_id"}), 400
            data = svc(api_id, season=season, game_id=game_id)
        elif sport in (2, 4):
            data = svc(name)
        elif sport == 3:
            data = svc(name, debug=False)
        return jsonify({"ok": True, "data": data})
    except LookupError as e:
        log.info("LookupError en player_info: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception as e:
        log.exception(e)
        abort(500)


@app.route("/precharge")
@login_required
def precharge():
    precharged = load_precharge()
    return render_template("precharge.html", players=precharged, sports=app.config["SPORTS_LIST"])


@app.route("/api/precharge/favorite/<pid>", methods=["POST"])
@login_required
def api_precharge_favorite(pid: str):
    pre_list = load_precharge()
    p = next((x for x in pre_list if x["DatosPersonales"]["id"] == pid), None)
    if not p:
        return jsonify(error="Deportista no encontrado"), 404
    favs = load_players()
    if any(x["DatosPersonales"]["id"] == pid for x in favs):
        return jsonify(error="Ya es favorito"), 400
    favs.append(p)
    save_players(favs)
    pre_list = [x for x in pre_list if x["DatosPersonales"]["id"] != pid]
    save_precharge(pre_list)
    return jsonify(success=True), 200


# ──────────────────────────────────────────────────────────────────────────────
# Warm-up thread (cache)
def _warm():
    while True:
        for p in load_players():
            try:
                _ = _stats_for_player(p)
            except Exception as e:
                log.warning("warm error: %s", e)
        time.sleep(6 * 3600)

threading.Thread(target=_warm, daemon=True).start()


# ──────────────────────────────────────────────────────────────────────────────
# Handlers de error
@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("errors/500.html"), 500


# ──────────────────────────────────────────────────────────────────────────────
# Registro de blueprints adicionales y ejecución
app.register_blueprint(posts_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=False
    )
