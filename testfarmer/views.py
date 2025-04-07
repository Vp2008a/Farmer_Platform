from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from .models import *
from .forms import *
from django.contrib.admin.views.decorators import staff_member_required

from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
import json
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.db.models import Q
from math import radians, sin, cos, sqrt, atan2
from django.db.models import F, Count, Sum
import requests
from django.core.cache import cache
from datetime import datetime, timedelta
from .prediction import predict_price
import os
import pandas as pd
from django.utils import timezone

# Replace GUJARAT_DISTRICTS with COMMON_COMMODITIES
COMMON_COMMODITIES = [
    "Cabbage", "Cauliflower", "Bhindi(Ladies Finger)", "Green Chilli", 
    "Brinjal", "Cotton", "Tomato", "Ginger(Green)", "Guar", 
    "Coriander(Leaves)", "Potato", "Onion", "Wheat", "Paddy(Dhan)(Common)",
    "Banana", "Amaranthus", "Colacasia", "Ashgourd", "Beetroot"
]

def get_market_prices(state=None, commodity=None):
    api_key = "579b464db66ec23bdd00000107385f0af1c74e134d572fd205eb9502"
    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    
    # Default limit is 10, but increase to 100 if state is selected
    limit = 100 if state else 10
    
    params = {
        'api-key': api_key,
        'format': 'json',
        'limit': limit,
        'offset': 0
    }
    
    if state:
        formatted_state = state.title()
        params['filters[state]'] = formatted_state
        print(f"Fetching data for state: {formatted_state}")
    
    if commodity:
        params['filters[commodity]'] = commodity.title()
        print(f"Filtering by commodity: {commodity}")
    
    try:
        all_records = [] #it collect record in every loop
        total_records = None #it store the total number of records, and it is constant value
        current_offset = 0  
        
        while state:
            params['offset'] = current_offset
            print(f"Fetching records with offset: {current_offset}")
            
            response = requests.get(
                url, 
                params=params,
                timeout=(5, 15),
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                current_records = data.get('records', [])
                
                if not current_records:
                    break
                    
                all_records.extend(current_records)
                
                if total_records is None:
                    total_records = data.get('total', 0)
                
                current_offset += limit
                
                # Break if we've fetched all records
                if current_offset >= total_records:
                    break
            else:
                print(f"Error: {response.status_code}")
                break
        else:
            # Single request for default case (no state selected)
            response = requests.get(
                url, 
                params=params,
                timeout=(5, 15),
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                all_records = data.get('records', [])
                total_records = data.get('total', 0)
            
        if all_records:
            
            sorted_records = sorted(
                all_records, 
                key=lambda x: int(x['modal_price']) if x.get('modal_price') and x['modal_price'].isdigit() else 0
            )
            
            return {
                'records': sorted_records,
                'total': total_records,
                'updated_date': data.get('updated_date')
            }
        
    except Exception as e:
        print(f"Error fetching market prices: {e}")
    
    return None

# List of Indian states
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

def index(request):
    # Get selected location from query parameters
    selected_location = request.GET.get('location', '').strip()
    
    # Base queryset for UserProfile with is_farmer=True
    farmer_profiles = UserProfile.objects.filter(is_farmer=True)
    products_query = Product.objects.select_related('farmer__user_profile')
    requests_query = ProductRequest.objects.all()
    
    # Apply location filter if selected
    if selected_location:
        # Search in farm_location, city, and address fields
        farmer_profiles = farmer_profiles.filter(
            Q(farmerprofile__farm_location__icontains=selected_location) |
            Q(city__icontains=selected_location) |
            Q(address__icontains=selected_location)
        )
        products_query = products_query.filter(
            Q(farmer__user_profile__farmerprofile__farm_location__icontains=selected_location) |
            Q(farmer__user_profile__city__icontains=selected_location) |
            Q(farmer__user_profile__address__icontains=selected_location)
        )
        requests_query = requests_query.filter(
            Q(district__icontains=selected_location)
        )
    
    # Get top regions by product availability
    top_regions = (
        products_query
        .values('farmer__user_profile__city')
        .annotate(
            region=F('farmer__user_profile__city'),
            product_count=Count('id'),
            total_quantity=Sum('quantity')
        )
        .filter(region__isnull=False)  # Exclude null regions
        .order_by('-product_count')[:5]
    )

    # Get most requested products - Include all fields and ensure proper grouping
    trending_products = (
        ProductRequest.objects
        .values('product_name')
        .annotate(
            request_count=Count('id'),
            total_quantity=Sum('quantity')
        )
        .filter(product_name__isnull=False)  # Exclude null product names
        .order_by('-request_count')[:5]
    )

    # Get active farmers count by region
    active_farmers = (
        farmer_profiles
        .values('city')
        .annotate(
            region=F('city'),
            farmer_count=Count('id')
        )
        .filter(region__isnull=False)  # Exclude null regions
        .order_by('-farmer_count')[:5]
    )

    # Get recent products with all necessary related fields
    recent_products = (
        products_query
        .select_related('farmer', 'farmer__user_profile')
        .order_by('-created_at')[:6]
    )

    # Market activity summary - ensure we're counting active records
    total_farmers = farmer_profiles.count()
    total_products = products_query.filter(quantity__gt=0).count()  # Only count products with quantity
    total_requests = ProductRequest.objects.filter(status='active').count() if hasattr(ProductRequest, 'status') else ProductRequest.objects.count()

    # Get active news items
    news_items = News.objects.filter(
        expiry_date__gt=timezone.now(),
        is_active=True
    ).order_by('-created_at')

    context = {
        'top_regions': top_regions,
        'trending_products': trending_products,
        'active_farmers': active_farmers,
        'recent_products': recent_products,
        'market_summary': {
            'total_farmers': total_farmers,
            'total_products': total_products,
            'total_requests': total_requests,
        },
        'selected_location': selected_location,
        'news_items': news_items,
    }
    return render(request, 'index.html', context)
    
    

def user_signup(request):
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save() #Saves user information (e.g., username, email, password) into the built-in Django User model.
            UserProfile.objects.create(
                user=user,
                is_farmer=False,
                phone=form.cleaned_data['phone'],
                city=form.cleaned_data['city'],
                address=form.cleaned_data['address']
            )
            login(request, user)
            return redirect('home')
    else:
        form = UserSignupForm()
    return render(request, 'signup.html', {'form': form, 'user_type': 'user'})

def farmer_signup(request):
    if request.method == 'POST':
        form = FarmerSignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            profile = UserProfile.objects.create(
                user=user,
                is_farmer=True,
                phone=form.cleaned_data['phone'],
                city=form.cleaned_data['city'],
                address=form.cleaned_data['address']
            )
            FarmerProfile.objects.create(
                user_profile=profile,
                farm_name=form.cleaned_data['farm_name'],
                farm_description=form.cleaned_data['farm_description'],
                farm_location=form.cleaned_data['farm_location'],
                farm_image=form.cleaned_data.get('farm_image')
            )
            login(request, user)
            return redirect('farmer_dashboard')
    else:
        form = FarmerSignupForm()
    return render(request, 'signup.html', {'form': form, 'user_type': 'farmer'})

@login_required
def home(request):
    farmers = FarmerProfile.objects.all()
    
    # Don't show the current farmer in the list if user is a farmer
    if request.user.userprofile.is_farmer:
        farmers = farmers.exclude(user_profile=request.user.userprofile)
    
    # Get location parameters
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    radius = request.GET.get('radius')
    
    # If location parameters are provided, filter by distance
    if all([user_lat, user_lng, radius]):
        try:
            nearby_farmers = []
            for farmer in farmers:
                if farmer.latitude and farmer.longitude:
                    distance = calculate_distance(
                        float(user_lat), float(user_lng),
                        float(farmer.latitude), float(farmer.longitude)
                    )
                    if distance <= float(radius):
                        farmer.distance = round(distance, 1)
                        farmer.has_distance = True
                        nearby_farmers.append(farmer)
                else:
                    farmer.has_distance = False
            farmers = sorted(nearby_farmers, key=lambda x: x.distance)
            
            if not farmers:
                messages.info(request, f"No farms found within {radius} km of your location.")
        except Exception as e:
            messages.error(request, "Error calculating distances. Please try again.")
    
    return render(request, 'home.html', {
        'farmers': farmers,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'radius': radius
    })

@login_required
def farmer_profile(request, farmer_id):
    farmer = get_object_or_404(FarmerProfile, id=farmer_id)
    products = Product.objects.filter(farmer=farmer)
    user_rating = None
    if request.user.is_authenticated and not request.user.userprofile.is_farmer:
        user_rating = Rating.objects.filter(
            farmer=farmer,
            user=request.user.userprofile
        ).first()
    
    # Get ratings with their replies
    ratings = Rating.objects.filter(farmer=farmer).prefetch_related('replies').order_by('-created_at')
    
    return render(request, 'farmer_profile.html', {
        'farmer': farmer,
        'products': products,
        'user_rating': user_rating,
        'ratings': ratings
    })

@login_required
def farmer_dashboard(request):
    if not request.user.userprofile.is_farmer:
        messages.error(request, "Access denied. Farmer account required.")
        return redirect('home')
    
    farmer = request.user.userprofile.farmerprofile
    # Get all interests for this farmer's products, ordered by product and date
    interests = Interest.objects.filter(
        product__farmer=farmer
    ).select_related(
        'product', 
        'user__user'
    ).order_by('product', '-created_at')

    context = {
        'farmer': farmer,
        'interests': interests,
        'product_form': ProductForm()
    }
    return render(request, 'farmer_dashboard.html', context)

@login_required
def update_profile(request):
    if not request.user.userprofile.is_farmer:
        return redirect('home')
    
    farmer = request.user.userprofile.farmerprofile
    if request.method == 'POST':
        farmer.farm_name = request.POST.get('farm_name')
        farmer.farm_description = request.POST.get('farm_description')
        farmer.farm_location = request.POST.get('farm_location')
        farmer.latitude = request.POST.get('latitude')
        farmer.longitude = request.POST.get('longitude')
        
        if request.FILES.get('farm_image'):
            farmer.farm_image = request.FILES['farm_image']
        
        farmer.save()
        messages.success(request, 'Profile updated successfully!')
    return redirect('farmer_dashboard')

@login_required
def add_product(request):
    if not request.user.userprofile.is_farmer:
        return redirect('home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user.userprofile.farmerprofile
            product.save()
            messages.success(request, 'Product added successfully!')
    return redirect('farmer_dashboard')

@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.farmer.user_profile.user != request.user:
        messages.error(request, "You can only edit your own products.")
        return redirect('farmer_dashboard')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
        else:
            messages.error(request, 'Error updating product. Please check the form.')
    return redirect('farmer_dashboard')

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.farmer.user_profile.user != request.user:
        messages.error(request, "You can only delete your own products.")
        return redirect('farmer_dashboard')
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
    return redirect('farmer_dashboard')


@login_required
def generate_request(request):
    if request.method == "POST":
        product_name = request.POST.get('product_name')
        quantity=request.POST.get('quantity')
        district=request.POST.get('district')
        message = request.POST.get('message')

        if product_name and quantity and district:
            ProductRequest.objects.create(user=request.user, product_name=product_name, message=message, quantity=quantity, district=district)
        
        return redirect('user_profile')  # Redirect back to the profile page

    return render(request, 'user_profile.html')

@login_required
def delete_interest(request, interest_id):
    interest = get_object_or_404(ProductRequest, id=interest_id, user=request.user)
    interest.delete()
    return redirect('user_profile')

@login_required
def find_buyers(request):
    commodity_query = request.GET.get('q', '').strip()
    district_query = request.GET.get('district', '').strip()

    buyer_requests = ProductRequest.objects.all()

    if commodity_query:
        buyer_requests = buyer_requests.filter(product_name__icontains=commodity_query)

    if district_query:
        buyer_requests = buyer_requests.filter(district__icontains=district_query)

    total_buyers = buyer_requests.count()
    return render(request, 'find_buyers.html', {
        'buyer_requests': buyer_requests,
        'commodity_query': commodity_query,
        'district_query': district_query,
        'total_buyers': total_buyers
    })

@login_required
def show_interest(request, product_id):
    if request.user.userprofile.is_farmer:
        messages.error(request, "Farmers cannot show interest in products.")
        return redirect('home')
    
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        Interest.objects.create(
            product=product,
            user=request.user.userprofile,
            message=request.POST.get('message', '')
        )
        messages.success(request, 'Interest shown successfully!')
    return redirect('farmer_profile', farmer_id=product.farmer.id)

def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('index')

@login_required
def user_profile(request):
    if request.user.userprofile.is_farmer:
        return redirect('farmer_dashboard')
    
    interests = Interest.objects.filter(user=request.user.userprofile).order_by('-created_at')
    return render(request, 'user_profile.html', {
        'interests': interests
    })

@login_required
def update_user_profile(request):
    if request.method == 'POST':
        user = request.user
        profile = user.userprofile
        
        user.email = request.POST.get('email')
        profile.phone = request.POST.get('phone')
        profile.city = request.POST.get('city')
        profile.address = request.POST.get('address')
        
        user.save()
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('user_profile')
    
    return redirect('user_profile')

@login_required
def change_username(request):
    if request.method == 'POST':
        new_username = request.POST.get('new_username')
        if new_username:
            if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                messages.error(request, 'Username already exists.')
            else:
                request.user.username = new_username
                request.user.save()
                messages.success(request, 'Username updated successfully!')
        else:
            messages.error(request, 'Username cannot be empty.')
    return redirect('farmer_dashboard' if request.user.userprofile.is_farmer else 'user_profile')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
        else:
            messages.error(request, 'Please correct the errors below.')
    return redirect('farmer_dashboard' if request.user.userprofile.is_farmer else 'user_profile')

@login_required
def send_sms_to_interested(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        if product.farmer.user_profile.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        interests = Interest.objects.filter(product=product)
        
        # Collect phone numbers
        phone_numbers = [interest.user.phone for interest in interests]
        
        # Here you would integrate with your SMS service
        # For example, using Twilio:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # for interest in interests:
        #     phone = interest.user.phone
        #     # Send SMS logic here
        #     message = client.messages.create(
        #         body=f"Update about {product.name} from {product.farmer.farm_name}",
        #         from_=settings.TWILIO_PHONE_NUMBER,
        #         to=phone
        #     )
        
        return JsonResponse({'success': True, 'phoneNumbers': phone_numbers})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def search(request):
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')
    region = request.GET.get('region', '')  # New parameter for region filtering
    
    results = {'farms': [], 'products': []}
    
    if search_type in ['all', 'farms']:
        farms_query = FarmerProfile.objects.select_related('user_profile').all()
        
        # Apply region filter if specified
        if region:
            farms_query = farms_query.filter(user_profile__city__iexact=region)
        
        # Apply search query if specified
        if query:
            farms_query = farms_query.filter(
                Q(farm_name__icontains=query) |
                Q(farm_description__icontains=query) |
                Q(farm_location__icontains=query)
            )
        
        results['farms'] = farms_query
    
    if search_type in ['all', 'products']:
        products_query = Product.objects.select_related('farmer__user_profile').all()
        
        # Apply region filter if specified
        if region:
            products_query = products_query.filter(farmer__user_profile__city__iexact=region)
        
        # Apply search query if specified
        if query:
            products_query = products_query.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(farmer__farm_name__icontains=query)
            )
        
        results['products'] = products_query
    
    # Get unique regions for the filter dropdown
    regions = UserProfile.objects.filter(is_farmer=True).values_list('city', flat=True).distinct().order_by('city')
    
    context = {
        'query': query,
        'search_type': search_type,
        'results': results,
        'selected_region': region,
        'regions': regions,
    }
    return render(request, 'search_results.html', context)

@login_required
def rate_farmer(request, farmer_id):
    if request.method == 'POST':
        farmer = get_object_or_404(FarmerProfile, id=farmer_id)
        if request.user.userprofile.is_farmer:
            messages.error(request, "Farmers cannot rate other farmers.")
            return redirect('farmer_profile', farmer_id=farmer_id)
        
        rating_value = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if rating_value:
            rating, created = Rating.objects.update_or_create(
                farmer=farmer,
                user=request.user.userprofile,
                defaults={'rating': rating_value, 'comment': comment}
            )
            messages.success(request, 'Rating submitted successfully!')
        else:
            messages.error(request, 'Please select a rating.')
    
    return redirect('farmer_profile', farmer_id=farmer_id)

@login_required
def reply_to_rating(request, rating_id):
    rating = get_object_or_404(Rating, id=rating_id)
    if request.method == 'POST' and request.user.userprofile.is_farmer:
        if request.user.userprofile.farmerprofile == rating.farmer:
            reply_text = request.POST.get('reply_text')
            if reply_text:
                Reply.objects.create(
                    rating=rating,
                    farmer=rating.farmer,
                    reply_text=reply_text
                )
                messages.success(request, 'Reply posted successfully!')
            else:
                messages.error(request, 'Reply cannot be empty.')
        else:
            messages.error(request, 'You can only reply to reviews of your farm.')
    return redirect('farmer_dashboard')

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

@login_required
def nearby_farms(request):
    radius = float(request.GET.get('radius', 10))  # Default 10km radius
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    
    if not user_lat or not user_lng:
        messages.error(request, "Location access is required to find nearby farms.")
        return redirect('home')
    
    # Get all farms
    farms = FarmerProfile.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    
    # Calculate distances and filter
    nearby_farms = []
    for farm in farms:
        distance = calculate_distance(
            user_lat, user_lng,
            farm.latitude, farm.longitude
        )
        if distance <= radius:
            farm.distance = round(distance, 1)
            nearby_farms.append(farm)
    
    # Sort by distance
    nearby_farms.sort(key=lambda x: x.distance)
    
    return render(request, 'nearby_farms.html', {
        'farms': nearby_farms,
        'radius': radius,
        'user_lat': user_lat,
        'user_lng': user_lng
    })

def market_prices(request):
    # API section parameters
    selected_state = request.GET.get('state')
    selected_commodity = request.GET.get('commodity')
    page = int(request.GET.get('page', 1))
    per_page = 10
    
    # Prediction section parameters
    prediction_district = request.GET.get('prediction_district')
    prediction_commodity = request.GET.get('prediction_commodity')
    
    # Get market data for API section
    market_data = get_market_prices(selected_state, selected_commodity)
    
    # Get price predictions if prediction parameters are provided
    price_predictions = None
    if prediction_district and prediction_commodity:
        price_predictions = predict_price(prediction_commodity, prediction_district)
    
    # Get districts from CSV file for prediction section
    gujarat_districts = []
    try:
        csv_path = os.path.join('farmprj', 'data', 'mandibhav.csv')
        df = pd.read_csv(csv_path)
        gujarat_districts = sorted(df['District'].unique())
    except Exception as e:
        print(f"Error loading districts: {e}")
    
    return render(request, 'market_prices.html', {
        'market_data': market_data,
        'states': sorted(INDIAN_STATES),
        'commodities': COMMON_COMMODITIES,
        'selected_state': selected_state,
        'selected_commodity': selected_commodity,
        'gujarat_districts': gujarat_districts,
        'prediction_district': prediction_district,
        'prediction_commodity': prediction_commodity,
        'price_predictions': price_predictions,
    })

@staff_member_required
def admin_analytics(request):
    try:
        # Get active news items
        news_items = News.objects.filter(
            expiry_date__gt=timezone.now(),
            is_active=True
        ).order_by('-created_at')
        
        # Get total buyers (users who are not farmers)
        total_buyers = UserProfile.objects.filter(is_farmer=False).count()
        
        # Get total products
        total_products = Product.objects.count()
        
        # Get total regions (unique cities)
        total_regions = UserProfile.objects.values('city').distinct().count()
        
        # Products by region analysis
        products_by_region = (
            Product.objects.select_related('farmer__user_profile')
            .values('farmer__user_profile__city')
            .annotate(
                region=F('farmer__user_profile__city'),
                count=Count('id'),
                total_quantity=Sum('quantity')
            )
            .order_by('-count')
        )
        
        # Most requested products analysis
        product_requests = (
            ProductRequest.objects.values('product_name')
            .annotate(
                request_count=Count('id'),
                total_quantity=Sum('quantity')
            )
            .order_by('-request_count')
        )
        
        # Buyers by region analysis
        buyers_by_region = (
            UserProfile.objects.filter(is_farmer=False)
            .values('city')
            .annotate(
                region=F('city'),
                buyer_count=Count('id'),
                request_count=Count('user__productrequest')
            )
            .order_by('-buyer_count')
        )
        
        context = {
            'news_items': news_items,
            'total_buyers': total_buyers,
            'total_products': total_products,
            'total_regions': total_regions,
            'products_by_region': products_by_region,
            'product_requests': product_requests,
            'buyers_by_region': buyers_by_region,
        }
        
        return render(request, 'admin_analytics.html', context)
    except Exception as e:
        messages.error(request, f'Error loading admin analytics: {str(e)}')
        return redirect('index')

@staff_member_required
def add_news(request):
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            content = request.POST.get('content')
            expiry_days = int(request.POST.get('expiry_days', 7))
            
            if not title or not content:
                messages.error(request, 'Title and content are required!')
                return redirect('admin_analytics')
            
            expiry_date = timezone.now() + timedelta(days=expiry_days)
            
            news = News.objects.create(
                title=title,
                content=content,
                expiry_date=expiry_date,
                is_active=True
            )
            
            messages.success(request, f'News item "{title}" added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding news: {str(e)}')
        
    return redirect('admin_analytics')

@staff_member_required
def delete_news(request, news_id):
    try:
        news = get_object_or_404(News, id=news_id)
        title = news.title
        news.delete()
        messages.success(request, f'News item "{title}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting news: {str(e)}')
    return redirect('admin_analytics')