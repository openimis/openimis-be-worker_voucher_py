from django.test import TestCase
from core.models import MutationLog, Role
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import GroupOfWorker, WorkerGroup
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import gql_mutation_create_group_of_worker
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker


class GQLGroupOfWorkerCreateTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None
    chf_id = None
    insurees_chf_id = None
    name = None

    @classmethod
    def setUpClass(cls):
        super(GQLGroupOfWorkerCreateTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.chf_id = F"{generate_random_insuree_number()}"
        cls.existing_worker = create_test_worker(cls.user, chf_id=F"{generate_random_insuree_number()}")
        cls.name = 'Group Test'
        cls.insurees_chf_id = [cls.existing_worker.chf_id]

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)

    def test_create_group_of_worker_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "93g453h5g77h04gh35"
        payload = gql_mutation_create_group_of_worker % (
            self.insurees_chf_id,
            self.eu.code,
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        group = GroupOfWorker.objects.filter(name=self.name)
        workers_group = WorkerGroup.objects.filter(group=group)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 1)

    def test_create_group_of_worker_empty_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h74klj78"
        payload = gql_mutation_create_group_of_worker % (
            [],
            self.eu.code,
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        group = GroupOfWorker.objects.filter(name=self.name)
        workers_group = WorkerGroup.objects.filter(group=group)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 0)

    def test_create_group_of_worker_false_not_existing_economic_unit(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh36"
        payload = gql_mutation_create_group_of_worker % (
            self.insurees_chf_id,
            'NOT-EXISTS',
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        group = GroupOfWorker.objects.filter(name=self.name)
        self.assertEquals(group.count(), 0)

    def test_create_group_of_worker_false_insuree_not_exist(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "19g453h5g92h04gh99"
        national_id = F"{generate_random_insuree_number()}"
        payload = gql_mutation_create_group_of_worker % (
            [national_id],
            self.eu.code,
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertTrue(mutation_log.error)
        group = GroupOfWorker.objects.filter(name=self.name)
        self.assertEquals(group.count(), 0)
