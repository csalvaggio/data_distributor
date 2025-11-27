# data_distributor - A Web-Visible Data Distribution Module

Create random slug-based directories for web-visible data distributions.
 
Given a local base directory and a corresponding public URL, this module
generates unique slugs, creates matching filesystem directories, and
(optionally) writes `index.html` files using either a remote HTML
template or an auto-generated fallback.

A common use case is making temporary, unguessable URLs for sharing data
during events, demos, or workflows where lightweight authenticated
access is not required.

---

## Features

-   **Secure random slug generation** (URL-safe characters)
-   **Automatic directory creation** under a configured base
    directory
-   **Public URL generation** corresponding to local slug directories
-   **Optional index generation**
    Fetch a remote HTML template **via HTTPS**, or\
    -   Automatically generate a simple fallback stub
-   Optional suppression of `InsecureRequestWarning` (useful when
    callers intentionally use `verify=False`)
-   **URL reachability testing** via HTTP HEAD/GET

---

## Installation

The module has no non-standard dependencies other than:

-   `requests`
-   `urllib3`

Install them (if needed) with:

``` bash
pip install requests urllib3
```

Then include the module in your project or place it on your Python path.

---

## Quick Start

Here is the minimal workflow to create a new slug directory and print
its URL:

``` python
from pathlib import Path
from data_distributor import DataDistributor

distributor = DataDistributor(
    base_directory="/var/www/data",
    base_url="https://example.com/data",
)

slug, path, url = distributor.create()

print("Slug:", slug)
print("Directory:", path)
print("URL:", url)
```

---

## Using a Remote Template for `index.html`

If you host a template:

``` python
distributor = DataDistributor(
    base_directory="/var/www/data",
    base_url="https://example.com/data",
    index_template_url="https://example.com/template/index.html",
)

slug, path, url = distributor.create(with_index=True)
```

If the template cannot be retrieved for any reason (timeout, non-200
status, SSL error, etc.), a fallback HTML stub is written instead.

---

## Creating a Temporary Distribution with a Single Call

The module includes a convenience helper:

``` python
from data_distributor import create_data_distribution

distributor, slug, path, url = create_data_distribution(
    base_directory="/var/www/data",
    base_url="https://example.com/data",
    with_index=True,
    index_title="My Dataset",
    index_body_html="<p>Hello world.</p>",
)

print("URL:", url)
```

---

## API Overview

### `DataDistributor`

#### Constructor

``` python
DataDistributor(
    base_directory: Path | str,
    base_url: str,
    index_template_url: str | None = None,
    slug_length: int = 32,
    suppress_insecure_warning: bool = False,
)
```

**Key behaviors**

-   Normalizes paths and strips URL trailing slashes.
-   If `suppress_insecure_warning=True`, disables
    `urllib3.InsecureRequestWarning` globally.
-   Does **not** change SSL verification behavior---only warnings.

---

### `make_slug(length: int | None = None) -> str`

Generate a random slug of letters, digits, `_` and `-`.\
Used internally by `create()`.

---

### `create_data_dir(slug: str) -> Path`

Creates:

    base_directory / slug

`exist_ok=False` ensures accidental overwrites become explicit errors.

---

### `create_data_url(slug: str) -> str`

Builds:

    "{base_url}/{slug}"

---

### `read_index_template(verify=True|False|path) -> str | None`

Attempts to fetch the remote template.\
Returns `None` on any network failure or HTTP error.

---

### `write_index(...) -> Path`

Creates `index.html` inside the given directory:

-   If template fetch succeeds → write template\
-   Otherwise → write fallback stub with optional `title` and
    `body_html`

---

### `create(...) -> (slug, path, url)`

Full workflow:

1.  Generate slug\
2.  Create directory\
3.  Optionally write `index.html`\
4.  Return `(slug, filesystem_path, public_url)`

---

### `url_exists(slug, timeout=3, verify=True|False|path) -> bool`

Checks reachability via:

1.  HTTP `HEAD`\
2.  Fallback HTTP `GET`

A status code `< 400` is considered **reachable**.

---

### Convenience Function

#### `create_data_distribution(...) -> (distributor, slug, path, url)`

Wrapper that both **creates** a new `DataDistributor` instance and
**creates a distribution** with it.

---

## Example Script (as in `__main__`)

``` python
if __name__ == "__main__":
    base_directory = "/home/cnspci/public_html/tmp/imagine_rit"
    base_url = "https://home.cis.rit.edu/~cnspci/tmp/imagine_rit"
    index_template_url = (
        "https://home.cis.rit.edu/~cnspci/tmp/imagine_rit/template/index.html"
    )

    distributor = DataDistributor(
        base_directory=base_directory,
        base_url=base_url,
        index_template_url=index_template_url,
    )

    slug, path, url = distributor.create(with_index=True)

    print("Slug:", slug)
    print("Directory:", path)
    print("URL:", url)
    print("URL reachable?", distributor.url_exists(slug, verify=False))
```

---

## Security Notes

-   Slugs are generated using **cryptographically secure randomness**
    (`secrets.choice`).
-   Slug directories are effectively *unguessable URLs*, but not
    intended for high-security applications.
-   If you disable SSL verification (`verify=False`), consider also
    enabling\
    `suppress_insecure_warning=True` to avoid warning spam---but
    understand the security implications.
-   Directory creation uses `exist_ok=False` to avoid silent collisions.

---

## Development Notes

-   Tested on Python 3.10+
-   Depends only on standard library + `requests`/`urllib3`
-   No external state or system modifications occur except directory
    creation and optional warning suppression
-   Network operations always use timeouts to avoid blocking

---

## License

This project is licensed under the MIT License.  
Copyright (c) 2025 Carl Salvaggio.

See the [LICENSE](LICENSE) file for details.

---

## Contact

**Carl Salvaggio, Ph.D.**  
Email: carl.salvaggio@rit.edu

[Chester F. Carlson Center for Imaging Science](https://www.rit.edu/science/chester-f-carlson-center-imaging-science)  
[Rochester Institute of Technology](https://www.rit.edu)  
Rochester, New York 14623  
United States
