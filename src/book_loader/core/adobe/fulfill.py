"""
ACSM fulfillment and download.
"""

from pathlib import Path
from .account import AdobeAccount
from ...utils.errors import ACSMFulfillmentError


class ACSMFulfiller:
    """ACSM file fulfiller."""

    def __init__(self, account: AdobeAccount):
        """
        Args:
            account: AdobeAccount instance
        """
        self.account = account

    def fulfill(self, acsm_path: Path, output_dir: Path) -> Path:
        """
        Fulfill ACSM file and download encrypted ebook.

        Args:
            acsm_path: .acsm file path
            output_dir: Output directory

        Returns:
            Downloaded encrypted file path (.epub or .pdf)
        """
        if not self.account.is_authorized():
            raise ACSMFulfillmentError("Not authorized, please authorize first")

        if not acsm_path.exists():
            raise ACSMFulfillmentError(f"ACSM file not found: {acsm_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Set authorization directory path
            from . import libadobe
            from . import libadobeFulfill

            libadobe.update_account_path(str(self.account.auth_dir))

            # Fulfill ACSM
            success, result = libadobeFulfill.fulfill(str(acsm_path), do_notify=True)

            if not success:
                error_msg = result if isinstance(result, str) else "Unknown error"
                raise ACSMFulfillmentError(f"ACSM fulfillment failed: {error_msg}")

            # Download file
            from . import libadobeFulfill as fulfill_module

            output_path = fulfill_module.download(result, str(output_dir))

            if not output_path or not Path(output_path).exists():
                raise ACSMFulfillmentError("Download failed")

            return Path(output_path)

        except ACSMFulfillmentError:
            raise
        except Exception as e:
            raise ACSMFulfillmentError(f"ACSM processing failed: {e}")
