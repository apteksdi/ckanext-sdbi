from collections import OrderedDict
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import ckan.model as model

from ckanext.sdbi.lib.json_rest import json_harvest_form_defaults


def sdbi_tanggap_rooms():
    """Rooms for the header Tanggap Darurat dropdown. Empty list if unset."""
    try:
        from ckanext.sdbi.lib.dashboard_rooms import load_rooms
        return load_rooms() or []
    except Exception:
        return []


def sdbi_totp_configured(username):
    """True when the user has completed at least one successful TOTP login."""
    try:
        from ckanext.security.model import SecurityTOTP
        record = SecurityTOTP.get_for_user(username)
        return bool(record and record.last_successful_challenge)
    except Exception:
        return False

def most_recent_datasets(num=4):
    """Get most recent datasets based on creation date using direct SQL query"""
    try:
        from sqlalchemy import text
        
        # Use direct SQL query to get datasets ordered by creation date
        query = text("""
            SELECT p.id, p.name, p.title, p.notes, p.state, p.private, 
                   p.metadata_created, p.metadata_modified
            FROM package p
            WHERE p.state = 'active' AND p.private = false
            ORDER BY p.metadata_created DESC
            LIMIT :limit
        """)
        
        result = model.Session.execute(query, {'limit': num})
        
        # Get package IDs from SQL result
        package_ids = [row.id for row in result]
        
        if not package_ids:
            return []
        
        # Get full package data using CKAN API for proper formatting
        packages = []
        for package_id in package_ids:
            try:
                package = toolkit.get_action('package_show')({}, {'id': package_id})
                packages.append(package)
            except:
                continue
        
        return packages
        
    except Exception as e:
        # Fallback to original method if there's an error
        datasets = toolkit.get_action('package_search')({}, {'sort': 'metadata_created desc',
                                                        'fq': 'private:false',
                                                        'rows': num})
        return datasets.get('results', [])

def most_popular_datasets(num=4):
    """Get most popular datasets based on view count using direct SQL JOIN"""
    try:
        from sqlalchemy import text
        
        # Use direct SQL query with JOIN to get datasets ordered by view count
        query = text("""
            SELECT p.id, p.name, p.title, p.notes, p.state, p.private, 
                   p.metadata_created, p.metadata_modified,
                   COUNT(t.url) as view_count
            FROM package p
            LEFT JOIN tracking_raw t ON t.url = '/dataset/' || p.name
            WHERE p.state = 'active' AND p.private = false
            GROUP BY p.id, p.name, p.title, p.notes, p.state, p.private, 
                     p.metadata_created, p.metadata_modified
            ORDER BY view_count DESC, p.metadata_modified DESC
            LIMIT :limit
        """)
        
        result = model.Session.execute(query, {'limit': num})
        
        # Get package IDs from SQL result
        package_ids = [row.id for row in result]
        
        if not package_ids:
            return []
        
        # Get full package data using CKAN API for proper formatting
        packages = []
        for package_id in package_ids:
            try:
                package = toolkit.get_action('package_show')({}, {'id': package_id})
                packages.append(package)
            except:
                continue
        
        return packages
        
    except Exception as e:
        # Fallback to recent datasets if there's an error
        return most_recent_datasets(num)

def beranda_kategori_counts():
    """Dataset counts per beranda category (cached), or None on failure."""
    from ckanext.sdbi.lib.beranda import kategori_counts
    return kategori_counts()


def beranda_extras():
    """Popular tags, formats and top providers for the beranda (cached)."""
    from ckanext.sdbi.lib.beranda import beranda_extras as _extras
    return _extras()


def beranda_waktu(iso_value):
    """Relative time in Bahasa Indonesia for beranda dataset lists."""
    from ckanext.sdbi.lib.beranda import waktu_relatif
    return waktu_relatif(iso_value)


