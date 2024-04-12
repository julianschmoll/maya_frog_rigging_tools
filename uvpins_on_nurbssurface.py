import pymel.core as pm


def create_uvpins(rbbn_transform, u_min: int, u_max:int , v_min: int, v_max: int, num_pins_u: int, num_pins_v: int):
    u_range = u_max - u_min
    v_range = v_max - v_min
    is_one_u = False
    is_one_v = False
    
    try:
        u_step_width = u_range / (num_pins_u - 1)
    except: 
        is_one_u = True
        u_step_width = 0.5

    try:
        v_step_width = v_range / (num_pins_v - 1)
    except:
        is_one_v = True 
        v_step_width = 0.5

    rbbn_shapes = rbbn_transform.getShapes()
    
    rbbn_shape = [s for s in rbbn_shapes if not s.intermediateObject.get()][0]
    try:
        rbbn_orig_shape = [s for s in rbbn_shapes if s.intermediateObject.get()][0]
    except IndexError:
        raise ValueError(f"No intermediate Object found for {rbbn_shapes}")
    
    uv_pin = pm.createNode("uvPin", n=f"{rbbn_transform.name()}_uvPin")

    rbbn_shape.attr("worldSpace[0]") >> uv_pin.deformedGeometry
    rbbn_orig_shape.attr("worldSpace[0]") >> uv_pin.originalGeometry

    grps = []

    print(f"{u_step_width}__{v_step_width}")
    tempInt = 0
    for u_index in range(num_pins_u):       
        for v_index in range (num_pins_v):
            grp = pm.group(empty=True)
            grp.rename(f"{rbbn_transform.name()}_{u_index}_{v_index}_grp")
            grps.append(grp)
            uv_pin.attr(f"outputMatrix[{tempInt}]") >> grp.offsetParentMatrix           
            uv_pin.attr(f"coordinate[{tempInt}]").set(u_min + u_index * u_step_width, v_min + v_index * v_step_width)           
            tempInt += 1

    return uv_pin, grps


uv_pin, grps = create_uvpins(pm.selected()[0], 0,1,0,1,3,5)

for index, grp in enumerate(grps):
    pm.joint(grp, n = f"{grp.name()}_bnd")