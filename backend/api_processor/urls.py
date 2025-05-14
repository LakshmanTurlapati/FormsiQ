"""
URL configuration for the API processor.
"""
from django.urls import path
from .views import ExtractFieldsView, FillPDFView, GetPDFFieldsView

urlpatterns = [
    path('extract-fields', ExtractFieldsView.as_view(), name='extract-fields'),
    path('fill-pdf', FillPDFView.as_view(), name='fill-pdf'),
    path('pdf-fields', GetPDFFieldsView.as_view(), name='pdf-fields'),
] 