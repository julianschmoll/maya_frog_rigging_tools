from pathlib import Path
import logging
from pymel import core as pm

from maya_frog_rigging_tools.limb_setup import LOGGER

LOGGER = logging.getLogger("Rigging Utils")


def get_project_root():
    return Path(__file__).parent.parent


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


def get_center(translations):
    x_sum, y_sum, z_sum = 0, 0, 0
    num_translations = len(translations)

    for x, y, z in translations:
        x_sum += x
        y_sum += y
        z_sum += z

    center_x = x_sum / num_translations
    center_y = y_sum / num_translations
    center_z = z_sum / num_translations

    return center_x, center_y, center_z


def match_transforms(source_obj, target_obj, **kwargs):
    LOGGER.info(f"Matching transforms of {source_obj} to {target_obj}")
    constraint = pm.parentConstraint(source_obj, target_obj, **kwargs)
    pm.delete(constraint)
