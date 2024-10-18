from uuid import uuid4

from django.test import TestCase
from core.models import MutationLog, Role
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import gql_mutation_group_of_worker_delete
from worker_voucher.tests.util import (
    create_test_eu_for_user,
    create_test_worker_for_eu,
    create_test_group_of_worker,
    create_test_worker_group
)
from worker_voucher.models import GroupOfWorker, WorkerGroup


class GQLGroupOfWorkerDeleteTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    user2 = None
    eu = None
    existing_worker = None
    existing_worker2 = None
    existing_worker3 = None
    group = None

    @classmethod
    def setUpClass(cls):
        super(GQLGroupOfWorkerDeleteTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser4', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user, code="ECTest2")
        cls.existing_worker = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.existing_worker2 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.existing_worker3 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.name = 'Test Group to Delete'
        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)
        cls.group = create_test_group_of_worker(cls.user, cls.eu, cls.name)
        create_test_worker_group(cls.user, cls.existing_worker, cls.group)
        create_test_worker_group(cls.user, cls.existing_worker2, cls.group)
        create_test_worker_group(cls.user, cls.existing_worker3, cls.group)

    def test_delete_group_of_worker_success(self):
        InsureeConfig.reset_validation_settings()
        group = GroupOfWorker.objects.filter(id=self.group.id, is_deleted=False)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 3)

        mutation_id = uuid4()
        mutation = gql_mutation_group_of_worker_delete % (
            self.group.uuid,
            self.eu.code,
            mutation_id
        )

        self.gql_client.execute(mutation, context=self.gql_context)
        self._assert_mutation_success(mutation_id)

        group = GroupOfWorker.objects.filter(id=self.group.id, is_deleted=False)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(group.count(), 0)
        self.assertEquals(workers_group.count(), 0)

    def test_delete_worker_failed_economic_unit_not_exist(self):
        InsureeConfig.reset_validation_settings()
        group = GroupOfWorker.objects.filter(id=self.group.id, is_deleted=False)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 3)

        mutation_id = uuid4()
        mutation = gql_mutation_group_of_worker_delete % (
            self.group.uuid,
            'NOT-EXIST',
            mutation_id
        )

        self.gql_client.execute(mutation, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)

        group = GroupOfWorker.objects.filter(id=self.group.id, is_deleted=False)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 3)

    def test_delete_worker_failed_no_group_not_exist(self):
        InsureeConfig.reset_validation_settings()
        group = GroupOfWorker.objects.filter(id=self.group.id, is_deleted=False)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 3)
        uuid_group_not_exist = "b47356b5-1423-4ca6-99e8-3b4b4642a640"
        group2 = GroupOfWorker.objects.filter(id=uuid_group_not_exist, is_deleted=False)
        self.assertEquals(group2.count(), 0)

        mutation_id = uuid4()
        mutation = gql_mutation_group_of_worker_delete % (
            uuid_group_not_exist,
            self.eu.code,
            mutation_id
        )

        self.gql_client.execute(mutation, context=self.gql_context)
        self._assert_mutation_failed(mutation_id)

        group = GroupOfWorker.objects.filter(id=self.group.id, is_deleted=False)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(group.count(), 1)
        self.assertEquals(workers_group.count(), 3)
        group2 = GroupOfWorker.objects.filter(id=uuid_group_not_exist, is_deleted=False)
        self.assertEquals(group2.count(), 0)

    def _assert_mutation_success(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 2)
        self.assertFalse(mutation_log.error)

    def _assert_mutation_failed(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 1)
        self.assertTrue(mutation_log.error)
