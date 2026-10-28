"""Mock COM protocol tests; MUST NOT be mistaken for actual AutoCAD integration tests."""
import sys,types,pytest
from autocad_agent.templates import create_template
from autocad_agent.cad_com import create_dwg
from autocad_agent.runtime import workspace

class Obj:
    def __init__(self):self.Layer='0';self.Rotation=0;self.Closed=False;self.Height=1

class Space:
    def __init__(self):self.calls=[]
    def __getattr__(self,k):
        if k.startswith('Add') or k=='InsertBlock':
            def create(*args,**kw):
                self.calls.append((k,args));return Obj()
            return create
        raise AttributeError(k)

class Layers(list):
    @property
    def Count(self):return len(self)
    def Item(self,i):return self[i]
    def Add(self,name):
        layer=types.SimpleNamespace(Name=name)
        self.append(layer);return layer

class Blocks:
    def __init__(self):self.created={}
    def Add(self,base,name):
        obj=Space();self.created[name]=obj;return obj

class Doc:
    def __init__(self):
        self.ModelSpace=Space();self.Layers=Layers([types.SimpleNamespace(Name='0')]);self.Blocks=Blocks();self.vars={}
        self.TextStyles=types.SimpleNamespace(Item=lambda name:Obj())
        self.Linetypes=types.SimpleNamespace(Item=lambda name:Obj())
    def SetVariable(self,k,v):self.vars[k]=v
    def SaveAs(self,path):
        from pathlib import Path
        Path(path).write_bytes(b'AC1027'+b'0'*300)

class App:
    Version='25.0';Name='AutoCAD'
    def __init__(self):
        self.created=[];self.Documents=self
    def Add(self):
        doc=Doc();self.created.append(doc);return doc

@pytest.fixture()
def fake_com(monkeypatch,tmp_path):
    system=tmp_path/'windows';(system/'Fonts').mkdir(parents=True)
    (system/'Fonts'/'arial.ttf').write_bytes(b'mock-font-path-only')
    monkeypatch.setenv('WINDIR',str(system))
    pythoncom=types.ModuleType('pythoncom')
    pythoncom.VT_ARRAY=1;pythoncom.VT_R8=2;pythoncom.CoInitialize=lambda:None;pythoncom.CoUninitialize=lambda:None
    pythoncom.PumpWaitingMessages=lambda:None
    pywintypes=types.ModuleType('pywintypes');pywintypes.com_error=type('com_error',(Exception,),{})
    client=types.ModuleType('win32com.client');app=App()
    client.GetActiveObject=lambda progid:app;client.VARIANT=lambda _,coords:coords
    client.gencache=types.SimpleNamespace(EnsureDispatch=lambda obj:obj)
    parent=types.ModuleType('win32com');parent.client=client
    monkeypatch.setitem(sys.modules,'pythoncom',pythoncom)
    monkeypatch.setitem(sys.modules,'pywintypes',pywintypes)
    monkeypatch.setitem(sys.modules,'win32com',parent)
    monkeypatch.setitem(sys.modules,'win32com.client',client)
    monkeypatch.setenv('CAD_OUTPUT_DIR',str(tmp_path))
    home=workspace()
    return app,home

def test_com_new_dwg_and_dimensions_mock(fake_com):
    app,home=fake_com
    job=create_template('mechanical',name='mock_plate.dwg')
    result=create_dwg(job,home)
    doc=app.created[0]
    assert result['status']=='DWG_CREATED_NEEDS_VISUAL_REVIEW'
    assert (home/'mock_plate.dwg').exists()
    assert doc.vars['INSUNITS']==4
    called=[item[0] for item in doc.ModelSpace.calls]
    assert 'AddDimAligned' in called
    assert 'AddDimDiametric' in called
    assert 'AddLightWeightPolyline' in called
    assert 'AddCircle' in called

def test_com_block_insert_mock(fake_com):
    app,home=fake_com
    job=create_template('mechanical',name='block_test.dwg')
    job['blocks']=[{'name':'BTEST','entities':[{'id':'l','type':'line','layer':'0','start':[0,0],'end':[1,0]}]}]
    job['geometry'].append({'id':'ib','layer':'M-BLOCK','type':'insert','block':'BTEST','position':[10,10]})
    result=create_dwg(job,home)
    assert result['status']=='DWG_CREATED_NEEDS_VISUAL_REVIEW'
    assert 'BTEST' in app.created[0].Blocks.created
    assert any(c[0]=='InsertBlock' for c in app.created[0].ModelSpace.calls)

def test_com_refuses_wrong_autocad_version(fake_com):
    app,home=fake_com;app.Version='24.3'
    with pytest.raises(RuntimeError,match='AutoCAD 2025 expected'):
        create_dwg(create_template('mechanical'),home)
    assert not app.created


def test_com_normalized_block_entity_with_no_explicit_layer(fake_com):
    app,home=fake_com
    job=create_template('mechanical',name='block_default_layer.dwg')
    job['blocks']=[{'name':'TESTBLOCK','entities':[{'id':'no-layer','type':'line','start':[0,0],'end':[2,0]}]}]
    job['geometry'].append({'id':'new-insert','type':'insert','layer':'M-BLOCK','block':'TESTBLOCK','position':[25,25]})
    result=create_dwg(job,home)
    assert result['status']=='DWG_CREATED_NEEDS_VISUAL_REVIEW'
    assert (home/'block_default_layer.dwg').exists()
