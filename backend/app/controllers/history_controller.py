from flask import request
from flask_jwt_extended import get_jwt_identity
from app.middleware.auth_middleware import require_auth
from app.models.analysis_model import AnalysisModel
from app.utils.response_helpers import success_response, error_response
import logging

logger = logging.getLogger(__name__)


class HistoryController:

    @staticmethod
    @require_auth
    def get_history():
        user_id = get_jwt_identity()
        try:
            limit = min(int(request.args.get('limit', 20)), 100)
            skip = int(request.args.get('skip', 0))
            history = AnalysisModel.get_user_history(user_id, limit=limit, skip=skip)
            return success_response(data={'history': history, 'count': len(history)})
        except Exception as e:
            logger.error(f"Get history error: {e}")
            return error_response('Failed to retrieve history', 500)

    @staticmethod
    @require_auth
    def get_one(analysis_id: str):
        user_id = get_jwt_identity()
        try:
            record = AnalysisModel.get_analysis_by_id(analysis_id, user_id)
            if not record:
                return error_response('Analysis not found or access denied', 404)
            return success_response(data=record)
        except Exception as e:
            logger.error(f"Get analysis error: {e}")
            return error_response('Failed to retrieve analysis', 500)

    @staticmethod
    @require_auth
    def delete_one(analysis_id: str):
        user_id = get_jwt_identity()
        try:
            deleted = AnalysisModel.delete_analysis(analysis_id, user_id)
            if not deleted:
                return error_response('Analysis not found or access denied', 404)
            return success_response(message='Analysis deleted successfully')
        except Exception as e:
            logger.error(f"Delete analysis error: {e}")
            return error_response('Failed to delete analysis', 500)
