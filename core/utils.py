# Create this file at: core/utils.py

import secrets
import string
from django.utils.crypto import get_random_string

def generate_leader_password(length=12):
    """
    Generate a secure password for group leaders
    Includes uppercase, lowercase, digits, and special characters
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def generate_group_code(prefix="GRP"):
    """
    Generate a unique group code
    """
    import datetime
    import random
    
    today = datetime.datetime.now()
    year = str(today.year)[2:]  # Last 2 digits of year
    month = str(today.month).zfill(2)
    day = str(today.day).zfill(2)
    random_num = str(random.randint(100, 999))
    
    return f"{prefix}-{year}{month}{day}-{random_num}"

def sanitize_matric_number(matric):
    """
    Validate and sanitize matric number format
    Example: NOU123456789
    """
    if not matric:
        return None
    
    # Remove whitespace and convert to uppercase
    matric = matric.strip().upper()
    
    # Basic validation - at least 10 characters
    if len(matric) < 10:
        return None
    
    # Should start with letters and contain numbers
    if not matric[:3].isalpha():
        return None
    
    return matric

def format_nigerian_date(datetime_obj):
    """
    Format date in Nigerian format: DD/MM/YYYY HH:MM
    """
    from django.utils import timezone
    
    if not datetime_obj:
        return None
    
    return datetime_obj.strftime("%d/%m/%Y %H:%M")
