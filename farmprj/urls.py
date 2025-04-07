
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from testfarmer import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('generate-request/', views.generate_request, name='generate_request'),
    path('delete-interest/<int:interest_id>/', views.delete_interest, name='delete_interest'),
    path('find_buyers/', views.find_buyers, name='find_buyers'),
    path('admin-analytics/', views.admin_analytics, name='admin_analytics'),
    path('signup/user/', views.user_signup, name='user_signup'),
    path('signup/farmer/', views.farmer_signup, name='farmer_signup'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('farmer/<int:farmer_id>/', views.farmer_profile, name='farmer_profile'),
    path('dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('update-user-profile/', views.update_user_profile, name='update_user_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('show-interest/<int:product_id>/', views.show_interest, name='show_interest'),
    path('my-profile/', views.user_profile, name='user_profile'),
    path('send-sms/<int:product_id>/', views.send_sms_to_interested, name='send_sms_to_interested'),
    path('change-username/', views.change_username, name='change_username'),
    path('search/', views.search, name='search'),
    path('rate-farmer/<int:farmer_id>/', views.rate_farmer, name='rate_farmer'),
    path('reply-to-rating/<int:rating_id>/', views.reply_to_rating, name='reply_to_rating'),
    path('nearby-farms/', views.nearby_farms, name='nearby_farms'),
    path('market-prices/', views.market_prices, name='market_prices'),
     path('news/add/', views.add_news, name='add_news'),
    path('news/delete/<int:news_id>/', views.delete_news, name='delete_news'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
