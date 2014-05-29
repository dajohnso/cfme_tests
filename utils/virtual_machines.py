"""Helper functions related to the creation and destruction of providers
"""

from utils.log import logger
from utils.mgmt_system import RHEVMSystem, EC2System, OpenstackSystem


def deploy_template(provider_crud, vm_name, template_name=None):

    deploy_args = {}
    deploy_args.update(vm_name=vm_name)
    if isinstance(provider_crud.get_mgmt_system(), RHEVMSystem):
        deploy_args.update(cluster_name=provider_crud.get_yaml_data()['default_cluster'])
    elif isinstance(provider_crud.get_mgmt_system(), EC2System):
        deploy_args.update(instance_type=provider_crud.get_yaml_data()['default_flavor'])
    elif isinstance(provider_crud.get_mgmt_system(), OpenstackSystem):
        deploy_args.update(flavour_name=provider_crud.get_yaml_data()['default_flavor'])
        deploy_args.update(assign_floating_ip=provider_crud.get_yaml_data()['default_ip_pool'])

    if template_name is None:
        template_name = provider_crud.get_yaml_data()['small_template']

    logger.info("Getting ready to deploy VM %s from template %s on provider %s" %
        (vm_name, template_name, provider_crud.get_yaml_data()['name']))

    try:
        logger.debug("deploy args: " + str(deploy_args))
        provider_crud.get_mgmt_system().deploy_template(template_name, **deploy_args)
    except Exception as e:
        logger.error('Could not provisioning VM %s (%s)', vm_name, e.message)
        logger.info('Attempting cleanup on VM %s', vm_name)
        try:
            if provider_crud.get_mgmt_system().does_vm_exist(vm_name):
                # Stop the vm first
                logger.warning('Destroying VM %s', vm_name)
                if provider_crud.get_mgmt_system().delete_vm(vm_name):
                    logger.info('VM %s destroyed', vm_name)
                else:
                    logger.error('Error destroying VM %s', vm_name)
        except Exception as f:
            logger.error('Could not destroy VM %s (%s)', vm_name, f.message)
        finally:
            raise e
