from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, 'chores/home.html')


def health_check(request):
    return JsonResponse({'status': 'ok'})
