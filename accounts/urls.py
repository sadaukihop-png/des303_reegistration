from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('leader-login/', views.group_leader_login_view, name='leader_login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-create-group/', views.admin_create_group, name='admin_create_group'),
    path('admin-delete-group/<int:group_id>/', views.admin_delete_group, name='admin_delete_group'),
    path('admin-delete-all/', views.admin_delete_all_groups, name='admin_delete_all'),
]