def dataset_count():
    """Return a count of all datasets"""
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT COUNT(1) as total
            FROM package 
            WHERE state = 'active' AND private = false
        """)
        
        result = model.Session.execute(query)
        row = result.fetchone()
        return row.total if row else 0
        
    except Exception as e:
        # Fallback to original method
        result = toolkit.get_action('package_search')({}, {'rows': 1})
        return result['count']

def get_connected_statistics():
    """Get statistics for connected provinces, NGOs, and ministries/institutions based on organization name prefixes"""
    try:
        from sqlalchemy import text
        
        # Count organizations based on title prefixes
        query = text("""
            SELECT 
                COUNT(CASE WHEN LOWER(title) LIKE '%provinsi%' THEN 1 END) as provinsi_count,
                COUNT(CASE WHEN LOWER(title) LIKE '%kementerian%' OR LOWER(title) LIKE '%lembaga%' OR LOWER(title) LIKE '%badan%' THEN 1 END) as kementerian_count,
                COUNT(CASE WHEN LOWER(title) LIKE '%ngo%' THEN 1 END) as ngo_count,
                COUNT(CASE WHEN LOWER(title) LIKE '%kabupaten%' OR LOWER(title) LIKE '%kota%' THEN 1 END) as kabupaten_kota_count
            FROM "group" 
            WHERE state = 'active'
        """)
        
        result = model.Session.execute(query)
        row = result.fetchone()
        
        return {
            'provinsi_terhubung': row.provinsi_count if row else 0,
            'kabupaten_kota_terhubung': row.kabupaten_kota_count if row else 0,
            'kementerian_lembaga_terhubung': row.kementerian_count if row else 0,
            'ngo_terhubung': row.ngo_count if row else 0
        }
        
    except Exception as e:
        return {
            'provinsi_terhubung': 0,
            'kabupaten_kota_terhubung': 0,
            'kementerian_lembaga_terhubung': 0,
            'ngo_terhubung': 0
        }




def get_view_count(package_name):
    """Get view count for a specific package"""
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT COUNT(*) as view_count
            FROM tracking_raw 
            WHERE url = '/dataset/' || :package_name
        """)
        
        result = model.Session.execute(query, {'package_name': package_name})
        row = result.fetchone()
        return row.view_count if row else 0
        
    except Exception as e:
        return 0


def groups():
    """Return a list of groups"""

    return toolkit.get_action('group_list')({}, {'all_fields': True})

def package_showcase_list(context):
    return toolkit.get_action('ckanext_package_showcase_list')({}, {'package_id': context.pkg_dict['id']})

def ckan_site_url():
    return config.get('ckan.site_url', '').rstrip('/')

def get_dataset_views(package_id):
    """Get tracking data for a dataset directly from raw tracking table"""
    try:
        # Get dataset name from package_id
        package = model.Package.get(package_id)
        if not package:
            return {'total_views': 0, 'recent_views': 0}
        
        dataset_url = f"/dataset/{package.name}"
        
        # Get total views from raw tracking table
        total_views = model.Session.query(model.TrackingRaw).filter(
            model.TrackingRaw.url == dataset_url
        ).count()
        
        # Get recent views (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_views = model.Session.query(model.TrackingRaw).filter(
            model.TrackingRaw.url == dataset_url,
            model.TrackingRaw.access_timestamp >= seven_days_ago
        ).count()
        
        # Get today's views
        today = datetime.utcnow().date()
        today_views = model.Session.query(model.TrackingRaw).filter(
            model.TrackingRaw.url == dataset_url,
            model.Session.func.date(model.TrackingRaw.access_timestamp) == today
        ).count()
        
        return {
            'total_views': total_views,
            'recent_views': recent_views,
            'today_views': today_views
        }
    except Exception as e:
        # Fallback to CKAN's tracking system if direct query fails
        try:
            tracking_summary = model.TrackingSummary.get_for_package(package_id)
            if tracking_summary:
                return {
                    'total_views': tracking_summary.get('total', 0),
                    'recent_views': tracking_summary.get('recent', 0),
                    'today_views': 0
                }
        except:
            pass
        return {'total_views': 0, 'recent_views': 0, 'today_views': 0}

