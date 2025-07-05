from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
import os
import json
import logging
import re

from .models import UserProfile, Doctor, UserType, LoginHistory
from .utils.db_helpers import with_db_retry, save_session_safely, login_user_safely

# Configure logging
logger = logging.getLogger(__name__)

# Create your views here.
def home(request):
    """
    View function for the home page of the website.
    """
    return render(request, 'core/home.html')

def about(request):
    """
    View function for the about page.
    """
    return render(request, 'core/about.html')

def doctors(request):
    """
    View function for the doctors listing page.
    """
    return render(request, 'core/doctors.html')

def facilities(request):
    """
    View function for the facilities page.
    """
    return render(request, 'core/facilities.html')

def services(request):
    """
    View function for the services listing page.
    """
    return render(request, 'core/services.html')

def specialties(request):
    """
    View function for the specialties page.
    """
    return render(request, 'core/specialties.html')

def treatments(request):
    """
    View function for the treatments page.
    """
    return render(request, 'core/treatments.html')

def blog(request):
    """
    View function for the blog listing page.
    """
    return render(request, 'core/blog.html')

def contact(request):
    """
    View function for the contact page.
    """
    return render(request, 'core/contact.html')

def appointment(request):
    """
    View function for the appointment booking page.
    """
    return render(request, 'core/appointment.html')

def user_login(request):
    """
    View function for the login page with email/registration number and password authentication.
    Patients log in with email, doctors log in with registration number.
    Uses improved database retry mechanisms to handle concurrency issues.
    """
    # Import necessary modules
    import time
    
    # Initialize session if needed
    if not request.session.session_key:
        request.session.create()
        logger.info("Created new session in login view")
    
    if request.method == 'POST':
        password = request.POST.get('password')
        user_type = request.POST.get('user_type', 'patient')  # Default to patient if not specified
        
        # Get identity field based on user type
        email = request.POST.get('email', '')
        registration_number = request.POST.get('registration_number', '')
        
        # Debug logging based on user type
        if user_type == 'patient':
            logger.info(f"Patient login attempt with email: {email}")
            if not email or not password:
                messages.error(request, "Please provide both email and password.")
                return render(request, 'core/login.html')
            
            # Check if the email is in a valid format
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                messages.error(request, "Invalid email format. Please enter a valid email address.")
                return render(request, 'core/login.html')
                
            # Check if a user with that email exists
            try:
                user_exists = User.objects.filter(email=email).exists()
                if not user_exists:
                    messages.error(request, "No account found with this email address. Please check your email or sign up.")
                    return render(request, 'core/login.html')
                    
                # Check if the user is of the correct type
                try:
                    user = User.objects.get(email=email)
                    user_type_obj = user.user_type
                    
                    if user_type_obj.type != user_type:
                        messages.error(request, f"This email is registered as a {user_type_obj.get_type_display()}, not a {user_type.capitalize()}. Please select the correct user type.")
                        return render(request, 'core/login.html')
                except Exception as e:
                    logger.error(f"Error checking user type: {str(e)}")
            except Exception as e:
                logger.error(f"Error checking user existence: {str(e)}")
            
            # Define authentication function for patient login
            def authenticate_user():
                user = authenticate(request, username=email, password=password)
                if user is not None:
                    logger.info(f"Authentication successful for patient {user.username}")
                    return user
                return None
                
        else:  # Doctor login with registration number
            logger.info(f"Doctor login attempt with registration number: {registration_number}")
            if not registration_number or not password:
                messages.error(request, "Please provide both registration number and password.")
                return render(request, 'core/login.html')
            
            # Check if a doctor with that registration number exists
            try:
                doctor_exists = Doctor.objects.filter(registration_number=registration_number).exists()
                if not doctor_exists:
                    messages.error(request, "No doctor account found with this registration number. Please check your registration number or sign up.")
                    return render(request, 'core/login.html')
                
                # Get the user associated with this registration number
                doctor = Doctor.objects.get(registration_number=registration_number)
                user = doctor.user
                
                # Check if the user is of the correct type
                if user.user_type.type != 'doctor':
                    messages.error(request, "This registration number is not associated with a doctor account.")
                    return render(request, 'core/login.html')
                
                # Override email with the doctor's email for authentication
                email = user.email
                
            except Exception as e:
                logger.error(f"Error checking doctor existence: {str(e)}")
                messages.error(request, "An error occurred while verifying your registration number. Please try again.")
                return render(request, 'core/login.html')
            
            # Define authentication function for doctor login
            def authenticate_user():
                user = authenticate(request, username=email, password=password)
                if user is not None:
                    logger.info(f"Authentication successful for doctor {user.username}")
                    return user
                return None
        
        # Use retry wrapper for authentication
        try:
            # Authenticate user with retry logic
            user = with_db_retry(authenticate_user, max_attempts=5, initial_wait=0.5)
            
            if user is not None:
                # Use our safe login helper
                login_success = login_user_safely(request, user)
                
                if login_success:
                    # Successfully logged in
                    messages.success(request, f"Welcome back, {user.first_name} {user.last_name}!")
                    
                    # Save session safely
                    save_session_safely(request)
                    
                    # Redirect to profile
                    return redirect('profile')
                else:
                    # Login failed due to technical issues
                    if user_type == 'patient':
                        logger.error(f"Login failed for patient {email} due to technical issues")
                    else:
                        logger.error(f"Login failed for doctor with registration {registration_number} due to technical issues")
                    messages.error(request, "We encountered an issue while logging you in. Please try again.")
            else:
                # Invalid credentials
                if user_type == 'patient':
                    logger.warning(f"Invalid credentials for patient email: {email}")
                    messages.error(request, "Incorrect password. Please check your password and try again.")
                else:
                    logger.warning(f"Invalid credentials for doctor registration: {registration_number}")
                    messages.error(request, "Incorrect password. Please check your registration number and password and try again.")
                
        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
            messages.error(request, "An error occurred during login. Please try again later.")
    
    # For GET requests or failed login attempts
    return render(request, 'core/login.html')

