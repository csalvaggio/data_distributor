import secrets
import string
import requests

from dataclasses import dataclass
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning


CHARSET = string.ascii_letters + string.digits + "-_"


@dataclass(frozen=True)
class DataDistributor:
    """
    Create random slug-based directories for web-visible data distributions.

    The class is responsible for creating unique slug-based directories within
    a base directory, building corresponding public URLs, and optionally
    generating an `index.html` file for each created distribution. It can also
    fetch a remote HTML template to use for index generation.

    Attributes
    ----------
    base_directory : Path | str
        Root directory under which all slug-based data directories are created.
    base_url : str
        Base URL corresponding to `base_directory` for constructing public
        URLs for each slug.
    index_template_url : str or None, optional
        URL of an HTML template used to generate `index.html`. If None, a
        simple default HTML stub is generated instead.
    slug_length : int, optional
        Default length of generated slugs. Used when `length` is not provided
        to `make_slug` or `create`.
    suppress_insecure_warning : bool, optional
        If True, suppresses insecure request warnings when SSL verification
        is disabled for HTTP requests.
    """

    base_directory: Path | str
    base_url: str
    index_template_url: str | None = None
    slug_length: int = 24
    suppress_insecure_warning: bool = False

    def __post_init__(self) -> None:
        """
        Normalize and finalize dataclass attributes after initialization.

        This method ensures that `base_directory` is a `Path` instance and
        strips any trailing slash from `base_url` and `index_template_url`.
        It also optionally suppresses insecure request warnings if
        `suppress_insecure_warning` is True.
        """
        # Normalize fields while keeping the dataclass frozen.
        object.__setattr__(self, "base_directory", Path(self.base_directory))
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
        if self.index_template_url is not None:
            object.__setattr__(
                self,
                "index_template_url",
                self.index_template_url.rstrip("/"),
            )
        if self.suppress_insecure_warning:
            urllib3.disable_warnings(InsecureRequestWarning)

    def make_slug(self, length: int | None = None) -> str:
        """
        Generate a random alpha/numeric/symbol slug with URL-safe characters.

        The slug is composed of ASCII letters and digits. If `length` is not
        provided, the instance attribute `slug_length` is used.

        Parameters
        ----------
        length : int or None, optional
            Length of the slug. If None, `self.slug_length` is used.

        Returns
        -------
        str
            A randomly generated slug string.
        """
        if length is None:
            length = self.slug_length
        return ''.join(secrets.choice(CHARSET) for _ in range(length))

    def create_data_dir(self, slug: str) -> Path:
        """
        Create a data directory for a given slug.

        The directory is created as a subdirectory of `base_directory` with
        the name equal to the provided slug.

        Parameters
        ----------
        slug : str
            Slug for which the data directory will be created.

        Returns
        -------
        pathlib.Path
            Path object pointing to the created directory.

        Raises
        ------
        FileExistsError
            If the directory already exists and cannot be created with
            `exist_ok=False`.
        """
        path = self.base_directory / slug
        path.mkdir(parents=True, exist_ok=False)
        return path

    def create_data_url(self, slug: str) -> str:
        """
        Build the public URL for a given slug.

        Parameters
        ----------
        slug : str
            Slug whose corresponding URL should be constructed.

        Returns
        -------
        str
            Full URL for the given slug, formed by combining `base_url`
            and the slug.
        """
        return f"{self.base_url}/{slug}"

    def read_index_template(self,
        verify: bool | str | None = None) -> str | None:
        """
        Retrieve the HTML template from `index_template_url`.

        This method attempts to download the template specified by
        `index_template_url` using an HTTP GET request. If the URL is
        not configured, if the request fails, or if a non-successful
        HTTP status is returned, the method returns ``None``.

        Parameters
        ----------
        verify : bool or str or None, optional
            SSL certificate verification setting passed to ``requests.get``.
            - If ``True`` (default), system CA certificates are used.
            - If ``False``, SSL verification is disabled (insecure).
            - If a string, it is treated as a path to a CA bundle.
            If ``None``, a default of ``True`` is applied.

        Returns
        -------
        str or None
            The retrieved template HTML as a string if the request
            succeeds; otherwise ``None``.

        Notes
        -----
        A timeout of 5 seconds is used. All network and HTTP-related
        exceptions are caught and result in ``None`` being returned.
        """
        if not self.index_template_url:
            return None

        if verify is None:
            verify = True  # safer default

        try:
            response = requests.get(
                self.index_template_url,
                timeout=5,
                verify=verify,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        return response.text

    def write_index(
        self,
        directory: Path,
        title: str | None = None,
        body_html: str | None = None,
    ) -> Path:
        """
        Create an `index.html` file in the given directory.

        If a remote index template is available and successfully retrieved,
        that template is written as-is. Otherwise, a simple default HTML
        stub is generated using the provided `title` and `body_html`
        parameters.

        Parameters
        ----------
        directory : pathlib.Path
            Directory in which `index.html` will be created.
        title : str or None, optional
            Text to use inside the `<title>` element of the fallback HTML.
            If None, a default title `"Data"` is used.
        body_html : str or None, optional
            HTML content to place inside the `<body>` element of the fallback
            HTML. If None, a simple default placeholder message is used.

        Returns
        -------
        pathlib.Path
            Path object pointing to the created `index.html` file.
        """
        # Attempt template fetch
        html = None
        if self.index_template_url:
            html = self.read_index_template(verify=False)

        # Fallback to a simple stub if no template is available
        if html is None:
            title = title or "Data"
            body_html = body_html or (
                "<h1>Data Placeholder</h1>\n"
                "<p>This page was automatically generated.</p>\n"
            )
            html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <title>{title}</title>
  </head>
  <body>
{body_html}
  </body>
</html>
"""

        # Write content to index file
        index_path = directory / "index.html"
        index_path.write_text(html, encoding="utf-8")
        return index_path

    def create(
        self,
        length: int | None = None,
        *,
        with_index: bool = False,
        index_title: str | None = None,
        index_body_html: str | None = None,
    ) -> tuple[str, Path, str]:
        """
        Create a new data distribution.

        This method generates a unique slug, creates the associated data
        directory, optionally writes an `index.html` file into that directory,
        and returns the slug, directory path, and public URL.

        Parameters
        ----------
        length : int or None, optional
            Optional override for the slug length. If None, `self.slug_length`
            is used.
        with_index : bool, optional
            If True, an `index.html` is created in the new directory using
            `write_index`. Defaults to False.
        index_title : str or None, optional
            Optional title to pass to `write_index` for the fallback template.
        index_body_html : str or None, optional
            Optional body HTML to pass to `write_index` for the fallback
            template.

        Returns
        -------
        tuple of (str, pathlib.Path, str)
            A tuple containing:

            - slug : str
                The generated slug.
            - path : pathlib.Path
                Path to the created data directory.
            - url : str
                Public URL corresponding to the created slug.
        """
        slug = self.make_slug(length)
        path = self.create_data_dir(slug)

        if with_index:
            self.write_index(path, index_title, index_body_html)

        url = self.create_data_url(slug)
        return slug, path, url

    def url_exists(
        self,
        slug: str,
        timeout: float = 3.0,
        verify: bool | str = True
    ) -> bool:
        """
        Check whether the URL corresponding to a slug is reachable.

        The method first attempts an HTTP HEAD request for efficiency. If the
        server does not support HEAD or an error occurs, it falls back to an
        HTTP GET request. A response is considered successful if its status
        code is less than 400.

        Parameters
        ----------
        slug : str
            The slug whose URL should be tested.
        timeout : float, optional
            Timeout in seconds for the HTTP requests. Defaults to 3.0.
        verify : bool or str, optional
            SSL certificate verification setting. Pass True to use system
            defaults, False to disable verification, or a path to a CA bundle.
            Defaults to True.

        Returns
        -------
        bool
            True if the URL responds with a status code < 400, otherwise
            False.
        """
        url = self.create_data_url(slug)

        # Try HEAD first
        try:
            r = requests.head(
                url,
                allow_redirects=True,
                timeout=timeout,
                verify=verify
            )
            if r.status_code < 400:
                return True
        except requests.RequestException:
            pass

        # Fallback to GET
        try:
            r = requests.get(
                url,
                stream=True,
                timeout=timeout,
                verify=verify
            )
            return r.status_code < 400
        except requests.RequestException:
            return False


if __name__ == "__main__":
    base_directory = "/home/cnspci/public_html/tmp/imagine_rit"
    base_url = "https://home.cis.rit.edu/~cnspci/tmp/imagine_rit"
    index_template_url = \
        "https://home.cis.rit.edu/~cnspci/tmp/imagine_rit/template/index.html"

    distributor = DataDistributor(
        base_directory,
        base_url,
        index_template_url,
        suppress_insecure_warning=False
    )

    slug, path, url = distributor.create(with_index=True)

    print("Slug:")
    print(slug)
    print("Directory:")
    print(path)
    print("URL:")
    print(url)
    print("URL reachable?")
    print(distributor.url_exists(slug, verify=False))

