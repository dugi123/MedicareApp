from django.shortcuts import render

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
    View function for the login page with ID card authentication.
    For existing users, only ID card name and number are required.
    """
    # This is a placeholder for future backend implementation
    # For now, we just render the login template with ID card form
    return render(request, 'core/login.html')

def user_signup(request):
    """
    View function for the signup page with ID card registration.
    """
    # This is a placeholder for future backend implementation
    # For now, we just render the signup template with ID card form
    return render(request, 'core/signup.html')

def profile(request):
    """
    View function for the user profile page.
    Shows ID card information and other user details.
    """
    # This is a placeholder for future backend implementation
    # For now, we just render the profile template with demo data
    return render(request, 'core/profile.html')
