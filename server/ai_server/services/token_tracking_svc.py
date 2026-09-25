from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from ai_server.config.config import app_config
from ai_server.config.constant import ADMIN_ROLE
from ai_server.dao.database import TokenUsage, get_async_session
from ai_server.dto.user_dto import UserDto
from ai_server.decorators.singleton import singleton
from ai_server.log.bot_factory_logger import BotFactoryLogger
from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError

logger = BotFactoryLogger()


@singleton
class TokenTrackingService:
    """Service pour traquer et gérer la consommation de tokens par utilisateur"""

    def __init__(self):
        self.logger = logger

    # Migrated to async: the only caller, LlmService's
    # TokenCountingCallback.on_llm_end (llm_svc.py), is itself now an
    # AsyncCallbackHandler -- LangChain's async callback manager awaits it
    # directly (no thread hop, see langchain_core.callbacks.manager.
    # _ahandle_event_for_handler's `if inspect.iscoroutinefunction(event)`
    # branch), so it can use get_async_session() like everything else
    # rag_svc.py's now-fully-async chain touches.
    async def record_token_usage(
        self,
        user_id: int,
        user_guest_id: int,
        bot_id: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        session_id: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> bool:
        """
        Enregistre l'utilisation de tokens dans la base de données

        Args:
            user_id: ID de l'utilisateur
            bot_id: ID du bot utilisé
            prompt_tokens: Nombre de tokens du prompt
            completion_tokens: Nombre de tokens de la réponse
            total_tokens: Nombre total de tokens
            session_id: ID de la session (optionnel)
            model_name: Nom du modèle utilisé (optionnel)

        Returns:
            bool: True si l'enregistrement a réussi, False sinon
        """
        session = get_async_session()
        try:
            token_usage = TokenUsage(
                user_id=user_id,
                user_guest_id=user_guest_id,
                bot_id=bot_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                session_id=session_id,
                model_name=model_name,
            )
            session.add(token_usage)
            await session.commit()

            self.logger.info(
                f"Token usage recorded: user_id={user_id} bot_id={bot_id} "
                f"session_id={session_id} model={model_name} "
                f"prompt={prompt_tokens} completion={completion_tokens} total={total_tokens}"
            )
            return True

        except SQLAlchemyError as e:
            self.logger.exception(
                f"Error recording token usage for user_id={user_id} bot_id={bot_id}: {e}"
            )
            await session.rollback()
            return False
        finally:
            await session.close()

    async def get_user_total_tokens(self, user_id: int) -> int:
        """
        Récupère le nombre total de tokens consommés par un utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            int: Nombre total de tokens consommés
        """
        session = get_async_session()
        try:
            result = await session.execute(
                select(func.sum(TokenUsage.total_tokens)).where(
                    TokenUsage.user_id == user_id
                )
            )
            total = result.scalar()

            self.logger.debug(f"get_user_total_tokens user_id={user_id} total={total or 0}")
            return total if total else 0

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting user total tokens for user_id={user_id}: {e}")
            return 0
        finally:
            await session.close()

    async def get_user_tokens_last_24h(self, user_id: int) -> int:
        """
        Récupère le nombre total de tokens consommés par un utilisateur depuis 24h

        Args:
            user_id: ID de l'utilisateur

        Returns:
            int: Nombre total de tokens consommés depuis 24h
        """
        session = get_async_session()
        try:
            # Calculer le timestamp d'il y a 24h

            result = await session.execute(
                select(func.sum(TokenUsage.total_tokens)).where(
                    TokenUsage.user_id == user_id,
                    TokenUsage.timestamp >= self.get_date_24h_ago(),
                )
            )
            total = result.scalar()

            self.logger.debug(f"get_user_tokens_last_24h user_id={user_id} total={total or 0}")
            return total if total else 0

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting user tokens last 24h for user_id={user_id}: {e}")
            return 0
        finally:
            await session.close()

    async def get_token_quota(self, user: UserDto) -> Dict:
        """
        Calcule le quota de tokens sur 24h glissantes d'un utilisateur
        (TOKEN_LIMIT_PER_USER_24H).

        Un guest est facturé sur le compte de son parent (cf.
        TokenCountingCallback.on_llm_end dans llm_svc.py) : le quota est
        donc celui du compte facturé, guests inclus.

        Returns:
            Dict {billed_user_id, limit_24h, used_24h, remaining_24h, exceeded}.
            limit_24h/remaining_24h valent None si aucune limite ne s'applique
            (limite désactivée ou Admin).
        """
        billed_user_id = user.parent_id if user.parent_id and user.parent_id > 0 else user.id
        used = await self.get_user_tokens_last_24h(billed_user_id)
        limit = app_config.TOKEN_LIMIT_PER_USER_24H
        if limit <= 0 or user.roles == ADMIN_ROLE:
            limit = None
        return {
            "billed_user_id": billed_user_id,
            "limit_24h": limit,
            "used_24h": int(used),
            "remaining_24h": None if limit is None else max(limit - int(used), 0),
            "exceeded": limit is not None and used >= limit,
        }

    async def get_user_stats_last_24h(
        self, user_id: int, include_records: bool = False, records_limit: int = 100
    ) -> Dict:
        """
        Récupère les statistiques détaillées de consommation de tokens d'un utilisateur depuis 24h

        Args:
            user_id: ID de l'utilisateur
            include_records: Si True, inclut les enregistrements individuels token_usage (par défaut False)
            records_limit: Nombre maximum d'enregistrements à retourner (par défaut 100)

        Returns:
            Dict contenant les statistiques détaillées de tokens pour les 24 dernières heures
            Si include_records=True, inclut aussi une clé 'records' avec les enregistrements individuels
        """
        # Calculer le timestamp d'il y a 24h
        time_24h_ago = self.get_date_24h_ago()
        time_now = datetime.now(timezone.utc)
        session = get_async_session()

        try:
            stats_result = await session.execute(
                select(
                    func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
                    func.sum(TokenUsage.completion_tokens).label(
                        "total_completion_tokens"
                    ),
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.count(TokenUsage.id).label("total_requests"),
                ).where(
                    TokenUsage.user_id == user_id, TokenUsage.timestamp >= time_24h_ago
                )
            )
            stats = stats_result.first()

            result = {
                "user_id": user_id,
                "period": "last_24h",
                "total_prompt_tokens": stats.total_prompt_tokens or 0,
                "total_completion_tokens": stats.total_completion_tokens or 0,
                "total_tokens": stats.total_tokens or 0,
                "total_requests": stats.total_requests or 0,
                "period_start": time_24h_ago.isoformat(),
                "period_end": time_now.isoformat(),
            }

            # Ajouter les enregistrements individuels si demandé
            if include_records:
                records_result = await session.execute(
                    select(TokenUsage)
                    .where(
                        TokenUsage.user_id == user_id,
                        TokenUsage.timestamp >= time_24h_ago,
                    )
                    .order_by(TokenUsage.id.desc())
                    .limit(records_limit)
                )
                records = records_result.scalars().all()

                result["records"] = [
                    {
                        "id": record.id,
                        "user_id": record.user_id,
                        "user_guest_id": record.user_guest_id,
                        "bot_id": record.bot_id,
                        "session_id": record.session_id,
                        "prompt_tokens": record.prompt_tokens,
                        "completion_tokens": record.completion_tokens,
                        "total_tokens": record.total_tokens,
                        "timestamp": record.timestamp,
                        "model_name": record.model_name,
                    }
                    for record in records
                ]

            self.logger.debug(
                f"get_user_stats_last_24h user_id={user_id} "
                f"total_tokens={result['total_tokens']} total_requests={result['total_requests']} "
                f"include_records={include_records}"
            )
            return result

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting user stats last 24h for user_id={user_id}: {e}")
            error_result = {
                "user_id": user_id,
                "period": "last_24h",
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_requests": 0,
                "period_start": time_24h_ago.isoformat(),
                "period_end": time_now.isoformat(),
            }
            if include_records:
                error_result["records"] = []
            return error_result
        finally:
            await session.close()

    async def get_user_token_stats(self, user_id: int) -> Dict:
        """
        Récupère les statistiques détaillées de consommation de tokens d'un utilisateur

        Args:
            user_id: ID de l'utilisateur

        Returns:
            Dict contenant les statistiques de tokens
        """
        session = get_async_session()
        try:
            stats_result = await session.execute(
                select(
                    func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
                    func.sum(TokenUsage.completion_tokens).label(
                        "total_completion_tokens"
                    ),
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.count(TokenUsage.id).label("total_requests"),
                ).where(TokenUsage.user_id == user_id)
            )
            stats = stats_result.first()

            return {
                "user_id": user_id,
                "total_prompt_tokens": stats.total_prompt_tokens or 0,
                "total_completion_tokens": stats.total_completion_tokens or 0,
                "total_tokens": stats.total_tokens or 0,
                "total_requests": stats.total_requests or 0,
            }

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting user token stats for user_id={user_id}: {e}")
            return {
                "user_id": user_id,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_requests": 0,
            }
        finally:
            await session.close()

    async def get_user_token_history(
        self, user_id: int, limit: int = 100, last_24h: bool = False
    ) -> List[Dict]:
        """
        Récupère l'historique de consommation de tokens d'un utilisateur

        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum d'enregistrements à retourner

        Returns:
            Liste de dictionnaires contenant l'historique
        """
        # Calculer le timestamp d'il y a 24h
        self.logger.debug(
            f"get_user_token_history user_id={user_id} limit={limit} last_24h={last_24h}"
        )
        session = get_async_session()
        try:
            stmt = select(TokenUsage)
            if last_24h:
                stmt = stmt.where(TokenUsage.timestamp >= self.get_date_24h_ago())
            stmt = stmt.order_by(TokenUsage.id.desc()).limit(limit)
            history = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "id": record.id,
                    "user_id": record.user_id,
                    "user_guest_id": record.user_guest_id,
                    "bot_id": record.bot_id,
                    "session_id": record.session_id,
                    "prompt_tokens": record.prompt_tokens,
                    "completion_tokens": record.completion_tokens,
                    "total_tokens": record.total_tokens,
                    "timestamp": record.timestamp,
                    "model_name": record.model_name,
                }
                for record in history
            ]

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting user token history for user_id={user_id}: {e}")
            return []
        finally:
            await session.close()

    async def get_bot_token_stats(self, bot_id: int) -> Dict:
        """
        Récupère les statistiques de consommation de tokens pour un bot

        Args:
            bot_id: ID du bot

        Returns:
            Dict contenant les statistiques de tokens du bot
        """
        session = get_async_session()
        try:
            stats_result = await session.execute(
                select(
                    func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
                    func.sum(TokenUsage.completion_tokens).label(
                        "total_completion_tokens"
                    ),
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.count(TokenUsage.id).label("total_requests"),
                    func.count(func.distinct(TokenUsage.user_id)).label("unique_users"),
                ).where(TokenUsage.bot_id == bot_id)
            )
            stats = stats_result.first()

            return {
                "bot_id": bot_id,
                "total_prompt_tokens": stats.total_prompt_tokens or 0,
                "total_completion_tokens": stats.total_completion_tokens or 0,
                "total_tokens": stats.total_tokens or 0,
                "total_requests": stats.total_requests or 0,
                "unique_users": stats.unique_users or 0,
            }

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting bot token stats for bot_id={bot_id}: {e}")
            return {
                "bot_id": bot_id,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_requests": 0,
                "unique_users": 0,
            }
        finally:
            await session.close()

    async def get_all_users_token_stats(self) -> List[Dict]:
        """
        Récupère les statistiques de consommation de tokens pour tous les utilisateurs

        Returns:
            Liste de dictionnaires contenant les statistiques par utilisateur
        """
        session = get_async_session()
        try:
            stats_result = await session.execute(
                select(
                    TokenUsage.user_id,
                    func.sum(TokenUsage.prompt_tokens).label("total_prompt_tokens"),
                    func.sum(TokenUsage.completion_tokens).label(
                        "total_completion_tokens"
                    ),
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.count(TokenUsage.id).label("total_requests"),
                )
                .group_by(TokenUsage.user_id)
                .order_by(func.sum(TokenUsage.total_tokens).desc())
            )
            stats = stats_result.all()

            result = [
                {
                    "user_id": stat.user_id,
                    "total_prompt_tokens": stat.total_prompt_tokens or 0,
                    "total_completion_tokens": stat.total_completion_tokens or 0,
                    "total_tokens": stat.total_tokens or 0,
                    "total_requests": stat.total_requests or 0,
                }
                for stat in stats
            ]
            self.logger.info(f"get_all_users_token_stats returned {len(result)} users")
            return result

        except SQLAlchemyError as e:
            self.logger.exception(f"Error getting all users token stats: {e}")
            return []
        finally:
            await session.close()

    def get_date_24h_ago(self) -> datetime:
        time_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        return time_24h_ago

    def get_date_30d_ago(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=30)

    async def get_admin_token_usage_summary(self, scope_user_id: Optional[int] = None) -> Dict:
        """
        Récupère, en 2 requêtes agrégées (pas de N+1), les tokens consommés
        sur 24h et 30j pour chaque compte (user_id) et chaque guest
        (user_guest_id).

        Un guest chatte toujours sous le user_id de son parent (cf.
        TokenCountingCallback.on_llm_end dans llm_svc.py, qui remonte
        user_id -> parent_id et pose user_guest_id = id du guest) : le total
        d'un compte inclut donc déjà ses guests, et scope_user_id == user_id
        suffit à restreindre les deux requêtes au périmètre d'un compte (lui
        + ses guests) sans avoir à connaître leurs ids à l'avance.

        Args:
            scope_user_id: si fourni, restreint aux lignes de ce compte --
                utilisé pour un caller non-admin qui ne doit voir que son
                propre périmètre. None (Admin) ne restreint rien.

        Returns:
            Dict avec deux mappings id -> {tokens_24h, tokens_30d}:
            {"accounts": {user_id: {...}}, "guests": {guest_id: {...}}}
        """
        since_30d = self.get_date_30d_ago()
        since_24h = self.get_date_24h_ago()
        tokens_24h_expr = func.sum(
            case((TokenUsage.timestamp >= since_24h, TokenUsage.total_tokens), else_=0)
        )
        session = get_async_session()

        try:
            account_stmt = select(
                TokenUsage.user_id,
                tokens_24h_expr.label("tokens_24h"),
                func.sum(TokenUsage.total_tokens).label("tokens_30d"),
            ).where(TokenUsage.timestamp >= since_30d)
            if scope_user_id is not None:
                account_stmt = account_stmt.where(TokenUsage.user_id == scope_user_id)
            account_stmt = account_stmt.group_by(TokenUsage.user_id)
            account_rows = (await session.execute(account_stmt)).all()

            guest_stmt = select(
                TokenUsage.user_guest_id,
                tokens_24h_expr.label("tokens_24h"),
                func.sum(TokenUsage.total_tokens).label("tokens_30d"),
            ).where(
                TokenUsage.timestamp >= since_30d,
                TokenUsage.user_guest_id.isnot(None),
                TokenUsage.user_guest_id != -1,
            )
            if scope_user_id is not None:
                guest_stmt = guest_stmt.where(TokenUsage.user_id == scope_user_id)
            guest_stmt = guest_stmt.group_by(TokenUsage.user_guest_id)
            guest_rows = (await session.execute(guest_stmt)).all()

            # The CASE-based tokens_24h sum comes back from PyMySQL as
            # Decimal (unlike a plain func.sum(int_column), which stays
            # int) -- Flask's JSON encoder serializes Decimal as a string
            # to avoid float precision loss, which would silently turn
            # tokens_24h into "42" instead of 42 for API consumers. Cast
            # both explicitly so the response is consistently numeric.
            result = {
                "accounts": {
                    row.user_id: {
                        "tokens_24h": int(row.tokens_24h or 0),
                        "tokens_30d": int(row.tokens_30d or 0),
                    }
                    for row in account_rows
                },
                "guests": {
                    row.user_guest_id: {
                        "tokens_24h": int(row.tokens_24h or 0),
                        "tokens_30d": int(row.tokens_30d or 0),
                    }
                    for row in guest_rows
                },
            }
            self.logger.info(
                f"get_admin_token_usage_summary scope_user_id={scope_user_id} "
                f"accounts={len(result['accounts'])} guests={len(result['guests'])}"
            )
            return result

        except SQLAlchemyError as e:
            self.logger.exception(
                f"Error getting admin token usage summary (scope_user_id={scope_user_id}): {e}"
            )
            return {"accounts": {}, "guests": {}}
        finally:
            await session.close()
