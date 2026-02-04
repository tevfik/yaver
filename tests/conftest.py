import pytest
from pathlib import Path
import shutil
import tempfile
import sys

# Ensure src is in python path
sys.path.append(str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_repo_path():
    """Return path to the sample python repo data"""
    return Path(__file__).parent / "data" / "sample_python_repo"


@pytest.fixture
def mock_session_id():
    return "test-session-123"


@pytest.fixture
def analysis_session(temp_workspace, mock_session_id):
    """Create a real AnalysisSession instance in a temp dir"""
    from core.analysis_session import AnalysisSession

    session = AnalysisSession(mock_session_id, base_dir=temp_workspace)
    return session
