# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import time
from cfme.common.vm import VM
from cfme.exceptions import CFMEException
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.cloud.provider.gce import GCEProvider
from utils import testgen
from utils.log import logger
from utils.wait import TimedOutError


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope="module")
def vm_name():
    return "test-dscvry-" + fauxfactory.gen_alpha(8).lower()


@pytest.fixture(scope="module")
def vm_crud(vm_name, provider):
    return VM.factory(vm_name, provider)


@pytest.mark.tier(1)
def test_discovery(request, setup_provider, provider, vm_crud):
    """ Tests whether MIQ will discover a vm change (add/delete) without being manually refreshed.
    Ultimately we want to see that the provider sends an EVENT which then triggers a provider
    refresh that discovers, inventories, and displays the new vm.  Only when provider does NOT
    support eventing should manual refresh be used.

    Prerequisities:
        * Desired provider set up

    Steps:
        * Create a virtual machine on the provider (outside of MIQ).
        * Wait for the VM to appear
        * Delete the VM from the provider (outside of MIQ)
        * Wait for the VM to become Archived.

    Metadata:
        test_flag: discovery
    """

    # cleanup anything we add after the test finishes
    @request.addfinalizer
    def _cleanup():
        vm_crud.provider.delete(cancel=False)
        vm_crud.delete_from_provider()

    # create the vm and wait for MIQ to discover it
    vm_crud.create_on_provider(allow_skip="default")

    if not provider.supports['EVENTS']:
        provider.refresh_provider_relationships()

    try:
        vm_crud.wait_to_appear(timeout=600, load_details=False)
    except TimedOutError:
        pytest.fail("VM was not found in MIQ")

    # delete the vm and wait for MIQ to recognize it
    vm_crud.delete_from_provider()

    if not provider.supports['EVENTS']:
        provider.refresh_provider_relationships()

    # TODO: this needs to be updated as it fails to find archived
    #       for the specific provider
    vm_crud.wait_for_vm_state_change(desired_state='Archived', timeout=600,
        with_relationship_refresh=False)
