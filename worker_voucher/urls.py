from django.urls import path

from worker_voucher.views import WorkerUploadAPIView

urlpatterns = [
    path('worker_upload/', WorkerUploadAPIView.as_view()),
]
