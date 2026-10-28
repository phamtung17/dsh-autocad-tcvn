"""Cross-discipline completeness gate (input presence only, NOT engineering verification)."""
from __future__ import annotations
from .schema import validate_job

REQUIREMENTS={
  'mechanical':('material','tolerance_basis','manufacturing_process'),
  'architectural':('occupancy','site_constraints','egress_review'),
  'structural':('load_case_reference','design_calculation_reference','material_grade'),
  'electrical':('voltage','load_schedule_reference','protective_device_study'),
  'hvac':('airflow_calculation_reference','heat_load_reference','equipment_schedule'),
  'plumbing':('flow_calculation_reference','pipe_material','slope_or_pressure_basis'),
  'mep':('coordination_reference','equipment_schedule','calculation_reference'),
  'civil':('survey_reference','coordinate_system','vertical_datum'),
  'fire_safety':('fire_risk_classification','egress_review','fire_engineer_approval'),
  'general':('design_basis_reference',)
}

def review(job):
    job=validate_job(job)
    data=job.get('engineering_inputs',{})
    # Schema rejects oversized/unstructured records; see schema.validate_job.
    required=REQUIREMENTS[job['discipline']]
    items=[{'field':name,'status':'DECLARED_UNVERIFIED' if data.get(name) else 'MISSING'} for name in required]
    missing=[row['field'] for row in items if row['status']=='MISSING']
    return {'discipline':job['discipline'],'purpose':job['purpose'],
            'status':'CONCEPT_ONLY' if job['purpose']=='concept_only' else 'INCOMPLETE' if missing else 'NEEDS_ENGINEER_VERIFICATION',
            'requirements':items,'missing':missing,
            'gate':'NOT_APPROVED','note':'Presence of an input/reference does not validate calculations or official standards.'}