def get_dataset_views_by_name(dataset_name):
    """Get tracking data for a dataset by name"""
    try:
        dataset_url = f"/dataset/{dataset_name}"
        
        # Use direct SQL query for better reliability
        from sqlalchemy import text
        
        # Get total views
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE url = :url
        """), {'url': dataset_url})
        total_views = result.fetchone()[0]
        
        # Get recent views (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE url = :url AND access_timestamp >= :seven_days_ago
        """), {'url': dataset_url, 'seven_days_ago': seven_days_ago})
        recent_views = result.fetchone()[0]
        
        # Get today's views
        today = datetime.utcnow().date()
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE url = :url AND DATE(access_timestamp) = :today
        """), {'url': dataset_url, 'today': today})
        today_views = result.fetchone()[0]
        
        return {
            'total_views': total_views,
            'recent_views': recent_views,
            'today_views': today_views
        }
    except Exception as e:
        # Return fallback data
        return {'total_views': 0, 'recent_views': 0, 'today_views': 0}

def get_dataset_downloads(package_id):
    """Get download count for a dataset from resource tracking data"""
    try:
        # Get dataset name from package_id
        package = model.Package.get(package_id)
        if not package:
            return {'total_downloads': 0, 'recent_downloads': 0}
        
        dataset_url = f"/dataset/{package.name}"
        
        # Get all resources for this dataset
        resources = package.resources
        
        # Count downloads for all resources of this dataset
        from sqlalchemy import text
        from datetime import datetime, timedelta
        
        # Get total downloads
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE tracking_type = 'resource' 
            AND url LIKE :dataset_pattern
        """), {'dataset_pattern': f"{dataset_url}/resource/%"})
        total_downloads = result.fetchone()[0]
        
        # Get recent downloads (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE tracking_type = 'resource' 
            AND url LIKE :dataset_pattern
            AND access_timestamp >= :seven_days_ago
        """), {
            'dataset_pattern': f"{dataset_url}/resource/%",
            'seven_days_ago': seven_days_ago
        })
        recent_downloads = result.fetchone()[0]
        
        # Get today's downloads
        today = datetime.utcnow().date()
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE tracking_type = 'resource' 
            AND url LIKE :dataset_pattern
            AND DATE(access_timestamp) = :today
        """), {
            'dataset_pattern': f"{dataset_url}/resource/%",
            'today': today
        })
        today_downloads = result.fetchone()[0]
        
        return {
            'total_downloads': total_downloads,
            'recent_downloads': recent_downloads,
            'today_downloads': today_downloads
        }
    except Exception as e:
        return {'total_downloads': 0, 'recent_downloads': 0, 'today_downloads': 0}

