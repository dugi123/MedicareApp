"""
Custom middleware for handling session issues in Django
"""
import logging
import time
import traceback
import sqlite3
from django.db import OperationalError, IntegrityError, connection
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.backends.base import UpdateError
from django.conf import settings
from django.http import HttpResponse
from .utils.db_helpers import save_session_safely

logger = logging.getLogger(__name__)

class SessionDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request first
        try:
            # Attempt to access the session to verify it's working
            if hasattr(request, 'session'):
                try:
                    # Just accessing the session_key will verify the session is working
                    session_key = request.session.session_key
                    if session_key:
                        logger.debug(f"Session key before response: {session_key}")
                    else:
                        logger.debug("No session key before response")
                except (SessionInterrupted, UpdateError, OperationalError, sqlite3.OperationalError) as e:
                    logger.warning(f"Session error detected before response: {str(e)}")
                    # Create a new session if there's an issue
                    self.recreate_session(request)
        except Exception as e:
            logger.error(f"Unexpected session error before response: {str(e)}")
            logger.error(traceback.format_exc())
        
        # Get response
        try:
            response = self.get_response(request)
        except (OperationalError, sqlite3.OperationalError) as e:
            if "database is locked" in str(e).lower():
                logger.warning(f"Database lock during response: {str(e)}")
                # Try to close and reconnect to release any locks
                try:
                    connection.close()
                    connection.connect()
                    # Retry the request (up to a point)
                    for attempt in range(3):
                        try:
                            logger.info(f"Retrying request after DB lock, attempt {attempt+1}/3")
                            response = self.get_response(request)
                            break
                        except (OperationalError, sqlite3.OperationalError) as retry_e:
                            if attempt == 2:  # Last attempt failed
                                logger.error(f"Failed to retry request after DB lock: {str(retry_e)}")
                                return HttpResponse("The server is experiencing high load. Please try again in a moment.", status=503)
                            time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
                except Exception as conn_e:
                    logger.error(f"Connection reset failed: {str(conn_e)}")
                    return HttpResponse("The server is experiencing technical difficulties. Please try again later.", status=500)
            else:
                logger.error(f"Non-lock database error during response: {str(e)}")
                return HttpResponse("Database error. Please try again later.", status=500)
        except Exception as e:
            logger.error(f"Unexpected error during response: {str(e)}")
            logger.error(traceback.format_exc())
            return HttpResponse("An unexpected error occurred. Please try again later.", status=500)
        
        # Process the session after the response
        try:
            if hasattr(request, 'session') and hasattr(request.session, 'modified') and request.session.modified:
                logger.debug(f"Session modified: {request.session.modified}")
                save_session_safely(request)
        except Exception as e:
            logger.error(f"Session error after response: {str(e)}")
            
        return response

    def process_exception(self, request, exception):
        # Handle specific exceptions
        if isinstance(exception, (SessionInterrupted, UpdateError)):
            logger.error(f"Session exception handled: {str(exception)}")
            self.recreate_session(request)
        elif isinstance(exception, (OperationalError, sqlite3.OperationalError)) and "database is locked" in str(exception).lower():
            logger.error(f"Database lock exception handled: {str(exception)}")
            # Try to close the connection to release locks
            try:
                connection.close()
            except Exception:
                pass
            
        return None
    
    def recreate_session(self, request):
        """Safely recreate a session when corruption is detected"""
        try:
            # Store user and auth info if available
            auth_data = {}
            if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
                from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
                auth_data = {
                    'user_id': request.user.id,
                    'backend': getattr(request.user, 'backend', None),
                    'hash': request.user.get_session_auth_hash() if hasattr(request.user, 'get_session_auth_hash') else None
                }
            
            # Flush the old session
            request.session.flush()
            
            # Create a new session
            request.session.create()
            
            # Restore auth if we had it
            if auth_data and all(auth_data.values()):
                request.session[SESSION_KEY] = str(auth_data['user_id'])
                request.session[BACKEND_SESSION_KEY] = auth_data['backend']
                if auth_data['hash']:
                    request.session[HASH_SESSION_KEY] = auth_data['hash']
                
            # Save the new session
            save_session_safely(request)
            logger.info("Successfully recreated session")
            return True
        except Exception as e:
            logger.error(f"Failed to recreate session: {str(e)}")
            logger.error(traceback.format_exc())
            return False
