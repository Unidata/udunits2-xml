# Copyright (c) 2019 University Corporation for Atmospheric Research/Unidata
# Distributed under the terms of the BSD 3-Clause License.
import getpass
import io
import json
import logging
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime

import requests

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
root.addHandler(handler)

# nexus urls
nexus_url = 'https://artifacts.unidata.ucar.edu/'
nexus_asset_search_and_download_url = urllib.parse.urljoin(nexus_url, '/service/rest/v1/search/assets/download/')
nexus_components_url = urllib.parse.urljoin(nexus_url, '/service/rest/v1/components/')
nexus_search_url = urllib.parse.urljoin(nexus_url, '/service/rest/v1/search/')

# file names (on-disk and in nexus)
copyright_file_name = 'UDUNITS-2_COPYRIGHT'
combined_xml_file_name = 'udunits2_combined.xml'


def get_udunits2_copyright_text(version):
    r"""Obtain copyright text to be used in the combined xml file.

    Parameters
    ----------
    version : string
       version of udunits as a dot separated set of integers

    """

    combined_copyright = ('Copyright {} University Corporation for Atmospheric Research\n\n'
                          'This file is derived from the UDUNITS-2 package.  See the UDUNITS-2_COPYRIGHT\n'
                          'https://docs.unidata.ucar.edu/thredds/udunits2/{}/UDUNITS-2_COPYRIGHT for copying and\n'
                          'redistribution conditions.\n').format(datetime.today().year, version)

    return combined_copyright


def fetch_udunits2_copyright_gh(version, save_filename):
    r"""Fetch the copyright file for UDUNITS-2 from github for a specific version.

    Parameters
    ----------
    version : string
       version of udunits as a dot separated set of integers
    save_filename : string
        filename to use for saving the UDUNITS-2 COPYRIGHT file to disk

    """

    cr_url = 'https://raw.githubusercontent.com/Unidata/UDUNITS-2/{}/COPYRIGHT'.format(version)
    response = requests.get(cr_url)
    response.raise_for_status()
    with open(save_filename, 'wb') as f:
        f.write(response.content)


def get_creds():
    r"""Obtain the necessary credentials for publishing to nexus.

    This function will check for credentials stored in environmental variables
    (NEXUS_USERNAME, NEXUS_PASSWORD). If both are not set, will prompt the user
    for a username and password

    Returns
    -------
    namedtuple
        credentials stored in a named tuple

    >>> creds = get_creds()
    >>> print(creds.name)
    username
    >>> print(creds.pw)
    password

    """
    NexusCred = namedtuple('nexus_credentials', 'name pw')

    nexus_name = os.environ.get('NEXUS_USERNAME')
    nexus_pw = os.environ.get('NEXUS_PASSWORD')

    if nexus_name and nexus_pw:
        logging.info('Found credentials.')
        nexus_cred = NexusCred(name=nexus_name, pw=nexus_pw)
    else:
        logging.info('Prompt user for credentials.')
        nexus_name = input("username:")
        nexus_pw = getpass.getpass()
        nexus_cred = NexusCred(name=nexus_name, pw=nexus_pw)

    del nexus_name, nexus_pw

    return nexus_cred


def get_latest_github_release_version():
    r"""Obtain the latest released version string of udunits-2 from github.

    Returns
    -------
    string
        latest release version string of udunits-2 as a dot separated set of
        integers with starting with v

    >>> print(get_latest_github_release_version())
    v2.2.27.6

    """
    response = requests.get('https://github.com/Unidata/UDUNITS-2/releases.atom')
    release_info_xml = response.content
    release_info = ET.fromstring(release_info_xml)
    entry_e = '{http://www.w3.org/2005/Atom}entry'
    title_e = '{http://www.w3.org/2005/Atom}title'
    udunits2_version = release_info.find(entry_e).find(title_e).text
    logging.info('Most recent UDUNITS-2 release version from github: {}'.format(udunits2_version))

    return udunits2_version


