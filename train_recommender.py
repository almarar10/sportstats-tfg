# train_recommender.py

import os
import joblib
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from nltk.corpus import stopwords

# 1) Cargar variables de entorno
load_dotenv()

# 2) Ajustar URI de la base de datos (igual que en app.py)
DB_URI = (
    f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASS')}"
    f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}/"
    f"{os.getenv('MYSQL_DB', 'sportstats')}?charset=utf8mb4"
)
engine = create_engine(DB_URI)

# 3) Leer todos los posts con sus metadatos
df = pd.read_sql("""
    SELECT p.id, p.content, p.created_at, p.like_count,
           u.fav_sport
      FROM posts p
      JOIN users u ON u.id = p.author_id
""", engine)

# 4) Preparar lista de stop-words en español
#    (asegúrate de haber hecho: python -m nltk.downloader stopwords)
spanish_stop = stopwords.words('spanish')

# 5) Configurar TF-IDF
vectorizer = TfidfVectorizer(
    stop_words=spanish_stop,
    max_features=5000,
    ngram_range=(1,1)
)

# 6) Generar matriz TF-IDF de los contenidos
tfidf_matrix = vectorizer.fit_transform(df['content'])

# 7) Entrenar NearestNeighbors con métrica coseno + brute force
nn = NearestNeighbors(metric='cosine', algorithm='brute')
nn.fit(tfidf_matrix)

# 8) Persistir todo en un único objeto
model = {
    'vectorizer': vectorizer,
    'nn_index':   nn,
    'posts_df':   df[['id','created_at','like_count','fav_sport']],
    'tfidf':      tfidf_matrix
}

joblib.dump(model, 'recommender_model.joblib')
print(f"[{datetime.now()}] Modelo entrenado y guardado.")
