###################################################################################################################### 
#  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           #
#                                                                                                                    # 
#  Licensed under the Apache License Version 2.0 (the "License"). You may not use this file except in compliance     # 
#  with the License. A copy of the License is located at                                                             # 
#                                                                                                                    # 
#      http://www.apache.org/licenses/                                                                               # 
#                                                                                                                    # 
#  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES # 
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    # 
#  and limitations under the License.                                                                                # 
######################################################################################################################

# !/bin/python

import boto3
import inspect
from lib.decorator import try_except_retry

class ServiceCatalog(object):
    sc_client = None
    logger = None

    def __init__(self, logger, client=None):
        self.logger = logger
        if client == None:
            self.sc_client = boto3.client('servicecatalog')
        else:
            self.sc_client = client

    def list_portfolios(self):
        """
        servicecatalog.list_portfolios wrapper function
        """
        try:
            response = self.sc_client.list_portfolios()
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_portfolio(self, name, desc, provider='AWS Solutions'):
        try:
            response = self.sc_client.create_portfolio(
                DisplayName=name,
                Description=desc,
                ProviderName=provider,
                Tags=[
                    {
                        'Key': 'AWS Solutions',
                        'Value': 'Landing Zone Solution'
                    },
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_portfolio(self, portfolio_id, name, desc, provider='AWS Solutions'):
        try:
            response = self.sc_client.update_portfolio(
                Id=portfolio_id,
                DisplayName=name,
                Description=desc,
                ProviderName=provider
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_product(self, name, owner, desc, artifact_params, product_type='CLOUD_FORMATION_TEMPLATE'):
        try:
            response = self.sc_client.create_product(
                Name=name,
                Owner=owner,
                Description=desc,
                ProvisioningArtifactParameters=artifact_params,
                ProductType=product_type,
                Tags=[
                    {
                        'Key': 'AWS Solutions',
                        'Value': 'Landing Zone Solution'
                    },
                ]
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def search_products_as_admin(self, id):
        try:
            response = self.sc_client.search_products_as_admin(
                PortfolioId=id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_product(self, product_id, name, owner, desc):
        try:
            response = self.sc_client.update_product(
                Id=product_id,
                Name=name,
                Owner=owner,
                Description=desc
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_principals_for_portfolio(self, portfolio_id):
        try:
            response = self.sc_client.list_principals_for_portfolio(
                PortfolioId=portfolio_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_portfolios_for_product(self, product_id):
        try:
            response = self.sc_client.list_portfolios_for_product(
                ProductId=product_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_constraints_for_portfolio(self, product_id, portfolio_id):
        try:
            response = self.sc_client.list_constraints_for_portfolio(
                ProductId=product_id,
                PortfolioId=portfolio_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def associate_product_with_portfolio(self, product_id, portfolio_id):
        try:
            self.sc_client.associate_product_with_portfolio(
                ProductId=product_id,
                PortfolioId=portfolio_id
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def associate_principal_with_portfolio(self, portfolio_id, arn, type='IAM'):
        try:
            self.sc_client.associate_principal_with_portfolio(
                PortfolioId=portfolio_id,
                PrincipalARN=arn,
                PrincipalType=type
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_portfolio(self, portfolio_id):
        try:
            response = self.sc_client.delete_portfolio(
                Id=portfolio_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_product(self, product_id):
        try:
            response = self.sc_client.delete_product(
                Id=product_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def disassociate_principal_from_portfolio(self, portfolio_id, arn):
        try:
            self.sc_client.disassociate_principal_from_portfolio(
                PortfolioId=portfolio_id,
                PrincipalARN=arn
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def disassociate_product_from_portfolio(self, product_id, portfolio_id):
        try:
            self.sc_client.disassociate_product_from_portfolio(
                PortfolioId=portfolio_id,
                ProductId=product_id,
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_constraint(self, constraint_id):
        try:
            response = self.sc_client.describe_constraint(
                Id=constraint_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_constraint(self, product_id, portfolio_id, parameters, description, type='LAUNCH'):
        try:
            response = self.sc_client.create_constraint(
                PortfolioId=portfolio_id,
                ProductId=product_id,
                Parameters=parameters,
                Type=type,
                Description=description
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_constraint(self, constraint_id):
        try:
            self.sc_client.delete_constraint(
                Id=constraint_id
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def list_provisioning_artifacts(self, product_id,):
        try:
            response = self.sc_client.list_provisioning_artifacts(
                ProductId=product_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def describe_provisioning_artifact(self, product_id, artifact_id):
        try:
            response = self.sc_client.describe_provisioning_artifact(
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def create_provisioning_artifact(self, product_id, artifact_params):
        try:
            response = self.sc_client.create_provisioning_artifact(
                ProductId=product_id,
                Parameters=artifact_params
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def update_provisioning_artifact(self, product_id, artifact_id, boolean_value):
        try:
            response = self.sc_client.update_provisioning_artifact(
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id,
                Active=boolean_value
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def delete_provisioning_artifact(self, product_id, artifact_id):
        try:
            self.sc_client.delete_provisioning_artifact(
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id
            )
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def provision_product(self, product_id, artifact_id, product_name, params):
        try:
            response = self.sc_client.provision_product(
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id,
                ProvisionedProductName=product_name,
                ProvisioningParameters=params
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def update_provisioned_product(self, product_id, artifact_id, provisioned_product_id, params):
        try:
            response = self.sc_client.update_provisioned_product(
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id,
                ProvisionedProductId=provisioned_product_id,
                ProvisioningParameters=params
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    def terminate_provisioned_product(self, provisioned_product_id):
        try:
            response = self.sc_client.terminate_provisioned_product(
                ProvisionedProductId=provisioned_product_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_record(self, record_id):
        try:
            response = self.sc_client.describe_record(
                Id=record_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def describe_provisioned_product(self, pp_id):
        '''
        :param pp_id:
        :return:
        {
            'ProvisionedProductDetail': {
                'Name': 'string',
                'Arn': 'string',
                'Type': 'string',
                'Id': 'string',
                'Status': 'AVAILABLE'|'UNDER_CHANGE'|'TAINTED'|'ERROR'|'PLAN_IN_PROGRESS',
                'StatusMessage': 'string',
                'CreatedTime': datetime(2015, 1, 1),
                'IdempotencyToken': 'string',
                'LastRecordId': 'string',
                'ProductId': 'string',
                'ProvisioningArtifactId': 'string'
            },
            'CloudWatchDashboards': [
                {
                    'Name': 'string'
                },
            ]
        }
        '''
        try:
            response = self.sc_client.describe_provisioned_product(
                Id=pp_id
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise

    @try_except_retry()
    def search_provisioned_products(self, product_id, next_token='0'):
        try:
            search_query = "productId:{}".format(product_id)
            response = self.sc_client.search_provisioned_products(
                AccessLevelFilter={
                    'Key': 'Account',
                    'Value': 'self'
                },
                Filters={
                    'SearchQuery': [
                        search_query
                    ]
                },
                PageToken=next_token,
                SortBy="createdTime"
            )
            return response
        except Exception as e:
            message = {'FILE': __file__.split('/')[-1], 'CLASS': self.__class__.__name__,
                       'METHOD': inspect.stack()[0][3], 'EXCEPTION': str(e)}
            self.logger.exception(message)
            raise
            
