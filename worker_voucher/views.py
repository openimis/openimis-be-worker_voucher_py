import logging

from django.db import transaction
from rest_framework import status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.utils import DefaultStorageFileHandler
from im_export.views import check_user_rights
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerUpload
from policyholder.models import PolicyHolder
from worker_voucher.services import WorkerUploadService
from insuree.apps import InsureeConfig

logger = logging.getLogger(__name__)


class WorkerUploadAPIView(views.APIView):
    permission_classes = [check_user_rights(InsureeConfig.gql_mutation_create_insurees_perms, )]

    @transaction.atomic
    def post(self, request):
        upload = WorkerUpload()
        economic_unit_code = request.GET.get('economic_unit_code')
        try:
            upload.save(username=request.user.login_name)
            file = request.FILES.get('file')
            target_file_path = WorkerVoucherConfig.get_worker_upload_payment_file_path(economic_unit_code, file.name)
            upload.file_name = file.name
            file_handler = DefaultStorageFileHandler(target_file_path)
            service = WorkerUploadService(request.user)
            file_to_upload, errors, summary = service.upload_worker(economic_unit_code, file, upload)
            print(errors, 'xxxx')
            print(summary)
            if errors:
                upload.status = WorkerUpload.Status.PARTIAL_SUCCESS
                upload.error = errors
                upload.json_ext = {'extra_info': summary}
            else:
                upload.status = WorkerUpload.Status.SUCCESS
                upload.json_ext = {'extra_info': summary}
            upload.save(username=request.user.login_name)
            file_handler.save_with_possibility_to_overwrite_file(file_to_upload)
            return Response({'success': True, 'error': errors, 'summary': summary}, status=201)
        except Exception as exc:
            logger.error("Error while uploading workers", exc_info=exc)
            if upload:
                upload.error = {'error': str(exc)}
                upload.policyholder = PolicyHolder.objects.filter(code=economic_unit_code).first()
                upload.status = WorkerUpload.Status.FAIL
                summary = {
                    'affected_rows': 0,
                }
                upload.json_ext = {'extra_info': summary}
                upload.save(username=request.user.login_name)
            return Response({'success': False, 'error': str(exc), 'summary': summary}, status=500)


@api_view(["GET"])
@permission_classes([check_user_rights(InsureeConfig.gql_mutation_create_insurees_perms, )])
def download_worker_upload(request):
    try:
        filename = request.query_params.get('filename')
        economic_unit_code = request.query_params.get('economic_unit_code')
        target_file_path = WorkerVoucherConfig.get_worker_upload_payment_file_path(economic_unit_code, filename)
        file_handler = DefaultStorageFileHandler(target_file_path)
        return file_handler.get_file_response_csv(filename)

    except ValueError as exc:
        logger.error("Error while fetching data", exc_info=exc)
        return Response({'success': False, 'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except FileNotFoundError as exc:
        logger.error("Error while getting file", exc_info=exc)
        return Response({'success': False, 'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.error("Unexpected error", exc_info=exc)
        return Response({'success': False, 'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
