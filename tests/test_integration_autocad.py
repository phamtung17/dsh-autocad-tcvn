"""Opt-in REAL AutoCAD regression; CI runs only the offline mock suite."""
import os
import sys
import pytest

@pytest.mark.autocad_real
def test_windows_autocad_2025_end_to_end():
    if sys.platform!='win32' or os.getenv('CAD_REAL_AUTOCAD_TEST')!='1':
        pytest.skip('Run explicitly on Windows with CAD_REAL_AUTOCAD_TEST=1 and AutoCAD 2025 open')
    from tools.autocad_2025_regression import run
    assert run(pdf=os.getenv('CAD_REAL_PDF_TEST')=='1')['status']=='REAL_AUTOCAD_2025_REGRESSION_PASS_REQUIRES_VISUAL_REVIEW'
