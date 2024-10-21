import graphene
import graphene_django_optimizer as gql_optimizer

from django.db.models import Q
from django.utils.translation import gettext as _
from django.contrib.auth.models import AnonymousUser

from core.gql.export_mixin import ExportableQueryMixin
from core.schema import OrderedDjangoFilterConnectionField
from core.utils import append_validity_filter, filter_validity
from insuree.apps import InsureeConfig
from insuree.gql_queries import InsureeGQLType
from insuree.models import Insuree
from insuree.services import custom_insuree_number_validation
from msystems.services.mconnect_worker_service import MConnectWorkerService
from policyholder.models import PolicyHolder
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.gql_queries import WorkerVoucherGQLType, AcquireVouchersValidationSummaryGQLType, WorkerGQLType, \
    OnlineWorkerDataGQLType, GroupOfWorkerGQLType, WorkerGroupGQLType
from worker_voucher.gql_mutations import CreateWorkerVoucherMutation, UpdateWorkerVoucherMutation, \
    DeleteWorkerVoucherMutation, AcquireUnassignedVouchersMutation, AcquireAssignedVouchersMutation, \
    DateRangeInclusiveInputType, AssignVouchersMutation, CreateWorkerMutation, DeleteWorkerMutation, \
    CreateOrUpdateGroupOfWorkerMutation, DeleteGroupOfWorkerMutation
from worker_voucher.models import WorkerVoucher, GroupOfWorker, WorkerGroup
from worker_voucher.services import (
    get_voucher_worker_enquire_filters,
    validate_acquire_unassigned_vouchers,
    validate_acquire_assigned_vouchers,
    validate_assign_vouchers,
    economic_unit_user_filter,
    worker_user_filter,
    get_group_worker_user_filters
)


