from pathlib import Path
import logging
from pymel import core as pm

LOGGER = logging.getLogger("Rigging Utils")


def get_project_root():
    return Path(__file__).parent.parent


def match_transforms(source_obj, target_obj, **kwargs):
    LOGGER.info(f"Matching transforms of {source_obj} to {target_obj}")
    constraint = pm.parentConstraint(source_obj, target_obj, **kwargs)
    pm.delete(constraint)


def align_center(obj1, obj2, obj3):
    matrix_1 = pm.xform(obj1, query=True, worldSpace=True, matrix=True)
    matrix_2 = pm.xform(obj2, query=True, worldSpace=True, matrix=True)
    center_matrix = []

    for index, pnt1 in enumerate(matrix_1):
        pnt2 = matrix_2[index]
        diff = (abs(pnt1) + abs(pnt2)) / 2
        pnt3 = min(pnt1, pnt2) + diff
        center_matrix.append(pnt3)

    pm.xform(obj3, worldSpace=True, matrix=center_matrix)