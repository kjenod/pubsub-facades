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

from collections.abc import Callable
from typing import Optional, List, Any

from subscription_manager_client.subscription_manager import SubscriptionManagerClient
from subscription_manager_client.models import Topic, Subscription
from swim_proton.containers import ProducerContainer, ConsumerContainer
from swim_proton.messaging_handlers import Messenger

from pubsub_facades.base import PubSubFacade


class SWIMPublisher(PubSubFacade):
    """ Encapsulates the communication between the SubscriptionManager https://github.com/eurocontrol-swim/subscription-manager
        and the broker (RabbitMQ) in a single interface by providing publisher related functionalities.
    """

    """ Is used to instantiate the underlying producer container that interacts with the broker (AMQP1.0 via swim-qpid-proton)"""
    container_class = ProducerContainer

    """ Is used to interact with the subscription management API of 
        https://github.com/eurocontrol-swim/subscription-manager"""
    sm_api_client_class = SubscriptionManagerClient

    def _get_topic_by_name(self, topic_name: str) -> Optional[Topic]:
        """
        Retrieves a SubscriptionManager Topic object by its name
        :param topic_name:
        :return:
        """
        topics = self.sm_api_client.get_topics()

        try:
            result = [topic for topic in topics if topic.name == topic_name][0]
        except IndexError:
            result = None

        return result

    def _get_or_create_sm_topic(self, topic_name: str) -> Topic:
        """
        Retrieves a SubscriptionManager Topic or creates it if it does not exist.

        :param topic_name:
        :return:
        """
        result = self._get_topic_by_name(topic_name)

        if result is None:
            result = self.sm_api_client.post_topic(topic=Topic(name=topic_name))

        return result

    def pre_schedule_messenger(self, messenger: Messenger):
        """
        Registers the message producer on an existing topic.

        To be used upon initialization of a publisher service in case the topics already exist in SubscriptionManager DB
        That way the broker will stay up to date as well.

        :param messenger:
        """
        topic = self._get_topic_by_name(messenger.id)

        if topic is None:
            raise ValueError(f"Topic with name '{messenger.id}' not found")

        self.container.producer.schedule_messenger(messenger)

    def add_topic_messenger(self, messenger: Messenger) -> Topic:
        """
        Adds a new topic in SubscriptionManager and registers the message_producer in order to be used for message
        sending in the broker.

        :param messenger:
        :return:
        """
        topic = self._get_or_create_sm_topic(messenger.id)

        self.container.producer.schedule_messenger(messenger)

        return topic

    @PubSubFacade.require_running
    def publish_topic_messenger(self, messenger: Messenger, context: Optional[Any] = None):
        """
        Triggers the topic send on demand by providing optional context that will be used in producing the message to
        be send in the broker.

        :param messenger:
        :param context:
        """
        self.container.producer.trigger_messenger(messenger, context=context)


class SWIMSubscriber(PubSubFacade):
    """ Encapsulates the communication between the SubscriptionManager https://github.com/eurocontrol-swim/subscription-manager
        and the broker (RabbitMQ) in a single interface by providing subscriber related functionalities.
    """

    """ Is used to instantiate the underlying consumer container that interacts with the broker (AMQP1.0 via swim-qpid-proton)"""
    container_class = ConsumerContainer

    """ Is used to interact with the subscription management API of 
        https://github.com/eurocontrol-swim/subscription-manager"""
    sm_api_client_class = SubscriptionManagerClient

    @PubSubFacade.require_running
    def preload_queue_message_consumer(self, queue: str, message_consumer: Callable):
        """
        Registers the message consumer on an existing queue.

        To be used upon initialization of a subscriber service in case the subscriptions already exist in
        SubscriptionManager DB. That way the broker will stay up to date as well.

        :param queue:
        :param message_consumer:
        """
        self.container.consumer.attach_message_consumer(queue=queue, message_consumer=message_consumer)

    @PubSubFacade.require_running
    def subscribe(self, topic_name: str, message_consumer: Callable) -> Subscription:
        """
        Creates a new subscription in Subscription Manager and registers the message consumer on a new AMQP1.0 receiver
        to be used upon message reception

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
        Updates (deactivates) the subscription's state by setting it to False in Subscription Manager.
        Upon successful action the corresponding queue will be unbound from the relative topic and no message will be
        arriving.

        :param subscription:
        :return:
        """
        update_data = {
            'active': False
        }
        subscription = self.sm_api_client.put_subscription(subscription.id, update_data)

        return subscription

    @PubSubFacade.require_running
    def resume(self, subscription: Subscription) -> Subscription:
        """
        Updates (reactivates) the subscription's state by setting it to True in Subscription Manager.
        Upon successful action the corresponding queue will be rebound to the relative topic and messages will start
        arriving again.

        :param subscription:
        :return:
        """
        update_data = {
            'active': True
        }
        subscription = self.sm_api_client.put_subscription(subscription.id, update_data)

        return subscription

    @PubSubFacade.require_running
    def unsubscribe(self, subscription: Subscription) -> None:
        """
        Deletes the subscription from the Subscription Manager, cleans up the corresponding queue in broker and removes
        the registered receiver.

        :param subscription:
        """
        self.sm_api_client.delete_subscription_by_id(subscription.id)

        self.container.consumer.detach_message_consumer(subscription.queue)
