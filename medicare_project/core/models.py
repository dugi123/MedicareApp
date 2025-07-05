# Models file

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator, MinLengthValidator

def profile_picture_upload_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_pictures/user_<id>/<timestamp>.<extension>
    extension = filename.split('.')[-1]
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'profile_pictures/user_{instance.user.id if instance.user else "new"}/{timestamp}.{extension}'

def doctor_license_upload_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/doctor_licenses/user_<id>/<timestamp>.<extension>
    extension = filename.split('.')[-1]
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'doctor_licenses/doctor_{instance.user.id if instance.user else "new"}/{timestamp}.{extension}'

def doctor_profile_picture_upload_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/doctor_pictures/user_<id>/<timestamp>.<extension>
    extension = filename.split('.')[-1]
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    return f'doctor_pictures/doctor_{instance.user.id if instance.user else "new"}/{timestamp}.{extension}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Duplicated auth fields from User model (for direct database access)
    email = models.EmailField(max_length=254, blank=True)
    password = models.CharField(max_length=128, blank=True)
    
    # Basic profile information with validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=20, blank=False, null=False)
    date_of_birth = models.DateField(null=False, blank=False)
    address = models.TextField(blank=False, null=False)
    
    # Optional profile picture
    profile_picture = models.ImageField(upload_to=profile_picture_upload_path, blank=True, null=True)
    
    # Account metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    @property
    def is_hidden(self):
        """Check if this profile should be hidden from public views"""
        return self.is_demo
    
    def sync_from_user(self):
        """Sync email and password from the linked user model"""
        if self.user:
            self.email = self.user.email
            self.password = self.user.password
            return True
        return False

class LoginHistory(models.Model):
    """Track user login history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    login_date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    successful = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Login histories"
    
    def __str__(self):
        status = "Successful" if self.successful else "Failed"
        return f"{status} login for {self.user.email} at {self.login_date}"

class Doctor(models.Model):
    # Link to Django's built-in User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    
    # Duplicated auth fields from User model (for direct database access)
    email = models.EmailField(max_length=254, blank=True)
    password = models.CharField(max_length=128, blank=True)
    
    # Professional information
    registration_number = models.CharField(max_length=50, unique=True, 
                                        help_text="Government-issued medical registration number")
    specialization = models.CharField(max_length=100)
    years_of_experience = models.PositiveIntegerField(default=0)
    
    # Basic information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=20)
    date_of_birth = models.DateField()
    address = models.TextField()
    
    # Documentation
    license_document = models.FileField(upload_to=doctor_license_upload_path, blank=True, null=True)
    profile_picture = models.ImageField(upload_to=doctor_profile_picture_upload_path, blank=True, null=True)
    
    # Medical practice details
    hospital_affiliation = models.CharField(max_length=200, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    available_for_appointments = models.BooleanField(default=True)
    
    # Account metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False, 
                                   help_text="Whether the doctor's credentials have been verified")
    
    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} ({self.registration_number})"
    
    def sync_from_user(self):
        """Sync email and password from the linked user model"""
        if self.user:
            self.email = self.user.email
            self.password = self.user.password
            return True
        return False

class UserType(models.Model):
    """Tracks whether a user is a patient or a doctor"""
    USER_TYPE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_type')
    type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='patient')
    
    def __str__(self):
        return f"{self.user.email} - {self.get_type_display()}"

# Signal to create user profile automatically when a user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        import datetime
        
        # Create UserType object - default is patient unless specified
        user_type = getattr(instance, 'user_type_value', 'patient')
        UserType.objects.create(user=instance, type=user_type)
        
        # Create the appropriate profile based on user type
        if user_type == 'patient':
            # Create patient profile (UserProfile)
            UserProfile.objects.create(
                user=instance,
                email=instance.email,
                password=instance.password,
                phone_number="0000000000",
                date_of_birth=datetime.date(2000, 1, 1),
                address="Not provided"
            )
        elif user_type == 'doctor':
            # Create doctor profile
            Doctor.objects.create(
                user=instance,
                email=instance.email,
                password=instance.password,
                registration_number="Pending",  # Will be updated during registration
                specialization="General",
                phone_number="0000000000",
                date_of_birth=datetime.date(2000, 1, 1),
                address="Not provided"
            )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        # Get user type
        user_type_obj = UserType.objects.get(user=instance)
        
        # Update the appropriate profile
        if user_type_obj.type == 'patient' and hasattr(instance, 'profile'):
            # Sync patient profile
            instance.profile.email = instance.email
            instance.profile.password = instance.password
            instance.profile.save()
        elif user_type_obj.type == 'doctor' and hasattr(instance, 'doctor_profile'):
            # Sync doctor profile
            instance.doctor_profile.email = instance.email
            instance.doctor_profile.password = instance.password
            instance.doctor_profile.save()
        
        # Always save the user type
        user_type_obj.save()
    except UserType.DoesNotExist:
        pass  # User type not set yet
