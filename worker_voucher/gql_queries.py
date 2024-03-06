import graphene

from graphene_django import DjangoObjectType
from core import ExtendedConnection, prefix_filterset
from insuree.gql_queries import InsureeGQLType
from invoice.models import Bill
from policyholder.gql import PolicyHolderGQLType
from worker_voucher.models import WorkerVoucher


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
