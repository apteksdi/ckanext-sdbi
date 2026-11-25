from ckanext.sdbi.auth import (
    HARVEST_SYSADMIN_ONLY_ACTIONS,
    datastore_search_sql,
    get_auth_functions,
    harvest_manage,
    package_create_harvest_guard,
    package_update_harvest_guard,
)


def test_anonymous_denied():
    for context in ({}, {'user': None}, {'user': ''}):
        result = datastore_search_sql(context, {})
        assert result['success'] is False
        assert 'sysadmin' in result['msg'].lower()


def test_normal_user_denied():
    result = datastore_search_sql(
        {'user': 'alice'}, {}, is_sysadmin=lambda _user: False
    )
    assert result['success'] is False


def test_sysadmin_allowed():
    result = datastore_search_sql(
        {'user': 'admin'}, {}, is_sysadmin=lambda _user: True
    )
    assert result == {'success': True}


def test_only_sql_action_is_registered():
    funcs = get_auth_functions()
    assert set(funcs) == {'datastore_search_sql'}
    assert funcs['datastore_search_sql'] is datastore_search_sql
    assert 'datastore_search' not in funcs
    assert 'datastore_create' not in funcs


def test_harvest_manage_denied_for_everyone():
    # Sysadmin never reaches this (CKAN authz bypass).
    result = harvest_manage({'user': 'editor'}, {})
    assert result['success'] is False
    assert 'sysadmin' in result['msg'].lower()


def test_harvest_sysadmin_only_action_list():
    assert 'harvest_source_create' in HARVEST_SYSADMIN_ONLY_ACTIONS
    assert 'harvest_job_create' in HARVEST_SYSADMIN_ONLY_ACTIONS
    assert 'harvest_source_list' not in HARVEST_SYSADMIN_ONLY_ACTIONS


def test_package_create_blocks_harvest_type():
    result = package_create_harvest_guard({}, {'type': 'harvest'})
    assert result['success'] is False


def test_package_create_allows_normal_dataset():
    assert package_create_harvest_guard({}, {'type': 'dataset'}) is None
    assert package_create_harvest_guard({}, {}) is None


def test_package_update_blocks_harvest_context_package():
    class _Pkg(object):
        type = 'harvest'

    result = package_update_harvest_guard({'package': _Pkg()}, {'id': 'x'})
    assert result['success'] is False
