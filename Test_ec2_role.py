import boto3

ec2 = boto3.client('ec2', region_name='us-east-1')

def get_ec2_role(instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instance_profile_arn = response['Reservations'][0]['Instances'][0]['IamInstanceProfile']['Arn']
    
    # Extract instance profile name
    profile_name = instance_profile_arn.split('/')[-1]
    
    # Get the role name
    iam = boto3.client('iam')
    response = iam.get_instance_profile(InstanceProfileName=profile_name)
    role_name = response['InstanceProfile']['Roles'][0]['RoleName']
    return role_name

print(get_ec2_role('i-1234567890abcdef0'))
