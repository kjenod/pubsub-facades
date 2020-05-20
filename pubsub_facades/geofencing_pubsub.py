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

from collections import Callable, namedtuple

from geofencing_service_client.geofencing_service import GeofencingServiceClient
from geofencing_service_client.models import UASZonesFilter
from swim_proton.containers import ConsumerContainer, PubSubContainer

from pubsub_facades.base import PubSubFacade


Subscription = namedtuple('Subscription', 'id queue')


class GeofencingSubscriber(PubSubFacade):
    """ Encapsulates the communication between the Geofencing Service https://github.com/eurocontrol-swim/geofencing-service
        and the broker (RabbitMQ) in a single interface by providing subscriber related functionalities.
    """

    """ Is used to instantiate the underlying consumer container that interacts with the broker (AMQP1.0 via swim-qpid-proton)"""
    container_class = ConsumerContainer

    """ Is used to interact with the subscription management API of 
        https://github.com/eurocontrol-swim/geofencing-servicer"""
    sm_api_client_class = GeofencingServiceClient

    def __init__(self, container: PubSubContainer, sm_api_client):
        super().__init__(container, sm_api_client)

        """Alias to avoid confusion with Subscription Manager API"""
        self.gs_client = self.sm_api_client

    @PubSubFacade.require_running
    def preload_queue_message_consumer(self, queue: str, message_consumer: Callable):
        """
        Registers the message consumer on an existing queue.

        To be used upon initialization of a subscriber service in case the subscriptions already exist in
        GeofencingService DB. That way the broker will stay up to date as well.

        :param queue:
        :param message_consumer:
        """
        self.container.consumer.attach_message_consumer(queue=queue, message_consumer=message_consumer)

    @PubSubFacade.require_running
    def subscribe(self, uas_zones_filter: UASZonesFilter, message_consumer: Callable) -> Subscription:
        """
        Creates a new subscription in Geofencing Service and registers the message consumer on a new AMQP1.0 receiver
        to be used upon message reception

        :param uas_zones_filter:
        :param message_consumer:
        :return:
        """
        reply = self.gs_client.post_subscription(uas_zones_filter=uas_zones_filter)

        self.container.consumer.attach_message_consumer(reply.publication_location, message_consumer)

        return Subscription(id=reply.subscription_id, queue=reply.publication_location)

    @PubSubFacade.require_running
    def pause(self, subscription_id: str) -> None:
        """
        Updates (deactivates) the subscription's state by setting it to False in Geofencing Service.
        Upon successful action the corresponding queue will be unbound from the relative topic and no message will be
        arriving.

        :param subscription_id:
        """
        update_data = {
            'active': False
        }
        self.gs_client.put_subscription(subscription_id, update_data)

    @PubSubFacade.require_running
    def resume(self, subscription_id: str) -> None:
        """
        Updates (reactivates) the subscription's state by setting it to True in Geofencing Service.
        Upon successful action the corresponding queue will be rebound to the relative topic and messages will start
        arriving again.

        :param subscription_id:
        """
        update_data = {
            'active': True
        }
        self.gs_client.put_subscription(subscription_id, update_data)

    @PubSubFacade.require_running
    def unsubscribe(self, subscription_id: str) -> None:
        """
        Deletes the subscription from the Geofencing Service, cleans up the corresponding queue in broker and removes
        the registered receiver.

        :param subscription_id:
        """
        uas_zone_subscription_reply = self.gs_client.get_subscription_by_id(subscription_id)

        self.container.consumer.detach_message_consumer(
            queue=uas_zone_subscription_reply.subscription.publication_location)

        self.gs_client.delete_subscription_by_id(subscription_id)

