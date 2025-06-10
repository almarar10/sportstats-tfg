# RmTop/routes.py
"""
Blueprint 'posts': gestiona la página de feed, la API REST de posts, likes y recomendaciones.
"""
import joblib
import numpy as np
from datetime import datetime

from flask import (
    Blueprint, request, jsonify,
    render_template, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import case

from extensions import db
from models     import Post, Like

bp = Blueprint('posts', __name__)


@bp.route('/posts', methods=['GET'])
@login_required
def posts_page():
    """
    Renderiza la vista principal del feed con microblogging.
    """
    sports = current_app.config['SPORTS_LIST']
    return render_template('posts.html', user=current_user, sports=sports)


@bp.route('/api/posts', methods=['GET'])
@login_required
def api_get_posts():
    """
    Devuelve JSON con un listado paginado de posts ordenados por:
      - updated_at desc (si editado)
      - created_at desc (si no editado)
    Incluye información de like_count y si el usuario actual ya ha dado like.
    Parámetro opcional 'cursor' (ISO timestamp) para paginar.
    """
    cursor = request.args.get('cursor')
    order_col = case(
        (Post.edited == True, Post.updated_at),
        else_=Post.created_at
    ).desc()

    query = Post.query.order_by(order_col)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            return jsonify(error="Cursor inválido"), 400
        query = query.filter(
            case(
                (Post.edited == True, Post.updated_at),
                else_=Post.created_at
            ) < cursor_dt
        )

    POSTS_PER_PAGE = 10
    posts = query.limit(POSTS_PER_PAGE).all()

    data = []
    for p in posts:
        liked = Like.query.filter_by(
            post_id=p.id, user_id=current_user.id
        ).first() is not None

        data.append({
            "id":         p.id,
            "author":     p.author.username,
            "content":    p.content,
            "likes":      p.like_count,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "fav_sport":  p.author.fav_sport,
            "liked":      liked,
            "edited":     p.edited
        })

    return jsonify(posts=data)


@bp.route('/api/posts', methods=['POST'])
@login_required
def api_create_post():
    """
    Crea un nuevo post. Espera un JSON { content: str }.
    Valida longitud y no vacío.
    """
    content = request.json.get('content', '').strip()
    if not content or len(content) > 280:
        return jsonify(error='Contenido inválido'), 400

    p = Post(author_id=current_user.id, content=content)
    db.session.add(p)
    db.session.commit()

    fav_emoji = "⚽🏀🏃🏁🥊"[current_user.fav_sport]
    return jsonify(
        id=p.id,
        content=p.content,
        author=current_user.username,
        likes=0,
        created_at=p.created_at.isoformat(),
        fav_emoji=fav_emoji
    ), 201


@bp.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def api_toggle_like(post_id):
    """
    Alterna el like del usuario actual sobre el post indicado.
    Devuelve {'liked': bool, 'likes': int}.
    """
    p = Post.query.get_or_404(post_id)
    existing = Like.query.filter_by(
        post_id=post_id, user_id=current_user.id
    ).first()

    if existing:
        db.session.delete(existing)
        p.like_count -= 1
        liked = False
    else:
        db.session.add(Like(post_id=post_id, user_id=current_user.id))
        p.like_count += 1
        liked = True

    db.session.commit()
    return jsonify(liked=liked, likes=p.like_count)


@bp.route('/api/posts/<int:post_id>', methods=['PUT'])
@login_required
def api_edit_post(post_id):
    """
    Edita el contenido de un post. Sólo el autor puede editar.
    Marca 'edited' y actualiza 'updated_at'.
    """
    p = Post.query.get_or_404(post_id)
    if p.author_id != current_user.id:
        return jsonify(error='No autorizado'), 403

    new_body = (request.get_json() or {}).get('content', '').strip()
    if not new_body or len(new_body) > 280:
        return jsonify(error='Contenido inválido'), 400

    p.content    = new_body
    p.edited     = True
    p.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "id":         p.id,
        "content":    p.content,
        "edited":     p.edited,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat()
    })


@bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def api_delete_post(post_id):
    """
    Elimina un post propio. Sólo el autor puede borrar.
    """
    p = Post.query.get_or_404(post_id)
    if p.author_id != current_user.id:
        return jsonify(error='No autorizado'), 403

    db.session.delete(p)
    db.session.commit()
    return jsonify(success=True)


@bp.route('/api/recommendations', methods=['GET'])
@login_required
def api_get_recommendations():
    """
    Devuelve posts sugeridos usando TF-IDF + k-NN.
    Parámetros opcionales: limit, offset.
    """
    limit  = request.args.get('limit',  default=5, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Carga modelo entrenado
    model      = joblib.load('recommender_model.joblib')
    vectorizer = model['vectorizer']
    knn        = model['nn_index']
    posts_df   = model['posts_df']

    # Perfil de usuario: propias y liked
    user_posts  = {p.id for p in Post.query.filter_by(author_id=current_user.id)}
    liked_posts = {lk.post_id for lk in Like.query.filter_by(user_id=current_user.id)}

    # Construye vector medio de likes
    id_to_idx = {int(pid): idx for idx, pid in enumerate(posts_df['id'])}
    liked_idxs = [id_to_idx[pid] for pid in liked_posts if pid in id_to_idx]
    user_vec = None
    if liked_idxs:
        liked_X = knn._fit_X[liked_idxs]
        user_vec = liked_X.mean(axis=0)

    # Mezcla interés por deporte favorito
    fav = current_user.fav_sport
    fav_vec = vectorizer.transform([str(fav)]).toarray()
    if user_vec is None:
        user_vec = fav_vec
    else:
        user_vec = (np.asarray(user_vec) + fav_vec) / 2

    # Fallback: posts más recientes si no hay perfil
    if user_vec is None or user_vec.size == 0:
        all_ids = [
            p.id for p in Post.query.order_by(Post.created_at.desc()).all()
            if p.id not in (user_posts | liked_posts)
        ]
    else:
        user_vec = user_vec.reshape(1, -1)
        k = min(10, knn._fit_X.shape[0])
        dists, idxs = knn.kneighbors(user_vec, n_neighbors=k)
        candidate_ids = [int(posts_df['id'].iloc[i]) for i in idxs.flatten()]
        all_ids = [pid for pid in candidate_ids if pid not in user_posts | liked_posts]

    page_ids = all_ids[offset: offset + limit]
    if not page_ids:
        return jsonify(posts=[])

    recs = Post.query.filter(Post.id.in_(page_ids)).all()
    recs.sort(key=lambda p: page_ids.index(p.id))

    return jsonify(posts=[
        {
            "id":         p.id,
            "author":     p.author.username,
            "content":    p.content,
            "created_at": p.created_at.isoformat(),
            "likes":      p.like_count,
            "fav_sport":  p.author.fav_sport,
            "edited":     p.edited
        }
        for p in recs
    ])
