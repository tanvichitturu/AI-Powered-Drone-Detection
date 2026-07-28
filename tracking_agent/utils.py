import math
import numpy as np
from typing import Sequence, Tuple, List

def calculate_iou(box1: Sequence[float], box2: Sequence[float]) -> float:
    """
    Calculates the Intersection over Union (IoU) between two bounding boxes.
    Format expected: [x1, y1, x2, y2]
    """
    if len(box1) != 4 or len(box2) != 4:
        raise ValueError(f"Boxes must have exactly 4 elements. Got {len(box1)} and {len(box2)}.")

    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])

    # Safe intersection area preventing negative bounds
    inter_w = max(0.0, x_right - x_left)
    inter_h = max(0.0, y_bottom - y_top)
    intersection_area = inter_w * inter_h

    # Safe individual box areas
    box1_area = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    box2_area = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])

    union_area = float(box1_area + box2_area - intersection_area)
    
    if union_area == 0.0:
        return 0.0
        
    return intersection_area / union_area


def iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    Vectorized pairwise IoU between two sets of boxes.
    boxes_a: (N, 4) array of [x1,y1,x2,y2]
    boxes_b: (M, 4) array of [x1,y1,x2,y2]
    Returns: (N, M) IoU matrix.

    Used by ByteTrack's cost-matrix construction instead of calling
    calculate_iou() once per (track, detection) pair in a Python loop -
    that approach is correct but doesn't scale past a handful of targets
    (O(N*M) Python-level function calls). This does the same math with
    NumPy broadcasting in one shot.
    """
    boxes_a = np.asarray(boxes_a, dtype=float)
    boxes_b = np.asarray(boxes_b, dtype=float)

    if boxes_a.size == 0 or boxes_b.size == 0:
        return np.zeros((len(boxes_a), len(boxes_b)))

    x_left = np.maximum(boxes_a[:, 0:1], boxes_b[:, 0])
    y_top = np.maximum(boxes_a[:, 1:2], boxes_b[:, 1])
    x_right = np.minimum(boxes_a[:, 2:3], boxes_b[:, 2])
    y_bottom = np.minimum(boxes_a[:, 3:4], boxes_b[:, 3])

    inter_w = np.clip(x_right - x_left, a_min=0.0, a_max=None)
    inter_h = np.clip(y_bottom - y_top, a_min=0.0, a_max=None)
    intersection = inter_w * inter_h

    area_a = np.clip(boxes_a[:, 2] - boxes_a[:, 0], 0.0, None) * np.clip(boxes_a[:, 3] - boxes_a[:, 1], 0.0, None)
    area_b = np.clip(boxes_b[:, 2] - boxes_b[:, 0], 0.0, None) * np.clip(boxes_b[:, 3] - boxes_b[:, 1], 0.0, None)

    union = area_a[:, None] + area_b[None, :] - intersection
    with np.errstate(divide="ignore", invalid="ignore"):
        iou = np.where(union > 0.0, intersection / union, 0.0)

    return iou


def xyxy_to_xywh(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    """
    Converts bounding box from [x1, y1, x2, y2] format to [center_x, center_y, width, height].
    Returns an immutable tuple.
    """
    if len(bbox) != 4:
        raise ValueError(f"Bounding box must have 4 elements. Got {len(bbox)}.")
        
    x1, y1, x2, y2 = bbox
    w = max(0.0, x2 - x1)
    h = max(0.0, y2 - y1)
    cx = x1 + (w / 2.0)
    cy = y1 + (h / 2.0)
    
    return (cx, cy, w, h)


def compute_squared_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
    """
    Calculates the squared Euclidean distance between two points to save CPU cycles.
    """
    return (pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2


def get_centroid(bbox: Sequence[float]) -> Tuple[float, float]:
    """
    Calculates the centroid (cx, cy) from an [x1, y1, x2, y2] bounding box.
    """
    return (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0


def get_bbox_area(bbox: Sequence[float]) -> float:
    """
    Calculates the safe area of an [x1, y1, x2, y2] bounding box.
    """
    w = max(0.0, bbox[2] - bbox[0])
    h = max(0.0, bbox[3] - bbox[1])
    return w * h


def compute_kinematics(
    history: List[Tuple[float, float]], 
    fps: float, 
    old_velocity: Tuple[float, float] = (0.0, 0.0), 
    alpha: float = 0.3
) -> Tuple[float, float, float, float]:
    """
    Calculates smoothed velocity (vx, vy), absolute speed, and heading (degrees).
    Uses Exponential Moving Average (EMA) to filter out bounding box jitter.
    
    Returns:
        Tuple containing: (vx, vy, speed, heading_deg)
    """
    raw_vx, raw_vy = 0.0, 0.0
    frame_delay = min(5, len(history))
    
    # Calculate raw velocity across the frame delay window
    if frame_delay > 1:
        dx = history[-1][0] - history[-frame_delay][0]
        dy = history[-1][1] - history[-frame_delay][1]
        time_span = (frame_delay - 1) / fps
        raw_vx = dx / time_span
        raw_vy = dy / time_span

    # Apply EMA Smoothing
    old_vx, old_vy = old_velocity
    if old_vx == 0.0 and old_vy == 0.0:
        smoothed_vx, smoothed_vy = raw_vx, raw_vy
    else:
        smoothed_vx = (alpha * raw_vx) + ((1.0 - alpha) * old_vx)
        smoothed_vy = (alpha * raw_vy) + ((1.0 - alpha) * old_vy)
        
    # Calculate absolute speed magnitude
    speed = math.sqrt(smoothed_vx**2 + smoothed_vy**2)
    
    # Calculate heading angle (trapping the stationary edge case)
    heading_deg = 0.0
    if speed >= 5.0: 
        heading_deg = math.degrees(math.atan2(-smoothed_vy, smoothed_vx)) % 360.0
        
    return (smoothed_vx, smoothed_vy, speed, heading_deg)