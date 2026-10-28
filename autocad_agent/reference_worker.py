"""STA worker accepts signed permits only; no arbitrary job files or paths."""
import json
import sys
from .reference_runtime import consume_reference_permit
from .reference_publish import publish_reference

if __name__=='__main__':
    try:
        job=consume_reference_permit(sys.argv[1])
        result=publish_reference(job)
    except Exception as exc:result={'status':'FAIL','error':str(exc)}
    print(json.dumps(result,ensure_ascii=True))
