from uuid import uuid4

from django.test import TestCase
from core.models import MutationLog, Role
from graphene import Schema
from graphene.test import Client
from core.test_helpers import create_test_interactive_user
from insuree.models import Insuree
from insuree.test_helpers import generate_random_insuree_number
from insuree.apps import InsureeConfig
from worker_voucher.models import WorkerGroup
from worker_voucher.schema import Query, Mutation
from worker_voucher.services import worker_user_filter
from worker_voucher.tests.data.gql_payloads import (
    gql_mutation_worker_delete,
    gql_mutation_worker_delete_multiple
)
from worker_voucher.tests.util import (
    create_test_eu_for_user,
    create_test_worker_for_eu,
    create_test_group_of_worker,
    create_test_worker_group
)


class GQLWorkerDeleteTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    user2 = None
    eu = None
    worker = None
    worker2 = None
    worker3 = None
    group = None

    @classmethod
    def setUpClass(cls):
        super(GQLWorkerDeleteTestCase, cls).setUpClass()
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)
        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.user2 = create_test_interactive_user(username='VoucherTestUser2', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)
        cls.worker2 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")
        cls.worker3 = create_test_worker_for_eu(cls.user, cls.eu, chf_id=F"{generate_random_insuree_number()}")

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)
        cls.gql_context2 = cls.GQLContext(cls.user2)
        cls.group = create_test_group_of_worker(cls.user, cls.eu, "GroupForTest")

    def test_delete_worker_success(self):
        workers_before = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_before, 3)

        mutation_id = uuid4()
        mutation = gql_mutation_worker_delete % (
            self.worker.uuid,
            self.eu.code,
            mutation_id
        )

        res = self.gql_client.execute(mutation, context=self.gql_context)
        self.assertFalse(res.get("errors", None))
        self._assert_mutation_success(mutation_id)

        workers_after = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_after, 2)

    def test_delete_worker_failed_no_worker(self):
        workers_before = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_before, 3)

        mutation_id = uuid4()
        mutation = gql_mutation_worker_delete % (
            self.worker.uuid,
            self.eu.code,
            mutation_id
        )

        res = self.gql_client.execute(mutation, context=self.gql_context2)
        self.assertFalse(res.get("errors", None))
        self._assert_mutation_failed(mutation_id)

        workers_after = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_after, 3)

    def test_delete_worker_with_group_success(self):
        InsureeConfig.reset_validation_settings()
        create_test_worker_group(self.user, self.worker, self.group)
        workers_before = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_before, 3)
        workers_group_before = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(workers_group_before.count(), 1)

        mutation_id = uuid4()
        mutation = gql_mutation_worker_delete % (
            self.worker.uuid,
            self.eu.code,
            mutation_id
        )

        res = self.gql_client.execute(mutation, context=self.gql_context)
        self.assertFalse(res.get("errors", None))
        self._assert_mutation_success(mutation_id)

        workers_after = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_after, 2)
        workers_group_after = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(workers_group_after.count(), 0)

    def test_delete_worker_multiple_with_group_success(self):
        InsureeConfig.reset_validation_settings()
        create_test_worker_group(self.user, self.worker, self.group)
        create_test_worker_group(self.user, self.worker2, self.group)
        workers_before = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_before, 3)
        workers_group = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(workers_group.count(), 2)

        mutation_id = uuid4()
        mutation = gql_mutation_worker_delete_multiple % (
            self.worker.uuid,
            self.worker2.uuid,
            self.worker3.uuid,
            self.eu.code,
            mutation_id
        )

        res = self.gql_client.execute(mutation, context=self.gql_context)
        self.assertFalse(res.get("errors", None))
        self._assert_mutation_success(mutation_id)

        workers_after = Insuree.objects.filter(worker_user_filter(self.user, economic_unit_code=self.eu.code)).count()
        self.assertEquals(workers_after, 0)
        workers_group_after = WorkerGroup.objects.filter(group__id=self.group.id)
        self.assertEquals(workers_group_after.count(), 0)

    def _assert_mutation_success(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 2)
        self.assertFalse(mutation_log.error)

    def _assert_mutation_failed(self, mutation_id):
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertEquals(mutation_log.status, 1)
        self.assertTrue(mutation_log.error)
