from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity
from app.models.user_model import UserModel
from app.middleware.auth_middleware import require_auth
from app.utils.validators import validate_email, validate_password, validate_name
from app.utils.response_helpers import success_response, error_response
from pymongo.errors import DuplicateKeyError
import logging

logger = logging.getLogger(__name__)


class AuthController:

    @staticmethod
    def register():
        data = request.get_json(silent=True)
        if not data:
            return error_response('Request body must be JSON', 400)

        name = str(data.get('name', '')).strip()
        email = str(data.get('email', '')).strip()
        password = str(data.get('password', ''))

        if not validate_name(name):
            return error_response('Name must be between 2 and 100 characters', 400)
        if not validate_email(email):
            return error_response('Invalid email address', 400)
        valid_pw, pw_msg = validate_password(password)
        if not valid_pw:
            return error_response(pw_msg, 400)

        try:
            user = UserModel.create_user(name, email, password)
            token = create_access_token(identity=str(user['_id']))
            return success_response(
                data={
                    'token': token,
                    'user': {
                        'id': str(user['_id']),
                        'name': user['name'],
                        'email': user['email']
                    }
                },
                message='Account created successfully',
                status_code=201
            )
        except DuplicateKeyError:
            return error_response('An account with this email already exists', 409)
        except ConnectionError as e:
            logger.error(f"DB connection error on register: {e}")
            return error_response(
                'Cannot connect to database. Make sure MongoDB is running and MONGO_URI is set correctly.',
                503
            )
        except Exception as e:
            logger.error(f"Register error: {e}", exc_info=True)
            return error_response('Registration failed. Please try again.', 500)

    @staticmethod
    def login():
        data = request.get_json(silent=True)
        if not data:
            return error_response('Request body must be JSON', 400)

        email = str(data.get('email', '')).strip()
        password = str(data.get('password', ''))

        if not email or not password:
            return error_response('Email and password are required', 400)

        try:
            user = UserModel.find_by_email(email)
            if not user or not UserModel.verify_password(password, user['password_hash']):
                return error_response('Invalid email or password', 401)

            token = create_access_token(identity=str(user['_id']))
            return success_response(
                data={
                    'token': token,
                    'user': {
                        'id': str(user['_id']),
                        'name': user['name'],
                        'email': user['email']
                    }
                },
                message='Login successful'
            )
        except ConnectionError as e:
            logger.error(f"DB connection error on login: {e}")
            return error_response(
                'Cannot connect to database. Make sure MongoDB is running.',
                503
            )
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return error_response('Login failed. Please try again.', 500)

    @staticmethod
    @require_auth
    def profile():
        user_id = get_jwt_identity()
        try:
            user = UserModel.find_by_id(user_id)
            if not user:
                return error_response('User not found', 404)
            return success_response(data={
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
                'created_at': user['created_at'].isoformat() if hasattr(user.get('created_at', ''), 'isoformat') else str(user.get('created_at', ''))
            })
        except Exception as e:
            logger.error(f"Profile error: {e}", exc_info=True)
            return error_response('Could not retrieve profile', 500)
