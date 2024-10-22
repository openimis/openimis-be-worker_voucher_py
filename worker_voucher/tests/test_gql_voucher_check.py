from django.test import TestCase
from graphene import Schema
from graphene.test import Client

from core import datetime
from core.models import Role
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import WorkerVoucher
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu
from worker_voucher.tests.data.gql_payloads import gql_query_voucher_check


class GQLVoucherCheckTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    worker = None
    eu = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(GQLVoucherCheckTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser10', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.today = datetime.datetime.now()
        cls.tomorrow = datetime.datetime.now() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.datetime.now() - datetime.datetimedelta(days=1)

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(None)

    def test_get_existed_voucher_by_code(self):
        voucher = self._create_test_voucher()
        payload = gql_query_voucher_check % (
            voucher.code
        )
        query_result = self.gql_client.execute(payload, context=self.gql_context)
        query_data = query_result['data']['voucherCheck']
        self.assertEqual(query_data['isExisted'], True)
        self.assertEqual(query_data['isValid'], True)
        assigned_date = datetime.strptime(query_data['assignedDate'], '%Y-%m-%d').date()
        self.assertEqual(assigned_date, voucher.assigned_date.date())
        self.assertEqual(query_data['employerCode'], voucher.policyholder.code)
        self.assertEqual(query_data['employerName'], voucher.policyholder.trade_name)

    def test_get_existed_voucher_from_tomorrow_by_code(self):
        voucher = self._create_test_voucher(assigned_date=self.tomorrow)
        payload = gql_query_voucher_check % (
            voucher.code
        )
        query_result = self.gql_client.execute(payload, context=self.gql_context)
        query_data = query_result['data']['voucherCheck']
        self.assertEqual(query_data['isExisted'], True)
        self.assertEqual(query_data['isValid'], True)
        assigned_date = datetime.strptime(query_data['assignedDate'], '%Y-%m-%d').date()
        self.assertEqual(assigned_date, voucher.assigned_date.date())
        self.assertEqual(query_data['employerCode'], voucher.policyholder.code)
        self.assertEqual(query_data['employerName'], voucher.policyholder.trade_name)

    def test_get_not_existed_voucher_by_code(self):
        payload = gql_query_voucher_check % (
            "Not-Existed"
        )
        query_result = self.gql_client.execute(payload, context=self.gql_context)
        query_data = query_result['data']['voucherCheck']
        self.assertEqual(query_data['isExisted'], False)
        self.assertEqual(query_data['isValid'], False)
        self.assertEqual(query_data['assignedDate'], None)
        self.assertEqual(query_data['employerCode'], None)
        self.assertEqual(query_data['employerName'], None)

    def test_get_existed_voucher_from_yesterday_by_code(self):
        voucher = self._create_test_voucher(assigned_date=self.yesterday)
        payload = gql_query_voucher_check % (
            voucher.code
        )
        query_result = self.gql_client.execute(payload, context=self.gql_context)
        query_data = query_result['data']['voucherCheck']
        self.assertEqual(query_data['isExisted'], True)
        self.assertEqual(query_data['isValid'], False)
        assigned_date = datetime.strptime(query_data['assignedDate'], '%Y-%m-%d').date()
        self.assertEqual(assigned_date, voucher.assigned_date.date())
        self.assertEqual(query_data['employerCode'], voucher.policyholder.code)
        self.assertEqual(query_data['employerName'], voucher.policyholder.trade_name)

    def _create_test_voucher(self, code="001", status=WorkerVoucher.Status.ASSIGNED, assigned_date=None,
                             expiry_date=None):
        voucher = WorkerVoucher(
            insuree=self.worker,
            policyholder=self.eu,
            code=code,
            status=status,
            assigned_date=self.today if not assigned_date else assigned_date,
            expiry_date=self.tomorrow if not expiry_date else expiry_date,
        )
        voucher.save(username=self.user.username)
        return voucher
