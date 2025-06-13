# SportStats 🏟️ | Real‑Time Sports Data & Microblogging in One Place

**SportStats** is an open‑source Flask web application that seamlessly integrates real‑time sports statistics (via API‑SPORTS or World Athletics scraping) with a Twitter‑style micro‑feed. Built with modular blueprints, Redis caching, and a TF‑IDF + k‑NN recommendation engine, SportStats delivers a performant, responsive experience for fans and analysts alike.

---

## ✨ Core Features

| Component           | Description                                                                                                                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Authentication**  | Secure registration & login (unique email), Flask‑Login sessions, bcrypt‑hashed passwords.                                                                 |
| **Athlete Catalog** | `/precharge` seeds athletes with “⭐” favorites; dynamic manual entry form with WTForms.                                                                    |
| **Statistics API**  | Service wrappers:                                                                                                                                          |
|                     | • `basket_api.py` (NBA, API‑Sports)                                                                                                                        |
|                     | • `football_api.py` (Football, API‑Sports)                                                                                                                 |
|                     | • `wa_scraper.py` (Track & Field, World Athletics)                                                                                                         |
|                     | • `formula1_api.py` (F1, API‑Sports)                                                                                                                       |
|                     | • `mma_api.py` (MMA, API‑Sports)                                                                                                                           |
| **Micro‑Feed**      | Composer with optimistic UI (draft & replay), inline edit/delete, AJAX likes & pagination.                                                                 |
| **Recommendations** | Offline training script (`train_recommender.py`): Spanish stop‑words TF‑IDF → k‑NN via `NearestNeighbors`; model serialized in `recommender_model.joblib`. |
| **Caching**         | Redis for API response caching (15‑min TTL) + local disk cache with TTL for HTTP calls.                                                                    |
| **Error Handling**  | Custom 404/500 templates; API error fallbacks with degraded UI indicators.                                                                                 |

---

## 📐 Architecture & Diagrams

1. **High‑Level Architecture**

   ```mermaid
   flowchart LR
     Client-->Nginx/Gunicorn-->Flask App
     Flask App-->Blueprints
     subgraph Services
       DB[(MySQL)]
       Redis(Cache)
       FAISS[Index]
       API_Sports
       WorldAthletics
     end
     Flask App-->DB
     Flask App-->Redis
     Flask App-->FAISS
     Flask App-->API_Sports
     Flask App-->WorldAthletics
   ```

2. **Data Model (ER Diagram)**

   ```mermaid
   erDiagram
     users ||--o{ posts : creates
     users ||--o{ likes : gives
     posts ||--o{ likes : receives
     users {
       int id PK
       string username
       string email
       string pw_hash
       int fav_sport
     }
     posts {
       int id PK
       int author_id FK
       string content
       int like_count
       bool edited
     }
     likes {
       int id PK
       int user_id FK
       int post_id FK
     }
   ```

3. **Recommendation Pipeline**

   * **Data Extraction:**   SQLAlchemy → pandas DataFrame
   * **Preprocessing:**     NLTK Spanish stop‑words, lowercase, tokenizer
   * **Vectorization:**     `TfidfVectorizer(max_features=5000)`
   * **Indexing:**          `NearestNeighbors(metric='cosine', algorithm='brute')`
   * **Runtime Query:**     Average liked vectors + fav\_sport embedding → k‑NN search → filter out own/liked posts.

---

## 🏗️ Project Structure

```text
RmTop/
├── app.py                   # Flask app factory & route registration
├── config.py                # Config classes & .env loader
├── extensions.py            # SQLAlchemy, Bcrypt, Flask-Login, Redis
├── models.py                # User, Post, Like ORM definitions
├── routes/
│   ├── auth.py              # register_user, login, logout
│   ├── players.py           # CRUD & detail views
│   └── posts.py             # micro‑feed API & page
├── services/
│   ├── basketball.py        # NBA API wrapper
│   ├── football.py          # Football API wrapper
│   ├── athletics.py         # World Athletics scraper
│   ├── formula1.py          # F1 API wrapper
│   └── mma.py               # MMA API wrapper
├── helpers/
│   ├── cache.py             # Disk cache TTL
│   └── session.py           # HTTP retries & rate limits
├── train_recommender.py     # offline training script
├── recommender_model.joblib # persisted recommendation model
├── requirements.txt         # pip dependencies
├── players.json             # user favorites
├── precharge_players.json   # seed catalog
├── static/
│   ├── css/
│   │   ├── app.css          # global theming & responsive
│   │   └── posts.css        # micro‑feed styles
│   └── js/
│       └── posts.js         # feed AJAX logic
└── templates/
    ├── base.html            # layout with navbar
    ├── auth/
    │   ├── login.html
    │   └── register_user.html
    ├── players/
    │   ├── list.html
    │   ├── detail.html
    │   └── form.html
    ├── posts.html
    ├── precharge.html
    ├── ranking.html
    └── errors/
        ├── 404.html
        └── 500.html
```

---

## ⚙️ Installation & Development

```bash
# Clone & navigate
git clone https://github.com/almarar10/sportstats-tfg.git
cd sportstats-tfg

# Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Env Variables
cp .env.example .env
# Edit .env: SECRET_KEY, APISPORTS_KEY, MYSQL_*...

# Database Migrations
flask db upgrade

# Train Model (~30s)
python train_recommender.py

# Start Dev Server
env FLASK_ENV=development flask run
```

---

## 🚀 Production Deployment

```bash
# Gunicorn + Nginx
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

* Use HTTPS (Let's Encrypt)
* Set `FLASK_ENV=production`
* Consider Redis for sessions & caching at scale

---

## 📚 Credits & License

**Final Degree Project** — B.Sc. in Computer Engineering (UPSA, 2024/25)
**Author:** Almar Ramos Curto — All rights reserved.
Non‑academic use requires contacting the author.

> *“Sport is the statistics you live; SportStats makes it a conversation.”*
