from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.permissions import role_required


@login_required
@role_required("veterinary")
def dashboard_view(request):
    return render(request, "veterinary_dashboard/dashboard.html")
