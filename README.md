# automated-aws-rds-private-dns-management
This project contains a solution to automated update private DNS records, managed by Route53, after Amazon RDS cluster completes a failover event.


## Prerequistes
Before move forward, you should have resources below set up:
- An active AWS account
- An IAM user with enough permissions to run CloudFormation and create all resources
- An Amazon RDS cluster with a writer instance and at one reader instance

