import graphene
from graphene_django import DjangoObjectType

from core import ExtendedConnection, prefix_filterset, datetime
from insuree.gql_queries import InsureeGQLType, PhotoGQLType, GenderGQLType
from insuree.models import Insuree
from invoice.models import Bill
from policyholder.gql import PolicyHolderGQLType
from worker_voucher.models import WorkerVoucher, GroupOfWorker, WorkerGroup
from worker_voucher.services import get_worker_yearly_voucher_count_counts


class WorkerGQLType(InsureeGQLType):
    vouchers_this_year = graphene.JSONString()

    def resolve_vouchers_this_year(self, info):
        return get_worker_yearly_voucher_count_counts(self.id, info.context.user, datetime.date.today().year)

    class Meta:
        model = Insuree
        filter_fields = {
            "uuid": ["exact", "iexact"],
            "chf_id": ["exact", "istartswith", "icontains", "iexact"],
            "last_name": ["exact", "istartswith", "icontains", "iexact"],
            "other_names": ["exact", "istartswith", "icontains", "iexact"],
            "email": ["exact", "istartswith", "icontains", "iexact", "isnull"],
            "phone": ["exact", "istartswith", "icontains", "iexact", "isnull"],
            "dob": ["exact", "lt", "lte", "gt", "gte", "isnull"],
            "head": ["exact"],
            "passport": ["exact", "istartswith", "icontains", "iexact", "isnull"],
            "gender__code": ["exact", "isnull"],
            "marital": ["exact", "isnull"],
            "status": ["exact"],
            "validity_from": ["exact", "lt", "lte", "gt", "gte", "isnull"],
            "validity_to": ["exact", "lt", "lte", "gt", "gte", "isnull"],
            **prefix_filterset("photo__", PhotoGQLType._meta.filter_fields),
            "photo": ["isnull"],
            "family": ["isnull"],
            **prefix_filterset("gender__", GenderGQLType._meta.filter_fields)
        }
        interfaces = (graphene.relay.Node,)
        connection_class = ExtendedConnection


class WorkerVoucherGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    date_updated_as_date = graphene.String()
    bill_id = graphene.UUID()

    class Meta:
        model = WorkerVoucher
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],

            "code": ["exact", "iexact", "istartswith", "icontains"],
            "status": ["exact", "iexact", "istartswith", "icontains"],
            "assigned_date": ["exact", "lt", "lte", "gt", "gte"],
            "expiry_date": ["exact", "lt", "lte", "gt", "gte"],

            **prefix_filterset("insuree__", InsureeGQLType._meta.filter_fields),
            **prefix_filterset("policyholder__", PolicyHolderGQLType._meta.filter_fields),

            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "date_updated": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_date_updated_as_date(self, info, **kwargs):
        return self.date_updated.to_ad_date()

    def resolve_bill_id(self, info, **kwargs):
        bill = Bill.objects.filter(line_items_bill__line_id=self.id,
                                   line_items_bill__is_deleted=False,
                                   is_deleted=False).first()
        if bill:
            return bill.id


class AcquireVouchersValidationSummaryGQLType(graphene.ObjectType):
    price = graphene.Decimal()
    count = graphene.Int()
    price_per_voucher = graphene.Decimal()


class OnlineWorkerDataGQLType(graphene.ObjectType):
    other_names = graphene.String()
    last_name = graphene.String()
    photo = graphene.String()


class GroupOfWorkerGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = GroupOfWorker
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            **prefix_filterset("policyholder__", PolicyHolderGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection


class WorkerGroupGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = WorkerGroup
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "insuree_id": ["exact"],
            **prefix_filterset("group__", GroupOfWorkerGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection
