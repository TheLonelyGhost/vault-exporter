#!/usr/bin/env python

import json
import logging
from pathlib import Path
from pprint import pprint  # noqa
from typing import Dict, List, Optional, Tuple

import hvac

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def recursively_list_secrets(client, path='', mount='secret', version='1') -> List[str]:
    output: List[str] = []

    try:
        log.debug('Listing v{version} secrets in {path!r} (Namespace: {ns!r}; Mount: {mnt!r})'.format(path=path, mnt=mount, ns=client._adapter.namespace, version=version))
        if version == '1':
            result = client.secrets.kv.v1.list_secrets(path=path, mount_point=mount)
        else:
            result = client.secrets.kv.v2.list_secrets(path=path, mount_point=mount)
    except hvac.exceptions.InvalidPath as e:
        if not path:
            # This should only occur at the base path, no subpath, due to how KV thinks
            # of "folders" similar to git: They only exist if there's a file in them. A
            # mount point can exist without there being any data in them though.
            log.info('No secrets found')
            return output
        raise e

    for key in result['data']['keys']:
        new_path = '/'.join([path, key])
        if new_path.startswith('/'):
            new_path = new_path[1:]

        if new_path.endswith('/'):
            output += recursively_list_secrets(client=client, path=new_path[:-1], mount=mount, version=version)
        else:
            output.append(new_path)

    return list(sorted(output))


def read_secret(client, path='', mount='secret', version='1') -> Optional[Dict[str, str]]:
    try:
        if version == '1':
            result = client.secrets.kv.v1.read_secret(path=path, mount_point=mount)['data']
        else:
            result = client.secrets.kv.v2.read_secret_version(path=path, mount_point=mount)['data']['data']
    except hvac.exceptions.InvalidPath:
        return None

    return result


def list_kv_mount_points(client) -> List[Tuple[str, str]]:
    mount_points = client.sys.list_mounted_secrets_engines()['data']

    return [(mount[:-1], config['options']['version']) for mount, config in mount_points.items() if config['type'] == 'kv']


def list_namespaces(client) -> List[str]:
    try:
        result = client.sys.list_namespaces()['data']
    except hvac.exceptions.InvalidPath:
        # sometimes Vault Enterprise will puke here if not using
        # namespaces. We should silently move on
        return []

    return list(sorted([namespace[:-1] for namespace in result['keys']]))


def export_secrets(client, namespace='', local_path='tmp'):
    tmp_dir = Path(local_path) / (namespace if namespace else '<root>')
    tmp_dir.mkdir(mode=0o750, parents=True, exist_ok=True)

    for mount, version in list_kv_mount_points(client=client):
        log.info('Found mount (v{}) at {!r}'.format(version, mount))
        base_dir = Path(tmp_dir) / Path(mount)
        for path in recursively_list_secrets(client=client, mount=mount, version=version):
            secret = read_secret(client=client, path=path, mount=mount, version=version)
            if not secret:
                continue

            backup = Path(path)
            (base_dir / backup.parent).mkdir(mode=0o750, parents=True, exist_ok=True)

            target = Path(str(base_dir / backup) + '.json')

            with target.open('w') as f:
                f.write(json.dumps(secret))
            log.info('Wrote {}'.format(target))


def main():
    tmp_dir = Path(__file__).parent / 'export'
    client = hvac.Client()

    namespaces = [''] + list_namespaces(client)  # root namespace and underlings
    # namespaces = list_namespaces(client)
    for namespace in namespaces:
        log.info('Entering namespace {!r}'.format(namespace))
        ns_client = hvac.Client(namespace=namespace)

        export_secrets(client=ns_client, namespace=namespace, local_path=str(tmp_dir))


if __name__ == '__main__':
    main()
