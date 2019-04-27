import rospy
import sys
from robot import Robot


if __name__ == '__main__':
    # robot_id body_id node_name
    
    rospy.init_node(sys.argv[1], anonymous=True)
    rospy.logfatal(sys.argv[1]+" - bt:"+ sys.argv[3] +" tag: "+sys.argv[2]+ " Online")
    robot = Robot(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    rospy.on_shutdown(robot.bluetooth_detach)
    rospy.spin()
