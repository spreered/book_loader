"""
Adobe 帳號授權管理
"""

import base64
from pathlib import Path
from lxml import etree

from ...utils.errors import AuthorizationError


class AdobeAccount:
    """管理 Adobe 授權流程"""

    def __init__(self, auth_dir: Path):
        """
        Args:
            auth_dir: 授權檔案儲存目錄（~/.config/book-loader/.adobe/）
        """
        self.auth_dir = auth_dir
        self.auth_dir.mkdir(parents=True, exist_ok=True)

        self.activation_xml = auth_dir / "activation.xml"
        self.device_xml = auth_dir / "device.xml"
        self.devicesalt = auth_dir / "devicesalt"

    def is_authorized(self) -> bool:
        """檢查是否已授權"""
        return all(
            [
                self.activation_xml.exists(),
                self.device_xml.exists(),
                self.devicesalt.exists(),
            ]
        )

    def get_auth_type(self) -> str:
        """
        取得授權類型：'anonymous' 或 'AdobeID'

        Returns:
            授權類型字串
        """
        if not self.is_authorized():
            return "none"

        try:
            tree = etree.parse(str(self.activation_xml))
            root = tree.getroot()
            # 查找 <credentials method="...">
            credentials = root.find(".//{http://ns.adobe.com/adept}credentials")
            if credentials is not None:
                method = credentials.get("method", "anonymous")
                return method
            return "anonymous"
        except Exception:
            return "unknown"

    def authorize_anonymous(self) -> None:
        """執行匿名授權（預設方式）"""
        try:
            # 設定授權目錄路徑
            from . import libadobe
            from . import libadobeAccount

            libadobe.update_account_path(str(self.auth_dir))

            # 執行五步驟授權流程
            libadobeAccount.createDeviceKeyFile()
            libadobeAccount.createDeviceFile(randomSerial=True, useVersionIndex=1)
            libadobeAccount.createUser(useVersionIndex=1)
            success = libadobeAccount.signIn("anonymous", "", "")
            if not success:
                raise AuthorizationError("匿名授權失敗")
            libadobeAccount.activateDevice(useVersionIndex=1)

        except Exception as e:
            raise AuthorizationError(f"匿名授權失敗: {e}")

    def authorize_adobe_id(self, email: str, password: str) -> None:
        """
        執行 Adobe ID 授權（需要帳號密碼）

        Args:
            email: Adobe ID 帳號（email）
            password: Adobe ID 密碼
        """
        try:
            # 設定授權目錄路徑
            from . import libadobe
            from . import libadobeAccount

            libadobe.update_account_path(str(self.auth_dir))

            # 執行五步驟授權流程
            libadobeAccount.createDeviceKeyFile()
            libadobeAccount.createDeviceFile(randomSerial=True, useVersionIndex=1)
            libadobeAccount.createUser(useVersionIndex=1)
            success = libadobeAccount.signIn("AdobeID", email, password)
            if not success:
                raise AuthorizationError("Adobe ID 授權失敗：請檢查帳號密碼")
            libadobeAccount.activateDevice(useVersionIndex=1)

        except Exception as e:
            raise AuthorizationError(f"Adobe ID 授權失敗: {e}")

    def get_device_key(self) -> bytes:
        """
        從 activation.xml 提取 RSA 私鑰（DER 格式）

        Returns:
            RSA 私鑰（bytes，DER 格式）供 DRM 移除使用
        """
        if not self.activation_xml.exists():
            raise AuthorizationError("授權檔案不存在，請先執行授權")

        try:
            tree = etree.parse(str(self.activation_xml))
            root = tree.getroot()

            # 查找 <privateLicenseKey>
            key_element = root.find(
                ".//{http://ns.adobe.com/adept}privateLicenseKey"
            )
            if key_element is None or not key_element.text:
                raise AuthorizationError("無法從授權檔案中提取私鑰")

            # Base64 解碼
            key_b64 = key_element.text.strip()
            key_der = base64.b64decode(key_b64)

            return key_der

        except Exception as e:
            raise AuthorizationError(f"提取私鑰失敗: {e}")

    def reset(self) -> None:
        """重置授權（刪除所有授權檔案）"""
        for file in [self.activation_xml, self.device_xml, self.devicesalt]:
            if file.exists():
                file.unlink()
