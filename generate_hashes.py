from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

password = "Secret123!"
for name in ["Almar", "Miguel", "Manuel"]:
    h = bcrypt.generate_password_hash(password).decode()
    print(name, "→", h)

