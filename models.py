# models.py
"""
Definición de los modelos de datos para SportStats:
- User: datos de usuario y relaciones hacia posts y likes.
- Post: contenido de microblogging con contador de likes.
- Like: relación muchos-a-muchos implícita entre usuarios y posts.
"""
from datetime import datetime

from flask_login import UserMixin
from extensions   import db, bcrypt


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer,    primary_key=True)
    username   = db.Column(db.String(40), unique=True, nullable=False)
    email      = db.Column(db.String(120),unique=True, nullable=False)
    pw_hash    = db.Column(db.String(128),nullable=False)
    fav_sport  = db.Column(db.Integer,    default=0)
    created_at = db.Column(db.DateTime,   server_default=db.func.now())

    # Relaciones
    posts = db.relationship(
        "Post",
        back_populates="author",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    likes = db.relationship(
        "Like",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def set_password(self, raw: str) -> None:
        """Hashea y guarda la contraseña."""
        self.pw_hash = bcrypt.generate_password_hash(raw).decode()

    def check_pw(self, raw: str) -> bool:
        """Verifica la contraseña contra el hash."""
        return bcrypt.check_password_hash(self.pw_hash, raw)


class Post(db.Model):
    __tablename__ = "posts"

    id         = db.Column(db.Integer,  primary_key=True)
    author_id  = db.Column(db.Integer,  db.ForeignKey("users.id"), nullable=False)
    content    = db.Column(db.String(280), nullable=False)
    like_count = db.Column(db.Integer,  default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=True)
    edited     = db.Column(db.Boolean,  default=False, nullable=False)

    author = db.relationship("User", back_populates="posts")
    likes  = db.relationship("Like", back_populates="post", cascade="all, delete-orphan")


class Like(db.Model):
    __tablename__ = "likes"

    id         = db.Column(db.Integer, primary_key=True)
    post_id    = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("post_id", "user_id", name="ux_post_user"),
    )

    user = db.relationship("User", back_populates="likes")
    post = db.relationship("Post", back_populates="likes")
