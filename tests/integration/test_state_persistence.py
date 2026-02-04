def test_analysis_session_init(analysis_session):
    """Test that session files are created on initialization"""
    assert analysis_session.plan_file.exists()
    assert analysis_session.findings_file.exists()
    assert analysis_session.progress_file.exists()

    # Check default content
    assert "# Task Plan" in analysis_session.plan_file.read_text()


def test_plan_update(analysis_session):
    """Test updating the task plan"""
    new_plan = "# Updated Plan\n- [x] Done"
    analysis_session.update_plan(new_plan)
    assert analysis_session.read_plan() == new_plan


def test_logging(analysis_session):
    """Test logging to findings and progress files"""
    # Log progress
    analysis_session.log_progress("Starting step 1")
    progress_content = analysis_session.progress_file.read_text()
    assert "Starting step 1" in progress_content
    assert "[`EXEC`]" in progress_content

    # Log finding
    analysis_session.log_finding("Bug Found", "Description of bug", "RISK")
    findings_content = analysis_session.findings_file.read_text()
    assert "[RISK] Bug Found" in findings_content
    assert "Description of bug" in findings_content
