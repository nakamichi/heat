# vim: tabstop=4 shiftwidth=4 softtabstop=4

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


import sys
import os

import nose
import unittest
import mox
import json

from nose.plugins.attrib import attr

from heat.common import exception
from heat.engine import parser
from heat.engine.resources import stack
from heat.engine.resources import dbinstance as dbi


@attr(tag=['unit', 'resource'])
@attr(speed='fast')
class DBInstanceTest(unittest.TestCase):
    def setUp(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(stack.Stack, 'create_with_template')
        self.m.StubOutWithMock(dbi.DBInstance, 'nested')

    def tearDown(self):
        self.m.UnsetStubs()
        print "DBInstanceTest teardown complete"

    def load_template(self):
        self.path = os.path.dirname(os.path.realpath(__file__)).\
            replace('heat/tests', 'templates')
        f = open("%s/WordPress_With_RDS.template" % self.path)
        t = json.loads(f.read())
        f.close()
        return t

    def parse_stack(self, t):
        class DummyContext():
            tenant = 'test_tenant'
            tenant_id = '1234abcd'
            username = 'test_username'
            password = 'password'
            auth_url = 'http://localhost:5000/v2.0'
        template = parser.Template(t)
        params = parser.Parameters('test_stack', template, {'KeyName': 'test'})
        stack = parser.Stack(DummyContext(), 'test_stack', template,
                             params, stack_id=-1)

        return stack

    def create_dbinstance(self, t, stack, resource_name):
        resource = dbi.DBInstance(resource_name,
                                      t['Resources'][resource_name],
                                      stack)
        self.assertEqual(None, resource.validate())
        self.assertEqual(None, resource.create())
        self.assertEqual(dbi.DBInstance.CREATE_COMPLETE, resource.state)
        return resource

    def test_dbinstance(self):

        class FakeDatabaseInstance:
            def _ipaddress(self):
                return '10.0.0.1'

        class FakeNested:
            resources = {'DatabaseInstance': FakeDatabaseInstance()}

        stack.Stack.create_with_template(mox.IgnoreArg()).AndReturn(None)

        fn = FakeNested()

        dbi.DBInstance.nested().AndReturn(None)
        dbi.DBInstance.nested().MultipleTimes().AndReturn(fn)
        self.m.ReplayAll()

        t = self.load_template()
        s = self.parse_stack(t)
        resource = self.create_dbinstance(t, s, 'DatabaseServer')

        self.assertEqual({'AllocatedStorage': u'5',
            'DBInstanceClass': u'db.m1.small',
            'DBName': u'wordpress',
            'DBSecurityGroups': [],
            'KeyName': 'test',
            'MasterUserPassword': u'admin',
            'MasterUsername': u'admin',
            'Port': '3306'}, resource._params())

        self.assertEqual('0.0.0.0', resource.FnGetAtt('Endpoint.Address'))
        self.assertEqual('10.0.0.1', resource.FnGetAtt('Endpoint.Address'))
        self.assertEqual('3306', resource.FnGetAtt('Endpoint.Port'))

        try:
            resource.FnGetAtt('foo')
        except exception.InvalidTemplateAttribute:
            pass
        else:
            raise Exception('Expected InvalidTemplateAttribute')

        self.m.VerifyAll()

    # allows testing of the test directly, shown below
    if __name__ == '__main__':
        sys.argv.append(__file__)
        nose.main()
