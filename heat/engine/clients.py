# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from novaclient.v1_1 import client as nc
from keystoneclient.v2_0 import client as kc

# swiftclient not available in all distributions - make s3 an optional
# feature
try:
    from swiftclient import client as swiftclient
    swiftclient_present = True
except ImportError:
    swiftclient_present = False
# quantumclient not available in all distributions - make quantum an optional
# feature
try:
    from quantumclient.v2_0 import client as quantumclient
    quantumclient_present = True
except ImportError:
    quantumclient_present = False

from heat.openstack.common import log as logging

logger = logging.getLogger('heat.engine.clients')


class Clients(object):
    '''
    Convenience class to create and cache client instances.
    '''

    def __init__(self, context):
        self.context = context
        self._nova = {}
        self._keystone = None
        self._swift = None
        self._quantum = None

    def keystone(self):
        if self._keystone:
            return self._keystone

        con = self.context
        args = {
            'auth_url': con.auth_url,
        }

        if con.password is not None:
            args['username'] = con.username
            args['password'] = con.password
            args['tenant_name'] = con.tenant
            args['tenant_id'] = con.tenant_id
        elif con.auth_token is not None:
            args['username'] = con.service_user
            args['password'] = con.service_password
            args['tenant_name'] = con.service_tenant
            args['token'] = con.auth_token
        else:
            logger.error("Keystone connection failed, no password or " +
                         "auth_token!")
            return None

        client = kc.Client(**args)
        client.authenticate()
        self._keystone = client
        return self._keystone

    def nova(self, service_type='compute'):
        if service_type in self._nova:
            return self._nova[service_type]

        con = self.context
        args = {
            'project_id': con.tenant,
            'auth_url': con.auth_url,
            'service_type': service_type,
        }

        if con.password is not None:
            args['username'] = con.username
            args['api_key'] = con.password
        elif con.auth_token is not None:
            args['username'] = con.service_user
            args['api_key'] = con.service_password
            args['project_id'] = con.service_tenant
            args['proxy_token'] = con.auth_token
            args['proxy_tenant_id'] = con.tenant_id
        else:
            logger.error("Nova connection failed, no password or auth_token!")
            return None

        client = None
        try:
            # Workaround for issues with python-keyring, need no_cache=True
            # ref https://bugs.launchpad.net/python-novaclient/+bug/1020238
            # TODO(shardy): May be able to remove when the bug above is fixed
            client = nc.Client(no_cache=True, **args)
            client.authenticate()
            self._nova[service_type] = client
        except TypeError:
            # for compatibility with essex, which doesn't have no_cache=True
            # TODO(shardy): remove when we no longer support essex
            client = nc.Client(**args)
            client.authenticate()
            self._nova[service_type] = client

        return client

    def swift(self):
        if swiftclient_present == False:
            return None
        if self._swift:
            return self._swift

        con = self.context
        args = {
            'auth_version': '2'
        }

        if con.password is not None:
            args['user'] = con.username
            args['key'] = con.password
            args['authurl'] = con.auth_url
            args['tenant_name'] = con.tenant
        elif con.auth_token is not None:
            args['user'] = None
            args['key'] = None
            args['authurl'] = None
            args['preauthtoken'] = con.auth_token
            # Lookup endpoint for object-store service type
            service_type = 'object-store'
            endpoints = self.keystone().service_catalog.get_endpoints(
                        service_type=service_type)
            if len(endpoints[service_type]) == 1:
                args['preauthurl'] = endpoints[service_type][0]['publicURL']
            else:
                logger.error("No endpoint found for %s service type" %
                             service_type)
                return None
        else:
            logger.error("Swift connection failed, no password or " +
                         "auth_token!")
            return None

        self._swift = swiftclient.Connection(**args)
        return self._swift

    def quantum(self):
        if quantumclient_present == False:
            return None
        if self._quantum:
            logger.debug('using existing _quantum')
            return self._quantum

        con = self.context
        args = {
            'auth_url': con.auth_url,
            'service_type': 'network',
        }

        if con.password is not None:
            args['username'] = con.username
            args['password'] = con.password
            args['tenant_name'] = con.tenant
        elif con.auth_token is not None:
            args['username'] = con.service_user
            args['password'] = con.service_password
            args['tenant_name'] = con.service_tenant
            args['token'] = con.auth_token
        else:
            logger.error("Quantum connection failed, "
                "no password or auth_token!")
            return None
        logger.debug('quantum args %s', args)

        self._quantum = quantumclient.Client(**args)

        return self._quantum
