#!/usr/bin/env python
import sys
import uuid
sys.path.insert(0, '../..')
import os
import jinja2
from bin.build_scripts import manifest_generator
from lib.manifest import Manifest

account_id = 'xxxxxxxxxxxx'
lambda_arn = 'arn:aws:lambda:us-east-1:' + account_id + ':function:LandingZone'
mf_file = "../../../deployment/aws_landing_zone_configuration/manifest.yaml".format(dir)
function_path = os.path.normpath('../../../deployment/aws_landing_zone_configuration')

def generate_avm():

    region_list = ['us-east-1','us-west-2','us-west-1']

    print("====== Generating product templates using Jinja2 ======")
    manifest = Manifest(mf_file)

    for portfolio in manifest.portfolios:
        for product in portfolio.products:
            if os.path.isfile(os.path.join(function_path, product.skeleton_file)):
                j2loader = jinja2.FileSystemLoader(function_path)
                j2env = jinja2.Environment(loader=j2loader)
                j2template = j2env.get_template(product.skeleton_file)
                portfolio_index = manifest.portfolios.index(portfolio)
                product_index = manifest.portfolios[portfolio_index].products.index(product)
                product_name = manifest.portfolios[portfolio_index].products[product_index].name
                print("Generating the product template for {} from {}".format(product_name, os.path.join(function_path, product.skeleton_file)))
                if product.product_type == 'baseline':
                        j2result = j2template.render(manifest = manifest, portfolio_index=portfolio_index, product_index=product_index, lambda_arn= lambda_arn, uuid=uuid.uuid4(), regions=region_list)
                # elif product.product_type == 'optional':
                #     if os.path.isfile(os.path.join(function_path, product.skeleton_file)):
                #         template_url = 'https://s3.amazonaws.com/aws-landing-zone-configuration-' + account_id + '-us-east-1/_aws_landing_zone_templates_staging/aws-landing-zone-aws-active-directory.template'
                #         j2result = j2template.render(manifest = manifest, portfolio_index=portfolio_index, product_index=product_index, lambda_arn= lambda_arn, uuid=uuid.uuid4(),
                #                                     template_url=template_url)
                output_template = os.path.join(function_path, product.skeleton_file[0:-3])
                print("Writing the generated product template to {}".format(output_template))
                with open(output_template, "w") as fh:
                    fh.write(j2result)


if __name__ == '__main__':
    #manifest_generator.generate_manifest()
    generate_avm()
