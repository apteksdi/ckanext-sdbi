# -*- coding: utf-8 -*-
"""JSON REST harvester for non-CKAN open data APIs (e.g. Satu Data Jakarta)."""
from __future__ import absolute_import

import json
import logging

import requests

from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject
from ckanext.sdbi.lib.datastore_table import sync_records_to_resource
from ckanext.sdbi.lib.json_rest import (
    JSONRestConfigError,
    apply_dataset_filters,
    attach_detail_urls,
    build_package_dict,
    dataset_from_source_url,
    extract_datasets_from_list_payload,
    parse_harvest_config,
    resolve_detail_url,
    tabular_records_from_payload,
)

log = logging.getLogger(__name__)


class JSONRestHarvester(HarvesterBase):
    """Harvest a JSON REST URL, or a configured list of datasets."""

    def info(self):
        return {
            'name': 'sdbi_json_harvester',
            'title': 'JSON REST',
            'description': (
                'Harvest a JSON REST URL the same way as CKAN and CSW: '
                'paste the dataset JSON URL, then optional configuration '
                '(title, default_tags, default_extras). For many datasets, '
                'use datasets[] plus detail_url_template, or list_url.'
            ),
            'form_config_interface': 'Text',
        }

    def validate_config(self, config):
        parse_harvest_config(config)
        return config

    def _load_config(self, harvest_job):
        return parse_harvest_config(harvest_job.source.config)

    def gather_stage(self, harvest_job):
        log.debug('JSONRestHarvester gather_stage (%s)', harvest_job.source.url)
        try:
            config = self._load_config(harvest_job)
            datasets = self._dataset_list(harvest_job, config)
        except JSONRestConfigError as exc:
            self._save_gather_error(str(exc), harvest_job)
            return None
        except Exception as exc:
            self._save_gather_error('Gather failed: %s' % exc, harvest_job)
            return None

        object_ids = []
        for remote in datasets:
            guid = remote['name']
            obj = HarvestObject(
                guid=guid,
                job=harvest_job,
                content=json.dumps({'remote': remote, 'config': config}),
            )
            obj.save()
            object_ids.append(obj.id)
        if not object_ids:
            self._save_gather_error('No datasets listed in harvest config', harvest_job)
            return None
        return object_ids

    def _dataset_list(self, harvest_job, config):
        datasets = list(config.get('datasets') or [])
        if not datasets:
            list_url = config.get('list_url')
            if list_url:
                response = requests.get(list_url, timeout=30)
                response.raise_for_status()
                datasets = extract_datasets_from_list_payload(response.json())
            else:
                datasets = [
                    dataset_from_source_url(harvest_job.source.url, config)
                ]
        datasets = apply_dataset_filters(datasets, config)
        if not datasets:
            raise JSONRestConfigError('No datasets left after filters')
        return attach_detail_urls(datasets, config)

    def fetch_stage(self, harvest_object):
        try:
            envelope = json.loads(harvest_object.content or '{}')
            remote = envelope['remote']
            config = envelope['config']
            url = resolve_detail_url(remote, config)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            self._save_object_error(
                'Fetch failed for %s: %s' % (harvest_object.guid, exc),
                harvest_object,
                'Fetch',
            )
            return False
        envelope['payload'] = payload
        harvest_object.content = json.dumps(envelope)
        harvest_object.save()
        return True

    def import_stage(self, harvest_object):
        if not harvest_object or not harvest_object.content:
            self._save_object_error(
                'Empty harvest object %s' % getattr(harvest_object, 'id', ''),
                harvest_object,
                'Import',
            )
            return False
        try:
            envelope = json.loads(harvest_object.content)
            remote = envelope['remote']
            config = envelope['config']
            payload = envelope.get('payload')
            package_dict = build_package_dict(
                remote=remote,
                config=config,
                payload=payload,
                harvest_source_title=harvest_object.source.title,
            )
            if not package_dict.get('owner_org'):
                source_dataset = self._get_source_org(harvest_object)
                if source_dataset:
                    package_dict['owner_org'] = source_dataset
            result = self._create_or_update_package(
                package_dict, harvest_object, package_dict_form='package_show'
            )
            if result:
                self._sync_datastore_table(package_dict, payload)
            return result
        except Exception as exc:
            log.exception(exc)
            self._save_object_error('%s' % exc, harvest_object, 'Import')
            return False

    def _get_source_org(self, harvest_object):
        try:
            from ckan.plugins import toolkit
            source_dataset = toolkit.get_action('package_show')(
                {'ignore_auth': True},
                {'id': harvest_object.source.id},
            )
            return source_dataset.get('owner_org')
        except Exception:
            return None

    def _sync_datastore_table(self, package_dict, payload):
        """Load tabular JSON into DataStore + ensure DataTables view."""
        records = tabular_records_from_payload(payload)
        if not records:
            return
        try:
            from ckan.plugins import toolkit
        except Exception:
            return
        context = {'ignore_auth': True, 'user': self._get_user_name()}
        try:
            pkg = toolkit.get_action('package_show')(
                context, {'id': package_dict['id']}
            )
        except Exception as exc:
            log.warning('DataStore sync skipped (package_show): %s', exc)
            return
        resources = pkg.get('resources') or []
        if not resources:
            return
        try:
            sync_records_to_resource(resources[0]['id'], records, context)
        except Exception as exc:
            log.warning(
                'DataStore sync failed for package %s: %s',
                package_dict.get('id'),
                exc,
            )
