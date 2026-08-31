from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('leads/', views.LeadListView.as_view(), name='lead-list'),
    path('leads/export/', views.export_leads, name='leads-export'),
    path('leads/bulk-verify/', views.BulkVerifyLeadsView.as_view(), name='bulk-verify-leads'),
    path('leads/verify-single/', views.VerifySingleEmailView.as_view(), name='verify-single-email'),
    path('leads/verify-multi/', views.MultiVerifyView.as_view(), name='verify-multi-email'),
    path('leads/verify-file/', views.FileUploadVerifyView.as_view(), name='verify-file-email'),
    path('deliverability/check/', views.DeliverabilityPolicyCheckView.as_view(), name='deliverability-policy-check'),
    path('leads/<int:pk>/', views.DeleteLeadView.as_view(), name='delete-lead'),
    path('leads/<int:pk>/verify/', views.VerifyLeadView.as_view(), name='verify-lead'),
    path('generate/', views.GenerateLeadsView.as_view(), name='generate-leads'),
    path('', views.hello_world, name='hello'),
]
