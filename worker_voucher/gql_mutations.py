import graphene as graphene
from django.db import transaction
from django.utils.translation import gettext as _
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from uuid import uuid4

from core import datetime
from core.gql.gql_mutations.base_mutation import BaseMutation
from core.models import MutationLog
from core.schema import OpenIMISMutation
from insuree.gql_mutations import CreateInsureeMutation, CreateInsureeInputType
from insuree.models import Insuree
from policyholder.models import PolicyHolder, PolicyHolderInsuree
from policyholder.services import PolicyHolderInsuree as PolicyHolderInsureeService
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import WorkerVoucherService, validate_acquire_unassigned_vouchers, \
    validate_acquire_assigned_vouchers, validate_assign_vouchers, create_assigned_voucher, create_voucher_bill, \
    create_unassigned_voucher, assign_voucher, policyholder_user_filter


class CreateWorkerVoucherInput(OpenIMISMutation.Input):
    code = graphene.String(max_length=255, required=True)
    status = graphene.String(max_length=255, required=False)
    assigned_date = graphene.Date(required=True)
    expiry_date = graphene.Date(required=True)
    insuree_id = graphene.Int(required=True)
    policyholder_id = graphene.ID(required=True)
    json_ext = graphene.types.json.JSONString(required=False)


class CreateWorkerMutation(CreateInsureeMutation):
    """
    Create a new worker
    """
    _mutation_module = "worker_voucher"
    _mutation_class = "CreateWorkerMutation"

    class Input(CreateInsureeInputType):
        economic_unit_code = graphene.String(required=True)

    @classmethod
    def async_mutate(cls, user, **data):
        user_policyholders = PolicyHolder.objects.filter(
            policyholder_user_filter(user)).values_list('id', flat=True)
        economic_unit_code = data.pop('economic_unit_code', None)
        chf_id = data.get('chf_id', None)
        ph = PolicyHolder.objects.filter(
            code=economic_unit_code,
            is_deleted=False,
        ).first()
        if not ph:
            return [{"message": _("workers.validation.economic_unit_not_exist")}]
        if ph.id not in user_policyholders:
            return [
                {
                    "message": _("workers.validation.no_authority_to_use_selected_economic_unit")
                }
            ]
        if economic_unit_code:
            phi = PolicyHolderInsuree.objects.filter(
                insuree__chf_id=chf_id,
                policy_holder__code=economic_unit_code,
                is_deleted=False,
            ).first()
            if not phi:
                result = None
                worker = Insuree.objects.filter(chf_id=chf_id).first()
                if not worker:
                    result = super().async_mutate(user, **data)
                if not result:
                    worker = Insuree.objects.filter(chf_id=chf_id).first()
                    policy_holder_insuree_service = PolicyHolderInsureeService(user)
                    policy_holder = PolicyHolder.objects.get(code=economic_unit_code, is_deleted=False)
                    policy_holder_insuree = {
                        'policy_holder_id': f'{policy_holder.id}',
                        'insuree_id': worker.id,
                        'contribution_plan_bundle_id': None,
                    }
                    policy_holder_insuree_service.create(policy_holder_insuree)
                else:
                    return result
            else:
                return [{"message": _("workers.validation.worker_already_assigned_to_unit")}]
        return None


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
        client_mutation_id = data.pop('client_mutation_id', None)
        client_mutation_label = data.pop('client_mutation_label', None)

        validate_result = validate_acquire_unassigned_vouchers(user, economic_unit_code, count)
        if not validate_result.get("success", False):
            return validate_result


        policyholder_id = validate_result.get("data").get("policyholder").id
        voucher_ids = []
        with transaction.atomic():
            for _ in range(validate_result.get("data").get("count")):
                voucher_ids.append(create_unassigned_voucher(user, policyholder_id))

            bill = create_voucher_bill(user, voucher_ids, policyholder_id)

            mutation = MutationLog.objects.get(
                client_mutation_id=client_mutation_id,
                client_mutation_label=client_mutation_label)

            mutation.json_ext = {'worker_voucher': {'bill_id': bill['data']['uuid']}}
            mutation.save()
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
        client_mutation_id = data.pop('client_mutation_id', None)
        client_mutation_label = data.pop('client_mutation_label', None)

        validate_result = validate_acquire_assigned_vouchers(user, economic_unit_code, workers, date_ranges)
        if not validate_result.get("success", False):
            return validate_result

        policyholder_id = validate_result.get("data").get("policyholder").id
        voucher_ids = []
        with transaction.atomic():
            for date in validate_result.get("data").get("dates"):
                for insuree in validate_result.get("data").get("insurees"):
                    voucher_ids.append(create_assigned_voucher(user, date, insuree.id, policyholder_id))
            if not voucher_ids:
                raise ValidationError("worker_voucher.validation.no_vouchers_created")

            bill = create_voucher_bill(user, voucher_ids, policyholder_id)
            mutation = MutationLog.objects.get(
                client_mutation_id=client_mutation_id,
                client_mutation_label=client_mutation_label)

            mutation.json_ext = {'worker_voucher': {'bill_id': bill['data']['uuid']}}
            mutation.save()
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

        voucher_ids = []
        vouchers = validate_result.get("data").get("unassigned_vouchers")
        with transaction.atomic():
            for date in validate_result.get("data").get("dates"):
                for insuree in validate_result.get("data").get("insurees"):
                    voucher = vouchers.pop(0)
                    voucher_ids.append(assign_voucher(user, insuree.id, voucher.id, date))
        return None

    class Input(AssignVouchersMutationInput):
        pass
