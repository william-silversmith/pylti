# -*- coding: utf-8 -*-
"""
Test pylti/test_common.py module
"""
import unittest
import semantic_version

import httpretty

import pylti
from pylti.common import (
    LTIOAuthDataStore,
    verify_request_common,
    LTIException,
    post_message,
    generate_request_xml
)

try:
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs

import urllib
import oauthlib.oauth1


class TestCommon(unittest.TestCase):
    """
    Tests for common.py
    """
    expected_response = """<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeResponse xmlns = "http://www.imsglobal.org/services/ltiv1p1\
/xsd/imsoms_v1p0">
    <imsx_POXHeader>
        <imsx_POXResponseHeaderInfo>
            <imsx_version>V1.0</imsx_version>
            <imsx_messageIdentifier>edX_fix</imsx_messageIdentifier>
            <imsx_statusInfo>
                <imsx_codeMajor>success</imsx_codeMajor>
                <imsx_severity>status</imsx_severity>
                <imsx_description>Score for StarX/StarX_DEMO/201X_StarX:\
edge.edx.org-i4x-StarX-StarX_DEMO-lti-40559041895b4065b2818c23b9cd9da8\
:18b71d3c46cb4dbe66a7c950d88e78ec is now 0.0</imsx_description>
                <imsx_messageRefIdentifier>
                </imsx_messageRefIdentifier>
            </imsx_statusInfo>
        </imsx_POXResponseHeaderInfo>
    </imsx_POXHeader>
    <imsx_POXBody><replaceResultResponse/></imsx_POXBody>
</imsx_POXEnvelopeResponse>
        """

    def test_version(self):
        # Will raise ValueError if not a semantic version
        semantic_version.Version(pylti.VERSION)

    def test_ltioauthdatastore(self):
        """
        Tests that LTIOAuthDataStore works
        """
        consumers = {
            "key1": {"secret": "secret1"},
            "key2": {"secret": "secret2"},
            "key3": {"secret": "secret3"},
            "keyNS": {"test": "test"}
        }
        store = LTIOAuthDataStore(consumers)
        self.assertEqual(store.lookup_consumer("key1").secret, "secret1")
        self.assertEqual(store.lookup_consumer("key2").secret, "secret2")
        self.assertEqual(store.lookup_consumer("key3").secret, "secret3")
        self.assertIsNone(store.lookup_consumer("key4"))
        self.assertIsNone(store.lookup_consumer("keyNS"))

    def test_ltioauthdatastore_no_consumers(self):
        """
        If consumers are not given it there are no consumer to return.

        """
        store = LTIOAuthDataStore(None)
        self.assertIsNone(store.lookup_consumer("key1"))

    def test_verify_request_common(self):
        """
        verify_request_common succeeds on valid request
        """
        headers = dict()
        consumers, method, url, verify_params, params = \
            self.generate_oauth_request()
        ret = verify_request_common(consumers, url, method,
                                    headers, verify_params)
        self.assertTrue(ret)

    def test_verify_request_common_via_proxy(self):
        """
        verify_request_common succeeds on valid request via proxy
        """
        headers = dict()
        headers['X-Forwarded-Proto'] = 'https'
        orig_url = 'https://localhost:5000/?'
        consumers, method, url, verify_params, params = \
            self.generate_oauth_request(url_to_sign=orig_url)
        ret = verify_request_common(consumers, url, method,
                                    headers, verify_params)
        self.assertTrue(ret)

    def test_verify_request_common_no_auth_fields(self):
        """
        verify_request_common fails on missing authentication
        """
        headers = dict()
        consumers, method, url, verify_params, params = \
            self.generate_oauth_request()
        ret = False
        try:
            ret = verify_request_common(consumers, url, method,
                                        headers, params)
        except LTIException:
            self.assertTrue(True)
        self.assertFalse(ret)

    def test_verify_request_common_no_params(self):
        """
        verify_request_common fails on missing parameters
        """
        consumers = {
            "__consumer_key__": {"secret": "__lti_secret__"}
        }
        url = 'http://localhost:5000/?'
        method = 'GET'
        headers = dict()
        params = dict()
        ret = False
        try:
            ret = verify_request_common(consumers, url, method,
                                        headers, params)
        except LTIException:
            self.assertTrue(True)
        self.assertFalse(ret)

    @httpretty.activate
    def test_post_response_invalid_xml(self):
        """
        Test post message with invalid XML response
        """
        uri = (u'https://edge.edx.org/courses/MITx/ODL_ENG/2014_T1/xblock/'
               u'i4x:;_;_MITx;_ODL_ENG;_lti;_94173d3e79d145fd8ec2e83f15836ac8/'
               u'handler_noauth/grade_handler')

        def request_callback(request, cburi, headers):
            return 200, headers, "success"

        httpretty.register_uri(httpretty.POST, uri, body=request_callback)
        consumers = {
            "__consumer_key__": {"secret": "__lti_secret__"}
        }
        body = '<xml></xml>'
        ret = post_message(consumers, "__consumer_key__", uri, body)
        self.assertFalse(ret)

    @httpretty.activate
    def test_post_response_valid_xml(self):
        """
        Test post grade with valid XML response
        """
        uri = 'https://localhost:8000/dev_stack'

        def request_callback(request, cburi, headers):
            return 200, headers, self.expected_response

        httpretty.register_uri(httpretty.POST, uri, body=request_callback)
        consumers = {
            "__consumer_key__": {"secret": "__lti_secret__"}
        }
        body = generate_request_xml('message_identifier_id', 'operation',
                                    'lis_result_sourcedid', '1.0')
        ret = post_message(consumers, "__consumer_key__", uri, body)
        self.assertTrue(ret)

    def test_generate_xml(self):
        """
        Generated post XML is valid
        """
        xml = generate_request_xml('message_identifier_id', 'operation',
                                   'lis_result_sourcedid', 'score')
        self.assertEqual(xml, """<?xml version='1.0' encoding='utf-8'?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/\
imsoms_v1p0"><imsx_POXHeader><imsx_POXRequestHeaderInfo><imsx_version>V1.0\
</imsx_version><imsx_messageIdentifier>message_identifier_id\
</imsx_messageIdentifier></imsx_POXRequestHeaderInfo></imsx_POXHeader>\
<imsx_POXBody><operationRequest><resultRecord><sourcedGUID><sourcedId>\
lis_result_sourcedid</sourcedId></sourcedGUID><result><resultScore>\
<language>en</language><textString>score</textString></resultScore>\
</result></resultRecord></operationRequest></imsx_POXBody>\
</imsx_POXEnvelopeRequest>""")
        xml = generate_request_xml('message_identifier_id', 'operation',
                                   'lis_result_sourcedid', None)
        self.assertEqual(xml, """<?xml version='1.0' encoding='utf-8'?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/\
imsoms_v1p0"><imsx_POXHeader><imsx_POXRequestHeaderInfo><imsx_version>V1.0\
</imsx_version><imsx_messageIdentifier>message_identifier_id\
</imsx_messageIdentifier></imsx_POXRequestHeaderInfo></imsx_POXHeader>\
<imsx_POXBody><operationRequest><resultRecord><sourcedGUID><sourcedId>\
lis_result_sourcedid</sourcedId></sourcedGUID></resultRecord></operationRequest>\
</imsx_POXBody></imsx_POXEnvelopeRequest>""")

    def generate_oauth_request(self, url_to_sign=None):
        """
        This code generated valid LTI 1.0 basic-lti-launch-request request
        """
        consumers = {
            "__consumer_key__": {"secret": "__lti_secret__"}
        }
        url = 'http://localhost:5000/?'
        method = 'GET'
        params = {'resource_link_id': u'edge.edx.org-i4x-MITx-ODL_ENG-'
                                      u'lti-94173d3e79d145fd8ec2e83f15836ac8',
                  'user_id': u'008437924c9852377e8994829aaac7a1',
                  'roles': u'Instructor',
                  'lis_result_sourcedid': u'MITx/ODL_ENG/2014_T1:edge.edx.org-'
                                          u'i4x-MITx-ODL_ENG-lti-'
                                          u'94173d3e79d145fd8ec2e83f15836ac8'
                                          u':008437924c9852377e8994829aaac7a1',
                  'context_id': u'MITx/ODL_ENG/2014_T1',
                  'lti_version': u'LTI-1p0',
                  'launch_presentation_return_url': u'',
                  'lis_outcome_service_url': u'https://edge.edx.org/courses/'
                                             u'MITx/ODL_ENG/2014_T1/xblock/'
                                             u'i4x:;_;_MITx;_ODL_ENG;_lti;_'
                                             u'94173d3e79d145fd8ec2e83f1583'
                                             u'6ac8/handler_noauth'
                                             u'/grade_handler',
                  'lti_message_type': u'basic-lti-launch-request',
                  }
        urlparams = urllib.urlencode(params)

        client = oauthlib.oauth1.Client('__consumer_key__',
                                        client_secret='__lti_secret__',
                                        signature_method=oauthlib.oauth1.
                                        SIGNATURE_HMAC,
                                        signature_type=oauthlib.oauth1.
                                        SIGNATURE_TYPE_QUERY)
        signature = client.sign("{}{}".format(url_to_sign or url, urlparams))

        q = urlparse(signature[0])
        qs = parse_qs(q.query, keep_blank_values=True)
        verify_params = dict()
        for k, v in qs.iteritems():
            verify_params[k] = v[0]
        return consumers, method, url, verify_params, params
