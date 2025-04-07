from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Product

class UserSignupForm(UserCreationForm):
    #UserCreationForm (which UserSignupForm extends) already includes the username, password1, and password2 fields by default.
    #If you want to control which fields appear, modify the fields tuple in the Meta class.
    #if remove meta then this 4 field will show only
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    class Meta:
        model = User 
        fields = ('username', 'email', 'password1', 'password2', 'phone', 'city', 'address')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):#it use for designe,you can add styling using widgets inside the Meta class:
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'

class FarmerSignupForm(UserSignupForm):
    farm_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    farm_description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    farm_location = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control'}))
    farm_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
#This means that this form is a ModelForm connected to the Product model.
#When you use form.save(), it automatically saves the data to the Product table in your database.
        fields = ['name', 'description', 'price', 'quantity', 'image']
        labels = {
            'price': 'Price (Rs.)',
            'quantity': 'Quantity (kg)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        } 