from django.contrib import admin
from .models import Group

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'is_active', 'get_member_count', 'get_paid_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['leader_password_raw', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.get_member_count()
    get_member_count.short_description = 'Total Members'
    
    def get_paid_count(self, obj):
        return obj.get_paid_count()
    get_paid_count.short_description = 'Paid Members'
