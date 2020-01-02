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

from collections import Callable
from dataclasses import dataclass

from geofencing_service_client.geofencing_service import GeofencingServiceClient
from geofencing_service_client.models import UASZonesFilter
from swim_proton.containers import ConsumerContainer

from pubsub_facades.base import PubSubFacade


@dataclass
class Subscription:
    id: str
    queue: str


class GeofencingSubscriber(PubSubFacade):
    container_class = ConsumerContainer
    sm_api_client_class = GeofencingServiceClient

    @PubSubFacade.require_running
    def subscribe(self, uas_zones_filter: UASZonesFilter, message_consumer: Callable) -> Subscription:
        """

        :param uas_zones_filter:
        :param message_consumer:
        :return:
        """
        reply = self.sm_api_client.post_subscription(uas_zones_filter=uas_zones_filter)

        self.container.consumer.attach_message_consumer(reply.publication_location, message_consumer)

        return Subscription(id=reply.subscription_id, queue=reply.publication_location)

    @PubSubFacade.require_running
    def pause(self, subscription: Subscription) -> None:
        """

        :param subscription:
        """
        update_data = {
            'active': False
        }
        self.sm_api_client.put_subscription(subscription.id, update_data)

    @PubSubFacade.require_running
    def resume(self, subscription: Subscription) -> None:
        """

        :param subscription:
        """
        update_data = {
            'active': True
        }
        self.sm_api_client.put_subscription(subscription.id, update_data)

    @PubSubFacade.require_running
    def unsubscribe(self, subscription: Subscription) -> None:
        """

        :param subscription:
        """
        self.sm_api_client.delete_subscription_by_id(subscription.id)

        self.container.consumer.detach_message_consumer(subscription.queue)
