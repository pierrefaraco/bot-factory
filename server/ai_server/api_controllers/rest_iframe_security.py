"""Context management REST API Controller"""

from functools import wraps
import json
import secrets
import hashlib
import hmac
from ai_server.services.authent_svc import AuthenticationService
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from marshmallow import Schema, fields, ValidationError
from ai_server.exceptions.api_error import ApiError
from ai_server.log.app_logger import AppLogger
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.template_svc import TemplateSvc
from ai_server.dao.database import db, User, ROOT_CHAPTER_ID
from ai_server.decorators.role_required import role_required
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.config.config import flask_config
from datetime import datetime, timedelta

CONTROLLER_NAME = "iframe"
CONTROLLER_PATH = "/iframe"

bp = Blueprint(CONTROLLER_NAME, __name__)

csrf_tokens = {}
iframe_sessions = {}
auth_svc = AuthenticationService()


# Domaines autorisés pour l'iframe
ALLOWED_ORIGINS = ["https://virtualfred.com:445", "https://virtualfred.com:445/"]


def verify_iframe_origin():
    """Décorateur pour vérifier l'origine de l'iframe"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            # Vérifier l'origine
            if origin not in ALLOWED_ORIGINS:
                return jsonify({"error": "Origin non autorisée"}), 403

            # Vérifier le referer pour s'assurer que la requête vient bien de notre domaine
            if referer:
                allowed_referer = any(
                    referer.startswith(allowed) for allowed in ALLOWED_ORIGINS
                )
                if not allowed_referer:
                    return jsonify({"error": "Referer non autorisé"}), 403

            # Vérifier le token X-Frame-Token personnalisé
            frame_token = request.headers.get("X-Frame-Token")
            if not frame_token or not verify_frame_token(frame_token):
                return jsonify({"error": "Token iframe invalide"}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def verify_frame_token(token):
    """Vérifie la validité du token de l'iframe"""
    # Vérifier dans notre stockage de sessions iframe
    for session_id, session_data in iframe_sessions.items():
        if session_data.get("frame_token") == token:
            # Vérifier l'expiration
            if datetime.utcnow() < session_data["expires"]:
                return True
    return False


@bp.route(f"{CONTROLLER_PATH}/init", methods=["POST"])
def init_iframe():
    """
    Initialise une session iframe sécurisée
    Cette route est appelée par le parent qui héberge l'iframe
    """
    data = request.json
    user_id = data.get("user_id")

    # Vérifier l'authentification du parent (vous pouvez ajouter votre logique ici)
    iframe_key = data.get("iframe_key")
    if not iframe_key:
        return jsonify({"error": "No iframe key"}), 401

    # Créer une session iframe
    iframe_token = generate_iframe_token(user_id)
    csrf_token = secrets.token_urlsafe(32)

    session_id = secrets.token_urlsafe(32)
    iframe_sessions[session_id] = {
        "user_id": user_id,
        "frame_token": iframe_token,
        "csrf_token": csrf_token,
        "created_at": datetime.utcnow(),
        "expires": datetime.utcnow() + timedelta(hours=1),
    }

    # Créer un JWT pour l'iframe
    access_token = auth_svc.login_with_iframe_key(
        iframe_key, session_id, user_id=user_id
    )

    response = jsonify(
        {
            "iframe_token": iframe_token,
            "csrf_token": csrf_token,
            "session_id": session_id,
            "access_token": access_token,
        }
    )

    # Définir un cookie sécurisé pour la session iframe
    response.set_cookie(
        "iframe_session",
        session_id,
        secure=True,
        httponly=True,
        samesite="None",
        max_age=3600,
    )

    return response


def generate_iframe_token(user_id):
    """Génère un token unique pour l'iframe"""
    token_data = f"{user_id}:{datetime.utcnow().timestamp()}:{secrets.token_hex(16)}"
    return hashlib.sha256(token_data.encode()).hexdigest()


@bp.route(f"{CONTROLLER_PATH}/authenticate", methods=["POST"])
@verify_iframe_origin()
def authenticate_iframe():
    """
    Authentifie automatiquement l'iframe
    """
    data = request.json
    iframe_key = data.get("iframe_key")
    csrf_token = data.get("csrf_token")

    # Vérifier le token CSRF
    session_id = request.cookies.get("iframe_session")
    if not session_id or session_id not in iframe_sessions:
        return jsonify({"error": "Session invalide"}), 401

    session_data = iframe_sessions[session_id]
    if session_data["csrf_token"] != csrf_token:
        return jsonify({"error": "Token CSRF invalide"}), 403

    # Créer un nouveau token d'accès pour cette session
    access_token = auth_svc.build_iframe_session_token(
        session_data["user_id"],
        session_id,
    )

    return jsonify(
        {
            "access_token": access_token,
            "user_id": session_data["user_id"],
            "expires_in": 3600,
        }
    )


def generate_iframe_signature(data):
    """Génère une signature HMAC pour valider l'intégrité"""

    secret = flask_config.SECRET_KEY.encode()
    message = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return signature


@bp.route(f"{CONTROLLER_PATH}/verify-signature", methods=["POST"])
@verify_iframe_origin()
def verify_signature():
    """Vérifie la signature de l'iframe pour s'assurer qu'elle n'a pas été modifiée"""
    data = request.json
    provided_signature = data.pop("signature", None)

    if not provided_signature:
        return jsonify({"error": "Signature manquante"}), 400

    expected_signature = generate_iframe_signature(data)

    if not hmac.compare_digest(provided_signature, expected_signature):
        return jsonify(
            {
                "error": "Signature invalide",
                "provided_signature": provided_signature,
                "expected_signature": expected_signature,
            }
        ), 403

    return jsonify({"valid": True})
