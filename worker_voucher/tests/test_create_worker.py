from django.test import TestCase
from core.models import Role, MutationLog
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from policyholder.models import PolicyHolderInsuree
from policyholder.tests import create_test_policy_holder
from insuree.models import Insuree
from insuree.test_helpers import create_test_insuree, generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import gql_mutation_create_worker


class GQLCreateWorkerTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    policyholder = None
    chf_id = None
    last_name = None
    other_names = None
    gender_id = None
    dob = None
    existing_worker = None

    @classmethod
    def setUpClass(cls):
        super(GQLCreateWorkerTestCase, cls).setUpClass()
        cls.user = create_test_interactive_user(username='VoucherTestUser2')
        cls.policyholder = create_test_policy_holder()
        cls.chf_id = F"{generate_random_insuree_number()}"
        cls.existing_worker = create_test_insuree(with_family=False)
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
            self.policyholder.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=self.chf_id)
        phi = PolicyHolderInsuree.objects.filter(policy_holder=self.policyholder)
        self.assertEquals(workers.count(), 1)
        self.assertEquals(phi.count(), 1)

    def test_create_existing_worker_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh34"
        payload = gql_mutation_create_worker % (
            self.existing_worker.chf_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.policyholder.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=self.existing_worker.chf_id)
        phi = PolicyHolderInsuree.objects.filter(policy_holder=self.policyholder)
        self.assertEquals(workers.count(), 1)
        self.assertEquals(phi.count(), 1)

    def test_create_worker_false_not_existing_economic_unit(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh34"
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
        self.assertEquals(workers, None)

    def test_create_worker_already_assigned_to_economic_unit(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh34"
        national_id = F"{generate_random_insuree_number()}"
        payload = gql_mutation_create_worker % (
            national_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.policyholder.code,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        workers = Insuree.objects.filter(chf_id=national_id)
        phi = PolicyHolderInsuree.objects.filter(policy_holder=self.policyholder)
        self.assertEquals(workers.count(), 1)
        self.assertEquals(phi.count(), 1)
        payload = gql_mutation_create_worker % (
            national_id,
            self.last_name,
            self.other_names,
            self.gender_id,
            self.dob,
            self.policyholder.code,
            mutation_id
        )
        _ = self.gql_client.execute(payload, context=self.gql_context)
        self.assertFalse(mutation_log.error)
