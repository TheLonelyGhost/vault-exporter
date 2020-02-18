# Vault Exporter

Exports KV secrets engine data into JSON, allowing us to backup data stored in vault in an admittedly insecure way, but far more accessible than a Consul KV export.

## Requirements

- Python 3 (>=3.8.0, preferably)

## Setup

Get the root token of the Vault cluster for which you would like to export data, then consider that your vault token for the context of this tool.

```shell
export VAULT_TOKEN='<root-token>'
export VAULT_ADDR='<vault-server>'

python3 -m venv ./venv
source ./venv/bin/activate
hash -r
pip install -r ./requirements.txt
```

## Usage

```shell
export VAULT_TOKEN='<root-token>'
export VAULT_ADDR='<vault-server>'

source ./venv/bin/activate
python3 ./export_kv_secrets.py
```
