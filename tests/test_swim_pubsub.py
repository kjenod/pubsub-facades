"""
Copyright 2020 EUROCONTROL
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

from unittest.mock import Mock

import pytest

from pubsub_facades.swim_pubsub import SWIMPublisher, SWIMSubscriber


def test_swimpublisher__publish_topic_requires_running():
    container = Mock()
    container.is_running = Mock(return_value=False)
    sm_api_client = Mock()
    swim_publisher = SWIMPublisher(container, sm_api_client)

    with pytest.raises(RuntimeError) as e:
        swim_publisher.publish_topic('topic')
    assert "Action cannot complete because container has not been started yet" == str(e.value)


def test_swimsubscriber__subscribe_requires_running():
    container = Mock()
    container.is_running = Mock(return_value=False)
    sm_api_client = Mock()
    swim_subscriber = SWIMSubscriber(container, sm_api_client)

    with pytest.raises(RuntimeError) as e:
        swim_subscriber.subscribe(topic_name='topic', message_consumer=Mock())
    assert "Action cannot complete because container has not been started yet" == str(e.value)


def test_swimsubscriber__pause_requires_running():
    container = Mock()
    container.is_running = Mock(return_value=False)
    sm_api_client = Mock()
    swim_subscriber = SWIMSubscriber(container, sm_api_client)

    with pytest.raises(RuntimeError) as e:
        swim_subscriber.pause(Mock())
    assert "Action cannot complete because container has not been started yet" == str(e.value)


def test_swimsubscriber__resume_requires_running():
    container = Mock()
    container.is_running = Mock(return_value=False)
    sm_api_client = Mock()
    swim_subscriber = SWIMSubscriber(container, sm_api_client)

    with pytest.raises(RuntimeError) as e:
        swim_subscriber.resume(Mock())
    assert "Action cannot complete because container has not been started yet" == str(e.value)


def test_swimsubscriber__unsubscribe_requires_running():
    container = Mock()
    container.is_running = Mock(return_value=False)
    sm_api_client = Mock()
    swim_subscriber = SWIMSubscriber(container, sm_api_client)

    with pytest.raises(RuntimeError) as e:
        swim_subscriber.unsubscribe(Mock())
    assert "Action cannot complete because container has not been started yet" == str(e.value)
