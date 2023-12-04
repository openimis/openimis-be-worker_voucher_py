import graphene
import graphene_django_optimizer as gql_optimizer

from django.utils.translation import gettext as _
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser
from core.schema import OrderedDjangoFilterConnectionField
from core.utils import append_validity_filter
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.gql_queries import WorkerVoucherGQLType
from worker_voucher.gql_mutations import CreateWorkerVoucherMutation, UpdateWorkerVoucherMutation, \
    DeleteWorkerVoucherMutation
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import get_voucher_worker_enquire_filters


class Query(graphene.ObjectType):
    module_name = "tasks_management"

    worker_voucher = OrderedDjangoFilterConnectionField(
        WorkerVoucherGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        client_mutation_id=graphene.String(),
    )

    enquire_worker = OrderedDjangoFilterConnectionField(
        WorkerVoucherGQLType,
        national_id=graphene.String(),
    )

    def resolve_worker_voucher(self, info, client_mutation_id=None, **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_search_perms)
        filters = append_validity_filter(**kwargs)

        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        query = WorkerVoucher.objects.filter(*filters)
        return gql_optimizer.query(query, info)

    def resolve_enquire_worker(self, info, national_id=None, **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_search_perms)
        filters = append_validity_filter(**kwargs)

        if not national_id:
            raise AttributeError(_("National ID required"))

        filters.append(*get_voucher_worker_enquire_filters(national_id))

        query = WorkerVoucher.objects.filter(*filters)
        return gql_optimizer.query(query, info)

    @staticmethod
    def _check_permissions(user, perms):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(perms):
            raise PermissionError(_("Unauthorized"))


class Mutation(graphene.ObjectType):
    createWorkerVoucher = CreateWorkerVoucherMutation.Field()
    updateWorkerVoucher = UpdateWorkerVoucherMutation.Field()
    deleteWorkerVoucher = DeleteWorkerVoucherMutation.Field()

