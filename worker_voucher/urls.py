from django.urls import path

from worker_voucher.views import WorkerUploadAPIView, download_worker_upload

urlpatterns = [
    path('worker_upload/', WorkerUploadAPIView.as_view()),
    path('download_worker_upload_file/', download_worker_upload),
]
