from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('doctors/', views.doctors, name='doctors'),
    path('facilities/', views.facilities, name='facilities'),
    path('services/', views.services, name='services'),
    path('specialties/', views.specialties, name='specialties'),
    path('treatments/', views.treatments, name='treatments'),
    path('blog/', views.blog, name='blog'),
    path('contact/', views.contact, name='contact'),
    path('appointment/', views.appointment, name='appointment'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('profile/', views.profile, name='profile'),
]
