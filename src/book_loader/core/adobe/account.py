"""
Adobe account authorization management.
"""

import base64
from pathlib import Path
from lxml import etree

from ...utils.errors import AuthorizationError


class AdobeAccount:
    """Manages Adobe authorization workflow."""

    def __init__(self, auth_dir: Path):
        """
        Args:
            auth_dir: Authorization file storage directory (~/.config/book-loader/.adobe/)
        """
        self.auth_dir = auth_dir
        self.auth_dir.mkdir(parents=True, exist_ok=True)

        self.activation_xml = auth_dir / "activation.xml"
        self.activation_dat = auth_dir / "activation.dat"  # ADE format
        self.device_xml = auth_dir / "device.xml"
        self.devicesalt = auth_dir / "devicesalt"

    def is_authorized(self) -> bool:
        """Check if already authorized (supports standard and ADE formats)."""
        # Standard format: all three files must exist
        standard_format = all(
            [
                self.activation_xml.exists(),
                self.device_xml.exists(),
                self.devicesalt.exists(),
            ]
        )
        # ADE format: only activation.dat is needed
        ade_format = self.activation_dat.exists()

        return standard_format or ade_format

    def get_auth_type(self) -> str:
        """
        Get authorization type: 'anonymous' or 'AdobeID'.

        Returns:
            Authorization type string
        """
        if not self.is_authorized():
            return "none"

        try:
            tree = etree.parse(str(self.activation_xml))
            root = tree.getroot()
            # Find <username method="..."> element (Adobe ID stores method here)
            username = root.find(".//{http://ns.adobe.com/adept}username")
            if username is not None:
                method = username.get("method")
                if method:
                    return method
            # Fallback to anonymous if no method attribute found
            return "anonymous"
        except Exception:
            return "unknown"

    def authorize_anonymous(self) -> None:
        """Execute anonymous authorization (default method)."""
        try:
            # Set authorization directory path
            from . import libadobe
            from . import libadobeAccount

            libadobe.update_account_path(str(self.auth_dir))

            # Execute five-step authorization process
            libadobe.createDeviceKeyFile()
            libadobeAccount.createDeviceFile(randomSerial=True, useVersionIndex=1)
            libadobeAccount.createUser(useVersionIndex=1)
            success = libadobeAccount.signIn("anonymous", "", "")
            if not success:
                raise AuthorizationError("Anonymous authorization failed")
            libadobeAccount.activateDevice(useVersionIndex=1)

        except Exception as e:
            raise AuthorizationError(f"Anonymous authorization failed: {e}")

    def authorize_adobe_id(self, email: str, password: str) -> None:
        """
        Execute Adobe ID authorization (requires account credentials).

        Args:
            email: Adobe ID account (email)
            password: Adobe ID password
        """
        try:
            # Set authorization directory path
            from . import libadobe
            from . import libadobeAccount

            libadobe.update_account_path(str(self.auth_dir))

            # Execute five-step authorization process
            libadobe.createDeviceKeyFile()
            libadobeAccount.createDeviceFile(randomSerial=True, useVersionIndex=1)
            libadobeAccount.createUser(useVersionIndex=1)
            success = libadobeAccount.signIn("AdobeID", email, password)
            if not success:
                raise AuthorizationError("Adobe ID authorization failed: Please check credentials")
            libadobeAccount.activateDevice(useVersionIndex=1)

        except Exception as e:
            raise AuthorizationError(f"Adobe ID authorization failed: {e}")

    def get_device_key(self) -> bytes:
        """
        Extract RSA private key (DER format) from activation.xml.

        Returns:
            RSA private key (bytes, DER format) for DRM removal
        """
        if not self.activation_xml.exists():
            raise AuthorizationError("Authorization file not found, please authorize first")

        try:
            tree = etree.parse(str(self.activation_xml))
            root = tree.getroot()

            # Find <privateLicenseKey>
            key_element = root.find(
                ".//{http://ns.adobe.com/adept}privateLicenseKey"
            )
            if key_element is None or not key_element.text:
                raise AuthorizationError("Cannot extract private key from authorization file")

            # Base64 decode
            key_b64 = key_element.text.strip()
            key_der = base64.b64decode(key_b64)

            return key_der

        except Exception as e:
            raise AuthorizationError(f"Failed to extract private key: {e}")

    def reset(self) -> None:
        """Reset authorization (delete all authorization files)."""
        for file in [self.activation_xml, self.activation_dat, self.device_xml, self.devicesalt]:
            if file.exists():
                file.unlink()
