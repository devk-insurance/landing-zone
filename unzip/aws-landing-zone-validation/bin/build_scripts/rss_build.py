import os
import sys
import jinja2
from markdown_to_json.vendor import CommonMark
from markdown_to_json.markdown_to_json import Renderer, CMarkASTNester
import json
from dateutil.parser import parse
import datetime


def make_dir(directory):
    # if exist skip else create dir
    try:
        os.stat(directory)
        print("\n Directory {} already exist... skipping".format(directory))
    except:
        print("\n Directory {} not found, creating now...".format(directory))
        os.makedirs(directory)


# Format the date e.g. 2017-06-22 to Thu, 22 Jun 2017 00:00:00
def datetimeformat(str_date, format='%a, %d %b %Y %H:%M:%S'):
    return parse(str_date).strftime(format)


# Returns the Unix Epoch time for the given date
# Context: Its used as the guid in RSS xml file,
# in order to preserve the guid from changing everytime the Rss xml file is generated
# it uses the epoch timestamp as the guid
def epoch(str_date):
    return str(parse(str_date).timestamp())


def process_j2_template(j2env, changelog, j2_file, output_file):
    j2template = j2env.get_template(j2_file)
    j2result = j2template.render(changelog=changelog,
                                 datetimeformat=datetimeformat,
                                 epoch=epoch,
                                 now=str(datetime.datetime.now()))
    file = open(output_file, 'w', encoding="utf-8")
    file.write(j2result)
    file.close()


def main(argv):
    rss_file_name = argv[0]
    release_notes_file_name = argv[1]

    if 'bin' not in os.getcwd():
        os.chdir('./source/bin/build_scripts')

    output_path = '../../../deployment/regional-s3-assets/'
    make_dir(output_path)

    print('Loading CHANGELOG.md into memory...')
    with open('../../../deployment/CHANGELOG.md', 'r', encoding="utf-8") as content_file:
        changelog = content_file.read()

    print('Parsing CHANGELOG.md...')
    ast = CommonMark.DocParser().parse(changelog)
    ast_dict = CMarkASTNester().nest(ast)

    print('Converting CHANGELOG.md into JSON...')
    # JSON representation of the CHANGELOG.md
    _json = Renderer().stringify_dict(ast_dict)

    print('Saving CHANGELOG.md JSON into file...')
    file = open('CHANGELOG.json', 'w', encoding="utf-8")
    file.write(json.dumps(_json))
    file.close()

    # Python dictionary representation of the CHANGELOG.md
    print('Converting CHANGELOG JSON into Python dict...')
    changelog = next(iter(_json.values()))

    j2loader = jinja2.FileSystemLoader('./')
    j2env = jinja2.Environment(loader=j2loader)

    print('Processing RSS xml Jinja template...')
    process_j2_template(j2env, changelog, rss_file_name + ".j2",
                        output_path + rss_file_name)
    print('Processing Release notes html Jinja template...')
    process_j2_template(j2env, changelog, release_notes_file_name + ".j2",
                        output_path + release_notes_file_name)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        print('No arguments provided. ')
        print('rss_build.py rss.xml release_notes.html')










