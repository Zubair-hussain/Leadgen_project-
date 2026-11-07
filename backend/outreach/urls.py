from django.urls import path

from . import cron, review, views

urlpatterns = [
    path('cron/tick/', cron.tick, name='outreach-cron-tick'),
    path('status/', views.OutreachStatusView.as_view(), name='outreach-status'),
    path('messages/', views.OutreachMessageListView.as_view(), name='outreach-messages'),
    path('messages/<int:pk>/', views.OutreachMessageDetailView.as_view(), name='outreach-message-detail'),
    path('messages/<int:pk>/preflight/', views.PreflightView.as_view(), name='outreach-message-preflight'),
    path('messages/<int:pk>/approve/', views.ApproveMessageView.as_view(), name='outreach-message-approve'),
    path('messages/<int:pk>/cancel/', views.CancelMessageView.as_view(), name='outreach-message-cancel'),
    path('review/<str:token>/', review.review_draft, name='outreach-review'),
    path('batch-review/<str:token>/', review.review_batch, name='outreach-batch-review'),
    path('batches/', views.BatchListView.as_view(), name='outreach-batches'),
    path('ai-drafts/', views.AiDraftsView.as_view(), name='outreach-ai-drafts'),
    path('suppressions/', views.SuppressionListView.as_view(), name='outreach-suppressions'),
    path('suppressions/<int:pk>/', views.SuppressionDetailView.as_view(), name='outreach-suppression-detail'),
]
