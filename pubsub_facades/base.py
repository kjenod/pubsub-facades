"""
Copyright 2019 EUROCONTROL
==========================================

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
   disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
   disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

==========================================

Editorial note: this license is an instance of the BSD license template as provided by the Open Source Initiative:
http://opensource.org/licenses/BSD-3-Clause

Details on EUROCONTROL: http://www.eurocontrol.int
"""

__author__ = "EUROCONTROL (SWIM)"

from functools import wraps
import logging.config
from typing import Type

import yaml
from rest_client.errors import APIError
from rest_client.typing import RestClient
from swim_proton.containers import PubSubContainer

from pubsub_facades import ConfigDict


def yaml_file_to_dict(filename: str) -> ConfigDict:
    """
    Converts a yml file into a dict
    :param filename:
    :return:
    """
    if not filename.endswith(".yml"):
        raise ValueError("YAML config files should end with '.yml' extension (RTFMG).")

    with open(filename) as f:
        obj = yaml.load(f, Loader=yaml.FullLoader)

    return obj or None


def sm_client_api_is_authenticated(sm_api_client: RestClient) -> bool:
    """
    Indicates whether the API client is authenticated. The client should provide a ping_credentials method.
    :param sm_api_client:
    :return:
    """
    try:
        sm_api_client.ping_credentials()
    except APIError as e:
        if e.status_code == 401:
            return False

    return True


def create_sm_api_client_from_config(config: ConfigDict, sm_api_client_class: Type[RestClient]) -> RestClient:
    """
    Factory method that creates an instance of an API client. The client should provide
    :param config:
    :param sm_api_client_class:
    :return:
    """
    return sm_api_client_class.create(
        host=config['host'],
        https=config['https'],
        timeout=config['timeout'],
        verify=config['verify'],
        username=config['username'],
        password=config['password']
    )


class PubSubFacade:

    """ Is used to instantiate the underlying container that interacts with the broker (AMQP1.0 via swim-qpid-proton)"""
    container_class: Type[PubSubContainer] = None

    """ Is used to interact with any subscription management api """
    sm_api_client_class: Type[RestClient] = None

    def __init__(self, container: PubSubContainer, sm_api_client: RestClient):
        """

        :param container:
        :param sm_api_client: a REST API client that interacts with a subscription management service
        """
        self.container = container
        self.sm_api_client = sm_api_client

        if not sm_client_api_is_authenticated(self.sm_api_client):
            raise ValueError("Invalid credentials")

    def run(self, threaded=False) -> None:
        """
        Runs the underlying container. The threaded mode is intended for the container in order to enable further usage
        of the underlying messaging_handler.
        :param threaded:
        """
        self.container.run(threaded=threaded)

    @classmethod
    def require_running(cls, f):
        """
        Decorator to be used in methods of classes that derive from PubSubFacade. It prevents them from running in case
        the underlying container has not started yet.
        :param f:
        :return:
        """
        @wraps(f)
        def decorator(*args, **kwargs):
            self = args[0]
            if not self.container.is_running():
                raise RuntimeError("Action cannot complete because container has not been started yet")
            return f(*args, **kwargs)
        return decorator

    @classmethod
    def create_from_config(cls, config_file: str):
        """
        Factory method to create the PubSubFacade
        :param config_file:
        :return: PubSubFacade
        """
        config = yaml_file_to_dict(config_file)

        container = cls.container_class.create_from_config(config['BROKER'])

        sm_api_client = create_sm_api_client_from_config(config['SUBSCRIPTION-MANAGER-API'],
                                                         sm_api_client_class=cls.sm_api_client_class)

        # configure logging
        if 'LOGGING' in config:
            logging.config.dictConfig(config['LOGGING'])

        return cls(container, sm_api_client)
