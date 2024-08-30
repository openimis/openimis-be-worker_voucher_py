import random

from insuree.models import Insuree
from policyholder.models import PolicyHolder, PolicyHolderUser, PolicyHolderInsuree


def create_test_eu(user, code='test_eu'):
    eu = PolicyHolder(
        code=code,
        trade_name='Test EU'
    )
    eu.save(user=user)
    return eu

def create_test_phu(user, eu):
    phu = PolicyHolderUser(
        policy_holder=eu,
        user=user
    )
    phu.save(user=user)
    return phu


def create_test_eu_for_user(user, code='test_eu'):
    eu = create_test_eu(user, code)
    _ = create_test_phu(user, eu)
    return eu

def create_test_worker(user, chf_id="2675135421017"):
    worker = Insuree(
        other_names="Test",
        last_name="Insuree",
        chf_id=chf_id,
        audit_user_id=user.id_for_audit
    )
    worker.save()
    return worker

def create_test_phi(user, eu, worker):
    phi = PolicyHolderInsuree(
        policy_holder=eu,
        insuree=worker
    )
    phi.save(user=user)
    return phi


def create_test_worker_for_eu(user, eu, chf_id="2675135421017"):
    worker = create_test_worker(user, chf_id)
    _ = create_test_phi(user, eu, worker)
    return worker

def get_idnp_crc(idnp_first_12_digits):
    assert len(idnp_first_12_digits) == 12

    values = [7, 3, 1]

    crc = 0
    for i, c in enumerate(idnp_first_12_digits):
        crc += int(c) * values[i % 3]

    return crc % 10


def generate_idnp():
    idnp_first_12_digits = random.randint(200000000000, 299999999999)
    return str(idnp_first_12_digits) + str(get_idnp_crc(str(idnp_first_12_digits)))