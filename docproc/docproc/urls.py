from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from documents import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_document, name='upload'),
    path('documents/<int:document_id>/', views.document_detail, name='document_detail'),
    path('documents/<int:document_id>/mark-validated/', views.mark_as_validated, name='mark_as_validated'),
    path('documents/<int:document_id>/reject/', views.reject_document, name='reject_document'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
