import secrets
import string
import requests
import urllib3

from dataclasses import dataclass
from pathlib import Path


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
        Normalized to a `pathlib.Path` during initialization.

    base_url : str
        Base URL corresponding to `base_directory` for constructing public
        URLs for each slug. Any trailing slash is removed during initialization.

    index_template_url : str or None, optional
        URL of an HTML template used to generate `index.html`. If provided,
        it is normalized by stripping any trailing slash. If None, a simple
        fallback HTML stub is used during index creation.

    slug_length : int, optional
        Default length of generated slugs. Used when `length` is not provided
        to `make_slug` or `create`.

    suppress_insecure_warning : bool, optional
        If True, disables `urllib3`'s `InsecureRequestWarning` globally in
        the current process. This is typically used when other code will make
        HTTPS requests with `verify=False`. It does not modify SSL verification
        behavior itself.
    """

    base_directory: Path | str
    base_url: str
    index_template_url: str | None = None
    slug_length: int = 32
    suppress_insecure_warning: bool = False

    def __post_init__(self) -> None:
        """
        Normalize and finalize dataclass attributes after initialization.

        This method ensures that `base_directory` is a `Path` instance and
        strips any trailing slash from `base_url` and `index_template_url`.
        If `suppress_insecure_warning` is True, it disables
        `urllib3`'s `InsecureRequestWarning` globally in the current process.
        """
        object.__setattr__(self, "base_directory", Path(self.base_directory))
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

        if self.index_template_url is not None:
            object.__setattr__(
                self,
                "index_template_url",
                self.index_template_url.rstrip("/"),
            )

        if self.suppress_insecure_warning:
            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning
            )

    def make_slug(self, length: int | None = None) -> str:
        """
        Generate a random alpha/numeric/symbol slug with URL-safe characters.

        The slug is composed of ASCII letters, digits, and valid symbols.
        If `length` is not provided, the instance attribute `slug_length`
        is used.

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

    def read_index_template(
        self,
        verify: bool | str | None = None
    ) -> str | None:
        """
        Retrieve the HTML template from `index_template_url`.

        This method attempts to download the template specified by
        `index_template_url` using an HTTP GET request. If the URL is
        not configured, if the request fails, or if a non-successful
        HTTP status is returned, the method returns ``None``.

        Parameters
        ----------
        verify : bool or str or None, optional
            SSL certificate verification setting passed to ``requests.get``:
            - If ``True``, system CA certificates are used.
            - If ``False``, SSL verification is disabled (insecure).
            - If a string, it is treated as a path to a CA bundle.
            - If ``None`` (the default), this method treats it as ``True``,
              matching the default behavior of ``requests``.

        Returns
        -------
        str or None
            The template HTML as a string if successfully retrieved; otherwise
            ``None``.

        Notes
        -----
        A timeout of 5 seconds is used. All network- and HTTP-related
        exceptions are caught and result in ``None`` being returned.
        """
        if not self.index_template_url:
            return None

        if verify is None:
            verify = True

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
        verify: bool | str | None = None,
    ) -> Path:
        """
        Create an `index.html` file in the given directory.

        If `index_template_url` is configured and a remote template is
        successfully retrieved, that template is written as-is. Otherwise,
        a simple fallback HTML stub is generated using the provided `title`
        and `body_html` parameters.

        Parameters
        ----------
        directory : pathlib.Path
            Directory in which `index.html` will be created.
        title : str or None, optional
            Text to use inside the `<title>` element of the fallback HTML.
            Ignored if a remote template is successfully fetched.
        body_html : str or None, optional
            Content to insert into the `<body>` element of the fallback HTML.
            Ignored if a remote template is successfully fetched.
        verify : bool or str or None, optional
            SSL certificate verification setting passed through to
            `read_index_template`. If None, default rules of that method
            apply (i.e., treated as verify=True).

        Returns
        -------
        pathlib.Path
            Path object pointing to the created `index.html` file.
        """
        html = None

        if self.index_template_url:
            html = self.read_index_template(verify=verify)

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

        This method generates a random slug, creates the associated data
        directory, optionally writes an index file, and returns the slug,
        the directory path, and the public URL.

        Parameters
        ----------
        length : int or None, optional
            Optional override for the slug length. If None, `self.slug_length`
            is used.
        with_index : bool, optional
            If True, an `index.html` is created via `write_index`.
        index_title : str or None, optional
            Title for the fallback `index.html` stub (used only if no remote
            template is fetched).
        index_body_html : str or None, optional
            Body HTML for the fallback `index.html` stub.

        Returns
        -------
        tuple[str, pathlib.Path, str]
            (slug, path, url)
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
        verify: bool | str | None = None
    ) -> bool:
        """
        Check whether the URL corresponding to a slug is reachable.

        The method first tries an HTTP HEAD request. If this fails or is not
        supported, it falls back to an HTTP GET request. A response is
        considered successful if its status code is less than 400.

        Parameters
        ----------
        slug : str
            The slug whose URL should be checked.
        timeout : float, optional
            Timeout in seconds for the HTTP requests. Default is 3.0.
        verify : bool or str or None, optional
            SSL certificate verification setting:
            - If ``True``, system CA certificates are used.
            - If ``False``, SSL verification is disabled (insecure).
            - If a string, it must be a path to a CA bundle file.
            - If ``None`` (the default), this method treats it as ``True``,
              matching the default behavior of `requests`.

        Returns
        -------
        bool
            True if the URL returns an HTTP status < 400, else False.
        """
        url = self.create_data_url(slug)

        if verify is None:
            verify = True

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

        try:
            with requests.get(
                url,
                stream=True,
                timeout=timeout,
                verify=verify
            ) as r:
                return r.status_code < 400
        except requests.RequestException:
            return False


