from django.shortcuts import render


def customer_page(request):
    return render(request, "customer.html")


def admin_page(request):
    return render(request, "manage.html")
