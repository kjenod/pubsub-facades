## pubsub-facades v0.0.2

`pubsub-facades` is a collection of interfaces that provide publish/subscribe functions. Such an interface interacts
with a broker (i.e. RabbitMQ) and a subscription management service. The interaction with the broker is done via 
AMQPv1.0 using the [swim-qpid-proton](https://github.com/eurocontrol-swim/swim-qpid-proton). The interaction with the 
subscription management service is done via a REST API, so such a service has to provide one. 

#### Configuration
The configuration is loaded via a YAML file and should provide the following parameters:

```shell script

BROKER:
    host: "rabbitmq:5671",
    cert_file: "path/to/client_certificate.pem",  # to be used for TLS connections 
    cert_key: "path/to/client_key.pem"            # to be used for TLS connections
    sasl_use: "username"                          # to be used for SASL connections
    sasl_password: "password"                     # to be used for SASL connections  
    cert_db: "path/to/ca_certificate.pem",        # to be used for both TLS and SASL connections

SUBSCRIPTION-MANAGER-API:
  host: 'localhost:8080'
  https: true
  timeout: 30
  verify: "path/to/ca_certificate.pem"
  username: username
  password: password

```
#### Broker
The interaction with the broker is done via AMQPv1.0 with the [swim-qpid-proton](https://github.com/eurocontrol-swim/swim-qpid-proton)
library. `swim-qpid-proton` provides two kind of containers:
- `ProducerContainer` that can be used as a message publishing interface in the broker
- `ConsumerContainer` that can be used as a message consuming interface from the the broker 

#### Subscription Management 
A subscription management service (i.e. [SubscriptionManager](https://github.com/eurocontrol-swim/subscription-manager) and 
[GeofencingService](https://github.com/eurocontrol-swim/geofencing-service) which are currently implemented) is supposed 
to provide a REST API allowing the creation/update/deletion of subscriptions and/or topics.

#### Examples

##### SWIMPublisher
`SWIMPublisher` uses [SubscriptionManager](https://github.com/eurocontrol-swim/subscription-manager) as subscription 
management API. There it can create new topics and route new messages about them in the broker. Here is a typical example:

```python
import random

from pubsub_facades.swim_pubsub import SWIMPublisher

# a message producer can acceps optionally extra context data that can be used while producing the message
def message_producer1(context=None):
    return 'here is message ' + context

def message_producer2(context=None):
    return random.randint(0, 1000) 

publisher = SWIMPublisher.create_from_config('/path/to/config_file.yml')

# the publisher container is started in threaded mode in order to be able to add topics afterwards
publisher.run(threaded=True)

publisher.add_topic(topic_name='topic1', message_producer=message_producer1)
publisher.add_topic(topic_name='topic2', message_producer=message_producer2, interval_in_sec=5)

publisher.publish_topic(topic_name='topic1', context='message')
publisher.publish_topic(topic_name='topic2')
```  
> Both of the above topics can be invoked on demand and publish message in the broker. However, `topic2` will also be 
> scheduled to publish a message every 5 seconds.


##### SWIMSubscriber
`SWIMSubscriber` uses [SubscriptionManager](https://github.com/eurocontrol-swim/subscription-manager) as subscription 
management API. There it can create/update/delete subscriptions and register specific consumer callables that will be
used to process the incoming messages. Here is a typical example:

```python
import random

import proton
from pubsub_facades.swim_pubsub import SWIMSubscriber
from subscription_manager_client.models import Subscription

# a message_consumer is supposed to accept a proton.Message parameter where the incoming message will be passed
def message_consumer(message: proton.Message):
    return message.body

subscriber = SWIMSubscriber.create_from_config('/path/to/config_file.yml')

# the subscriber container is started in threaded mode in order to be able to add message consumers afterwards
subscriber.run(threaded=True)

# a new subscription is added in SubscriptionManager and the message_consumer will be associated with the generated 
# broker queue
subscription: Subscription = subscriber.subscribe(topic_name='topic1', message_consumer=message_consumer)

# the subscription is deactivated in the Subscription Manager and the corresponding queue will stop receiving messages
subscriber.pause(subscription)

# the subscription is reactivated in the Subscription Manager and the corresponding queue will start receiving messages
# again
subscriber.resume(subscription)

# the subscription is deleted in the Subscription Manager and the corresponding queue will be deleted in the broker
subscriber.unsubscribe(subscription)
```

##### GeofencingSubscriber
`GeofencingSubscriber` uses [GeofencingService](https://github.com/eurocontrol-swim/geofencing-service) as subscription 
management API. There it can create/update/delete subscriptions and register specific consumer callables that will be
used to process the incoming messages. Here is a typical example:

```python
import proton
from pubsub_facades.geofencing_pubsub import GeofencingSubscriber, Subscription

uas_zones_filter = {
    'airspaceVolume': {
        'polygon': [
            {'LAT': 50.901767, 'LON': 4.371125}, 
            {'LAT': 50.866953, 'LON': 4.22433}, 
            {'LAT': 50.788595, 'LON': 4.342881}, 
            {'LAT': 50.84643, 'LON': 4.535647}, 
            {'LAT': 50.901767, 'LON': 4.371125}
        ], 
        'lowerLimit': 0, 
        'upperLimit': 100000, 
        'lowerVerticalReference': 'WGS84', 
        'upperVerticalReference': 'WGS84'
    }, 
    'startDateTime': '2020-01-01T00:00:00+01:00', 
    'endDateTime': '2021-01-01T00:00:00+01:00', 
    'regions': [1], 
    'requestID': '1'
}


# a message_consumer is supposed to accept a proton.Message parameter where the incoming message will be passed
def message_consumer(message: proton.Message):
    return message.body

subscriber = GeofencingSubscriber.create_from_config('/path/to/config_file.yml')

# the subscriber container is started in threaded mode in order to be able to add message consumers afterwards
subscriber.run(threaded=True)

# a new subscription is added in GeofencingService based on the provided filter and the message_consumer will be 
# associated with the generated broker queue
subscription: Subscription = subscriber.subscribe(uas_zones_filter=uas_zones_filter, message_consumer=message_consumer)

# the subscription is deactivated in the GeofencingService and the corresponding queue will stop receiving messages
subscriber.pause(subscription.id)

# the subscription is reactivated in the GeofencingService and the corresponding queue will start receiving messages
# again
subscriber.resume(subscription.id)

# the subscription is deleted in the GeofencingService and the corresponding queue will be deleted in the broker
subscriber.unsubscribe(subscription.id)
```
