from django.test import TestCase
from core.models import MutationLog, Role
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import GroupOfWorker, WorkerGroup
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import (
    gql_mutation_update_group_of_worker_single,
    gql_mutation_update_group_of_worker_multiple
)
from worker_voucher.tests.util import (
    create_test_eu_for_user,
    create_test_worker_for_eu,
    create_test_group_of_worker
)


class GQLGroupOfWorkerUpdateTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None
    chf_id = None
    name = None
    existing_worker = None
    existing_worker2 = None
    group = None

    @classmethod
    def setUpClass(cls):
        super(GQLGroupOfWorkerUpdateTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser3', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user, code='test_eu3')
        cls.chf_id = F"{generate_random_insuree_number()}"
        cls.existing_worker = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.existing_worker2 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.name = 'Group Test Update'

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)
        cls.group = create_test_group_of_worker(cls.user, cls.eu, cls.name)

    def test_update_group_of_worker_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "93g453h5g77h04gh01"
        payload = gql_mutation_update_group_of_worker_multiple % (
            self.group.id,
            self.existing_worker.chf_id,
            self.existing_worker2.chf_id,
            self.eu.code,
            self.name,
            mutation_id
        )

        workers_group = WorkerGroup.objects.filter(group=self.group)
        self.assertEquals(workers_group.count(), 0)
        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_success(mutation_id)
        group = GroupOfWorker.objects.filter(name=self.name)
        workers_group = WorkerGroup.objects.filter(group=group.first())
        self.assertEquals(group.count(), 1)
        self.assertEquals(group.first().name, self.name)
        self.assertEquals(workers_group.count(), 2)

    def test_update_group_of_worker_change_name_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "93g453h5g77h04gh00"
        changed_name = 'ChangedName'
        payload = gql_mutation_update_group_of_worker_multiple % (
            self.group.id,
            self.existing_worker.chf_id,
            self.existing_worker2.chf_id,
            self.eu.code,
            changed_name,
            mutation_id
        )
        workers_group = WorkerGroup.objects.filter(group=self.group)
        self.assertEquals(workers_group.count(), 0)
        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_success(mutation_id)
        group = GroupOfWorker.objects.filter(name=changed_name)
        workers_group = WorkerGroup.objects.filter(group=group.first())
        self.assertEquals(group.count(), 1)
        self.assertEquals(group.first().name, changed_name)
        self.assertEquals(workers_group.count(), 2)

    def test_update_group_of_worker_remove_one_of_worker_success(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "93g453h5g77h04gh01"
        payload = gql_mutation_update_group_of_worker_multiple % (
            self.group.id,
            self.existing_worker.chf_id,
            self.existing_worker2.chf_id,
            self.eu.code,
            self.name,
            mutation_id
        )

        workers_group = WorkerGroup.objects.filter(group=self.group)
        self.assertEquals(workers_group.count(), 0)
        _ = self.gql_client.execute(payload, context=self.gql_context)
        group = GroupOfWorker.objects.filter(name=self.name)
        workers_group = WorkerGroup.objects.filter(group=group.first())
        self.assertEquals(group.count(), 1)
        self.assertEquals(group.first().name, self.name)
        self.assertEquals(workers_group.count(), 2)

        mutation_id = "93g453h5g77h04gh09"
        payload = gql_mutation_update_group_of_worker_single % (
            self.group.id,
            self.existing_worker.chf_id,
            self.eu.code,
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_success(mutation_id)
        group = GroupOfWorker.objects.filter(name=self.name)
        workers_group = WorkerGroup.objects.filter(group=group.first())
        self.assertEquals(group.count(), 1)
        self.assertEquals(group.first().name, self.name)
        self.assertEquals(workers_group.count(), 1)
        self.assertEquals(workers_group.first().insuree.chf_id, self.existing_worker.chf_id)

    def test_update_group_of_worker_false_not_existing_economic_unit(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "39g453h5g92h04gh03"
        payload = gql_mutation_update_group_of_worker_single % (
            self.group.id,
            self.existing_worker.chf_id,
            'NOT-EXISTS',
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)
        group = GroupOfWorker.objects.filter(name=self.name)
        self.assertEquals(group.count(), 1)
        workers_group = WorkerGroup.objects.filter(group=group.first())
        self.assertEquals(group.first().name, self.name)
        self.assertEquals(workers_group.count(), 0)

    def test_update_group_of_worker_insuree_not_exist(self):
        InsureeConfig.reset_validation_settings()
        mutation_id = "19g453h5g92h04gh04"
        national_id = F"{generate_random_insuree_number()}"
        payload = gql_mutation_update_group_of_worker_single % (
            self.group.id,
            national_id,
            self.eu.code,
            self.name,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)
        group = GroupOfWorker.objects.filter(name=self.name)
        self.assertEquals(group.count(), 1)
        workers_group = WorkerGroup.objects.filter(group=group.first())
        self.assertEquals(group.first().name, self.name)
        self.assertEquals(workers_group.count(), 0)

    def _assert_mutation_success(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 2)
        self.assertFalse(mutation_log.error)

    def _assert_mutation_failed(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 1)
        self.assertTrue(mutation_log.error)
