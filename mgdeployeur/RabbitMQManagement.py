from requests import HTTPError
import requests
import json
import urllib

import logging


class RabbitMQAPI:
    """
    Provient de https://pypi.org/project/rabbitmq-admin/
    Copie pour ajouter handling cert CA pour https (verify)
    """

    def __init__(self, docker_nodename, password, ca_certs, port=8443):
        self.logger = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.url = 'https://%s:%d' % (docker_nodename, port)
        self.auth = ('admin', password)
        self.ca_cert_path = ca_certs

        self.headers = {
            'Content-type': 'application/json',
        }

    def get_overview(self):
        overview = self._api_get('/api/overview')
        self.logger.debug("Overview:\n%s" % json.dumps(overview, indent=4))
        return overview

    def get_vhost(self, name):
        """
        Details about an individual vhost.

        :param name: The vhost name
        :type name: str
        """
        return self._api_get('/api/vhosts/{0}'.format(
            urllib.parse.quote_plus(name)
        ))

    def create_vhost(self, name, tracing=False):
        """
        Create an individual vhost.

        :param name: The vhost name
        :type name: str

        :param tracing: Set to ``True`` to enable tracing
        :type tracing: bool
        """
        data = {'tracing': True} if tracing else {}
        self._api_put(
            '/api/vhosts/{0}'.format(urllib.parse.quote_plus(name)),
            data=data,
        )

    def get_user(self, name):
        """
        Details about an individual user.

        :param name: The user's name
        :type name: str
        """
        return self._api_get('/api/users/{0}'.format(
            urllib.parse.quote_plus(name)
        ))

    def create_user(self, name):
        """
        Create a user

        :param name: The user's name
        :type name: str
        """
        data = {
            'tags': '',
            'password_hash': ''  # Desactive auth par mot de passe
        }

        self._api_put(
            '/api/users/{0}'.format(urllib.parse.quote_plus(name)),
            data=data,
        )

    def create_user_permission(self,
                               name,
                               vhost,
                               configure=None,
                               write=None,
                               read=None):
        """
        Create a user permission
        :param name: The user's name
        :type name: str
        :param vhost: The vhost to assign the permission to
        :type vhost: str

        :param configure: A regex for the user permission. Default is ``.*``
        :type configure: str
        :param write: A regex for the user permission. Default is ``.*``
        :type write: str
        :param read: A regex for the user permission. Default is ``.*``
        :type read: str
        """
        data = {
            'configure': configure or '.*',
            'write': write or '.*',
            'read': read or '.*',
        }
        self._api_put(
            '/api/permissions/{0}/{1}'.format(
                urllib.parse.quote_plus(vhost),
                urllib.parse.quote_plus(name)
            ),
            data=data
        )

    def create_user_topic(self, name, vhost, exchange, write=None, read=None):
        data = {
            'exchange': exchange,
            'write': write or '.*',
            'read': read or '.*',
        }
        self._api_put(
            '/api/topic-permissions/{0}/{1}'.format(
                urllib.parse.quote_plus(vhost),
                urllib.parse.quote_plus(name)
            ),
            data=data
        )

    def _api_get(self, url, **kwargs):
        """
        A convenience wrapper for _get. Adds headers, auth and base url by
        default
        """
        kwargs['url'] = self.url + url
        kwargs['auth'] = self.auth

        headers = dict()
        headers.update(self.headers)
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        kwargs['verify'] = self.ca_cert_path

        return self.__get(**kwargs)

    def __get(self, *args, **kwargs):
        """
        :returns:
        """
        response = requests.get(*args, **kwargs)
        response.raise_for_status()
        return response.json()

    def _api_put(self, url, **kwargs):
        """
        A convenience wrapper for _put. Adds headers, auth and base url by
        default
        """
        kwargs['url'] = self.url + url
        kwargs['auth'] = self.auth

        headers = dict()
        headers.update(self.headers)
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        kwargs['verify'] = self.ca_cert_path
        self._put(**kwargs)

    def _put(self, *args, **kwargs):
        """
        A wrapper for putting things. It will also json encode your 'data' parameter

        :returns: The response of your put
        :rtype: dict
        """
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        response = requests.put(*args, **kwargs)
        print(str(response))
        response.raise_for_status()

    def _api_post(self, url, **kwargs):
        """
        A convenience wrapper for _post. Adds headers, auth and base url by
        default
        """
        kwargs['url'] = self.url + url
        kwargs['auth'] = self.auth

        headers = dict()
        headers.update(self.headers)
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        kwargs['verify'] = self.ca_cert_path
        self._post(**kwargs)

    def _post(self, *args, **kwargs):
        """
        A wrapper for posting things. It will also json encode your 'data' parameter

        :returns: The response of your post
        :rtype: dict
        """
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        response = requests.post(*args, **kwargs)
        response.raise_for_status()

    def _api_delete(self, url, **kwargs):
        """
        A convenience wrapper for _delete. Adds headers, auth and base url by
        default
        """
        kwargs['url'] = self.url + url
        kwargs['auth'] = self.auth

        headers = dict()
        headers.update(self.headers)
        headers.update(kwargs.get('headers', {}))
        kwargs['headers'] = headers
        kwargs['verify'] = self.ca_cert_path
        self._delete(**kwargs)

    def _delete(self, *args, **kwargs):
        """
        A wrapper for deleting things

        :returns: The response of your delete
        :rtype: dict
        """
        response = requests.delete(*args, **kwargs)
        response.raise_for_status()