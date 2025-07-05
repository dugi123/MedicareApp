from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Lists all database tables'

    def handle(self, *args, **kwargs):
        tables = connection.introspection.table_names()
        for table in tables:
            self.stdout.write(self.style.SUCCESS(f'- {table}'))
