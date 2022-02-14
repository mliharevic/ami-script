#!/usr/bin/env python3
#
# Gathers AMI information and associated instances
#

import os
import json
import jmespath
import boto3
from botocore.exceptions import ClientError

class AmiAssociation():

#   Set Up Variables
    def __init__(self):
        self.access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        self.secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        self.region = os.environ.get('AWS_DEFAULT_REGION')
        self.account = os.environ.get('AWS_ACCOUNT_ID')
        self.session = os.environ.get('AWS_SESSION_TOKEN')
        self.ec2_conn = boto3.client('ec2', region_name=f'{self.region}',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            aws_session_token=self.session
        )

#   Generates List of AMI's in use
    def getAllInstanceAmis(self):
        ami_ids = []
        token = None
        try:
            paginator = self.ec2_conn.get_paginator('describe_instances')
            for page in paginator.paginate(PaginationConfig={'PageSize': 50, 'StartingToken':token}):
                ami_output = ','.join(jmespath.search(f"Reservations[].Instances[].ImageId", page))
                output_ids = list(map(str, ami_output.split(',')))
                for ami in output_ids:
                    if ami not in ami_ids:
                        ami_ids.append(ami)
                next_token = page.get('NextToken', None)
                if next_token:
                    token = page['NextToken']
            return ami_ids
        except ClientError as e:
            raise Exception("boto3 ClientError in getAllInstanceAmis: " + e.__str__())
        except Exception as e:
            raise Exception("Unexpected error in getAllInstanceAmis: " + e.__str__())
        
#   Generates Dictionary of AMI info
    def createDict(self, images):
        image_dict = {}
        for image in images:
            image_info = self.getAmiInfo(image)
            image_dict[f"{image}"] = image_info
        return image_dict

#   Gets List of instance id's associated with AMI
    def getAssociatedInstances(self, ami):
        instance_ids = []
        try:
            paginator = self.ec2_conn.get_paginator('describe_instances')
            token = None
            for page in paginator.paginate(Filters=[{'Name': 'image-id','Values': [f'{ami}',]},], PaginationConfig={'PageSize': 50, 'StartingToken':token}):
                instance_output = ','.join(jmespath.search(f"Reservations[].Instances[].InstanceId", page))
                if "," in instance_output:
                    instances = list(map(str, instance_output.split(',')))
                    instance_ids.extend(instances)
                elif instance_output:
                    instance_ids.append(instance_output)
                next_token = page.get('NextToken', None)
                if next_token:
                    token = page['NextToken']
            return instance_ids
        except ClientError as e:
            raise Exception("boto3 ClientError in getAssociatedInstances: " + e.__str__())
        except Exception as e:
            raise Exception("Unexpected error in getAssociatedInstances: " + e.__str__())

#   Convert Dictionary to JSON
    def dictToJson(self, ami_dict):
        try:
            result = json.dumps(ami_dict, indent = 4)
            return result
        except:
            print("Unable to serialize the ami dictionary")

#   Gets AMI info
    def getAmiInfo(self, ami):
        ami_dict = {}
        response = self.ec2_conn.describe_images(
        ImageIds=[
            f'{ami}',
        ],
        )
        ami_desc=''.join(jmespath.search("Images[].Description", response)) or "null"
        ami_dict["ImageDescription"]=ami_desc
        ami_name=''.join(jmespath.search("Images[].Name", response)) or "null"
        ami_dict["ImageName"]=ami_name
        ami_loc=''.join(jmespath.search("Images[].ImageLocation", response)) or "null"
        ami_dict["ImageLocation"]=ami_loc
        ami_own=''.join(jmespath.search("Images[].OwnerId", response)) or "null"
        ami_dict["OwnerId"]=ami_own
        instance_ids = self.getAssociatedInstances(ami)
        ami_dict["InstanceIds"]=instance_ids
        return ami_dict

#   Gathers all information and outputs as JSON
    def getAmis(self):
        images = self.getAllInstanceAmis()
        image_dict = self.createDict(images)
        json = self.dictToJson(image_dict)
        print(json)

if __name__ == '__main__':
    obj = AmiAssociation()
    obj.getAmis()