def get_dataset_downloads_by_name(dataset_name):
    """Get download count for a dataset by name"""
    try:
        # Use direct SQL query for better reliability
        from sqlalchemy import text
        from datetime import datetime, timedelta
        
        # Get dataset ID from name first
        result = model.Session.execute(text("""
            SELECT id FROM package WHERE name = :dataset_name
        """), {'dataset_name': dataset_name})
        dataset_row = result.fetchone()
        
        if not dataset_row:
            return {'total_downloads': 0, 'recent_downloads': 0, 'today_downloads': 0}
        
        dataset_id = dataset_row[0]
        
        # Get total downloads - menggunakan dataset ID
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE tracking_type = 'resource' 
            AND url LIKE :dataset_pattern
        """), {'dataset_pattern': f"%/dataset/{dataset_id}/resource/%"})
        total_downloads = result.fetchone()[0]
        
        # Get recent downloads (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE tracking_type = 'resource' 
            AND url LIKE :dataset_pattern
            AND access_timestamp >= :seven_days_ago
        """), {
            'dataset_pattern': f"%/dataset/{dataset_id}/resource/%",
            'seven_days_ago': seven_days_ago
        })
        recent_downloads = result.fetchone()[0]
        
        # Get today's downloads
        today = datetime.utcnow().date()
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw 
            WHERE tracking_type = 'resource' 
            AND url LIKE :dataset_pattern
            AND DATE(access_timestamp) = :today
        """), {
            'dataset_pattern': f"%/dataset/{dataset_id}/resource/%",
            'today': today
        })
        today_downloads = result.fetchone()[0]
        
        return {
            'total_downloads': total_downloads,
            'recent_downloads': recent_downloads,
            'today_downloads': today_downloads
        }
    except Exception as e:
        return {'total_downloads': 0, 'recent_downloads': 0, 'today_downloads': 0}

def get_total_visitors():
    """Get total number of unique visitors from tracking_raw table"""
    try:
        from sqlalchemy import text
        
        # Get total unique visitors (unique user_key)
        result = model.Session.execute(text("""
            SELECT COUNT(DISTINCT user_key) as count FROM tracking_raw 
            WHERE user_key != 'anonymous'
        """))
        unique_visitors = result.fetchone()[0]
        
        # Get total page views
        result = model.Session.execute(text("""
            SELECT COUNT(*) as count FROM tracking_raw
        """))
        total_views = result.fetchone()[0]
        
        # Get today's visitors
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        
        result = model.Session.execute(text("""
            SELECT COUNT(DISTINCT user_key) as count FROM tracking_raw 
            WHERE DATE(access_timestamp) = :today AND user_key != 'anonymous'
        """), {'today': today})
        today_visitors = result.fetchone()[0]
        
        # Get yesterday's visitors
        yesterday = today - timedelta(days=1)
        result = model.Session.execute(text("""
            SELECT COUNT(DISTINCT user_key) as count FROM tracking_raw 
            WHERE DATE(access_timestamp) = :yesterday AND user_key != 'anonymous'
        """), {'yesterday': yesterday})
        yesterday_visitors = result.fetchone()[0]
        
        # Get online visitors (active in last 5 minutes)
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        result = model.Session.execute(text("""
            SELECT COUNT(DISTINCT user_key) as count FROM tracking_raw 
            WHERE access_timestamp >= :five_minutes_ago AND user_key != 'anonymous'
        """), {'five_minutes_ago': five_minutes_ago})
        online_visitors = result.fetchone()[0]
        
        return {
            'unique_visitors': unique_visitors,
            'total_views': total_views,
            'today_visitors': today_visitors,
            'yesterday_visitors': yesterday_visitors,
            'online_visitors': online_visitors
        }
    except Exception as e:
        return {
            'unique_visitors': 0,
            'total_views': 0,
            'today_visitors': 0,
            'yesterday_visitors': 0,
            'online_visitors': 0
        }

def json_loads(data):
    """Parse JSON string safely"""
    try:
        import json
        if data:
            return json.loads(data)
        return None
    except (ValueError, TypeError):
        return None

class SDBIPlugin(plugins.SingletonPlugin):
    # SDBI Plugin for BNPB Data Portal
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IResourceController, inherit=True)

    # IConfigurer
    def update_config(self, config_):
        # Local/dev MFA bypass flag (ckanext-envvars + CKAN 2.10 may not stick undeclared keys).
        import os
        from ckantoolkit import asbool
        raw = os.environ.get('CKANEXT__SECURITY__ENABLE_TOTP')
        if raw is not None:
            config_['ckanext.security.enable_totp'] = raw
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'sdbi')
        # Only api_info needs to beat ckanext-datastore. Putting the whole
        # templates/ tree on extra_template_paths breaks {% ckan_extends %}
        # (e.g. user/read.html extends itself → RecursionError).
        priority_tpl = os.path.join(
            os.path.dirname(__file__), 'templates_priority'
        )
        existing = [
            p for p in (config_.get('extra_template_paths') or '').split(',')
            if p and os.path.abspath(p) != os.path.abspath(priority_tpl)
        ]
        config_['extra_template_paths'] = ','.join([priority_tpl] + existing)
        # ckanext-security monkeypatches user schemas and drops image_url,
        # so profile photo uploads write to disk then get stripped on validate.
        self._restore_user_image_url_schema()

    @staticmethod
    def _restore_user_image_url_schema():
        # IConfigurer runs in reverse plugin order, so security.update_config
        # reassigns schemas AFTER us. Patch ckanext.security.schema itself so
        # that reassignment still keeps image_url / image_display_url.
        from ckan.lib.navl.validators import ignore_missing, unicode_safe
        from ckan.logic import schema as core_schema

        try:
            from ckanext.security import schema as sec_schema
        except ImportError:
            sec_schema = None

        targets = (
            'default_user_schema',
            'user_new_form_schema',
            'user_edit_form_schema',
            'default_update_user_schema',
        )

        def _with_image_url(schema_func):
            if getattr(schema_func, '_sdbi_image_url_restored', False):
                return schema_func

            def wrapped(*args, **kwargs):
                schema = schema_func(*args, **kwargs)
                schema['image_url'] = [ignore_missing, unicode_safe]
                schema['image_display_url'] = [ignore_missing, unicode_safe]
                return schema

            wrapped.__name__ = getattr(schema_func, '__name__', 'wrapped')
            wrapped.__module__ = getattr(schema_func, '__module__', __name__)
            wrapped._sdbi_image_url_restored = True
            return wrapped

        if sec_schema is not None:
            for name in targets:
                fn = getattr(sec_schema, name, None)
                if callable(fn):
                    setattr(sec_schema, name, _with_image_url(fn))

        for name in targets:
            fn = getattr(core_schema, name, None)
            if callable(fn):
                setattr(core_schema, name, _with_image_url(fn))

    # IFacets
    def dataset_facets(self, facets_dict, package_type):

        if package_type != 'dataset':
            return facets_dict

        return OrderedDict([('jenis', 'Jenis Bencana'),
                            ('fase', 'Fase'),
                            #('groups', 'Grup'),
                            ('organization', 'Organisasi'),
                            #('vocab_category_all', 'Topic Categories'),
                            #('metadata_type', 'Dataset Type'),
                            #('tags', 'Tagging'),
                            ('res_format', 'Format'),
                            #('organization_type', 'Organization Types'),
                            #('publisher', 'Publishers'),
                            #('extras_progress', 'Progress'),
                            ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if not package_type:
            return OrderedDict([('organization', 'Organisasi'),
                                ('jenis', 'Jenis Bencana'),
                                ('fase', 'Fase'),
                                #('groups', 'Grup'),
                                #('organization', 'Instansi'),
                                #('vocab_category_all', 'Topic Categories'),
                                #('metadata_type', 'Dataset Type'),
                                #('tags', 'Tagging'),
                                ('res_format', 'Format'),
                                #('harvest_source_title', 'Harvest Source'),
                                #('capacity', 'Visibility'),
                                #('dataset_type', 'Resource Type'),
                                #('publisher', 'Publishers'),
                                ])
        else:
            return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):

        # get the categories key
        group_id = plugins.toolkit.c.group_dict['id']
        key = 'vocab___category_tag_%s' % group_id
        if not package_type:
            return OrderedDict([('jenis', 'Jenis Bencana'),
                                ('fase', 'Fase'),
                                #('groups', 'Grup'),
                                ('organization', 'Organisasi'),
                                #('metadata_type', 'Dataset Type'),
                                #('organization_type', 'Organization Types'),
                                #('tags', 'Tagging'),
                                ('res_format', 'Format'),
                                #(key, 'Categories'),
                                #('publisher', 'Publisher'),
                                ])
        else:
            return facets_dict

    def get_helpers(self):
        """Register sdbi_theme_* helper functions"""

        return {'sdbi_theme_most_recent_datasets': most_recent_datasets,
                'sdbi_theme_most_popular_datasets': most_popular_datasets,
                'sdbi_theme_dataset_count': dataset_count,
                'sdbi_theme_connected_statistics': get_connected_statistics,
                'sdbi_theme_get_view_count': get_view_count,
                'sdbi_theme_groups': groups,
                'ckan_site_url': ckan_site_url,
                'package_showcase_list': package_showcase_list,
                'get_dataset_views': get_dataset_views,
                'get_dataset_views_by_name': get_dataset_views_by_name,
                'get_dataset_downloads': get_dataset_downloads,
                'get_dataset_downloads_by_name': get_dataset_downloads_by_name,
                'get_total_visitors': get_total_visitors,
                'json_loads': json_loads,
                'sdbi_json_harvest_form_defaults': json_harvest_form_defaults,
                'sdbi_tanggap_rooms': sdbi_tanggap_rooms,
                'sdbi_totp_configured': sdbi_totp_configured,
                'sdbi_beranda_kategori_counts': beranda_kategori_counts,
                'sdbi_beranda_waktu': beranda_waktu,
                'sdbi_beranda_extras': beranda_extras}

    def get_auth_functions(self):
        # CKAN 2.10 refuses a second implementation of the same auth
        # function unless it is chained onto the existing one.
        from ckanext.sdbi.auth import (
            HARVEST_SYSADMIN_ONLY_ACTIONS,
            datastore_search_sql as sql_auth,
            harvest_manage,
            package_create_harvest_guard,
            package_delete_harvest_guard,
            package_update_harvest_guard,
        )

        @toolkit.chained_auth_function
        def datastore_search_sql(next_auth, context, data_dict):
            result = sql_auth(context, data_dict)
            if result.get('success'):
                return next_auth(context, data_dict)
            return result

        # Harvest sources are package type "harvest"; UI uses package_create/update.
        @toolkit.chained_auth_function
        def package_create(next_auth, context, data_dict):
            denied = package_create_harvest_guard(context, data_dict)
            if denied is not None:
                return denied
            return next_auth(context, data_dict)

        @toolkit.chained_auth_function
        def package_update(next_auth, context, data_dict):
            denied = package_update_harvest_guard(context, data_dict)
            if denied is not None:
                return denied
            return next_auth(context, data_dict)

        @toolkit.chained_auth_function
        def package_delete(next_auth, context, data_dict):
            denied = package_delete_harvest_guard(context, data_dict)
            if denied is not None:
                return denied
            return next_auth(context, data_dict)

        auth = {
            'datastore_search_sql': datastore_search_sql,
            'package_create': package_create,
            'package_update': package_update,
            'package_delete': package_delete,
        }

        # Harvest API actions — sysadmins never hit these (authz bypass).
        def _make_harvest_deny():
            @toolkit.chained_auth_function
            def _deny(next_auth, context, data_dict):
                return harvest_manage(context, data_dict)

            return _deny

        for action in HARVEST_SYSADMIN_ONLY_ACTIONS:
            auth[action] = _make_harvest_deny()

        return auth

    # IResourceController — remote CSV/Excel links → DataStore table view
    def after_resource_create(self, context, resource):
        self._maybe_sync_remote_table(context, resource)

    def after_resource_update(self, context, resource):
        self._maybe_sync_remote_table(context, resource)

    @staticmethod
    def _maybe_sync_remote_table(context, resource):
        try:
            from ckanext.sdbi.lib.datastore_table import (
                sync_remote_tabular_resource,
            )
            sync_remote_tabular_resource(resource, context=context)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                'Remote tabular sync failed for resource %s',
                (resource or {}).get('id'),
            )

    # IBlueprint
    def get_blueprint(self):
        """Register blueprints"""
        import logging
        log = logging.getLogger(__name__)
        log.info("Registering blueprints")
        
        from ckanext.sdbi.controllers.google_forms import google_forms_blueprint
        from ckanext.sdbi.controllers.tracking import TrackingController
        from ckanext.sdbi.controllers.analytics import analytics_blueprint
        from ckanext.sdbi.controllers.tanggap_darurat import tanggap_darurat_blueprint
        from ckanext.sdbi.controllers.sebaran_bpbd import sebaran_bpbd_blueprint
        from ckanext.sdbi.controllers.bantuan import bantuan_blueprint
        from ckanext.sdbi.controllers.mfa import mfa_blueprint
        
        # Create tracking blueprint
        from flask import Blueprint
        tracking_blueprint = Blueprint('tracking', __name__)
        
        # Add routes
        tracking_blueprint.add_url_rule('/sdbi/tracking', 'track', TrackingController().track, methods=['POST'])
        tracking_blueprint.add_url_rule('/sdbi/tracking/page', 'track_page', TrackingController().track_page, methods=['GET'])
        tracking_blueprint.add_url_rule('/sdbi/downloads/<dataset_name>', 'get_downloads', TrackingController().get_downloads, methods=['GET'])
        
        # Return list of blueprints
        return [
            google_forms_blueprint,
            tracking_blueprint,
            analytics_blueprint,
            tanggap_darurat_blueprint,
            sebaran_bpbd_blueprint,
            bantuan_blueprint,
            mfa_blueprint,
        ]


