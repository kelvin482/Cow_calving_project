from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.permissions import role_required


@login_required
@role_required("farmer")
def dashboard_view(request):
    return render(request, "farmers_dashboard/dashboard.html")
