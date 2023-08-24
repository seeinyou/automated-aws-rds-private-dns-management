import boto3
import json
import re
import os

aws_region = os.environ['AWS_REGION']

rds_client = boto3.client('rds')
route53 = boto3.client('route53')

hosted_zone_configs = [{'cluster': 'apsoutheast1-aurora-cluster-1', 'hosted-zone-id': 'Z03525084XG1NZMN0005', 'record-id': 'aurora-read1.myrds.com'}]

## Get RDS instances
def list_db_instances(cluster_id, removed_db_id=''):
    db_list = []
    
    full_db_list = rds_client.describe_db_instances(Filters=[
        {
            'Name': 'db-cluster-id',
            'Values': [
                cluster_id,
            ]
        }
    ], MaxRecords=20)
    # print('#DB:', full_db_list)
    
    if 'DBInstances' in full_db_list:
        
        for db_instance in full_db_list['DBInstances']:
            print('#INST:', db_instance)
            
            if not removed_db_id or db_instance['DBInstanceIdentifier'] != removed_db_id:
                db_list.append({'key': db_instance['DBInstanceIdentifier'], 'endpoint':db_instance['Endpoint']['Address']})

                print('#VPC:', db_instance['DBSubnetGroup']['VpcId'])
    
    return db_list


## Get Hosted Zone info from configurations by RDS cluster name
def get_dns_hosted_zone_id(cluster_name):
    # Get hosted zone info from configurations
    for zones in hosted_zone_configs:
        if cluster_name == zones['cluster']:
            return zones

# UPSERT Route53 hosted zone DNS records
def dns_upsert (hosted_zone_id, record_name, endpoint):
    # Hosted zone ID 
    print('#HOSTED ID:', hosted_zone_id)

    # Update the DNS record
    response = route53.change_resource_record_sets(
    HostedZoneId = hosted_zone_id,
    ChangeBatch = {
      'Changes': [
        {
          'Action': 'UPSERT',
          'ResourceRecordSet': {
            'Name': record_name,
            'Type': 'CNAME',
            'TTL': 30,
            'ResourceRecords': [
              {
                'Value': endpoint
              }
            ]
          }
        }
      ]
    }
    )
    
    return response

'''
 Lambda Handler

 @param event: EventBridge Amazon RDS event

 @return HTTP JSON response
'''
def lambda_handler(event, context):
    # Get Hosted Zone from configurations
    zone_info = get_dns_hosted_zone_id(event['detail']['SourceIdentifier'])
    print('#HOST INFO:', zone_info)
    
    print("#WRITER:", event['detail']['Message'])
    
    # Extract the new RDS cluster writer name from event
    # example: text = "Completed failover to DB instance: apsoutheast1-aurora-cluster-test-1"
    match = re.search(r'DB instance: (\S+)', event['detail']['Message'])

    if match:
        writer_id = match.group(1)
        print(match.group(1))
    
    # Get a list of RDS DB instances by RDS cluster name
    db_instances = list_db_instances(event['resources'][0], writer_id)
    print('#DB:', db_instances)
    
    if db_instances:

        for instance in db_instances:
            # Update Route 53 DNS
            dns_response = dns_upsert(zone_info['hosted-zone-id'], zone_info['record-id'], instance['endpoint'])
            break

        print('#CHANGE DNS:', dns_response)
        response_body = dns_response
    else:
        response_body = json.dumps('No action!')
            
    
    # TODO implement
    return {
        'statusCode': 200,
        'body': response_body
    }
