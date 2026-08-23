from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('health/', lambda r: HttpResponse('ok', content_type='text/plain')),
    path('healthz/', lambda r: HttpResponse('ok', content_type='text/plain')),
    path('admin/', admin.site.urls),
    path('', include('events.urls')),
]
