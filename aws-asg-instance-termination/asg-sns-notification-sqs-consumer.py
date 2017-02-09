#!/usr/bin/python

import json
import sys
from boto import ec2
from fabric.api import *
from fabric.state import *
from fabric.state import output
import time
import datetime
import subprocess
import boto3
import logging

date = (datetime.datetime.now().strftime("%Y-%m-%d"))

logfile = "aws-utils/script-logs/aws-asg-termination-notification-%s.log" % (datetime.datetime.now().strftime("%Y-%m-%d-%H-%M"))

logging.basicConfig(filename=logfile, level=logging.INFO, format='%(asctime)s  [%(levelname)s]  %(message)s')

#logging to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
#format for console
formatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)



def infra_details():

    conn = ec2.connect_to_region('ap-southeast-1')

    file = open("aws-utils/aws-asg-instance-termination/prod_infra_details.txt", 'w')
    file.close()

    infraDict = {}

    while True:
        try:

            all_live_prod_instances = conn.get_all_instances(filters={"vpc-id" : "<Your-VPC-ID>"})

            for i in all_live_prod_instances:
                for m in i.instances:
                    file = open("aws-utils/aws-asg-instance-termination/prod_infra_details.txt", 'a')
                    file.write(m.id+"|"+m.private_ip_address+"|"+m.state+"\n")
                    file.close()
                    infraDict[m.id] = m.private_ip_address

            logging.info("Infra List Loaded\n")

            return infraDict
            break

        except Exception as err:

            logging.error("Cannot Load Infra List. Next Retry After 2 Minutes. Error : {0}\n".format(err))
            time.sleep(2000)
            pass



def disable_monitoring(private_ip):


        env.key_filename='aws-utils/properties/aws/key'
        env.user = 'ec2-user'

        env.host_string=private_ip
        env.warn_only = True
        env.disable_known_hosts = True
        #env.abort_on_prompts = True
        env.skip_password_prompts=True

        try:
            output=run("") #Execute custom command before terminating
            logging.info("Monitoring disabled for instance : {0}\n".format(private_ip))

            time.sleep(1)

        except Exception as err:
                logging.error("Unable to disable the monitoring for instance : {0}. Error : {1}\n".format(private_ip,err))

        hostname = run("sudo hostname -f")
        return hostname


#remove_from_icinga - If you use icinga as infra monitoring tool.

def remove_from_icinga(instance_id):

    private_ip = infraDict[instance_id]
    hostname = disable_monitoring(private_ip)
    logging.info("Instance Id {0} : Private Ip {1} : Hostname {2}\n".format(instance_id,private_ip,hostname))

    icinga_downtime = "" #Put downtime scheduler here.
    icinga_deregister = "" #Put deregister command here.

    output,error  = subprocess.Popen(icinga_downtime, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    logging.info("Icinga Downtime - Output : {0} || Error : {1}\n".format(output,error))

    output,error  = subprocess.Popen(icinga_deregister, universal_newlines=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    logging.info("Icinga Deregister - Output : {0} || Error : {1}\n".format(output,error))


infraDict = infra_details()


sqs = boto3.resource('sqs')

#QueueName='ASG-EVENTS'

queue = sqs.get_queue_by_name(QueueName='ASG-EVENTS')

while True:

    time.sleep(1)

    for message in queue.receive_messages():
        msg = message.body
        msg_json = json.loads(str(msg))
        logging.info("Message Consumed From SQS : {0}\n".format(msg_json))

        try :
            event = json.loads(msg_json['Message'])['Event']
            logging.info("Notification Received From SQS : {0}\n".format(event))
            message.delete()
            continue
        except KeyError:
            print ""

        state = json.loads(msg_json['Message'])['LifecycleTransition']
        instance_id = json.loads(msg_json['Message'])['EC2InstanceId']
        asg = json.loads(msg_json['Message'])['AutoScalingGroupName']

        if state == "autoscaling:EC2_INSTANCE_TERMINATING":
            logging.info("Instance Id {0} OF ASG {1} Is Marked For Termination\n".format(instance_id,asg))
        else:
            logging.info("Not A Termination Request\n")

        message.delete()
        time.sleep(1)

        try:

            if instance_id in infraDict:

                remove_from_icinga(instance_id)

            else:
                logging.info("Instance Id Not Found In Infra Dictionary. Reloading Infra List\n")
                infraDict = infra_details()
                logging.info("Infra List Reloaded Successfully\n")

                remove_from_icinga(instance_id)

        except Exception as err:
            logging.error("Error/Failure : {0}\n".format(err))
