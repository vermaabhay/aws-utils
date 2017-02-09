1 - asg-sns-notification-sqs-consumer.py

Prerequisite
i - Private key to login to server. 

Directory Structure -
i - aws-utils/script-logs - To store all logs.

How To Set Life Cycle Hook On An AutoScaling Group

aws autoscaling put-lifecycle-hook --lifecycle-hook-name
EC2_INSTANCE_TERMINATE --heartbeat-timeout 7200 --auto-scaling-group-name
<Your-ASG-Name> --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING
--notification-target-arn arn:aws:sns:ap-southeast-1:470661122947:<Your-SNS-Topic-Name>
--role-arn arn:aws:iam::470661122947:role/<Your-SQS-Queue-Name>

Example -

aws autoscaling put-lifecycle-hook --lifecycle-hook-name
EC2_INSTANCE_TERMINATE --heartbeat-timeout 7200 --auto-scaling-group-name
<Your-ASG-Name> --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING
--notification-target-arn arn:aws:sns:ap-southeast-1:470661122947:ASG-EVENTS
--role-arn arn:aws:iam::470661122947:role/ASG-EVENTS

