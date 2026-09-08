from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    # Public views
    path('public-list/', views.public_group_list, name='public_group_list'),
    path('detail/<int:group_id>/', views.group_detail, name='group_detail'),
    
    # Leader views
    path('leader-dashboard/', views.leader_dashboard, name='leader_dashboard'),
    path('leader-confirm-payment/<int:member_id>/', views.leader_confirm_payment, name='leader_confirm_payment'),
    path('leader-reverse-payment/<int:member_id>/', views.leader_reverse_payment, name='leader_reverse_payment'),
    path('leader-delete-member/<int:member_id>/', views.leader_delete_member, name='leader_delete_member'),
    
    # Export views
    path('export-csv/<int:group_id>/', views.export_group_members_csv, name='export_csv'),
    path('export-excel/<int:group_id>/', views.export_group_members_excel, name='export_excel'),
    path('export-pdf/<int:group_id>/', views.export_group_members_pdf, name='export_pdf'),
]