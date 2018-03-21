from utils import error_rates
import copy
import os
import cv2
import json

from copy import deepcopy

import numpy as np

def interpolate(key1, key2, lf, lf_idx, step_percent):
    x0 = lf[lf_idx][key1]
    y0 = lf[lf_idx][key2]
    x1 = lf[lf_idx+1][key1]
    y1 = lf[lf_idx+1][key2]

    x = x1 * step_percent + x0 * (1.0 - step_percent)
    y = y1 * step_percent + y0 * (1.0 - step_percent)

    return x, y

def get_subdivide_pt(i, pred_full, lf):
    percent = (float(i)+0.5) / float(len(pred_full))
    lf_percent = (len(lf)-1) * percent

    lf_idx = int(np.floor(lf_percent))
    step_percent = lf_percent - lf_idx

    x0, y0 = interpolate("x0", "y0", lf, lf_idx, step_percent)
    x1, y1 = interpolate("x1", "y1", lf, lf_idx, step_percent)

    return x0, y0, x1, y1

def save_improved_idxs(improved_idxs, decoded_hw, decoded_raw_hw, out, x, json_folder, trim_to_sol):

    output_lines = [{
        "gt": gt['gt']
    } for gt in x['gt_json']]


    # for i in improved_idxs:
    for i in xrange(len(output_lines)):

        if not i in improved_idxs:
            output_lines[i] = x['gt_json'][i]
            continue

        k = improved_idxs[i]

        line_points = []
        lf_path = out['lf']
        for j in xrange(len(lf_path)):
            p = lf_path[j][k]
            s = out['results_scale']

            line_points.append({
                "x0": p[0][1] * s,
                "x1": p[0][0] * s,
                "y0": p[1][1] * s,
                "y1": p[1][0] * s
            })



        pred_full = decoded_raw_hw[k]
        first_idx = 0
        for l_idx in range(len(pred_full)):
            if pred_full[l_idx] != "~":
                first_idx = l_idx
                break

        sol_point = deepcopy(line_points[1])#TODO: update to backward idx

        if trim_to_sol:
            if first_idx != 0:
                x0, y0, x1, y1 = get_subdivide_pt(first_idx, pred_full, line_points)
                sol_point['x0'] = x0
                sol_point['y0'] = y0
                sol_point['x1'] = x1
                sol_point['y1'] = y1

        img_file_name = "{}_{}.png".format(x['img_key'], i)

        output_lines[i]['pred'] = decoded_hw[k]
        output_lines[i]['pred_full'] = decoded_raw_hw[k]
        output_lines[i]['sol'] = sol_point
        output_lines[i]['lf'] = line_points
        output_lines[i]['start_idx'] = 1 #TODO: update to backward idx
        output_lines[i]['hw_path'] = img_file_name

        line_img = out['line_imgs'][k]

        full_img_file_name = os.path.join(json_folder, img_file_name)
        cv2.imwrite(full_img_file_name, line_img)

    json_path = x['json_path']
    with open(json_path, 'w') as f:
        json.dump(output_lines, f)

def update_ideal_results(pick, costs, decoded_hw, gt_json):

    most_ideal_pred = []
    improved_idxs = {}

    for i in xrange(len(gt_json)):
        gt_obj = gt_json[i]

        prev_pred = gt_obj.get('pred', '')
        gt = gt_obj['gt']

        pred = decoded_hw[pick[i]]

        prev_cer = error_rates.cer(gt, prev_pred)
        cer = costs[i]

        if cer > prev_cer or len(pred) == 0:
            most_ideal_pred.append(prev_pred)
            continue

        most_ideal_pred.append(pred)
        improved_idxs[i] = pick[i]

    return most_ideal_pred, improved_idxs
