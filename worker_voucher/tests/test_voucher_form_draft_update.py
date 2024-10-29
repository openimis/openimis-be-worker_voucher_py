from django.test import TestCase
from core.models import MutationLog, Role
from graphene import Schema
from graphene.test import Client
from core import datetime
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import (
    VoucherFormDraft,
    VoucherFormDraftDateRangesDetails,
    VoucherFormDraftWorkersDetails,
)
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import (
    gql_mutation_voucher_draft_form_create,
    gql_mutation_voucher_draft_form_update,
)
from worker_voucher.tests.util import (
    create_test_eu_for_user,
    create_test_worker_for_eu
)


class GQLVoucherDraftFormUpdateTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None
    chf_id = None
    existing_worker = None
    existing_worker2 = None
    existing_worker3 = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(GQLVoucherDraftFormUpdateTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser2', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user, code='test_eu2')
        cls.chf_id = F"{generate_random_insuree_number()}"
        cls.existing_worker = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.existing_worker2 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.existing_worker3 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

    def test_update_draft_form_success(self):
        InsureeConfig.reset_validation_settings()
        before_test = VoucherFormDraft.objects.filter(
            policyholder__code=self.eu.code,
            user=self.user,
            type="ASSIGNMENT"
        )
        self.assertEquals(before_test.count(), 0)

        # create draft
        mutation_id = "93g453h5g77h04f001"
        payload = gql_mutation_voucher_draft_form_create % (
            self.existing_worker.id,
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

        # update draft
        mutation_id = "93g453h5g77p04f0002"
        payload = gql_mutation_voucher_draft_form_update % (
            self.existing_worker.id,
            self.existing_worker2.id,
            self.existing_worker3.id,
            self.today,
            self.today,
            self.tomorrow,
            self.tomorrow,
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
        self.assertEquals(draft_dates.count(), 2)
        self.assertEquals(draft_workers.count(), 3)

    def _assert_mutation_success(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 2)
        self.assertFalse(mutation_log.error)

    def _assert_mutation_failed(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 1)
        self.assertTrue(mutation_log.error)
