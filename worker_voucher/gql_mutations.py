import graphene as graphene
from django.db import transaction
from pydantic.error_wrappers import ValidationError
from django.contrib.auth.models import AnonymousUser

from core.gql.gql_mutations.base_mutation import BaseMutation
from core.schema import OpenIMISMutation
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import WorkerVoucherService


class CreateWorkerVoucherInput(OpenIMISMutation.Input):
    code = graphene.String(max_length=255, required=True)
    status = graphene.String(max_length=255, required=False)
    assigned_date = graphene.Date(required=True)
    expiry_date = graphene.Date(required=True)
    insuree_id = graphene.Int(required=True)
    policyholder_id = graphene.ID(required=True)
    json_ext = graphene.types.json.JSONString(required=False)


class UpdateWorkerVoucherInput(CreateWorkerVoucherInput):
    id = graphene.ID(required=True)


class CreateWorkerVoucherMutation(BaseMutation):
    _mutation_class = "CreateWorkerVoucherMutation"
    _mutation_module = "worker_voucher"
    _model = WorkerVoucher

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(
                WorkerVoucherConfig.gql_worker_voucher_create_perms):
            raise ValidationError("mutation.authentication_required")

    @classmethod
    def _mutate(cls, user, **data):
        if "client_mutation_id" in data:
            data.pop('client_mutation_id')
        if "client_mutation_label" in data:
            data.pop('client_mutation_label')

        service = WorkerVoucherService(user)
        response = service.create(data)
        if not response['success']:
            return response
        return None

    class Input(CreateWorkerVoucherInput):
        pass


class UpdateWorkerVoucherMutation(BaseMutation):
    _mutation_class = "UpdateWorkerVoucherMutation"
    _mutation_module = "worker_voucher"
    _model = WorkerVoucher

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(
                WorkerVoucherConfig.gql_worker_voucher_update_perms):
            raise ValidationError("mutation.authentication_required")

    @classmethod
    def _mutate(cls, user, **data):
        if "client_mutation_label" in data:
            data.pop('client_mutation_label')

        service = WorkerVoucherService(user)
        response = service.update(data)
        if not response['success']:
            return response
        return None

    class Input(UpdateWorkerVoucherInput):
        pass


class DeleteWorkerVoucherMutation(BaseMutation):
    _mutation_class = "DeleteWorkerVoucherMutation"
    _mutation_module = "worker_voucher"
    _model = WorkerVoucher

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(
                WorkerVoucherConfig.gql_worker_voucher_delete_perms):
            raise ValidationError("mutation.authentication_required")

    @classmethod
    def _mutate(cls, user, **data):
        if "client_mutation_id" in data:
            data.pop('client_mutation_id')
        if "client_mutation_label" in data:
            data.pop('client_mutation_label')

        service = WorkerVoucherService(user)
        ids = data.get('ids')
        if ids:
            with transaction.atomic():
                for id in ids:
                    service.delete({'id': id})

    class Input(OpenIMISMutation.Input):
        ids = graphene.List(graphene.UUID)
