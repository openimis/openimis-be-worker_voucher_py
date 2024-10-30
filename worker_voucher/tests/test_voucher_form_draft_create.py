from uuid import uuid4

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
)
from worker_voucher.tests.util import (
    create_test_eu_for_user,
    create_test_worker_for_eu
)


class GQLVoucherDraftFormCreateTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None
    chf_id = None
    existing_worker = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(GQLVoucherDraftFormCreateTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='DraftUser', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user, code='draft')
        cls.chf_id = F"{generate_random_insuree_number()}"
        cls.existing_worker = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

    def test_create_draft_form_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = uuid4()
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

    def test_create_voucher_draft_form_false_not_existing_form_type(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = uuid4()
        payload = gql_mutation_voucher_draft_form_create % (
            self.existing_worker.id,
            self.today,
            self.today,
            "ASSIGNMENT-NOT",
            self.eu.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)
        draft = VoucherFormDraft.objects.filter(
            policyholder__code=self.eu.code,
            user=self.user,
            type="ASSIGNMENT"
        )
        self.assertEquals(draft.count(), 0)

    def test_create_voucher_draft_form_false_not_existing_eu(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = uuid4()
        payload = gql_mutation_voucher_draft_form_create % (
            self.existing_worker.id,
            self.today,
            self.today,
            "ASSIGNMENT",
            "NOT_EXIST",
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)
        draft = VoucherFormDraft.objects.filter(
            policyholder__code=self.eu.code,
            user=self.user,
            type="ASSIGNMENT"
        )
        self.assertEquals(draft.count(), 0)