def publish_to_nexus(version, combined_xml_filename, copyright_filename):
    r"""Publish combined udunits xml to nexus.

    Parameters
    ----------
    version : string
       version of udunits as a dot separated set of integers
    combined_xml_filename : string
       filename of the combined unit xml file (on disk)
    copyright_filename : string
        filename of the UDUNITS-2 COPYRIGHT file (on disk)

    """
    logging.info('Obtain nexus credentials.')
    nexus_cred = get_creds()
    raw_directory_versioned = '/udunits2/{}/'.format(version)
    raw_directory_current = '/udunits2/current/'

    params = (
        ('repository', 'udunits-2-docs'),
    )

    with open(combined_xml_filename, 'rb') as xmlfile, open(copyright_filename, 'rb') as cr_file:
        logging.info('Publish versioned files.')
        files = {
            'raw.directory': (None, raw_directory_versioned),
            'raw.asset1': (combined_xml_filename, xmlfile),
            'raw.asset1.filename': (None, combined_xml_filename),
            'raw.asset2': (copyright_filename, cr_file),
            'raw.asset2.filename': (None, copyright_filename),
        }

        # make post.
        response = requests.post(nexus_components_url,
                                 params=params,
                                 files=files,
                                 auth=(nexus_cred.name, nexus_cred.pw))

        # if unsuccessful, raise an error
        response.raise_for_status()
        logging.info('...success.')

        # clear out "current" directory in nexus
        search_params = {
            'repository': 'udunits-2-docs',
            'group': raw_directory_current.rstrip('/'),
        }

        # have to use search to get everything under "/udunits2/current",
        # then remove items one-by-one
        search_response = requests.get(nexus_search_url,
                                       params=search_params)
        search_response.raise_for_status()

        results = json.loads(search_response.content)
        items = results.get('items')
        if items:
            logging.info('Clean out "current" files.')

            for item in items:
                item_id = item.get('id')
                if item_id:
                    asset_url = urllib.parse.urljoin(nexus_components_url, item_id)
                    delete_response = requests.delete(asset_url, auth=(nexus_cred.name, nexus_cred.pw))
                    delete_response.raise_for_status()
                    logging.debug('...removed {}.'.format(item.get('name')))
            logging.info('...success.')

        # before updating the current version, need to go back to the
        # beginning of the files, otherwise empty file will appear in
        # nexus
        xmlfile.seek(0)
        cr_file.seek(0)

        logging.info('Update "current" files.')
        files['raw.directory'] = (None, raw_directory_current)

        response = requests.post(nexus_components_url,
                                 params=params,
                                 files=files,
                                 auth=(nexus_cred.name, nexus_cred.pw))

        # if unsuccessful, raise an error
        response.raise_for_status()
        logging.info('...success.')


def should_update_nexus(latest_version):
    r"""Check to see if latest version is already published is nexus.

    Parameters
    ----------
    latest_version : string
       latest release version string of udunits-2 as a dot separated set
       of integers with starting with v

    Returns
    -------
    bool
        If False, nexus is up-to-date. If True, current version in nexus is
         not the same as latest version on github, or a current version does
         not exist on nexus.

    >>> print(should_update_nexus('v2.2.27.6'))
    False

    """
    update = False
    current_udunits2_combined_component_name = 'udunits2/current/udunits2_combined.xml'

    logging.debug('Search and fetch current version of the combined xml from nexus.')

    search_params = {
        'repository': 'udunits-2-docs',
        'name': current_udunits2_combined_component_name,
    }

    # use nexus asset search and download api to get current version of combined
    # xml file
    search_response = requests.get(nexus_asset_search_and_download_url,
                                   params=search_params)

    if search_response.status_code == 404:
        # if status is 404, file does not exist and we should update
        # (this is the bootstrap case)
        logging.info('Current version does not exist on nexus server - force update.')
        # current xml file does not exists on nexus, so for sure create it
        update = True
    else:

        # if request for current version of the xml as stored on nexus fails,
        # raise an error
        search_response.raise_for_status()

    # if we don't need to update due to a 404, do further checks
    if not update:
        # read the xml
        udunits2_nexus_xml = search_response.content

        # extract the namespaces
        namespaces = dict([node for _, node in ET.iterparse(io.BytesIO(udunits2_nexus_xml),
                                                            events=['start-ns'])])
        # namespace looks like:
        # xmlns:a="https://raw.githubusercontent.com/Unidata/UDUNITS-2/v2.2.27.6/lib/udunits2-accepted.xml"
        # so by splitting on /, we can get the version string from element 5
        # this is kind of lame, but if the format of the url changes, then the script will break before any
        # new artifact is published
        udunits2_version_nexus = namespaces.get('a').split('/')[5]
        # but, in an attempt to validate that this is a version number of sorts...
        if len(udunits2_version_nexus.split('.')) < 2:
            raise ValueError(
                'nexus version {} does not appear to be an actual version number. exiting.'.format(
                    udunits2_version_nexus))
        # check if version strings match. If not, need an update
        logging.info('UDUNITS-2 release version used to build current nexus version: {}'.format(udunits2_version_nexus))
        update = latest_version != udunits2_version_nexus

    return update


