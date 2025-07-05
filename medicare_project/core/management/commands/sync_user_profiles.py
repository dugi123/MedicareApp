from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = 'Sync email and password fields from User model to UserProfile model for existing users'

    def handle(self, *args, **options):
        self.stdout.write('Starting to sync email and password fields...')
        
        # Get all user profiles
        profiles = UserProfile.objects.all()
        count = 0
        
        for profile in profiles:
            try:
                # Copy email and password from User to UserProfile
                profile.email = profile.user.email
                profile.password = profile.user.password
                profile.save()
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating profile for {profile.user}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} user profiles!'))
