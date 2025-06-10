**SportStats 🏟️ | Estadísticas + Microblogging en un solo lugar**

**SportStats** es una plataforma web que combina, en tiempo real, datos deportivos detallados (extraídos vía API‑SPORTS o scraping de World Athletics) con un micro‑feed al estilo X/Twitter. Incluye:

* **Motor de recomendación** basado en TF‑IDF + k‑NN
* **Catálogo semilla** de deportistas pre‑cargados
* **Interfaz responsive** con Bootstrap 5 y Lucide Icons
* **Publicación optimista** (optimistic UI), edición inline y likes

---

## ✨ Características principales

| Área                | Funcionalidad                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| **Autenticación**   | Registro/login con email único, contraseñas hash bcrypt, sesión gestionada con Flask‑Login.         |
| **Catálogo**        | `/precharge`: elenco pre‑cargado (players) con ⭐ para añadir a favoritos (`players.json`).          |
| **Gestión manual**  | Formulario WTForms para dar de alta/deportistas; campos dinámicos (athlete\_id, jersey, posición…). |
| **Estadísticas**    | Wrappers en `basket_api.py`, `football_api.py`, `wa_scraper.py`, `formula1_api.py`, `mma_api.py`.   |
| **Micro‑feed**      | Composer, optimistc UI, AJAX para likes, paginación «Cargar más» (`/api/posts`).                    |
| **Recomendaciones** | `train_recommender.py` entrena TF‑IDF + k‑NN; modelo en `recommender_model.joblib`.                 |
| **Errores**         | Plantillas personalizadas en `templates/errors/404.html` y `500.html`.                              |

---

## 🏗️ Estructura del proyecto

```
RmTop/
├── app.py               # Punto de entrada: Flask, blueprints, rutas y servidor
├── .env                 # Configuración sensible (SECRET_KEY, API_KEYS, MySQL)
├── requirements.txt     # Dependencias Python
├── generate_hashes.py   # Script auxiliar para generar hash bcrypt de ejemplo
├── train_recommender.py # Entrena y guarda modelo de recomendación
├── players.json         # Deportistas favoritos (persistencia local JSON)
├── precharge_players.json # Catálogo semilla de deportistas
├── ath_player_cache.json  # Cache de Athlete ID (World Athletics)
├── extensions.py        # Instancia de SQLAlchemy, Bcrypt
├── models.py            # Definición de User, Post, Like
├── routes.py            # Blueprint de micro‑feed (posts, likes, recomendaciones)
├── basket_api.py        # Wrapper NBA (API‑Sports)
├── football_api.py      # Wrapper Fútbol (API‑Sports)
├── wa_scraper.py        # Scraper World Athletics
├── formula1_api.py      # Wrapper F1 (API‑Sports)
├── mma_api.py           # Wrapper MMA (API‑Sports)
├── forms.py             # WTForms (register, login)
├── helpers/
│   ├── cache.py         # Caching JSON con TTL
│   └── session.py       # Cliente HTTP con reintentos y límite de llamadas
├── static/
│   ├── css/
│   │   ├── app.css      # Estilos globales
│   │   └── posts.css    # Estilos específicos del feed
│   └── js/
│       └── posts.js     # Lógica AJAX del micro‑feed
└── templates/
    ├── layout.html      # Base HTML con navbar
    ├── index.html       # Portada tras login
    ├── login.html       # Login con AJAX
    ├── register_user.html # Registro de cuenta
    ├── register.html    # Alta manual de deportistas
    ├── users.html       # Listado collapsible de deportistas
    ├── player_detail.html # Panel estadístico detallado (AJAX + servidor)
    ├── posts.html       # Vista central del feed
    ├── precharge.html   # Catálogo pre‑cargado
    ├── ranking.html     # Ranking por disciplina (DataTables)
    └── errors/          # Errores 404, 500
        ├── 404.html
        └── 500.html
```

---

## ⚙️ Instalación y ejecución (desarrollo)

1. Clona el repositorio:

   ```bash
   git clone https://github.com/almarar10/sportstats-tfg.git
   cd sportstats-tfg
   ```
2. Crea y activa un entorno virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```
4. Copia y configura variables de entorno:

   ```bash
   cp .env.example .env
   # Edita .env: SECRET_KEY, APISPORTS_KEY, MYSQL_* etc.
   ```
5. Inicializa la base de datos:

   ```bash
   flask db upgrade
   ```
6. Entrena el modelo de recomendaciones (\~30 s):

   ```bash
   python train_recommender.py
   ```
7. Arranca el servidor en modo debug:

   ```bash
   flask run --debug
   # Visitar http://127.0.0.1:5000
   ```

---

## 🚀 Despliegue en producción

* Configura un WSGI (Gunicorn) tras Nginx:

  ```bash
  gunicorn -w 4 -b 0.0.0.0:8000 app:app
  ```
* Usa HTTPS (Let’s Encrypt)
* Variables de entorno: `FLASK_ENV=production`
* Considera Redis para cache y sesiones si escalas horizontalmente.

---

## 📚 Créditos y licencia

Trabajo Fin de Grado — Grado en Ingeniería Informática (UPSA, 2024/25)

Autor: Almar Ramos Curto — todos los derechos reservados.
Uso académico exclusivamente; para otro tipo de licencia, contactar con el autor.

> “El deporte es la estadística que se vive; SportStats lo hace conversación.”