def update_nexus(version):
    r"""Update nexus with the given version of udunits-2.

    This will update both the versioned copy on nexus (e.g.
    https://docs.unidata.ucar.edu/thredds/udunits2/2.2.27.6/udunits2_combined.xml)
    as well as the current version (e.g.
    https://docs.unidata.ucar.edu/thredds/udunits2/current/udunits2_combined.xml)

    Parameters
    ----------
    version : string
       latest release version string of udunits-2 as a dot separated set
       of integers with starting with v

    >>> update_nexus('v2.2.27.6')

    """
    # first, grab udunits-2 copyright
    fetch_udunits2_copyright_gh(version, copyright_file_name)

    prefix_map = {
        'udunits2-prefixes.xml': 'p',
        'udunits2-base.xml': 'b',
        'udunits2-derived.xml': 'd',
        'udunits2-accepted.xml': 'a',
        'udunits2-common.xml': 'c'
    }

    udunits2_prefix = 'u2'
    udunits2_uri = 'https://doi.org/10.5065/D6KD1WN0'

    namespaces = {}

    udunits_resource_base_url = 'https://raw.githubusercontent.com/Unidata/UDUNITS-2/{}/lib/'.format(version)

    response = requests.get(urllib.parse.urljoin(udunits_resource_base_url, 'udunits2.xml'))
    udunits2_xml = response.content
    udunits2_registry = ET.fromstring(udunits2_xml)

    udunits2_unit_systems = udunits2_registry.findall('import')

    all_elements = []
    for system_doc_element in udunits2_unit_systems:
        system_filename = system_doc_element.text
        logging.info('Processing info from {}.'.format(system_filename))
        prefix = prefix_map[system_filename]
        url = urllib.parse.urljoin(udunits_resource_base_url, system_filename)
        namespaces[prefix] = url
        response = requests.get(url)
        system_xml = response.content
        system = ET.fromstring(system_xml)
        logging.debug('...looking for <unit> elements')
        elements_to_add = system.findall('unit')
        if len(elements_to_add) > 0:
            logging.debug('...found {} <unit> elements.'.format(len(elements_to_add)))
        else:
            logging.debug('...no <unit> elements found. Looking for <prefix> elements.')
            elements_to_add = system.findall('prefix')
            if len(elements_to_add) > 0:
                logging.debug('...found {} <prefix> elements.'.format(len(elements_to_add)))
            else:
                msg = '...no <prefix> or <unit> elements found in {}.'.format(system_filename)
                logging.error(msg)
                raise ValueError(msg)

        logging.debug('...adding namespace prefix to all {} found elements'.format(len(elements_to_add)))
        for element in elements_to_add:
            for child in element.iter():
                child.tag = '{}:{}'.format(prefix, child.tag)

        logging.info('...processed {} entries.'.format(len(elements_to_add)))
        all_elements.extend(elements_to_add)

    logging.info('Construct combined xml document.')
    combined_systems = ET.Element('udunits-2')

    combined_root = ET.ElementTree(combined_systems)
    logging.debug('...adding namespaces')
    combined_root.getroot().set('xmlns:{}'.format(udunits2_prefix), udunits2_uri)
    for prefix, url in namespaces.items():
        combined_root.getroot().set('xmlns:{}'.format(prefix), url)

    logging.debug('...adding unit systems')
    unit_systems = ET.Element('{}:unit-system'.format(udunits2_prefix))
    for element in all_elements:
        unit_systems.append(element)

    combined_systems.append(unit_systems)
    logging.info('...combined {} total entries.'.format(len(all_elements)))
    logging.debug('Add udunits-2 copyright info')
    version_no_v = version.replace('v', '')
    combined_file_copyright = ET.Comment(get_udunits2_copyright_text(version_no_v))
    combined_root.getroot().insert(0, combined_file_copyright)

    logging.info('Write combined xml document to disk.')
    combined_root.write(combined_xml_file_name, encoding="UTF-8", xml_declaration=True)

    logging.info('\nSuccess! Publish combined xml document to nexus.\n')
    publish_to_nexus(version_no_v, combined_xml_file_name, copyright_file_name)


if __name__ == "__main__":
    r"""Check github for new releases of udunits-2, and update nexus as needed
    
    This script will update both the versioned copy on nexus (e.g.
    https://docs.unidata.ucar.edu/thredds/udunits2/2.2.27.6/udunits2_combined.xml)
    as well as the current version (e.g.
    https://docs.unidata.ucar.edu/thredds/udunits2/current/udunits2_combined.xml)
    if the current version does not exist on nexus, or if the current version
    on nexus does not match the released version string from the udunits-2
    github repository. The appropriate version of the udunits2 COPYRIGHT file is
    also stored on nexus and referenced in the new combined xml file.

    """
    logging.info('=+=+=+=+=+=')
    logging.info('Begin update process.')
    # get latest version info from github
    udunits2_version_gh = get_latest_github_release_version()

    # check latest version from nexus, and see if the string differs from what we got from github
    if not should_update_nexus(udunits2_version_gh):
        # create new combined xml based on new release
        update_nexus(udunits2_version_gh)
        # cleanup like good citizens
        if os.path.exists(copyright_file_name) and os.path.exists(combined_xml_file_name):
            logging.info('Cleanup temporary files.')
            os.remove(copyright_file_name)
            os.remove(combined_xml_file_name)
        logging.info('Finished update. Exiting.')
    else:
        logging.info('No new version of udunits-2 detected. Exiting.')

    logging.info('=+=+=+=+=+=')