def create_data_distribution(
        base_directory: Path | str,
        base_url: str,
        *,
        index_template_url: str | None = None,
        slug_length: int = 32,
        suppress_insecure_warning: bool = False,
        with_index: bool = False,
        index_title: str | None = None,
        index_body_html: str | None = None,
    ) -> tuple[DataDistributor, str, Path, str]:
    """
    Convenience factory to create a DataDistributor and a new data distribution.

    This function instantiates a `DataDistributor` with the provided parameters,
    creates a new slug-based data directory (optionally with an `index.html`),
    and returns both the distributor and the details of the created distribution.

    Parameters
    ----------
    base_directory : Path or str
        Root directory under which all slug-based data directories are created.
    base_url : str
        Base URL corresponding to `base_directory`.
    index_template_url : str or None, optional
        Optional URL of an HTML template used to generate `index.html`.
        If provided, it may be fetched via HTTPS.
    slug_length : int, optional
        Default slug length for the created `DataDistributor`.
    suppress_insecure_warning : bool, optional
        If True, disables `urllib3`'s `InsecureRequestWarning` globally in the
        current process. This is usually used when callers intend to perform
        HTTPS requests with `verify=False`.
    with_index : bool, optional
        If True, an `index.html` file is created in the new directory.
    index_title : str or None, optional
        Title for the fallback `index.html` stub (used only if no remote
        template is available).
    index_body_html : str or None, optional
        Body content for the fallback `index.html` stub.

    Returns
    -------
    distributor : DataDistributor
        The constructed distributor instance.
    slug : str
        The generated slug.
    path : pathlib.Path
        Path to the created slug directory.
    url : str
        Public URL corresponding to the created slug.

    Notes
    -----
    This helper does not modify SSL verification behavior. Any network requests
    (template retrieval, URL checks) follow the distributor's documented `verify`
    rules unless explicitly overridden by callers.
    """
    distributor = DataDistributor(
        base_directory=base_directory,
        base_url=base_url,
        index_template_url=index_template_url,
        slug_length=slug_length,
        suppress_insecure_warning=suppress_insecure_warning
    )

    slug, path, url = distributor.create(
        with_index=with_index,
        index_title=index_title,
        index_body_html=index_body_html,
    )

    return distributor, slug, path, url



if __name__ == "__main__":
    base_directory = "/home/cnspci/public_html/tmp/imagine_rit"
    base_url = "https://home.cis.rit.edu/~cnspci/tmp/imagine_rit"
    index_template_url = \
        "https://home.cis.rit.edu/~cnspci/tmp/imagine_rit/template/index.html"

    distributor = DataDistributor(
        base_directory=base_directory,
        base_url=base_url,
        index_template_url=index_template_url,
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

