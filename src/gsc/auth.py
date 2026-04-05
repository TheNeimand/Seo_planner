"""
Google Search Console authentication module.
"""
import logging
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from src.config import GSC_SCOPES

logger = logging.getLogger(__name__)


def get_gsc_service(credentials_file: str | Path):
    """
    Authenticate with Google Search Console using a service account.

    Args:
        credentials_file: Path to the service account JSON key file.

    Returns:
        A Google Search Console API service resource.
    """
    credentials_file = Path(credentials_file)

    if not credentials_file.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {credentials_file}"
        )

    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(credentials_file),
            scopes=GSC_SCOPES,
        )
        service = build("searchconsole", "v1", credentials=credentials)
        logger.info("Successfully authenticated with GSC API.")
        return service
    except Exception as e:
        logger.error(f"Failed to authenticate with GSC: {e}")
        raise


def verify_site_access(service, site_url: str) -> bool:
    """
    Verify that the service account has access to the given site.

    Args:
        service: GSC API service resource.
        site_url: The site URL or property to verify.

    Returns:
        True if access is verified, False otherwise.
    """
    try:
        sites = service.sites().list().execute()
        site_list = sites.get("siteEntry", [])
        for site in site_list:
            if site.get("siteUrl") == site_url:
                logger.info(f"Access verified for site: {site_url}")
                return True

        # Try alternate formats
        logger.warning(
            f"Site '{site_url}' not found. Available sites: "
            f"{[s.get('siteUrl') for s in site_list]}"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to verify site access: {e}")
        return False
