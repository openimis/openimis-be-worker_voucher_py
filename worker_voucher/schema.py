import graphene
import graphene_django_optimizer as gql_optimizer

from django.db.models import Q
from django.utils.translation import gettext as _
from django.contrib.auth.models import AnonymousUser
from core.schema import OrderedDjangoFilterConnectionField
from core.utils import append_validity_filter
from insuree.apps import InsureeConfig
from insuree.gql_queries import InsureeGQLType
from insuree.models import Insuree
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.gql_queries import WorkerVoucherGQLType
from worker_voucher.models import WorkerVoucher


class Query(graphene.ObjectType):
    module_name = "tasks_management"

    worker_voucher = OrderedDjangoFilterConnectionField(
        WorkerVoucherGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        client_mutation_id=graphene.String(),
    )

    previous_workers = OrderedDjangoFilterConnectionField(
        InsureeGQLType,
        orderBy=graphene.List(of_type=graphene.String),
        economic_unit_code=graphene.String(required=True)
    )

    def resolve_worker_voucher(self, info, **kwargs):
        Query._check_permissions(info.context.user, WorkerVoucherConfig.gql_worker_voucher_search_perms)
        filters = append_validity_filter(**kwargs)

        client_mutation_id = kwargs.get("client_mutation_id", None)
        if client_mutation_id:
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        query = WorkerVoucher.objects.filter(*filters)
        return gql_optimizer.query(query, info)

    def resolve_previous_workers(self, info, economic_unit_code=None, **kwargs):
        Query._check_permissions(info.context.user, InsureeConfig.gql_query_insuree_perms)
        filters = append_validity_filter(**kwargs)

        query = Insuree.get_queryset(None, info.context.user).filter(
            validity_to__isnull=True,
            workervoucher__is_deleted=False,
            workervoucher__policyholder__is_deleted=False,
            workervoucher__policyholder__code=economic_unit_code
        )

        return gql_optimizer.query(query, info)

    @staticmethod
    def _check_permissions(user, perms):
        if type(user) is AnonymousUser or not user.id or not user.has_perms(perms):
            raise PermissionError(_("Unauthorized"))
