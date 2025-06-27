#  Terraform Module Updater

This Python script scans Terraform configuration files (`.tf`) in a specified directory to check module versions against the public Terraform Registry or a private registry (e.g., Terraform Cloud at `app.terraform.io`). It generates a table showing module details, including whether updates are available, and supports updating module versions either interactively or automatically. The script dynamically fetches the private registry's module API path using the `.well-known/terraform.json` endpoint and handles both public and private registries.

## ✨ Features

-   **Scans Terraform Files**: Recursively scans `.tf` files in a specified directory (default: current directory) to extract module names, sources, and version constraints.
-   **Registry Support**:
    -   Queries the public Terraform Registry (`registry.terraform.io`) for public modules.
    -   Queries private registries (e.g., `app.terraform.io`) using a Terraform Cloud token, with the module API path fetched from `https://<hostname>/.well-known/terraform.json`.
-   **Table Output**: Displays a table with columns: `UPDATE?`, `NAME`, `CONSTRAINT`, `VERSION`, `LATEST MATCHING`, `LATEST`.
-   **Version Updates**:
    -   Optionally prompts to update modules to the latest matching or latest version (`--update`).
    -   Automatically updates all modules without prompting (`--all`).
    -   Creates backups of modified `.tf` files with timestamps.
-   **Custom Directory**: Supports scanning a specific directory with the `--path` parameter.
-   **Error Handling**: Skips invalid modules, handles API errors (e.g., 404 for missing modules), and provides clear error messages.

## 🚀 Getting Started

### Prerequisites

-   Python 3.6+
-   Python Packages:
    -   `requests`: For HTTP requests to the Terraform Registry.
    -   `hcl2`: For parsing Terraform configuration files.
    -   `packaging`: For version comparison and constraint parsing.
-   Terraform Configuration: `.tf` files with `module` blocks specifying `source` and `version`.
-   Terraform Cloud Token (optional): Required for private registry access, stored in `~/.terraform.d/credentials.tfrc.json`.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/terraform-module-version-checker.git
    cd terraform-module-version-checker
    ```
2.  **Install dependencies:**
    ```bash
    pip install requests hcl2 packaging
    ```
3.  **Ensure a Terraform Cloud token is available (for private registries):**
    Store the token in `~/.terraform.d/credentials.tfrc.json` in the format:
    ```json
    {
      "credentials": {
        "app.terraform.io": {
          "token": "your-terraform-cloud-token"
        }
      }
    }
    ```
    Generate the token in Terraform Cloud under **User Settings > Tokens**.

## 💻 Usage

Run the script with the desired options to check and optionally update Terraform module versions.

### Command

```bash
uv run tf_module_update.py [options]
```

### Options

-   `--use-token`: Use the Terraform Cloud token from `~/.terraform.d/credentials.tfrc.json` for private registry access (e.g., `app.terraform.io`).
-   `--path <directory>`: Specify the directory to scan for `.tf` files (default: current directory `.`).
-   `--update`: Prompt for confirmation before updating each module to the latest matching or latest version.
-   `--all`: Automatically update all modules with available updates to the latest matching or latest version without prompting.

## <caption> Examples

**Check modules in the current directory (public registry):**

```bash
uv run tf_module_update.py
```

**Output:**

```
Processing module: apigateway_servicerole (source: terraform-aws-modules/apigateway_servicerole/aws)
| UPDATE? | NAME                     | CONSTRAINT | VERSION | LATEST MATCHING | LATEST |
|---------|--------------------------|------------|---------|-----------------|--------|
| (Y)     | apigateway_servicerole   | 0.4.0      | 0.4.0   |                 | 0.5.3  |
```

**Check modules in a specific directory (private registry):**

```bash
uv run tf_module_update.py --use-token --path ./terraform
```

**Output:**

```
Processing module: datadog (source: app.terraform.io/company/module-s3/aws)
| UPDATE? | NAME                     | CONSTRAINT | VERSION | LATEST MATCHING | LATEST |
|---------|--------------------------|------------|---------|-----------------|--------|
| (Y)     | module-3                 | 0.5.0      | 0.5.0   |                 | 0.5.1  |
```

**Check and prompt for updates:**

```bash
uv run tf_module_update.py --use-token --update
```

**Automatically update all modules:**

```bash
uv run tf_module_update.py --use-token --all
```

## 📊 Table Format

The script outputs a table with the following columns:

-   `UPDATE?`: `(Y)` if an update is available (latest matching or latest version differs from current).
-   `NAME`: The module name from the `.tf` file.
-   `CONSTRAINT`: The version constraint specified in the `version` attribute (e.g., `0.4.0`, `~> 0.3.0`).
-   `VERSION`: The current version or constraint used.
-   `LATEST MATCHING`: The latest version that satisfies the constraint (if applicable).
-   `LATEST`: The latest available version in the registry.

### Example Terraform File

The script expects `.tf` files with `module` blocks like:

```hcl
module "s3" {
  source  = "app.terraform.io/company/module-s3/aws"
  version = "0.5.0"
}

module "apigateway_servicerole" {
  source  = "terraform-aws-modules/apigateway_servicerole/aws"
  version = "0.4.0"
}
```

## 💡 Troubleshooting

-   **404 Not Found Error**:
    -   Ensure the module source is correct.
    -   Verify the module exists in Terraform Cloud.
    -   Check that the token has access to the namespace.
-   **Invalid Directory**: Ensure the `--path` specifies a valid directory.
-   **No Modules Found**: Confirm that `.tf` files exist and contain valid `module` blocks.
-   **Private Registry Issues**: Use `--use-token` and verify the `.well-known/terraform.json` endpoint.

## 🤝 Contributing

Contributions are welcome! Please submit a pull request or open an issue on GitHub for bug reports, feature requests, or improvements.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
