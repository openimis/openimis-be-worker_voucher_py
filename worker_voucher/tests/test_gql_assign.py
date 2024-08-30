from uuid import uuid4
from django.test import TestCase
from core.models import Role, MutationLog
from graphene import Schema
from graphene.test import Client
from core import datetime
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import WorkerVoucher
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import gql_mutation_assign
from worker_voucher.tests.util import create_test_worker_for_eu, create_test_eu_for_user


class GQLAssignVouchersTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None
    worker = None
    unassigned_voucher = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(GQLAssignVouchersTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

        cls.unassigned_voucher = WorkerVoucher(code=uuid4(), expiry_date=cls.tomorrow, policyholder=cls.eu,
                                               status=WorkerVoucher.Status.UNASSIGNED)
        cls.unassigned_voucher.save(username=cls.user.username)

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)

    def test_validate_success(self):
        mutation_id = "39g453h5g92h04gh32"
        payload = gql_mutation_assign % (
            self.eu.code,
            self.worker.chf_id,
            self.today,
            self.today,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        vouchers = WorkerVoucher.objects.filter(policyholder=self.eu, insuree=self.worker,
                                                assigned_date=self.today)
        self.assertEquals(vouchers.count(), 1)
