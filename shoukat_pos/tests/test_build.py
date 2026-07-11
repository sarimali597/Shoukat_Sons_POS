"""
Smoke tests for the PyInstaller build process.

These tests verify:
- Spec file syntax is valid
- Required files exist for building
- Build configuration is correct

Note: Actual executable building requires Windows and is not tested here.
"""

import ast
from pathlib import Path

import pytest


class TestSpecFileSyntax:
    """Test that the PyInstaller spec file has valid Python syntax."""

    def test_spec_file_exists(self) -> None:
        """Test that ShoukatPOS.spec exists in project root."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        assert spec_file.exists(), f"Spec file not found at {spec_file}"

    def test_spec_file_valid_python(self) -> None:
        """Test that the spec file contains valid Python syntax."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        
        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # This will raise SyntaxError if the file is not valid Python
        ast.parse(content)

    def test_spec_file_contains_analysis(self) -> None:
        """Test that the spec file defines an Analysis object."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        
        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "Analysis(" in content, "Spec file should contain Analysis definition"

    def test_spec_file_contains_exe(self) -> None:
        """Test that the spec file defines an EXE object."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        
        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "EXE(" in content, "Spec file should contain EXE definition"

    def test_spec_file_uses_onedir_mode(self) -> None:
        """Test that the spec file does NOT use onefile mode in actual configuration."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        
        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # The spec should not have onefile=True or --onefile as an active option
        # Comments mentioning onefile are OK, but not actual configuration
        lines = content.split('\n')
        for line in lines:
            # Skip comments
            if line.strip().startswith('#'):
                continue
            # Check that onefile is not set to True
            assert 'onefile=True' not in line.lower(), (
                "Spec file should NOT use onefile=True (AV false positive risk)"
            )

    def test_spec_file_includes_hiddenimports(self) -> None:
        """Test that the spec file includes required hidden imports."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        
        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        required_imports = [
            "customtkinter",
            "tksheet",
            "PIL",
            "bcrypt",
        ]
        
        for imp in required_imports:
            assert imp in content, f"Spec file should include '{imp}' in hiddenimports"

    def test_spec_file_includes_datas(self) -> None:
        """Test that the spec file includes required data files."""
        project_root = Path(__file__).parent.parent.parent
        spec_file = project_root / "ShoukatPOS.spec"
        
        with open(spec_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "assets" in content, "Spec file should include assets directory"
        assert "migrations" in content, "Spec file should include migrations directory"


class TestBuildScript:
    """Test the Windows build script."""

    def test_build_script_exists(self) -> None:
        """Test that build.bat exists in project root."""
        project_root = Path(__file__).parent.parent.parent
        build_script = project_root / "build.bat"
        assert build_script.exists(), f"Build script not found at {build_script}"

    def test_build_script_uses_spec_file(self) -> None:
        """Test that build.bat references the spec file."""
        project_root = Path(__file__).parent.parent.parent
        build_script = project_root / "build.bat"
        
        with open(build_script, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "ShoukatPOS.spec" in content, "Build script should reference spec file"

    def test_build_script_mentions_onedir(self) -> None:
        """Test that build.bat mentions onedir mode in comments."""
        project_root = Path(__file__).parent.parent.parent
        build_script = project_root / "build.bat"
        
        with open(build_script, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Should mention onedir somewhere (in comments or commands)
        assert "onedir" in content.lower() or "--windowed" in content, (
            "Build script should mention onedir/windowed mode"
        )


class TestInstallerScript:
    """Test the Inno Setup installer script."""

    def test_installer_script_exists(self) -> None:
        """Test that installer.iss exists in project root."""
        project_root = Path(__file__).parent.parent.parent
        installer_script = project_root / "installer.iss"
        assert installer_script.exists(), f"Installer script not found at {installer_script}"

    def test_installer_script_has_app_name(self) -> None:
        """Test that installer.iss defines the application name."""
        project_root = Path(__file__).parent.parent.parent
        installer_script = project_root / "installer.iss"
        
        with open(installer_script, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "AppName=" in content, "Installer script should define AppName"
        assert "Shoukat" in content, "Installer script should reference Shoukat POS"

    def test_installer_script_references_executable(self) -> None:
        """Test that installer.iss references the built executable."""
        project_root = Path(__file__).parent.parent.parent
        installer_script = project_root / "installer.iss"
        
        with open(installer_script, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "ShoukatPOS.exe" in content, (
            "Installer script should reference ShoukatPOS.exe"
        )


class TestDeploymentDocumentation:
    """Test deployment documentation exists and is complete."""

    def test_deployment_guide_exists(self) -> None:
        """Test that DEPLOYMENT.md exists in project root."""
        project_root = Path(__file__).parent.parent.parent
        deployment_guide = project_root / "DEPLOYMENT.md"
        assert deployment_guide.exists(), f"Deployment guide not found at {deployment_guide}"

    def test_deployment_guide_has_checklist(self) -> None:
        """Test that DEPLOYMENT.md includes deployment checklist."""
        project_root = Path(__file__).parent.parent.parent
        deployment_guide = project_root / "DEPLOYMENT.md"
        
        with open(deployment_guide, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "Checklist" in content or "checklist" in content, (
            "Deployment guide should include a checklist"
        )

    def test_deployment_guide_has_troubleshooting(self) -> None:
        """Test that DEPLOYMENT.md includes troubleshooting section."""
        project_root = Path(__file__).parent.parent.parent
        deployment_guide = project_root / "DEPLOYMENT.md"
        
        with open(deployment_guide, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "roubleshoot" in content.lower(), (
            "Deployment guide should include troubleshooting section"
        )

    def test_deployment_guide_mentions_code_signing(self) -> None:
        """Test that DEPLOYMENT.md mentions code signing."""
        project_root = Path(__file__).parent.parent.parent
        deployment_guide = project_root / "DEPLOYMENT.md"
        
        with open(deployment_guide, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "sign" in content.lower(), (
            "Deployment guide should mention code signing"
        )


class TestUpdateVerifierIntegration:
    """Test that update verifier is properly integrated."""

    def test_update_verifier_module_exists(self) -> None:
        """Test that update_verifier.py exists."""
        utils_dir = Path(__file__).parent.parent / "utils"
        update_verifier = utils_dir / "update_verifier.py"
        assert update_verifier.exists(), f"Update verifier not found at {update_verifier}"

    def test_update_verifier_has_update_checker_class(self) -> None:
        """Test that update_verifier.py defines UpdateChecker class."""
        utils_dir = Path(__file__).parent.parent / "utils"
        update_verifier = utils_dir / "update_verifier.py"
        
        with open(update_verifier, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "class UpdateChecker" in content, (
            "Update verifier should define UpdateChecker class"
        )

    def test_update_verifier_has_sha256_verification(self) -> None:
        """Test that update_verifier.py includes SHA-256 verification."""
        utils_dir = Path(__file__).parent.parent / "utils"
        update_verifier = utils_dir / "update_verifier.py"
        
        with open(update_verifier, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "sha256" in content.lower(), (
            "Update verifier should include SHA-256 verification"
        )
        assert "hashlib" in content, (
            "Update verifier should import hashlib"
        )
