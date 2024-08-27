from django.test import TestCase
from core.models import MutationLog
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from policyholder.models import PolicyHolderInsuree
from insuree.models import Insuree
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import gql_mutation_create_worker
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker


class GQLWorkerCreateTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None

    chf_id = None
    last_name = None
    other_names = None
    gender_id = None
    dob = None

    existing_worker = None

    @classmethod
    def setUpClass(cls):
        super(GQLWorkerCreateTestCase, cls).setUpClass()
        cls.user = create_test_interactive_user(username='VoucherTestUser2')
        cls.eu = create_test_eu_for_user(cls.user)
        cls.chf_id = F"{generate_random_insuree_number()}"
        cls.existing_worker = create_test_worker(cls.user, chf_id=F"{generate_random_insuree_number()}")
        cls.last_name = 'Test'
        cls.other_names = 'Test'
        cls.gender_id = 'M'
        cls.dob = "1990-01-01"

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)

    def test_create_worker_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh34"
        payload = gql_mutation_create_worker % (
            self.chf_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.eu.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=self.chf_id)
        phi = PolicyHolderInsuree.objects.filter(policy_holder=self.eu)
        self.assertEquals(workers.count(), 1)
        self.assertEquals(phi.count(), 1)

    def test_create_existing_worker_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh35"
        payload = gql_mutation_create_worker % (
            self.existing_worker.chf_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.eu.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=self.existing_worker.chf_id)
        phi = PolicyHolderInsuree.objects.filter(policy_holder=self.eu)
        self.assertEquals(workers.count(), 1)
        self.assertEquals(phi.count(), 1)

    def test_create_worker_false_not_existing_economic_unit(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh36"
        national_id = F"{generate_random_insuree_number()}"
        payload = gql_mutation_create_worker % (
            national_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            'NOT-EXIST',
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=national_id)
        self.assertEquals(workers.count(), 0)

    def test_create_worker_already_assigned_to_economic_unit(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh37"
        national_id = F"{generate_random_insuree_number()}"
        payload = gql_mutation_create_worker % (
            national_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.eu.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=national_id)
        phi = PolicyHolderInsuree.objects.filter(policy_holder=self.eu)
        self.assertEquals(workers.count(), 1)
        self.assertEquals(phi.count(), 1)
        payload = gql_mutation_create_worker % (
            national_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.eu.code,
            mutation_id
        )
        _ = self.gql_client.execute(payload, context=self.gql_context)
        self.assertFalse(mutation_log.error)
