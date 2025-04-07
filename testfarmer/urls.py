from django.urls import path
from . import views

urlpatterns = [
    # ... existing URL patterns ...
    
    # News Management URLs
    path('admin/news/add/', views.add_news, name='add_news'),
    path('admin/news/delete/<int:news_id>/', views.delete_news, name='delete_news'),
    
    # ... rest of existing URL patterns ...
] 