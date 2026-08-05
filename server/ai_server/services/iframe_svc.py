from ai_server.dao.database import IFrame
from ai_server.dto.iframe_dto import IFrameDto
from ai_server.dao.database import db


class IFrameSvc:
    def get_iframe_by_bot_id_and_key(self, bot_id, key) -> IFrameDto:
        iframe = IFrame.query.filter_by(bot_id=bot_id, key=key).first()
        return IFrameDto(iframe.id, iframe.bot_id, iframe.key, iframe.allowed_origins)

    def register_iframe(self, bot_id: int, key: str, allowed_origin: str) -> bool:
        """
        Register a user with specific parameters.

        Args:
        bot_id: bot_id avaiable on iframe
        key: key of the IFrame
        allowed_origins: Domain with the Iframe


        Returns:
        True

        Raises:
        ServiceError: When IFrameDto registration fails
        """

        iframe = IFrame(bot_id, key, allowed_origin)
        db.session.add(iframe)
        db.session.commit()

        return True
