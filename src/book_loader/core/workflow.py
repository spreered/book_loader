"""
Main workflow orchestration.
"""

from pathlib import Path
from .adobe import AdobeAccount, ACSMFulfiller
from .drm import DRMRemover
from .conversion import ConversionEngine
from ..utils.config import Config
from ..utils.errors import WorkflowError


class BookLoader:
    """Main ebook loading workflow."""

    def __init__(self, config: Config):
        self.config = config
        self.account = AdobeAccount(config.auth_dir)
        self.fulfiller = ACSMFulfiller(self.account)
        self.drm_remover = DRMRemover()

    def process_acsm(
        self,
        acsm_path: Path,
        output_dir: Path,
        optimize: bool = False,
        to_pdf: bool = False,
        convert_engine: str = "python",
        keep_encrypted: bool = False,
    ) -> Path:
        """
        Complete processing workflow.

        Args:
            acsm_path: ACSM file path
            output_dir: Output directory
            optimize: Whether to optimize EPUB (not yet implemented)
            to_pdf: Whether to convert to PDF
            convert_engine: PDF conversion engine ('python' or 'calibre')
            keep_encrypted: Whether to keep encrypted file

        Returns:
            Final output file path
        """
        # 1. Ensure authorization
        if not self.account.is_authorized():
            print("First-time use, creating anonymous authorization...")
            self.account.authorize_anonymous()
            print("✓ Authorization complete")

        # 2. Fulfill ACSM, download encrypted file
        print("Downloading encrypted file...")
        temp_dir = output_dir / ".temp"
        encrypted_path = self.fulfiller.fulfill(acsm_path, temp_dir)
        print(f"✓ Downloaded: {encrypted_path.name}")

        # 3. Remove DRM
        print("Removing DRM...")
        decrypted_path = output_dir / encrypted_path.name
        user_key = self.account.get_device_key()
        self.drm_remover.remove_drm(encrypted_path, decrypted_path, user_key)
        print(f"✓ DRM removed: {decrypted_path.name}")

        # Clean up encrypted file if not keeping intermediate files
        # Note: keep_encrypted controls deletion of both encrypted source and intermediate files
        if not keep_encrypted:
            encrypted_path.unlink()
            # Clean up temporary directory
            try:
                temp_dir.rmdir()
            except OSError:
                pass

        current_path = decrypted_path

        # 4. Optional: Optimize EPUB
        if optimize and current_path.suffix == ".epub":
            print("Optimization feature not yet implemented")
            # TODO: Implement optimization feature

        # 5. Optional: Convert to PDF
        if to_pdf and current_path.suffix == ".epub":
            print(f"\nConverting to PDF (using {convert_engine} engine)...")
            pdf_path = current_path.with_suffix(".pdf")

            try:
                engine = ConversionEngine(engine=convert_engine)
                engine.convert_epub_to_pdf(current_path, pdf_path)

                # Delete intermediate decrypted EPUB after PDF conversion (controlled by keep_encrypted flag)
                # Note: current_path here is the decrypted EPUB, not the encrypted file
                if not keep_encrypted:
                    current_path.unlink()

                current_path = pdf_path
            except Exception as e:
                print(f"⚠ PDF conversion failed: {e}")
                print(f"Keeping EPUB file: {current_path}")

        return current_path
