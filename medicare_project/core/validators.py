"""
Custom password validators
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class PasswordComplexityValidator:
    """
    Validate that the password meets complexity requirements:
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    - Length between 8 and 14 characters
    """
    
    def __init__(self, min_length=8, max_length=14):
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Password must be at least %(min_length)d characters long."),
                code='password_too_short',
                params={'min_length': self.min_length},
            )
        
        if len(password) > self.max_length:
            raise ValidationError(
                _("Password must be at most %(max_length)d characters long."),
                code='password_too_long',
                params={'max_length': self.max_length},
            )
            
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )
            
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
            
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code='password_no_digit',
            )
            
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code='password_no_special',
            )
    
    def get_help_text(self):
        return _(
            "Your password must be between %(min_length)d and %(max_length)d characters long, "
            "and must contain uppercase and lowercase letters, digits, and special characters."
        ) % {'min_length': self.min_length, 'max_length': self.max_length}
