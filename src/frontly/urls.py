#from django.conf import settings
from django.urls import include, path

from . import views


app_name = 'frontly'

urlpatterns = [
    path('', views.frontly_editor, name='editor'),

    # Fragments
]