def user_signup(request):
    """
    View function for the signup page with email and password registration.
    Includes validation for all fields and proper error handling.
    Uses improved database retry mechanisms to handle concurrency issues.
    """
    # Import necessary modules
    import re
    from django.core.exceptions import ValidationError
    from django.contrib.auth.password_validation import validate_password
    
    # Initialize session if needed
    if not request.session.session_key:
        request.session.create()
        logger.info("Created new session in signup view")
    
    if request.method == 'POST':
        logger.info("Processing signup form submission")
        
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()
        user_type = request.POST.get('user_type', 'patient')  # Default to patient
        
        # Debug logging for request data
        logger.info(f"Signup request received for {email}, user type: {user_type}")
        
        # Doctor-specific fields - only required if user_type is 'doctor'
        registration_number = None
        specialization = None
        years_of_experience = None
        hospital_affiliation = None
        consultation_fee = None
        license_document = None
        
        if user_type == 'doctor':
            # Get doctor-specific form data
            registration_number = request.POST.get('registration_number', '').strip()
            specialization = request.POST.get('specialization', '').strip()
            years_of_experience = request.POST.get('years_of_experience', '0').strip()
            hospital_affiliation = request.POST.get('hospital_affiliation', '').strip()
            consultation_fee = request.POST.get('consultation_fee', '0').strip()
            
            # Get file uploads
            license_document = request.FILES.get('license_document')
            # No profile picture upload required for doctors
        
        # Validate all required fields
        errors = []
        
        if not first_name:
            errors.append("First name is required")
        
        if not last_name:
            errors.append("Last name is required")
        
        if not email:
            errors.append("Email is required")
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append("Please enter a valid email address")
        
        if not phone:
            errors.append("Phone number is required")
        elif not re.match(r'^\+?[0-9]{10,15}$', phone):
            errors.append("Please enter a valid phone number (10-15 digits)")
        
        if not date_of_birth:
            errors.append("Date of birth is required")
        
        if not address:
            errors.append("Address is required")
        
        if not password:
            errors.append("Password is required")
        
        if not password_confirm:
            errors.append("Please confirm your password")
        
        # Perform password validation
        if password:
            # Check password complexity
            if len(password) < 8 or len(password) > 14:
                errors.append("Password must be between 8 and 14 characters")
            elif not re.search(r'[A-Z]', password):
                errors.append("Password must contain at least one uppercase letter")
            elif not re.search(r'[a-z]', password):
                errors.append("Password must contain at least one lowercase letter")
            elif not re.search(r'[0-9]', password):
                errors.append("Password must contain at least one number")
            elif not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
                errors.append("Password must contain at least one special character")
            
            # Check if passwords match
            if password != password_confirm:
                errors.append("Passwords do not match")
        
        # Validate doctor-specific fields if user type is doctor
        if user_type == 'doctor':
            if not registration_number:
                errors.append("Registration number is required for doctors")
            
            if not specialization:
                errors.append("Specialization is required for doctors")
            
            try:
                years_of_experience = int(years_of_experience)
                if years_of_experience < 0:
                    errors.append("Years of experience cannot be negative")
            except ValueError:
                errors.append("Years of experience must be a number")
            
            try:
                if consultation_fee:
                    consultation_fee = float(consultation_fee)
                    if consultation_fee < 0:
                        errors.append("Consultation fee cannot be negative")
            except ValueError:
                errors.append("Consultation fee must be a number")
        
        # Check if email already exists - using retry logic
        try:
            def check_email_exists():
                return User.objects.filter(email=email).exists()
            
            email_exists = with_db_retry(check_email_exists, max_attempts=3, initial_wait=0.5)
            if email_exists:
                errors.append("This email is already registered. Please login instead.")
        except Exception as e:
            logger.error(f"Error checking if email exists: {str(e)}")
            errors.append("An error occurred while checking email availability. Please try again.")
        
        # If there are validation errors, return them to the user
        if errors:
            for error in errors:
                messages.error(request, error)
            
            # Return form with entered values
            context = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'date_of_birth': date_of_birth,
                'address': address,
            }
            return render(request, 'core/signup.html', context)
        
        # Create user account with retry logic
        try:
            # Define the user creation function for retry wrapper
            def create_user_and_profile():
                # Create new user with email as username
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Set user type attribute before save to trigger the right signal handler
                user.user_type_value = user_type
                
                if user_type == 'patient':
                    # Update UserProfile with submitted data
                    user_profile = UserProfile.objects.get(user=user)
                    user_profile.phone_number = phone
                    user_profile.date_of_birth = date_of_birth
                    user_profile.address = address
                    user_profile.save()
                    
                    return user, user_profile
                else:  # user_type == 'doctor'
                    # Update Doctor profile with submitted data
                    doctor_profile = user.doctor_profile
                    doctor_profile.phone_number = phone
                    doctor_profile.date_of_birth = date_of_birth
                    doctor_profile.address = address
                    doctor_profile.registration_number = registration_number
                    doctor_profile.specialization = specialization
                    doctor_profile.years_of_experience = years_of_experience
                    
                    if hospital_affiliation:
                        doctor_profile.hospital_affiliation = hospital_affiliation
                    
                    if consultation_fee:
                        doctor_profile.consultation_fee = consultation_fee
                    
                    # Handle file uploads if provided
                    if license_document:
                        doctor_profile.license_document = license_document
                    
                    # No profile picture processing needed for doctors
                    
                    doctor_profile.save()
                    
                    return user, doctor_profile
            
            # Create user with retry logic
            user, _ = with_db_retry(create_user_and_profile, max_attempts=5, initial_wait=0.5)
            
            # Login the user
            login_success = login_user_safely(request, user)
            
            if login_success:
                # Success message
                messages.success(request, f"Welcome, {user.first_name} {user.last_name}! Your account has been created successfully.")
                logger.info(f"User {user.username} registered and logged in successfully")
                
                # Ensure session is saved
                save_session_safely(request)
                
                # Redirect to profile page
                return redirect('profile')
            else:
                # Account created but login failed
                messages.warning(request, "Account created but automatic login failed. Please try logging in manually.")
                return redirect('login')
                
        except Exception as e:
            logger.error(f"Error during user creation: {str(e)}")
            messages.error(request, "An error occurred while creating your account. Please try again.")
    
    # For GET request, show the signup form
    return render(request, 'core/signup.html')
    
    # For GET request, show the signup form
    return render(request, 'core/signup.html')

