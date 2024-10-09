import logging

from django.db import transaction
from rest_framework import views
from rest_framework.response import Response

from core.utils import DefaultStorageFileHandler
from im_export.views import check_user_rights
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import Payroll, CsvReconciliationUpload
from worker_voucher.services import CsvReconciliationService

logger = logging.getLogger(__name__)


class WorkerUploadAPIView(views.APIView):
    permission_classes = [check_user_rights(WorkerVoucherConfig.gql_worker_voucher_create_perms, )]

    @transaction.atomic
    def post(self, request):
        upload = CsvReconciliationUpload()
        economic_unit_id = request.GET.get('economic_unit_id')
        try:
            upload.save(username=request.user.login_name)
            file = request.FILES.get('file')
            target_file_path = WorkerVoucherConfig.get_payroll_payment_file_path(payroll_id, file.name)
            upload.file_name = file.name
            file_handler = DefaultStorageFileHandler(target_file_path)
            file_handler.check_file_path()
            service = CsvReconciliationService(request.user)
            file_to_upload, errors, summary = service.upload_reconciliation(payroll_id, file, upload)
            if errors:
                upload.status = CsvReconciliationUpload.Status.PARTIAL_SUCCESS
                upload.error = errors
                upload.json_ext = {'extra_info': summary}
            else:
                upload.status = CsvReconciliationUpload.Status.SUCCESS
                upload.json_ext = {'extra_info': summary}
            upload.save(username=request.user.login_name)
            file_handler.save_file(file_to_upload)
            return Response({'success': True, 'error': None}, status=201)
        except Exception as exc:
            logger.error("Error while uploading CSV reconciliation", exc_info=exc)
            if upload:
                upload.error = {'error': str(exc)}
                upload.payroll = Payroll.objects.filter(id=payroll_id).first()
                upload.status = CsvReconciliationUpload.Status.FAIL
                summary = {
                    'affected_rows': 0,
                }
                upload.json_ext = {'extra_info': summary}
                upload.save(username=request.user.login_name)
            return Response({'success': False, 'error': str(exc)}, status=500)
