from django.contrib import admin
from .models import UserProfile, FarmerProfile, Product, Interest, Rating, Reply, ProductRequest, News

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_farmer', 'phone', 'city')
    list_filter = ('is_farmer', 'city')
    search_fields = ('user__username', 'phone', 'city', 'address')

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('farm_name', 'user_profile', 'farm_location', 'average_rating')
    list_filter = ('farm_location',)
    search_fields = ('farm_name', 'farm_description', 'farm_location')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'farmer', 'price', 'quantity', 'created_at')
    list_filter = ('created_at', 'farmer')
    search_fields = ('name', 'description', 'farmer__farm_name')
    ordering = ('-created_at',)

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('product__name', 'user__user__username', 'message')
    ordering = ('-created_at',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('farmer', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('farmer__farm_name', 'user__user__username', 'comment')
    ordering = ('-created_at',)

@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('rating', 'farmer', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('farmer__farm_name', 'reply_text')
    ordering = ('-created_at',)

@admin.register(ProductRequest)
class ProductRequestAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'user', 'quantity', 'district', 'created_at')
    list_filter = ('district', 'created_at')
    search_fields = ('product_name', 'user__username', 'district', 'message')
    ordering = ('-created_at',)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'created_at', 'expiry_date')
    search_fields = ('title', 'content')