class Query(ExportableQueryMixin, graphene.ObjectType):
    exportable_fields = ['worker_voucher', 'worker']
    module_name = "worker_voucher"

    worker = OrderedDjangoFilterConnectionField(
        WorkerGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        client_mutation_id=graphene.String(),
        economic_unit_code=graphene.String()
    )

    worker_voucher = OrderedDjangoFilterConnectionField(
        WorkerVoucherGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        client_mutation_id=graphene.String(),
    )

    previous_workers = OrderedDjangoFilterConnectionField(
        InsureeGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        economic_unit_code=graphene.String(required=True),
        date_range=DateRangeInclusiveInputType(required=False)
    )

    enquire_worker = OrderedDjangoFilterConnectionField(
        WorkerVoucherGQLType,
        national_id=graphene.String(),
    )

    acquire_unassigned_validation = graphene.Field(
        AcquireVouchersValidationSummaryGQLType,
        economic_unit_code=graphene.ID(),
        count=graphene.Int()
    )

    acquire_assigned_validation = graphene.Field(
        AcquireVouchersValidationSummaryGQLType,
        economic_unit_code=graphene.ID(),
        workers=graphene.List(graphene.ID),
        date_ranges=graphene.List(DateRangeInclusiveInputType)
    )

    assign_vouchers_validation = graphene.Field(
        AcquireVouchersValidationSummaryGQLType,
        economic_unit_code=graphene.ID(),
        workers=graphene.List(graphene.ID),
        date_ranges=graphene.List(DateRangeInclusiveInputType)
    )

    online_worker_data = graphene.Field(
        OnlineWorkerDataGQLType,
        national_id=graphene.String(),
        economic_unit_code=graphene.ID(),
    )

    group_of_worker = OrderedDjangoFilterConnectionField(
        GroupOfWorkerGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        economic_unit_code=graphene.String(),
        client_mutation_id=graphene.String(),
    )

    def resolve_worker(self, info, client_mutation_id=None, economic_unit_code=None, **kwargs):
        Query._check_permissions(info.context.user, InsureeConfig.gql_query_insurees_perms)
        filters = filter_validity(**kwargs)

        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        query = Insuree.get_queryset(None, info.context.user).distinct('id').filter(
            worker_user_filter(info.context.user, economic_unit_code=economic_unit_code),
        )

        return gql_optimizer.query(query.filter(*filters).distinct(), info)

    def resolve_worker_voucher(self, info, client_mutation_id=None, **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_search_perms)
        filters = append_validity_filter(**kwargs)

        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        query = (WorkerVoucher.objects.filter(economic_unit_user_filter(info.context.user, prefix='policyholder__'))
                 .filter(*filters))
        return gql_optimizer.query(query, info)

    def resolve_previous_workers(self, info, economic_unit_code=None, date_range=None, **kwargs):
        Query._check_permissions(info.context.user, InsureeConfig.gql_query_insuree_perms)
        filters = append_validity_filter(**kwargs)

        eu = PolicyHolder.objects.filter(economic_unit_user_filter(info.context.user), code=economic_unit_code).first()
        if not eu:
            return [{"message": _("workers.validation.economic_unit_not_exist")}]

        query = Insuree.get_queryset(None, info.context.user).distinct('id').filter(
            worker_user_filter(info.context.user, economic_unit_code=economic_unit_code),
            workervoucher__is_deleted=False,
            workervoucher__policyholder__is_deleted=False,
            workervoucher__policyholder__code=economic_unit_code,
        )

        if date_range:
            start_date, end_date = date_range.get("start_date"), date_range.get("end_date")
            query = query.filter(workervoucher__assigned_date__in=(start_date, end_date))

        return gql_optimizer.query(query, info)

    def resolve_enquire_worker(self, info, national_id=None, **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_search_perms)
        filters = append_validity_filter(**kwargs)

        if not national_id:
            raise AttributeError(_("National ID required"))

        filters.append(*get_voucher_worker_enquire_filters(national_id))

        query = WorkerVoucher.objects.filter(*filters)
        return gql_optimizer.query(query, info)

    def resolve_acquire_unassigned_validation(self, info, economic_unit_code=None, count=None, **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_acquire_unassigned_perms)
        if not WorkerVoucherConfig.unassigned_voucher_enabled:
            raise AttributeError("worker_voucher.validation.unassigned_voucher_disabled")
        validation_result = validate_acquire_unassigned_vouchers(info.context.user, economic_unit_code, count)

        if not validation_result.get("success", False):
            raise AttributeError(validation_result.get("error", _("Unknown Error")))

        validation_summary = validation_result.get("data")
        validation_summary.pop("policyholder")
        return AcquireVouchersValidationSummaryGQLType(**validation_summary)

    def resolve_acquire_assigned_validation(self, info, economic_unit_code=None, workers=None, date_ranges=None,
                                            **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_acquire_assigned_perms)

        validation_result = validate_acquire_assigned_vouchers(info.context.user, economic_unit_code, workers,
                                                               date_ranges)

        if not validation_result.get("success", False):
            raise AttributeError(validation_result.get("error", _("Unknown Error")))

        validation_summary = validation_result.get("data")
        validation_summary.pop("policyholder")
        validation_summary.pop("insurees")
        validation_summary.pop("dates")
        return AcquireVouchersValidationSummaryGQLType(**validation_summary)

    def resolve_assign_vouchers_validation(self, info, economic_unit_code=None, workers=None, date_ranges=None,
                                           **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_assign_vouchers_perms)
        if not WorkerVoucherConfig.unassigned_voucher_enabled:
            raise AttributeError("worker_voucher.validation.unassigned_voucher_disabled")
        validation_result = validate_assign_vouchers(info.context.user, economic_unit_code, workers, date_ranges)
        if not validation_result.get("success", False):
            raise AttributeError(validation_result.get("error", _("Unknown Error")))

        validation_summary = validation_result.get("data")
        validation_summary.pop("policyholder")
        validation_summary.pop("insurees")
        validation_summary.pop("dates")
        validation_summary.pop("unassigned_vouchers")
        return AcquireVouchersValidationSummaryGQLType(**validation_summary)

    def resolve_online_worker_data(self, info, national_id=None, economic_unit_code=None, **kwargs):
        Query._check_permissions(info.context.user, InsureeConfig.gql_query_insuree_perms)

        eu = PolicyHolder.objects.filter(economic_unit_user_filter(info.context.user), code=economic_unit_code).first()
        if not eu:
            return [{"message": _("workers.validation.economic_unit_not_exist")}]

        if InsureeConfig.get_insuree_number_validator():
            errors = custom_insuree_number_validation(national_id)
            if errors:
                return errors

        online_result = MConnectWorkerService().fetch_worker_data(national_id, info.context.user, eu)
        if not online_result.get("success", False):
            raise AttributeError(online_result.get("error", _("Unknown Error")))

        return OnlineWorkerDataGQLType(
            other_names=online_result["data"]["GivenName"],
            last_name=online_result["data"]["FamilyName"],
            photo=online_result["data"]["Photo"]
        )

    def resolve_group_of_worker(self, info, economic_unit_code=None, **kwargs):
        if not info.context.user.has_perms(WorkerVoucherConfig.gql_group_of_worker_search_perms):
            raise PermissionError("Unauthorized")
        filters = []
        query = GroupOfWorker.objects
        client_mutation_id = kwargs.get("client_mutation_id", None)
        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))
        if economic_unit_code:
            filters.append(Q(policyholder__code=economic_unit_code))
        filters.extend(get_group_worker_user_filters(info.context.user))
        return gql_optimizer.query(query.filter(*filters), info)

    @staticmethod
    def _check_permissions(user, perms):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(perms):
            raise PermissionError(_("Unauthorized"))


class Mutation(graphene.ObjectType):
    create_worker = CreateWorkerMutation.Field()
    delete_worker = DeleteWorkerMutation.Field()

    create_worker_voucher = CreateWorkerVoucherMutation.Field()
    update_worker_voucher = UpdateWorkerVoucherMutation.Field()
    delete_worker_voucher = DeleteWorkerVoucherMutation.Field()

    acquire_unassigned_vouchers = AcquireUnassignedVouchersMutation.Field()
    acquire_assigned_vouchers = AcquireAssignedVouchersMutation.Field()
    assign_vouchers = AssignVouchersMutation.Field()

    create_or_update_group_of_workers = CreateOrUpdateGroupOfWorkerMutation.Field()
    delete_group_of_workers = DeleteGroupOfWorkerMutation.Field()