def user_logout(request):
    """
    View function to log out a user.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

@login_required
def profile(request):
    """
    View function for the user profile page.
    Shows user information and profile details for both patients and doctors.
    """
    # Debug logging
    logger.info(f"Profile view accessed by user: {request.user.username}, auth: {request.user.is_authenticated}")
    
    try:
        # Get the user type
        user_type_obj = request.user.user_type
        user_type = user_type_obj.type
        
        context = {
            'user': request.user,
            'user_type': user_type
        }
        
        if user_type == 'patient':
            # Access the patient profile
            user_profile = request.user.profile
            
            # Check if this is a demo account profile and redirect if needed
            if user_profile.is_demo:
                logger.info(f"Demo account accessed: {request.user.username}, redirecting to home")
                messages.warning(request, "This account profile is unavailable.")
                return redirect('home')
            
            # Add patient profile to context
            context['user_profile'] = user_profile
            
        elif user_type == 'doctor':
            # Access the doctor profile
            doctor_profile = request.user.doctor_profile
            
            # Add doctor profile to context
            context['doctor_profile'] = doctor_profile
            
        # Log success
        logger.info(f"Found profile for user {request.user.username} of type {user_type}")
        
        return render(request, 'core/profile.html', context)
    
    except Exception as e:
        logger.error(f"Error in profile view: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('home')

@login_required
def update_profile(request):
    """
    View function for updating user profile information.
    Allows updating both User model fields (email, password) and profile fields (UserProfile or Doctor).
    """
    if request.method == 'POST':
        try:
            user = request.user
            
            # Get user type
            user_type_obj = user.user_type
            user_type = user_type_obj.type
            
            # Get the appropriate profile based on user type
            if user_type == 'patient':
                profile = user.profile
            else:  # user_type == 'doctor'
                profile = user.doctor_profile
            
            # Update email if provided and changed
            new_email = request.POST.get('email', '').strip()
            if new_email and new_email != user.email:
                # Check if email is already in use
                if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                    messages.error(request, "This email is already in use by another account.")
                    return redirect('profile')
                
                # Update email in both models
                user.email = new_email
                user.username = new_email  # Since we use email as username
                profile.email = new_email
            
            # Update password if provided
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            
            if new_password:
                # Validate current password
                current_password = request.POST.get('current_password', '').strip()
                if not current_password or not user.check_password(current_password):
                    messages.error(request, "Current password is incorrect.")
                    return redirect('profile')
                
                # Check if passwords match
                if new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                    return redirect('profile')
                
                # Update password
                user.set_password(new_password)
                # Password hash will be updated in profile via signal handler
            
            # Update common profile fields
            if request.POST.get('phone_number'):
                profile.phone_number = request.POST.get('phone_number')
            
            if request.POST.get('address'):
                profile.address = request.POST.get('address')
            
            # Update user type specific fields
            if user_type == 'doctor':
                # Update doctor-specific fields
                if request.POST.get('specialization'):
                    profile.specialization = request.POST.get('specialization')
                
                if request.POST.get('years_of_experience'):
                    try:
                        profile.years_of_experience = int(request.POST.get('years_of_experience'))
                    except ValueError:
                        messages.warning(request, "Years of experience must be a number. This field was not updated.")
                
                if request.POST.get('hospital_affiliation'):
                    profile.hospital_affiliation = request.POST.get('hospital_affiliation')
                
                if request.POST.get('consultation_fee'):
                    try:
                        profile.consultation_fee = float(request.POST.get('consultation_fee'))
                    except ValueError:
                        messages.warning(request, "Consultation fee must be a number. This field was not updated.")
                
                # Handle license document upload
                if request.FILES.get('license_document'):
                    profile.license_document = request.FILES['license_document']
            
            # Handle profile picture upload (common for both types)
            if request.FILES.get('profile_picture'):
                profile.profile_picture = request.FILES['profile_picture']
            
            # Save changes
            user.save()
            profile.sync_from_user()  # Make sure password hash is synced
            profile.save()
            
            messages.success(request, "Your profile has been updated successfully.")
            
            # If password was changed, re-authenticate user
            if new_password:
                from django.contrib.auth import login
                login(request, user)
                
            return redirect('profile')
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            messages.error(request, f"An error occurred while updating your profile: {str(e)}")
    
    return redirect('profile')


