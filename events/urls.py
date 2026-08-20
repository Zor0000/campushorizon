from django.urls import path
from events import views

app_name = 'events'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('hackathons/', views.hackathons, name='hackathons'),
    path('tech-events/', views.tech_events, name='tech_events'),
]
