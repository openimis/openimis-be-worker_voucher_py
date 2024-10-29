from uuid import uuid4

from django.test import TestCase
from core.models import MutationLog, Role
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from insuree.models import Insuree
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.models import (
    VoucherFormDraft,
    VoucherFormDraftDateRangesDetails,
    VoucherFormDraftWorkersDetails
)
from worker_voucher.schema import Query, Mutation
from worker_voucher.services import worker_user_filter
from worker_voucher.tests.data.gql_payloads import (
    gql_mutation_voucher_draft_form_delete,
    gql_mutation_voucher_draft_form_create
)
from worker_voucher.tests.util import (
    create_test_eu_for_user,
    create_test_worker_for_eu
)


class GQLVoucherDraftFormDeleteTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    user2 = None
    eu = None
    worker = None

    @classmethod
    def setUpClass(cls):
        super(GQLVoucherDraftFormDeleteTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)
        cls.gql_context2 = cls.GQLContext(cls.user2)

    def test_delete_voucher_form_draft_success(self):
        InsureeConfig.reset_validation_settings()
        # create draft
        mutation_id = uuid4()
        payload = gql_mutation_voucher_draft_form_create % (
            self.worker.id,
            self.today,
            self.today,
            "ASSIGNMENT",
            self.eu.code,
            mutation_id
        )
        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_success(mutation_id)
        draft = VoucherFormDraft.objects.filter(
            policyholder__code=self.eu.code,
            user=self.user,
            type="ASSIGNMENT"
        )
        self.assertEquals(draft.count(), 1)
        draft = draft.first()
        draft_workers = VoucherFormDraftWorkersDetails.objects.filter(voucher_form_draft=draft)
        draft_dates = VoucherFormDraftDateRangesDetails.objects.filter(voucher_form_draft=draft)
        self.assertEquals(draft.policyholder.code, self.eu.code)
        self.assertEquals(draft.type, "ASSIGNMENT")
        self.assertEquals(draft_dates.count(), 1)
        self.assertEquals(draft_workers.count(), 1)

        mutation_id = uuid4()
        mutation = gql_mutation_voucher_draft_form_delete % (
            self.eu.code,
            "ASSIGNMENT",
            mutation_id
        )
        res = self.gql_client.execute(mutation, context=self.gql_context)
        self.assertFalse(res.get("errors", None))
        self._assert_mutation_success(mutation_id)

        draft_workers = VoucherFormDraftWorkersDetails.objects.filter(
            voucher_form_draft__policyholder__code=self.eu.code,
            voucher_form_draft__user=self.user,
            voucher_form_draft__type="ASSIGNMENT"
        )
        draft_dates = VoucherFormDraftDateRangesDetails.objects.filter(
            voucher_form_draft__policyholder__code=self.eu.code,
            voucher_form_draft__user=self.user,
            voucher_form_draft__type="ASSIGNMENT"
        )
        draft = VoucherFormDraft.objects.filter(
            policyholder__code=self.eu.code,
            user=self.user,
            type="ASSIGNMENT"
        )
        self.assertEquals(draft.count(), 0)
        self.assertEquals(draft_dates.count(), 0)
        self.assertEquals(draft_workers.count(), 0)

    def test_delete_voucher_form_draft_failed_no_draft(self):
        mutation_id = uuid4()
        mutation = gql_mutation_voucher_draft_form_delete % (
            self.eu.code,
            'ASSIGNMENT',
            mutation_id
        )

        self.gql_client.execute(mutation, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)

    def test_delete_voucher_form_draft_failed_not_existed_form(self):
        InsureeConfig.reset_validation_settings()
        # create draft
        mutation_id = uuid4()
        payload = gql_mutation_voucher_draft_form_create % (
            self.worker.id,
            self.today,
            self.today,
            "ASSIGNMENT",
            self.eu.code,
            mutation_id
        )
        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_success(mutation_id)

        mutation_id = uuid4()
        mutation = gql_mutation_voucher_draft_form_delete % (
            self.eu.code,
            'NOT-EXIST',
            mutation_id
        )

        self.gql_client.execute(mutation, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)

        draft_workers = VoucherFormDraftWorkersDetails.objects.filter(
            voucher_form_draft__policyholder__code=self.eu.code,
            voucher_form_draft__user=self.user,
            voucher_form_draft__type="ASSIGNMENT"
        )
        draft_dates = VoucherFormDraftDateRangesDetails.objects.filter(
            voucher_form_draft__policyholder__code=self.eu.code,
            voucher_form_draft__user=self.user,
            voucher_form_draft__type="ASSIGNMENT"
        )
        draft = VoucherFormDraft.objects.filter(
            policyholder__code=self.eu.code,
            user=self.user,
            type="ASSIGNMENT"
        )
        self.assertEquals(draft.count(), 1)
        self.assertEquals(draft_dates.count(), 1)
        self.assertEquals(draft_workers.count(), 1)

    def _assert_mutation_success(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 2)
        self.assertFalse(mutation_log.error)

    def _assert_mutation_failed(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 1)
        self.assertTrue(mutation_log.error)
