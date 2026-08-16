from functools import wraps
from ai_server.decorators.session_checker import session_checker
from flask import jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)


def role_required(roles):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            jwt_data = get_jwt()
            # print(f'jwt_data {jwt_data}')
            current_roles = jwt_data.get("roles", [])

            # Vérifie si l'utilisateur a au moins un des rôles requis
            if not any(role in current_roles for role in roles):
                return jsonify({"error": "Access denied"}), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper
