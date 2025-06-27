#!/usr/bin/env python3

import os
import json
import argparse
import logging
import requests
import hcl2
from packaging import version, specifiers
from datetime import datetime

def get_terraform_token():
    """Read Terraform Cloud token from credentials file."""
    try:
        with open(os.path.expanduser('~/.terraform.d/credentials.tfrc.json'), 'r') as f:
            data = json.load(f)
        return data['credentials']['app.terraform.io']['token']
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Failed to read Terraform token from ~/.terraform.d/credentials.tfrc.json: {e}")
        exit(1)

def get_modules_path(hostname):
    """Fetch the modules.v1 path from the .well-known/terraform.json endpoint."""
    try:
        url = f"https://{hostname}/.well-known/terraform.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        modules_path = data.get('modules.v1', '/api/registry/v1/modules/')
        return modules_path.rstrip('/')  # Ensure no trailing slash
    except requests.RequestException as e:
        logging.error(f"Error fetching .well-known/terraform.json from {hostname}: {e}")
        logging.info("Falling back to default modules path: /api/registry/v1/modules")
        return '/api/registry/v1/modules'

def parse_module_source(source):
    """Parse module source to extract registry type, namespace, module, and provider."""
    parts = source.split('/')
    if len(parts) >= 4 and '.' in parts[0]:
        # Private registry: hostname/namespace/module/provider
        return {
            'registry': 'private',
            'hostname': parts[0],
            'namespace': parts[1],
            'module': parts[2],
            'provider': parts[3]
        }
    elif len(parts) >= 3:
        # Public registry: namespace/module/provider
        return {
            'registry': 'public',
            'hostname': 'registry.terraform.io',
            'namespace': parts[0],
            'module': parts[1],
            'provider': parts[2]
        }
    else:
        logging.warning(f"Invalid module source format: {source}")
        return None

def get_module_versions(module_info, token=None):
    """Query Terraform Registry for module versions."""
    if module_info['registry'] == 'private' and token:
        modules_path = get_modules_path(module_info['hostname'])
        url = f"https://{module_info['hostname']}{modules_path}/{module_info['namespace']}/{module_info['module']}/{module_info['provider']}/versions"
        headers = {'Authorization': f'Bearer {token}'}
    else:
        url = f"https://registry.terraform.io/v1/modules/{module_info['namespace']}/{module_info['module']}/{module_info['provider']}/versions"
        headers = {}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        versions = [v['version'] for v in data.get('modules', [{}])[0].get('versions', [])]
        if not versions:
            print(f"Warning: No versions found for {module_info['namespace']}/{module_info['module']}/{module_info['provider']} in {module_info['registry']} registry")
        return sorted(versions, key=lambda x: version.parse(x), reverse=True)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Error: Module {module_info['namespace']}/{module_info['module']}/{module_info['provider']} not found in {module_info['registry']} registry at {url}")
            print("Please verify the module source, namespace, and token permissions in Terraform Cloud.")
        else:
            print(f"Error fetching versions for {module_info['namespace']}/{module_info['module']}/{module_info['provider']}: {e}")
        return []
    except requests.RequestException as e:
        print(f"Error fetching versions for {module_info['namespace']}/{module_info['module']}/{module_info['provider']}: {e}")
        return []

def find_latest_matching_version(versions, constraint):
    """Find the latest version that matches the version constraint."""
    try:
        spec = specifiers.SpecifierSet(constraint)
        matching_versions = [v for v in versions if v in spec]
        return max(matching_versions, key=lambda x: version.parse(x)) if matching_versions else ""
    except Exception:
        return ""

def scan_terraform_modules(path):
    """Scan all .tf files in the specified directory and subdirectories for modules."""
    modules = []
    try:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.tf'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            config = hcl2.load(f)
                            for module in config.get('module', []):
                                for module_name, module_data in module.items():
                                    source = module_data.get('source', '')
                                    version_constraint = module_data.get('version', '')
                                    module_info = parse_module_source(source)
                                    if module_info:
                                        modules.append({
                                            'name': module_name,
                                            'source': source,
                                            'constraint': version_constraint,
                                            'file_path': file_path,
                                            'module_info': module_info
                                        })
                                    else:
                                        print(f"Skipping module {module_name} in {file_path} due to invalid source: {source}")
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
    except Exception as e:
        print(f"Error scanning directory {path}: {e}")
    return modules

def update_module_version(file_path, module_name, new_version):
    """Update the version of a specific module in a Terraform file."""
    try:
        # Create a backup
        backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(file_path, 'r') as f:
            content = f.read()
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"Created backup: {backup_path}")

        # Parse and update the file
        with open(file_path, 'r') as f:
            config = hcl2.load(f)
        for module in config.get('module', []):
            if module_name in module:
                module[module_name]['version'] = new_version
        with open(file_path, 'w') as f:
            hcl2.dump(config, f)
        print(f"Updated {module_name} in {file_path} to version {new_version}")
    except Exception as e:
        print(f"Error updating {file_path}: {e}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Check and update Terraform module versions.")
    parser.add_argument('--use-token', action='store_true', help="Use Terraform Cloud token for private registry access")
    parser.add_argument('--path', default='.', help="Directory to scan for Terraform files (default: current directory)")
    parser.add_argument('--update', action='store_true', help="Prompt to update module versions")
    parser.add_argument('--all', action='store_true', help="Update all modules to latest matching or latest version without prompting")
    parser.add_argument('--log', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Set the logging level (default: INFO)")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=args.log, format='%(asctime)s - %(levelname)s - %(message)s')

    # Validate path
    if not os.path.isdir(args.path):
        print(f"Error: Directory {args.path} does not exist or is not a directory.")
        exit(1)

    # Get Terraform token if --use-token is specified
    token = get_terraform_token() if args.use_token else None

    # Scan for modules
    modules = scan_terraform_modules(args.path)
    if not modules:
        print(f"No Terraform modules found in {args.path}.")
        return

    # Prepare table
    print("| UPDATE? | NAME                     | CONSTRAINT | VERSION  | LATEST MATCHING | LATEST |")
    print("|---------|--------------------------|------------|----------|-----------------|--------|")

    # Process each module
    for module in modules:
        module_info = module['module_info']
        #print(f"Processing module: {module['name']} (source: {module['source']})")
        versions = get_module_versions(module_info, token)
        latest_version = versions[0] if versions else ""
        latest_matching = find_latest_matching_version(versions, module['constraint']) if module['constraint'] else ""
        current_version = module['constraint'].replace('=', '').strip() if module['constraint'].startswith('=') else module['constraint']

        # Determine if update is possible
        update_possible = (
            latest_version and
            (not current_version or (latest_version != current_version and (not latest_matching or latest_matching != current_version)))
        )
        update_flag = "(Y)" if update_possible else ""

        # Print table row
        print(f"| {update_flag:<7} | {module['name']:<24} | {module['constraint']:<10} | {current_version:<8} | {latest_matching:<15} | {latest_version:<6} |")

        # Update version if requested
        if update_possible and (args.all or args.update):
            if args.all:
                new_version = latest_matching if latest_matching else latest_version
                if new_version:
                    update_module_version(module['file_path'], module['name'], new_version)
            elif args.update:
                update = input(f"\nUpdate {module['name']} to {'latest matching (' + latest_matching + ')' if latest_matching else 'latest (' + latest_version + ')'}? (y/n): ").strip().lower()
                if update == 'y':
                    new_version = latest_matching if latest_matching else latest_version
                    if new_version:
                        update_module_version(module['file_path'], module['name'], new_version)

if __name__ == "__main__":
    main()