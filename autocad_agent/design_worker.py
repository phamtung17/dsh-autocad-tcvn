"""STA worker accepts signed one-use design permits only."""
import json,sys
from .design_runtime import consume_design_permit
from .detailed_publish import publish_new_design
if __name__=='__main__':
    try:
        value=consume_design_permit(sys.argv[1]);result=publish_new_design(value['spec'],value['branding'])
    except Exception as exc:result={'status':'FAIL','error':str(exc)}
    print(json.dumps(result,ensure_ascii=True))
