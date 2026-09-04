"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import path
from chores import views

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', views.health_check, name='health-check'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', views.UserLoginView.as_view(), name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('households/create/', views.household_create, name='household-create'),
    path('households/join/', views.household_join, name='household-join'),
    path('chores/', views.dashboard, name='dashboard'),
    path('chores/new/', views.chore_create, name='chore-create'),
    path('chores/<int:pk>/edit/', views.chore_edit, name='chore-edit'),
    path('chores/<int:pk>/delete/', views.chore_delete, name='chore-delete'),
    path(
        'chores/<int:chore_id>/occurrence/<str:due_date>/assign/',
        views.occurrence_override,
        name='occurrence-override',
    ),
    path('occurrences/<int:occurrence_id>/complete/', views.occurrence_complete, name='occurrence-complete'),
    path('admin/', admin.site.urls),
]
