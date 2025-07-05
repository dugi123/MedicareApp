from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import UserProfile, LoginHistory
import logging
import traceback

logger = logging.getLogger(__name__)

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in with their email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user based on email address as the username.
        """
        UserModel = get_user_model()
        
        try:
            # Check if the username is an email
            if username is None or password is None:
                logger.warning("Authentication attempted without username or password")
                return None
                
            logger.info(f"Attempting authentication for username/email: {username}")
            
            # Try to fetch the user by username or email
            try:
                # Case-insensitive lookup for both username and email
                user = UserModel.objects.get(Q(username=username) | Q(email__iexact=username))
            except UserModel.DoesNotExist:
                # No user found with that username or email
                logger.warning(f"No user found with username/email: {username}")
                
                # Log failed login attempt if we have a request
                if request:
                    self._log_login_attempt(request, username, successful=False)
                return None
                
            # Check the password
            if user.check_password(password):
                logger.info(f"Authentication successful for {user.username} (email: {user.email})")
                
                # Log successful login attempt
                if request:
                    self._log_login_attempt(request, username, user=user, successful=True)
                return user
            else:
                logger.warning(f"Password mismatch for username/email: {username}")
                
                # Log failed login attempt
                if request:
                    self._log_login_attempt(request, username, user=user, successful=False)
                return None
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
    def _log_login_attempt(self, request, username, user=None, successful=False):
        """
        Log login attempts to the database
        """
        try:
            # Only log if we have a user object
            if user:
                # Get IP address from request
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
                
                # Get user agent
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Check if LoginHistory table exists by trying to access it
                from django.db import connection
                with connection.cursor() as cursor:
                    try:
                        cursor.execute("SELECT 1 FROM core_loginhistory LIMIT 1")
                        # Table exists, create the record
                        LoginHistory.objects.create(
                            user=user,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            successful=successful
                        )
                    except Exception as table_error:
                        # Table doesn't exist, just log instead
                        status = "Successful" if successful else "Failed"
                        logger.info(f"{status} login for {user.email} from {ip_address} with {user_agent}")
        except Exception as e:
            logger.error(f"Error logging login attempt: {str(e)}")
            # Don't raise the exception - this is just for logging

    def get_user(self, user_id):
        """
        Retrieve a user by their ID.
        """
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            logger.warning(f"No user found with ID: {user_id}")
            return None

class DoctorRegistrationBackend(ModelBackend):
    """
    Custom authentication backend that allows doctors to log in with their registration number.
    """

    def authenticate(self, request, registration_number=None, password=None, **kwargs):
        """
        Authenticate a doctor based on registration number.
        """
        from .models import Doctor
        UserModel = get_user_model()
        
        try:
            # Check if the registration number is provided
            if registration_number is None or password is None:
                logger.warning("Doctor authentication attempted without registration number or password")
                return None
                
            logger.info(f"Attempting doctor authentication for registration number: {registration_number}")
            
            # Try to fetch the doctor by registration number
            try:
                # Look up the doctor by registration number
                doctor = Doctor.objects.get(registration_number=registration_number)
                user = doctor.user
            except Doctor.DoesNotExist:
                # No doctor found with that registration number
                logger.warning(f"No doctor found with registration number: {registration_number}")
                
                # Log failed login attempt if we have a request
                if request:
                    self._log_login_attempt(request, registration_number, successful=False)
                return None
                
            # Check the password
            if user.check_password(password):
                logger.info(f"Authentication successful for doctor {user.username} (reg: {registration_number})")
                
                # Log successful login attempt
                if request:
                    self._log_login_attempt(request, registration_number, user=user, successful=True)
                return user
            
            # Invalid password
            logger.warning(f"Invalid password for doctor with registration number: {registration_number}")
            
            # Log failed login attempt
            if request:
                self._log_login_attempt(request, registration_number, successful=False)
            return None
            
        except Exception as e:
            logger.error(f"Exception in doctor authentication: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _log_login_attempt(self, request, identifier, user=None, successful=False):
        """
        Log the login attempt to the database.
        """
        try:
            # Get IP and user agent
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Create login history record if we have a user
            if user:
                LoginHistory.objects.create(
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    successful=successful
                )
            else:
                # Just log the attempt without saving to DB (no user to link it to)
                log_msg = f"{'Successful' if successful else 'Failed'} login attempt from {ip_address} with identifier {identifier}"
                if successful:
                    logger.info(log_msg)
                else:
                    logger.warning(log_msg)
                    
        except Exception as e:
            logger.error(f"Error logging login attempt: {str(e)}")
    
    def _get_client_ip(self, request):
        """
        Get the client's IP address from the request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
