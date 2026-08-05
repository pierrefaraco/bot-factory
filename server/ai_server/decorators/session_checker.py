from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.exceptions.api_error import ApiError
from ai_server.services.authent_svc import AuthenticationService


def session_checker(function):
    """
    This decorator check the token and the Jwt:

    Jwt verification: This decorator is decorated with the flask decorator 'jwt_required', that check if the jwt token is valid.

    """

    logger = BotFactoryLogger()
    auth_svc = AuthenticationService()

    error_msg = "Session check error!"

    @jwt_required()
    @wraps(function)
    def alm_session_checker(*params, **kwargs):

        # Activate the following line to get rid of sessions !! :-)
        # return function(*params, **kwargs)

        try:
            identity = get_jwt_identity()
            if not (isinstance(identity, str) and identity.startswith("rag|")):
                logger.error("Session identity is not correct !")
                raise ApiError(error_msg, status_code=401)

            logger.info("the session is checked")
            if auth_svc.is_jwt_revoked():
                message = "The session is ended."
                logger.error(message)
                raise ApiError(message, status_code=401)
        except Exception as exc:
            logger.error(f"Session check exception: {exc}")
            raise ApiError(error_msg, status_code=401)
        return function(*params, **kwargs)

    return alm_session_checker
