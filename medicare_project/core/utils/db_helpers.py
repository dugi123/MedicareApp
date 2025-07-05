"""
Utility functions for handling database and session operations
"""
import time
import sqlite3
import logging
import traceback
import threading
from functools import wraps
from django.db import OperationalError, IntegrityError, connection, transaction
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.backends.base import UpdateError
from django.conf import settings

logger = logging.getLogger(__name__)

# Thread-local storage for connection state
_local = threading.local()

def reset_db_connection():
    """
    Close and reset the database connection to resolve lock issues
    """
    try:
        # Close the connection to release any locks
        connection.close()
        # Clear thread-local connection state
        if hasattr(_local, 'connection_attempts'):
            delattr(_local, 'connection_attempts')
        # Connect again
        connection.connect()
        return True
    except Exception as e:
        logger.error(f"Error resetting DB connection: {str(e)}")
        return False

def with_db_retry(func=None, max_attempts=5, initial_wait=0.5, reset_conn=True):
    """
    Decorator to retry a database operation on lock error
    
    Args:
        func: The function to retry
        max_attempts: Maximum number of retry attempts
        initial_wait: Initial wait time before retry (will be doubled each time)
        reset_conn: Whether to reset the connection before retrying
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            wait_time = initial_wait
            last_error = None
            
            # Initialize thread-local connection attempt counter
            if not hasattr(_local, 'connection_attempts'):
                _local.connection_attempts = 0
            
            while attempt < max_attempts:
                try:
                    # Reset connection if needed and not too many resets
                    if reset_conn and _local.connection_attempts < 10:
                        _local.connection_attempts += 1
                        reset_db_connection()
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Reset counter on success
                    _local.connection_attempts = 0
                    
                    return result
                    
                except (OperationalError, sqlite3.OperationalError) as e:
                    if "database is locked" in str(e).lower():
                        attempt += 1
                        last_error = e
                        logger.warning(f"Database lock detected, attempt {attempt}/{max_attempts}: {str(e)}")
                        
                        if attempt < max_attempts:
                            # Wait before retrying with exponential backoff
                            logger.info(f"Waiting {wait_time} seconds before retry")
                            time.sleep(wait_time)
                            # Increase wait time for next retry
                            wait_time *= 2
                        else:
                            logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                            raise
                    else:
                        # If it's another type of OperationalError, reraise immediately
                        logger.error(f"Non-lock OperationalError: {str(e)}")
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise
            
            if last_error:
                raise last_error
            return None
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)

def save_session_safely(request):
    """
    Save the session with retry logic for database locks
    
    Args:
        request: The HTTP request object with a session
        
    Returns:
        bool: True if session was saved successfully, False otherwise
    """
    max_attempts = 5
    attempt = 0
    wait_time = 0.5  # seconds
    
    while attempt < max_attempts:
        try:
            # Reset connection before trying to save
            if attempt > 0:
                reset_db_connection()
                
            # Try to save the session
            request.session.save()
            return True
        except (OperationalError, sqlite3.OperationalError) as e:
            if "database is locked" in str(e).lower():
                attempt += 1
                logger.warning(f"Database lock detected during session save, attempt {attempt}/{max_attempts}")
                
                if attempt < max_attempts:
                    # Wait before retrying with exponential backoff
                    time.sleep(wait_time)
                    wait_time *= 2
                else:
                    logger.error(f"Failed to save session after {max_attempts} attempts")
                    # Try to create a new session
                    try:
                        # Use transaction isolation to ensure this completes
                        with transaction.atomic():
                            request.session.flush()
                            request.session.create()
                        logger.info("Created new session after save failure")
                    except Exception as e2:
                        logger.error(f"Failed to create new session: {str(e2)}")
            else:
                # If it's another type of OperationalError, log and break
                logger.error(f"Non-lock OperationalError during session save: {str(e)}")
                break
        except (SessionInterrupted, UpdateError) as e:
            logger.error(f"Session interrupted: {str(e)}")
            # Try to create a new session
            try:
                # Use transaction isolation to ensure this completes
                with transaction.atomic():
                    request.session.flush()
                    request.session.create()
                logger.info("Created new session after interruption")
                return True
            except Exception as e2:
                logger.error(f"Failed to create new session: {str(e2)}")
                break
        except Exception as e:
            # Log other exceptions and break the retry loop
            logger.error(f"Session save error: {str(e)}")
            logger.error(traceback.format_exc())
            break
                
    return False

def login_user_safely(request, user):
    """
    Log in a user with retry logic for database locks
    
    Args:
        request: The HTTP request object
        user: The User object to log in
        
    Returns:
        bool: True if login was successful, False otherwise
    """
    from django.contrib.auth import login
    
    max_attempts = 5
    attempt = 0
    wait_time = 0.5  # seconds
    
    while attempt < max_attempts:
        try:
            # Reset connection before trying to login
            if attempt > 0:
                reset_db_connection()
                
            # Use transaction isolation to ensure this completes
            with transaction.atomic():
                # Attempt login
                login(request, user)
                
            # Try to explicitly save the session
            save_session_safely(request)
            return True
        except (OperationalError, sqlite3.OperationalError) as e:
            if "database is locked" in str(e).lower():
                attempt += 1
                logger.warning(f"Database lock during login, attempt {attempt}/{max_attempts}: {str(e)}")
                
                if attempt < max_attempts:
                    time.sleep(wait_time)
                    wait_time *= 2
                else:
                    logger.error(f"Failed to login after {max_attempts} attempts")
                    # Try manual session creation as a last resort
                    try:
                        # Try a different approach: manually set session data
                        request.session.flush()
                        from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
                        request.session[SESSION_KEY] = str(user.pk)
                        request.session[BACKEND_SESSION_KEY] = user.backend
                        request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
                        save_session_safely(request)
                        request.user = user
                        logger.info(f"Manual session creation for {user.username}")
                        return True
                    except Exception as manual_error:
                        logger.error(f"Manual session creation failed: {str(manual_error)}")
                        return False
            else:
                # If it's another type of OperationalError, log and break
                logger.error(f"Non-lock OperationalError during login: {str(e)}")
                break
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            logger.error(traceback.format_exc())
            break
    
    return False

# Create a transaction with retry for common database operations
def transaction_with_retry(max_attempts=5):
    """
    Create a transaction context manager with retry logic
    
    Usage:
        with transaction_with_retry() as txn:
            # Do database operations
    """
    class RetryableTransaction:
        def __enter__(self):
            self.attempt = 0
            self.wait_time = 0.5
            self.max_attempts = max_attempts
            self.txn = None
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.txn:
                if exc_type is None:
                    try:
                        self.txn.__exit__(None, None, None)
                        return True
                    except (OperationalError, sqlite3.OperationalError) as e:
                        if "database is locked" in str(e).lower() and self.attempt < self.max_attempts:
                            self.attempt += 1
                            logger.warning(f"Database lock during transaction commit, attempt {self.attempt}/{self.max_attempts}")
                            time.sleep(self.wait_time)
                            self.wait_time *= 2
                            # Try again
                            reset_db_connection()
                            return self.__enter__().__exit__(exc_type, exc_val, exc_tb)
                        raise
                else:
                    self.txn.__exit__(exc_type, exc_val, exc_tb)
            return False
            
        def __call__(self):
            try:
                if self.attempt > 0:
                    reset_db_connection()
                self.txn = transaction.atomic().__enter__()
                return self
            except (OperationalError, sqlite3.OperationalError) as e:
                if "database is locked" in str(e).lower() and self.attempt < self.max_attempts:
                    self.attempt += 1
                    logger.warning(f"Database lock during transaction start, attempt {self.attempt}/{self.max_attempts}")
                    time.sleep(self.wait_time)
                    self.wait_time *= 2
                    # Try again
                    return self()
                raise
    
    return RetryableTransaction()
