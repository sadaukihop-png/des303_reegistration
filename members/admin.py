from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'matric_number', 'group', 'has_paid', 'registered_at']
    list_filter = ['group', 'has_paid', 'is_active']
    search_fields = ['full_name', 'matric_number']
    readonly_fields = ['registered_at', 'updated_at']
