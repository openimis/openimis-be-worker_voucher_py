from datetime import datetime, timedelta
from django.test import TestCase
from graphene import Schema
from graphene.test import Client


from core.models import Role
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import (
    VoucherFormDraft,
    VoucherFormDraftWorkersDetails,
    VoucherFormDraftDateRangesDetails,
)
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu
from worker_voucher.tests.data.gql_payloads import gql_query_voucher_draft_form


class GQLVoucherFormDraftTestCase(TestCase):
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
        super(GQLVoucherFormDraftTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser10', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.today = datetime.now()
        cls.tomorrow = datetime.now() + timedelta(days=1)
        cls.yesterday = datetime.now() - timedelta(days=1)

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(None)

    def test_get_existed_draft(self):
        draft, draft_dates, draft_worker = self._create_test_draft()
        payload = gql_query_voucher_draft_form
        print(payload)
        query_result = self.gql_client.execute(payload, context=self.gql_context)
        print(query_result['data'])
        print(query_result['data']['voucherFormDraft'])
        query_data = query_result['data']['voucherFormDraft']['edges'][0]['node']
        self.assertEqual(query_data['uuid'], draft.id)
        self.assertEqual(query_data['user']['username'], draft.user.username)
        self.assertEqual(query_data['policyholder']['code'], draft.policyholder.code)
        self.assertEqual(query_data['type'], draft.type)
        self.assertEqual(query_data['workers'][0]['chfId'], draft_worker.insuree.chf_id)
        self.assertEqual(query_data['dateRanges'][0]['startDate'], draft_dates.start_date)
        self.assertEqual(query_data['dateRanges'][0]['endDate'], draft_dates.end_date)

    def test_get_empty_query_draft(self):
        payload = gql_query_voucher_draft_form
        print(payload)
        query_result = self.gql_client.execute(payload, context=self.gql_context)
        print(query_result['data'])
        print(query_result['data']['voucherFormDraft'])
        query_data = query_result['data']['voucherFormDraft']['edges']
        self.assertEqual(len(query_data), 0)

    def _create_test_draft(self):
        draft = VoucherFormDraft(
            policyholder=self.eu,
            user=self.user,
            type="ASSIGNMENT",
        )
        draft.save(username=self.user.username)
        draft_dates = VoucherFormDraftDateRangesDetails(
            voucher_form_draft=draft,
            start_date=self.today,
            end_date=self.today,
        )
        draft_dates.save(username=self.user.username)
        draft_worker = VoucherFormDraftWorkersDetails(
            voucher_form_draft=draft,
            insuree=self.worker,
        )
        draft_worker.save(username=self.user.username)
        return draft, draft_dates, draft_worker
