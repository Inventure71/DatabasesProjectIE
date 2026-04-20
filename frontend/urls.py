from django.urls import path
from . import views
 
urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<int:card_id>/', views.card_detail, name='card_detail'),
    path('collection/', views.collection, name='collection'),
    path('my-listings/', views.my_listings, name='my_listings'),
    path('listings/', views.listings, name='listings'),
    path('listings/<int:listing_id>/', views.listing_detail, name='listing_detail'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
 
