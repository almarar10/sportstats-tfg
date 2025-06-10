# SportStats 🏟️ | Estadísticas + Microblogging en un solo lugar

**SportStats** es una plataforma web que integra, en tiempo real,  
*datos detallados de deportistas* (extraídos vía API-SPORTS o *scraping* de World Athletics) con un **micro-feed** al estilo X/Twitter.  
Incluye un motor de recomendación TF-IDF + k-NN, un catálogo semilla de atletas “pre-cargados” y una interfaz moderna basada en Bootstrap 5.

---

## ✨ Características principales

| Área | Funcionalidad |
|------|---------------|
| **Auth** | Registro y login con e-mail único, hash *bcrypt*, gestión de sesión vía *Flask-Login*. |
| **Catálogo** | Vista **/precharge** con 5–6 atletas por deporte listos para marcar ⭐; la selección se copia a `players.json` sin recarga. |
| **Gestión manual** | Formulario WTForms para crear nuevos deportistas (campos dinámicos: `athlete_id` en atletismo/NBA, `jersey` en NBA/Fútbol/F1). |
| **Estadísticas** | Wrappers:<br>• `football_api.py` (API-SPORTS, fallback multi-liga)<br>• `wa_scraper.py` (World Athletics)<br>• `basket_api.py`, `formula1_api.py`, `mma_api.py`.<br>Resultados cacheados (Redis) → carga media 1 ,7 s. |
| **Micro-feed** | Publicación instantánea (*optimistic UI*), edición inline, likes, paginación AJAX «Cargar más». |
| **Recomendaciones** | TF-IDF sobre posts + vector de deporte favorito; modelo entrenado con `train_recommender.py` y guardado vía *joblib*. |
| **Errores** | Plantillas 404 y 500 personalizadas ubicadas en `templates/errors/`. |

---

## 🏗️ Estructura del proyecto

sportstats/
├── app.py # Bootstrap Flask + blueprints
├── config.py # Carga .env, clases Config
├── requirements.txt
├── train_recommender.py # (re)entrena TF-IDF + k-NN
├── precharge_players.json
├── players.json
├── app/
├── init.py # create_app(), SQLAlchemy, LoginMgr, Redis cache
├── models.py # User, Post, Like, Player
├── services/
│ ├── football_api.py # API-SPORTS wrapper
│ ├── wa_scraper.py # Scraping World Athletics
│ ├── basket_api.py
│ ├── formula1_api.py
│ ├── mma_api.py
│ └── recommender.py
├── auth/ # Blueprint autenticación
├── main/ # Blueprint feed, stats, precharge, ranking…
├── templates/
│ ├── layout.html
│ ├── index.html
│ ├── errors/{404.html,500.html}
│ └── … (posts, ranking, precharge, etc.)
└── static/{css,js,imgs}



---

## ⚙️ Puesta en marcha (modo desarrollo)

```bash
git clone https://github.com/<tu-usuario>/sportstats.git
cd sportstats
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copia y ajusta variables
cp .env.example .env         # edita SECRET_KEY, APISPORTS_KEY, credenciales MySQL …

# Inicializa base de datos
flask db upgrade             # o `python -m flask db upgrade`

# Entrena recomendaciones iniciales (≈30 s)
python train_recommender.py

# Lanza el servidor
flask run --debug            # http://127.0.0.1:5000

👩‍💻 Uso básico
Registro → Login
Selecciona deporte favorito; influirá en las primeras sugerencias.

Añadir deportistas
• Nuevo deportista → Formulario manual o
• … → Deportistas pre-cargados y pulsa ⭐ para moverlo al listado personal.

Consultar estadísticas
Menú Ranking o clic sobre un atleta → panel detallado con datos de la API correspondiente.

Micro-blogging
Escribe en «¿Qué está pasando?» → Postear; los demás usuarios pueden Me gusta (sin duplicados).

Re-entrenar recomendaciones
Cada cierto tiempo: python train_recommender.py y reinicia Gunicorn/Flask.

🔧 Mantenimiento rápido
Tarea	Comando	Periodicidad
Re-entrenar modelo	python train_recommender.py	mensual / tras oleada de posts
Vaciar caché API	redis-cli FLUSHDB	cuando detectes datos obsoletos
Renovar API key	editar .env y reiniciar servicio	al agotar cuota
Backup DB (MySQL)	mysqldump -u… sportstats > dump.sql	según política IT

🚀 Despliegue en producción
Gunicorn detrás de Nginx (gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()").

FLASK_ENV=production, SECRET_KEY robusto.

HTTPS obligatorio (Let’s Encrypt).

Logs y workers supervisados con systemd o supervisor.

Para escalado horizontal, habilita Redis como backend de sesión y cache.

📚 Créditos y licencia
Trabajo Fin de Grado – Grado en Ingeniería Informática
Universidad Pontificia de Salamanca, curso 2024/25.

Autor: Almar Ramos Curto — todos los derechos reservados.
Uso exclusivamente académico; para otro tipo de licencia contactar con el autor.

“El deporte es la estadística que se vive; SportStats lo hace conversación.”