import graphene
from graphene_django import DjangoObjectType

from core import ExtendedConnection, prefix_filterset, datetime
from insuree.gql_queries import InsureeGQLType, PhotoGQLType, GenderGQLType
from insuree.models import Insuree
from invoice.models import Bill
from policyholder.gql import PolicyHolderGQLType
from core.gql_queries import UserGQLType
from worker_voucher.models import (
    WorkerVoucher,
    GroupOfWorker,
    WorkerGroup,
    VoucherFormDraft,
    VoucherFormDraftDateRangesDetails,
    VoucherFormDraftWorkersDetails,
)
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

            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "date_updated": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
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

            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "date_updated": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
        }
        connection_class = ExtendedConnection


class VoucherCheckGQLType(graphene.ObjectType):
    is_existed = graphene.Boolean()
    is_valid = graphene.Boolean()
    assigned_date = graphene.DateTime()
    employer_code = graphene.String()
    employer_name = graphene.String()


class DateRangeType(graphene.ObjectType):
    start_date = graphene.Date()
    end_date = graphene.Date()


class WorkersType(graphene.ObjectType):
    id = graphene.String()
    uuid = graphene.String()
    chf_id = graphene.String()
    last_name = graphene.String()
    other_names = graphene.String()
    dob = graphene.Date()


class VoucherFormDraftGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    workers = graphene.List(WorkersType)
    date_ranges = graphene.List(DateRangeType)

    class Meta:
        model = VoucherFormDraft
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            **prefix_filterset("user__", UserGQLType._meta.filter_fields),
            **prefix_filterset("policyholder__", PolicyHolderGQLType._meta.filter_fields),
            "type": ["exact", "istartswith", "icontains", "iexact"],

            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "date_updated": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_workers(self, info):
        workers = VoucherFormDraftWorkersDetails.objects.filter(
            voucher_form_draft=self
        ).values(
            'insuree__chf_id',
            'insuree__id',
            'insuree__uuid',
            'insuree__dob',
            'insuree__last_name',
            'insuree__other_names',
        )
        return [
            WorkersType(
                id=worker['insuree__id'],
                uuid=worker['insuree__uuid'],
                chf_id=worker['insuree__chf_id'],
                last_name=worker['insuree__last_name'],
                other_names=worker['insuree__other_names'],
                dob=worker['insuree__dob'],
            )
            for worker in workers]

    # Resolver for date_ranges
    def resolve_date_ranges(self, info):
        date_ranges = VoucherFormDraftDateRangesDetails.objects.filter(
            voucher_form_draft=self
        ).values('start_date', 'end_date')
        return [DateRangeType(start_date=dr['start_date'], end_date=dr['end_date']) for dr in date_ranges]


class VoucherFormDraftWorkerDetailsGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = VoucherFormDraftWorkersDetails
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "insuree_id": ["exact"],
            **prefix_filterset("voucher_form_draft__", VoucherFormDraftGQLType._meta.filter_fields),

            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "date_updated": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
        }
        connection_class = ExtendedConnection


class VoucherFormDraftDateRangesDetailsGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = VoucherFormDraftDateRangesDetails
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            **prefix_filterset("voucher_form_draft__", VoucherFormDraftGQLType._meta.filter_fields),

            "start_date": ["exact", "lt", "lte", "gt", "gte"],
            "end_date": ["exact", "lt", "lte", "gt", "gte"],
            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "date_updated": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
        }
        connection_class = ExtendedConnection
