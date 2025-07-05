from django.contrib import admin
from .models import UserProfile, LoginHistory, Doctor, UserType

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'date_of_birth', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number', 'email')
    readonly_fields = ('created_at', 'updated_at')

class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'registration_number', 'specialization', 'years_of_experience', 'is_verified')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'registration_number', 'specialization')
    list_filter = ('is_verified', 'specialization', 'available_for_appointments')
    readonly_fields = ('created_at', 'updated_at')

class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_date', 'ip_address', 'successful')
    list_filter = ('successful', 'login_date')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'login_date', 'ip_address', 'user_agent', 'successful')

class UserTypeAdmin(admin.ModelAdmin):
    list_display = ('user', 'type')
    list_filter = ('type',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')

# Register the models
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(LoginHistory, LoginHistoryAdmin)
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(UserType, UserTypeAdmin)
