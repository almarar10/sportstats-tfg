# forms.py
"""
Formularios WTForms para registro de usuarios.
- RegisterForm: validaciones de campos y llenado dinámico de deportes.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.fields import EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class RegisterForm(FlaskForm):
    username   = StringField(
        "Usuario",
        validators=[DataRequired(), Length(min=3, max=40)]
    )
    email      = EmailField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=120)]
    )
    password   = PasswordField(
        "Contraseña",
        validators=[DataRequired(), Length(min=6)]
    )
    confirm    = PasswordField(
        "Repetir Contraseña",
        validators=[
            DataRequired(),
            EqualTo("password", message="Las contraseñas deben coincidir")
        ]
    )
    fav_sport  = SelectField("Deporte favorito", validators=[DataRequired()])
    submit     = SubmitField("Registrar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from flask import current_app
        sports_list = current_app.config.get("SPORTS_LIST", [])
        self.fav_sport.choices = [(str(i), name) for i, name in enumerate(sports_list)]
