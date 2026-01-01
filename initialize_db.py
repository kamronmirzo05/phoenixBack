"""
Script to initialize the SQLite database for Phoenix Scientific Platform
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def initialize_database():
    """Initialize the SQLite database with migrations"""
    print("Initializing SQLite database...")
    
    # Run migrations to create all tables
    print("Applying database migrations...")
    execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    
    print("Database initialized successfully!")
    
    # Create a superuser if one doesn't exist
    try:
        django.setup()  # Setup Django after environment is configured
        
        from apps.users.models import User  # Using the custom user model
        
        if not User.objects.filter(is_superuser=True).exists():
            print("Creating initial superuser...")
            superuser = User.objects.create_superuser(
                phone='998901234567',
                password='admin123',
                first_name='Admin',
                last_name='User',
                email='admin@ilmiyfaoliyat.uz'
            )
            print(f"Superuser created with phone: {superuser.phone}")
        else:
            print("Superuser already exists.")
    except Exception as e:
        print(f"Error creating superuser: {e}")
        print("This might be fine if the database isn't fully migrated yet.")
    
    print("Database initialization complete!")

if __name__ == '__main__':
    initialize_database()