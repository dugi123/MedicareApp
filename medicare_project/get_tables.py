from django.apps import apps
from django.db import connection

def get_all_models():
    return apps.get_models()

def get_all_tables():
    return connection.introspection.table_names()

print("All tables in the database:")
for table in get_all_tables():
    print(f"- {table}")

print("\nAll models defined in Django:")
for model in get_all_models():
    print(f"- {model.__name__} ({model._meta.db_table})")
