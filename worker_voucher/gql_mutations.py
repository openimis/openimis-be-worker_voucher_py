import graphene as graphene
from django.db import transaction
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from uuid import uuid4

from core import datetime
from core.gql.gql_mutations.base_mutation import BaseMutation
from core.schema import OpenIMISMutation
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import WorkerVoucherService, validate_acquire_unassigned_vouchers, \
    validate_acquire_assigned_vouchers, validate_assign_vouchers


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
        data.pop('client_mutation_id', None)
        data.pop('client_mutation_label', None)

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
        data.pop('client_mutation_id', None)
        data.pop('client_mutation_label', None)

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
        data.pop('client_mutation_id', None)
        data.pop('client_mutation_label', None)

        service = WorkerVoucherService(user)
        ids = data.get('ids')
        if ids:
            with transaction.atomic():
                for id in ids:
                    service.delete({'id': id})

    class Input(OpenIMISMutation.Input):
        ids = graphene.List(graphene.UUID)


class AcquireUnassignedVouchersMutation(BaseMutation):
    _mutation_class = "AcquireUnassignedVouchersMutation"
    _mutation_module = "worker_voucher"
    _model = WorkerVoucher

    @classmethod
    def _validate_mutation(cls, user, **data):
        if not WorkerVoucherConfig.unassigned_voucher_enabled:
            raise ValidationError("worker_voucher.validation.unassigned_voucher_disabled")

        if type(user) is AnonymousUser or not user.id or not user.has_perms(
                WorkerVoucherConfig.gql_worker_voucher_acquire_unassigned_perms):
            raise ValidationError("mutation.authentication_required")

    @classmethod
    def _mutate(cls, user, count=None, economic_unit_code=None, **data):
        data.pop('client_mutation_id', None)
        data.pop('client_mutation_label', None)

        validate_result = validate_acquire_unassigned_vouchers(user, economic_unit_code, count)
        if not validate_result.get("success", False):
            return validate_result

        expiry_period = WorkerVoucherConfig.voucher_expiry_period

        service = WorkerVoucherService(user)
        voucher_ids = []
        with transaction.atomic():
            for _ in range(validate_result.get("data").get("count")):
                service_result = service.create({
                    "policyholder_id": validate_result.get("data").get("policyholder").id,
                    "code": str(uuid4()),
                    "expiry_date": datetime.datetime.now() + datetime.datetimedelta(**expiry_period)

                })
        if service_result.get("success", False):
            voucher_ids.append(service_result.get("data").get("id"))
        else:
            raise Exception(service_result["error"])

        # TODO integrate with mPay and send payment request
        return None

    class Input(OpenIMISMutation.Input):
        economic_unit_code = graphene.ID(required=True)
        count = graphene.Int(required=True)


class DateRangeInclusiveInputType(graphene.InputObjectType):
    start_date = graphene.Date(required=True)
    end_date = graphene.Date(required=True)


class AcquireAssignedVouchersMutationInput(OpenIMISMutation.Input):
    economic_unit_code = graphene.ID(required=True)
    date_ranges = graphene.List(DateRangeInclusiveInputType, required=True)
    workers = graphene.List(graphene.ID, required=True)


class AcquireAssignedVouchersMutation(BaseMutation):
    _mutation_class = "AcquireAssignedVouchersMutation"
    _mutation_module = "worker_voucher"
    _model = WorkerVoucher

    @classmethod
    def _validate_mutation(cls, user, **data):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(
                WorkerVoucherConfig.gql_worker_voucher_acquire_assigned_perms):
            raise ValidationError("mutation.authentication_required")

    @classmethod
    def _mutate(cls, user, count=None, economic_unit_code=None, workers=None, date_ranges=None, **data):
        data.pop('client_mutation_id', None)
        data.pop('client_mutation_label', None)

        validate_result = validate_acquire_assigned_vouchers(user, economic_unit_code, workers, date_ranges)
        if not validate_result.get("success", False):
            return validate_result

        expiry_period = WorkerVoucherConfig.voucher_expiry_period

        service = WorkerVoucherService(user)
        voucher_ids = []
        with transaction.atomic():
            for date in validate_result.get("data").get("dates"):
                for insuree in validate_result.get("data").get("insurees"):
                    service_result = service.create({
                        "policyholder_id": validate_result.get("data").get("policyholder").id,
                        "insuree_id": insuree.id,
                        "code": str(uuid4()),
                        "assigned_date": date,
                        "expiry_date": datetime.datetime.now() + datetime.datetimedelta(**expiry_period)
                    })
                    if service_result.get("success", True):
                        voucher_ids.append(service_result.get("data").get("id"))
                    else:
                        raise Exception(service_result["error"])

        # TODO integrate with mPay and send payment request
        return None

    class Input(AcquireAssignedVouchersMutationInput):
        pass


class AssignVouchersMutationInput(OpenIMISMutation.Input):
    economic_unit_code = graphene.ID(required=True)
    date_ranges = graphene.List(DateRangeInclusiveInputType, required=True)
    workers = graphene.List(graphene.ID, required=True)


class AssignVouchersMutation(BaseMutation):
    _mutation_class = "AssignVouchersMutation"
    _mutation_module = "worker_voucher"
    _model = WorkerVoucher

    @classmethod
    def _validate_mutation(cls, user, **data):
        if not WorkerVoucherConfig.unassigned_voucher_enabled:
            raise ValidationError("worker_voucher.validation.unassigned_voucher_disabled")

        if type(user) is AnonymousUser or not user.id or not user.has_perms(
                WorkerVoucherConfig.gql_worker_voucher_assign_vouchers_perms):
            raise ValidationError("mutation.authentication_required")

    @classmethod
    def _mutate(cls, user, count=None, economic_unit_code=None, workers=None, date_ranges=None, **data):
        data.pop('client_mutation_id', None)
        data.pop('client_mutation_label', None)

        validate_result = validate_assign_vouchers(user, economic_unit_code, workers, date_ranges)
        if not validate_result.get("success", False):
            return validate_result

        service = WorkerVoucherService(user)
        voucher_ids = []
        vouchers = validate_result.get("data").get("unassigned_vouchers")
        with transaction.atomic():
            for date in validate_result.get("data").get("dates"):
                for insuree in validate_result.get("data").get("insurees"):
                    voucher = vouchers.pop(0)
                    service_result = service.update({
                        "id": voucher.id,
                        "insuree_id": insuree.id,
                        "assigned_date": date,
                        "status": WorkerVoucher.Status.ASSIGNED,
                    })
                    if service_result.get("success", True):
                        voucher_ids.append(service_result.get("data").get("id"))
                    else:
                        raise Exception(service_result["error"])

        # TODO integrate with mPay and send payment request
        return None

    class Input(AssignVouchersMutationInput):
        pass
