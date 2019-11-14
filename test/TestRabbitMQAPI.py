import logging
import json

from requests import HTTPError
from mgdeployeur.RabbitMQManagement import RabbitMQAPI

import rabbitmq_admin

class TestAPI:

    def __init__(self):
        self.api = RabbitMQAPI('mg-dev3', 'dudE_W475@euch', '/opt/millegrilles/dev3/pki/deployeur/pki.ca.fullchain.pem')

    def vhost_tests(self):
        vhost_name = 'dev1'
        try:
            vhost = self.api.get_vhost(vhost_name)
            logger.debug("Vhost:\n%s" % json.dumps(vhost, indent=4))
        except HTTPError:
            self.api.create_vhost(vhost_name)
            logger.debug("Cree vhost %s" % vhost_name)

    def overview(self):
        self.api.get_overview()

    def create_user(self):
        username = 'user5'
        vhost = 'dev1'
        exchange = 'test_exchange'
        self.api.create_user(username)
        self.api.create_user_permission(username, vhost)
        self.api.create_user_topic(username, vhost, exchange)

    def get_user(self, name):
        return self.api.get_user(name)

    def create_exchange(self, name, vhost):
        self.api.create_exchange_for_vhost(name, vhost, {
            "type": "topic",
            "durable": True,
        })

    def run_healthchecks(self):
        print(self.api.healthchecks())
        print(self.api.aliveness('dev1'))

    def changer_motdepasse(self):
        self.api.create_user('user2', 'p1234')


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger('__main__').setLevel(logging.DEBUG)
    logging.getLogger('mgdeployeur').setLevel(logging.DEBUG)

    logger = logging.getLogger('__main__')

    test = TestAPI()
    #test.overview()
    #test.vhost_tests()
    # test.create_user()
    # user = test.get_user('user2')
    # logger.debug("User:\n%s" % json.dumps(user, indent=4))
    # test.create_exchange('exchange1', 'dev1')
    # test.run_healthchecks()
    test.changer_motdepasse()

