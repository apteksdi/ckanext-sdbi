_DENY_MSG = 'Only sysadmins may use datastore_search_sql'
_HARVEST_DENY_MSG = 'Only sysadmins may manage harvest'
_HARVEST_TYPE = 'harvest'

# Harvest action auth (API). UI create/edit also goes through package_*.
HARVEST_SYSADMIN_ONLY_ACTIONS = (
    'harvest_source_create',
    'harvest_source_update',
    'harvest_source_delete',
    'harvest_source_clear',
    'harvest_source_reindex',
    'harvest_job_create',
    'harvest_send_job_to_gather_queue',
    'harvest_job_list',
    'harvest_job_show',
)


def _ckan_is_sysadmin(user):
    import ckan.authz as authz

    return bool(authz.is_sysadmin(user))


def datastore_search_sql(context, data_dict, is_sysadmin=None):
    user = context.get('user') or ''
    if not user:
        return {'success': False, 'msg': _DENY_MSG}
    if is_sysadmin is None:
        is_sysadmin = _ckan_is_sysadmin
    if is_sysadmin(user):
        return {'success': True}
    return {'success': False, 'msg': _DENY_MSG}


def harvest_manage(context, data_dict):
    """Always deny; CKAN sysadmin bypass never reaches this."""
    return {'success': False, 'msg': _HARVEST_DENY_MSG}


def _package_is_harvest(context, data_dict):
    data_dict = data_dict or {}
    if data_dict.get('type') == _HARVEST_TYPE:
        return True
    pkg = context.get('package')
    if pkg is not None and getattr(pkg, 'type', None) == _HARVEST_TYPE:
        return True
    pkg_id = data_dict.get('id') or data_dict.get('name')
    if not pkg_id:
        return False
    import ckan.model as model

    pkg = model.Package.get(pkg_id)
    return bool(pkg and pkg.type == _HARVEST_TYPE)


def package_create_harvest_guard(context, data_dict):
    if _package_is_harvest(context, data_dict):
        return harvest_manage(context, data_dict)
    return None


def package_update_harvest_guard(context, data_dict):
    if _package_is_harvest(context, data_dict):
        return harvest_manage(context, data_dict)
    return None


def package_delete_harvest_guard(context, data_dict):
    if _package_is_harvest(context, data_dict):
        return harvest_manage(context, data_dict)
    return None


def get_auth_functions():
    return {
        'datastore_search_sql': datastore_search_sql,
    }
