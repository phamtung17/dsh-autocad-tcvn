"""Select the detailed generator without changing legacy studio inputs."""
def build_project(spec):
    if isinstance(spec,dict) and spec.get('engine')=='building_v1':
        from .building_design import build_building_set
        return build_building_set(spec)
    from .fitout_design import build_studio_set
    return build_studio_set(spec)

def project_quantities(project):
    if 'takeoff' in project:return project['takeoff']
    from .fitout_design import quantities
    return quantities(project['spec'])
