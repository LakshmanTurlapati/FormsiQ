import os
import django
# Need to set DJANGO_SETTINGS_MODULE if not already set by manage.py shell context
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'formsiq_project.settings') # Assuming this is your settings module
# django.setup() # This is often needed if running a script standalone

from api_processor.pdf_service import get_pdf_fields_info, get_pdf_field_categories

print("--- PDF Fields Info ---")
fields_info = get_pdf_fields_info()
if fields_info:
    for field_name, info in fields_info.items():
        print(f"Field: {field_name}, Type: {info.get('type', 'N/A')}, Value: {info.get('value', 'N/A')}, Options: {info.get('options', 'N/A')}")
else:
    print("Could not retrieve PDF fields info.")

print("\n--- PDF Field Categories ---")
field_categories = get_pdf_field_categories()
if field_categories:
    for category, fields in field_categories.items():
        print(f"Category: {category}")
        for field_name in fields:
            print(f"  - {field_name}")
else:
    print("Could not retrieve PDF field categories.")

quit() # To exit the shell 