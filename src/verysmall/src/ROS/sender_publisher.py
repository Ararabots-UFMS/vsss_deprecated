from typing import List
import numpy as np
import rospy
from verysmall.msg import message_server_topic


class SenderPublisher:
    def __init__(self, owner_id: str = None):
        self.TAG = "ROBOT SENDER PUBLISHER"
        suffix = '' if owner_id is None else '_' + owner_id
        self.publisher = rospy.Publisher('message_server_topic' + suffix,
                                         message_server_topic,
                                         queue_size=1)

    def publish(self, priority: int, socket_id: int, msg: List):
        try:
            self.publisher.publish(priority, socket_id, msg)
        except rospy.ROSException as e:
            rospy.logfatal(self.TAG + " " + str(socket_id) + ": UNABLE TO PUBLISH MESSAGE: "
                           + repr(msg) + " " + repr(e))
