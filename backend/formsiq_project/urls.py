"""
URL configuration for formsiq_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def api_root(request):
    """API root endpoint"""
    return JsonResponse({
        'message': 'FormsIQ API',
        'version': '1.0',
        'endpoints': {
            'health': '/api/health/',
            'extract_fields': '/api/extract-fields/',
            'fill_pdf': '/api/fill-pdf/',
            'pdf_fields': '/api/pdf-fields/'
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api_processor.urls')),
    # API root for documentation
    path('', api_root, name='api_root'),
]

# Serve media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files  
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
