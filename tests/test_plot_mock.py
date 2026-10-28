"""Plot API orchestration mocked; does not prove AutoCAD 2025 rendering."""
from pathlib import Path
from unittest.mock import patch
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from autocad_agent.templates import create_template
from autocad_agent.schema import validate_job
from autocad_agent.plotting import choose_media,configure_layout_and_pdf

class MockLayout:
    def __init__(self):
        self.Name='CAD_AGENT_SHEET'
        self.ConfigName='';self.CanonicalMediaName='';self.PlotRotation=None
        self.PaperUnits=None;self.PlotType=None;self.UseStandardScale=None
        self.StandardScale=None;self.CenterPlot=None
    def RefreshPlotDeviceInfo(self):return None
    def GetCanonicalMediaNames(self):return ['ISO_A3_(420.00_x_297.00_MM)','ISO_A4_(297.00_x_210.00_MM)']
    def GetPaperSize(self):
        return (420.,297.) if 'A3' in self.CanonicalMediaName else (297.,210.)
    def GetPlotStyleTableNames(self):return ['monochrome.ctb']
    def GetPaperMargins(self):return ((0.,0.),(0.,0.))

class MockViewport:
    def __init__(self):self.on=False
    def Display(self,on):self.on=on

class MockPaper:
    Count=0
    def __init__(self):self.ports=[]
    def AddPViewport(self,center,width,height):
        port=MockViewport();self.ports.append((center,width,height,port));return port

class MockLayouts:
    def Add(self,name):return MockLayout()
    def __iter__(self):return iter([])

class MockPlot:
    def __init__(self,doc):self.doc=doc
    def PlotToFile(self,name):
        w,h=(420*mm,297*mm)
        c=canvas.Canvas(name,pagesize=(w,h));c.drawString(10,100,'mock plot');c.showPage();c.save()
        return True

class MockDoc:
    def __init__(self):
        self.Layouts=MockLayouts();self.PaperSpace=MockPaper();self.Plot=MockPlot(self)
        self.state={'BACKGROUNDPLOT':1}
        self.rebuilt=False
        from types import SimpleNamespace
        self.Layers=SimpleNamespace(Add=lambda name:SimpleNamespace())
        self.Application=SimpleNamespace(ZoomCenter=lambda point,height:None)
    def GetVariable(self,name):return self.state[name]
    def SetVariable(self,name,value):self.state[name]=value
    def Regen(self,mode):self.rebuilt=True


def test_media_selected_by_dimensions():
    layout=MockLayout()
    with patch('autocad_agent.plotting._constant',return_value=0):
        got=choose_media(layout,(420,297),'A3')
    assert got['native_size_mm']==(420,297)
    assert 'A3' in got['canonical_name']


def test_mock_full_plot_and_pdf_validation(tmp_path):
    job=create_template('mechanical',width=200,height=100)
    job['plot']={'enabled':True,'pdf':True,'ctb':'monochrome.ctb'}
    job=validate_job(job)
    doc=MockDoc()
    flag=[]
    enum={'acPaperSpace':0,'acVpCustomScale':0,'ac0degrees':0,'acMillimeters':1,
          'acLayout':5,'ac1_1':16,'acAllViewports':1,'ac90degrees':1}
    with patch('autocad_agent.plotting._constant',side_effect=lambda name:enum[name]):
        output=configure_layout_and_pdf(doc,job,tmp_path/'plot.pdf',lambda p:p,lambda fn:fn(),lambda:flag.append('saved'))
    assert output['status']=='AUTOCAD_PDF_PAGE_SIZE_CHECKED_NEEDS_VISUAL_REVIEW'
    assert output['pdf_size_mm']==[420.,297.]
    assert flag==['saved']
    assert doc.rebuilt
    assert doc.state['BACKGROUNDPLOT']==1
    assert doc.PaperSpace.ports[0][-1].CustomScale==pytest.approx(1.)
    assert doc.PaperSpace.ports[0][-1].DisplayLocked


def test_mock_plot_fails_if_ctb_missing(tmp_path):
    job=create_template('mechanical');job['plot']={'enabled':True,'pdf':True,'ctb':'absent.ctb'}
    with patch('autocad_agent.plotting._constant',return_value=0):
        with pytest.raises(RuntimeError,match='CTB not installed'):
            configure_layout_and_pdf(MockDoc(),validate_job(job),tmp_path/'bad.pdf',lambda p:p,lambda fn:fn())


def test_mock_plot_fails_wrong_paper_size():
    layout=MockLayout()
    with patch('autocad_agent.plotting._constant',return_value=0):
        with pytest.raises(RuntimeError,match='No installed PDF canonical media'):
            choose_media(layout,(1189,841),'A0')
