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
from typing import Optional, List, Any

from subscription_manager_client.subscription_manager import SubscriptionManagerClient
from subscription_manager_client.models import Topic, Subscription
from swim_proton.containers import ProducerContainer, ConsumerContainer

from pubsub_facades.base import PubSubFacade


class SWIMPublisher(PubSubFacade):
    container_class = ProducerContainer
    sm_api_client_class = SubscriptionManagerClient

    def _get_or_create_sm_topic(self, topic_name: str) -> Topic:
        topics = self.sm_api_client.get_topics()

        try:
            result = [topic for topic in topics if topic.name == topic_name][0]
        except IndexError:
            result = self.sm_api_client.post_topic(topic=Topic(name=topic_name))

        return result

    def add_topic(self, topic_name: str, message_producer: Callable, interval_in_sec: Optional[int] = None) -> Topic:
        """

        :param topic_name:
        :param message_producer:
        :param interval_in_sec:
        :return:
        """
        topic = self._get_or_create_sm_topic(topic_name)

        self.container.producer.add_message_producer(id=topic_name,
                                                     message_producer=message_producer,
                                                     interval_in_sec=interval_in_sec)
        return topic

    @PubSubFacade.require_running
    def publish_topic(self, topic_name: str, context: Optional[Any] = None):
        """

        :param context:
        :param topic_name:
        """
        self.container.producer.trigger_message_producer(message_producer_id=topic_name, context=context)


class SWIMSubscriber(PubSubFacade):
    container_class = ConsumerContainer
    sm_api_client_class = SubscriptionManagerClient

    @PubSubFacade.require_running
    def subscribe(self, topic_name: str, message_consumer: Callable) -> Subscription:
        """

        :param topic_name:
        :param message_consumer:
        :return:
        """
        topics: List[Topic] = self.sm_api_client.get_topics()

        try:
            topic = [topic for topic in topics if topic.name == topic_name][0]
        except AttributeError:
            raise ValueError(f"No topic found with name {topic_name}")

        subscription = self.sm_api_client.post_subscription(subscription=Subscription(topic_id=topic.id))

        self.container.consumer.attach_message_consumer(subscription.queue, message_consumer)

        return subscription

    @PubSubFacade.require_running
    def pause(self, subscription: Subscription) -> Subscription:
        """

        :param subscription:
        :return:
        """
        subscription.active = False
        self.sm_api_client.put_subscription(subscription.id, subscription)

        return subscription

    @PubSubFacade.require_running
    def resume(self, subscription: Subscription) -> Subscription:
        """

        :param subscription:
        :return:
        """
        subscription.active = True
        self.sm_api_client.put_subscription(subscription.id, subscription)

        return subscription

    @PubSubFacade.require_running
    def unsubscribe(self, subscription: Subscription) -> None:
        """

        :param subscription:
        """
        self.sm_api_client.delete_subscription_by_id(subscription.id)

        self.container.consumer.detach_message_consumer(subscription.queue)
