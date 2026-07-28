import cv2
import numpy as np
from collections import deque
from scipy.optimize import linear_sum_assignment

# Local SDK Imports
from logger import flight_log
from utils import (
    compute_kinematics, 
    get_centroid, 
    get_bbox_area,
    iou_matrix
)

class DroneTracker:
    def __init__(
        self, 
        frame_rate=30, 
        max_history=30, 
        match_thresh=60.0, 
        max_lost=15,
        ema_alpha=0.3,
        gmc_redetect_interval=20,
        gmc_max_corners=100,
        gmc_quality_level=0.3,
        gmc_min_distance=7,
        bytetrack_high_thresh=0.5,
        bytetrack_match_thresh=0.3,
        bytetrack_low_match_thresh=0.5
    ):
        # Explicit Dependency Injection
        self.frame_rate = frame_rate
        self.max_history = max_history
        self.match_thresh_sq = match_thresh ** 2  # kept for _match_spatial_distance (unused by default, see below)
        self.max_lost = max_lost
        self.ema_alpha = ema_alpha

        # ByteTrack parameters
        # high_thresh: confidence split point between "high" and "low" detections
        # match_thresh: min IoU required to accept a match in stage 1 (high-conf vs all tracks)
        # low_match_thresh: min IoU required to accept a match in stage 2 (low-conf vs still-unmatched tracks)
        self.bytetrack_high_thresh = bytetrack_high_thresh
        self.bytetrack_match_thresh = bytetrack_match_thresh
        self.bytetrack_low_match_thresh = bytetrack_low_match_thresh
        
        self.next_id = 1
        self.active_tracks = {} 
        
        # GMC Optical Flow Parameters
        self.prev_gray_frame = None
        self.gmc_features = None
        self.gmc_frame_counter = 0
        self.gmc_redetect_interval = gmc_redetect_interval
        self.gmc_max_corners = gmc_max_corners
        self.gmc_quality_level = gmc_quality_level
        self.gmc_min_distance = gmc_min_distance

        flight_log.info(f"DroneTracker initialized. FPS: {self.frame_rate} | Max Lost: {self.max_lost}f.")

    def _apply_gmc(self, frame):
        if frame is None:
            # No pixel data available (e.g. a headless/decoupled tracker fed
            # detections over the network with no camera access). GMC needs
            # actual frames to compute optical flow, so it cannot run here -
            # this is a capability tradeoff, not a bug. Log once so it's
            # visible instead of silently degrading accuracy.
            if not getattr(self, "_gmc_disabled_warned", False):
                flight_log.warning(
                    "DroneTracker.update() called with frame=None: "
                    "Global Motion Compensation is disabled for this session."
                )
                self._gmc_disabled_warned = True
            return 0.0, 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        camera_dx, camera_dy = 0.0, 0.0
        
        if self.prev_gray_frame is not None:
            if (self.gmc_features is None or 
                self.gmc_frame_counter % self.gmc_redetect_interval == 0 or 
                len(self.gmc_features) < 15):
                
                self.gmc_features = cv2.goodFeaturesToTrack(
                    self.prev_gray_frame, 
                    maxCorners=self.gmc_max_corners, 
                    qualityLevel=self.gmc_quality_level, 
                    minDistance=self.gmc_min_distance
                )
            
            if self.gmc_features is not None and len(self.gmc_features) > 0:
                curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
                    self.prev_gray_frame, gray, self.gmc_features, None
                )
                
                if curr_pts is not None and status is not None:
                    good_prev = self.gmc_features[status == 1]
                    good_curr = curr_pts[status == 1]
                    
                    if len(good_curr) > 0:
                        shifts = good_curr - good_prev
                        camera_dx = float(np.median(shifts[:, 0]))
                        camera_dy = float(np.median(shifts[:, 1]))
                        self.gmc_features = good_curr.reshape(-1, 1, 2)
                    else:
                        self.gmc_features = None
                else:
                    self.gmc_features = None
                    
        self.prev_gray_frame = gray
        self.gmc_frame_counter += 1
        return camera_dx, camera_dy

    # ==========================================
    # MATCHING STRATEGIES
    # ==========================================

    def _match_spatial_distance(self, current_centroids, cam_dx, cam_dy):
        detection_to_id = {}
        unmatched_detections = list(range(len(current_centroids)))
        
        for track_id, track_state in self.active_tracks.items():
            expected_x = track_state["centroid"][0] - cam_dx
            expected_y = track_state["centroid"][1] - cam_dy
            
            best_match_idx = -1
            best_dist_sq = self.match_thresh_sq
            
            for i in unmatched_detections:
                cx, cy = current_centroids[i]
                dist_sq = (cx - expected_x)**2 + (cy - expected_y)**2
                
                if dist_sq < best_dist_sq:
                    best_dist_sq = dist_sq
                    best_match_idx = i
                    
            if best_match_idx != -1:
                detection_to_id[best_match_idx] = track_id
                unmatched_detections.remove(best_match_idx)

        return detection_to_id, unmatched_detections

    def _match_bytetrack(self, current_centroids, current_bboxes, current_confs, cam_dx, cam_dy):
        """
        ByteTrack-style two-stage association using IoU cost + the Hungarian
        algorithm (optimal assignment), instead of greedy nearest-centroid.

        Stage 1: HIGH-confidence detections vs ALL active tracks.
        Stage 2: LOW-confidence detections vs tracks still unmatched after
                 stage 1. This is ByteTrack's key idea - a low-confidence box
                 (blurred/partially occluded) is still useful to keep an
                 existing track alive, even though it's not trustworthy
                 enough to START a brand new track from scratch.

        Detections that remain unmatched after both stages: only HIGH-conf
        ones are eligible to spawn new tracks. Unmatched low-conf detections
        are discarded entirely - there's not enough evidence in a single
        low-confidence box with no prior track to justify creating an ID.
        """
        n_dets = len(current_bboxes)
        detection_to_id = {}
        unmatched_detections = list(range(n_dets))

        track_ids = list(self.active_tracks.keys())
        if n_dets == 0 or not track_ids:
            # No tracks to match against yet: everything unmatched, but only
            # high-conf detections should go on to spawn new tracks.
            unmatched_detections = [
                i for i in unmatched_detections
                if current_confs[i] >= self.bytetrack_high_thresh
            ]
            return detection_to_id, unmatched_detections

        # Predict each track's bbox forward using GMC camera-shift compensation,
        # same idea as the old centroid strategy, just applied to full boxes.
        predicted_bboxes = {}
        for tid in track_ids:
            x1, y1, x2, y2 = self.active_tracks[tid]["bbox"]
            predicted_bboxes[tid] = [x1 - cam_dx, y1 - cam_dy, x2 - cam_dx, y2 - cam_dy]

        high_idx = [i for i in range(n_dets) if current_confs[i] >= self.bytetrack_high_thresh]
        low_idx = [i for i in range(n_dets) if current_confs[i] < self.bytetrack_high_thresh]

        unmatched_track_ids = list(track_ids)

        def _run_stage(det_indices, track_id_pool, iou_thresh):
            """Runs one Hungarian-assignment pass, returns (matched_pairs, still_unmatched_tracks, still_unmatched_dets)."""
            if not det_indices or not track_id_pool:
                return [], list(track_id_pool), list(det_indices)

            track_box_arr = np.array([predicted_bboxes[tid] for tid in track_id_pool])
            det_box_arr = np.array([current_bboxes[i] for i in det_indices])
            cost = 1.0 - iou_matrix(track_box_arr, det_box_arr)

            row_ind, col_ind = linear_sum_assignment(cost)

            matched_pairs = []
            matched_tracks_set = set()
            matched_dets_set = set()
            for r, c in zip(row_ind, col_ind):
                if cost[r, c] <= (1.0 - iou_thresh):
                    tid = track_id_pool[r]
                    det_i = det_indices[c]
                    matched_pairs.append((tid, det_i))
                    matched_tracks_set.add(tid)
                    matched_dets_set.add(det_i)

            still_unmatched_tracks = [t for t in track_id_pool if t not in matched_tracks_set]
            still_unmatched_dets = [d for d in det_indices if d not in matched_dets_set]
            return matched_pairs, still_unmatched_tracks, still_unmatched_dets

        # ---- Stage 1: high-confidence detections vs ALL active tracks ----
        stage1_pairs, unmatched_track_ids, high_idx = _run_stage(
            high_idx, unmatched_track_ids, self.bytetrack_match_thresh
        )
        for tid, det_i in stage1_pairs:
            detection_to_id[det_i] = tid
            if det_i in unmatched_detections:
                unmatched_detections.remove(det_i)

        # ---- Stage 2: remaining unmatched tracks vs LOW-confidence detections ----
        stage2_pairs, unmatched_track_ids, low_idx = _run_stage(
            low_idx, unmatched_track_ids, self.bytetrack_low_match_thresh
        )
        for tid, det_i in stage2_pairs:
            detection_to_id[det_i] = tid
            if det_i in unmatched_detections:
                unmatched_detections.remove(det_i)

        # Only high-confidence leftovers can spawn new tracks. Low-confidence
        # detections that matched nothing are dropped here, by design.
        unmatched_detections = [
            i for i in unmatched_detections
            if current_confs[i] >= self.bytetrack_high_thresh
        ]

        return detection_to_id, unmatched_detections

    # ==========================================
    # LIFECYCLE ORCHESTRATOR
    # ==========================================

    def update(self, yolo_boxes, frame):
        # 1. Global Motion Compensation
        cam_dx, cam_dy = self._apply_gmc(frame)
        
        # 2. Parse Detections
        current_centroids = []
        current_bboxes = []
        current_confs = []
        current_classes = []
        
        if len(yolo_boxes) > 0:
            if hasattr(yolo_boxes, "xyxy"):
                # Path A: Ultralytics YOLO `Boxes` object (used by video_test.py
                # and benchmark.py's MockYoloBoxes, which mimics this interface).
                boxes_data = yolo_boxes.xyxy.cpu().numpy()
                confs_data = yolo_boxes.conf.cpu().numpy()
                cls_data = yolo_boxes.cls.cpu().numpy()
            else:
                # Path B: plain detections (e.g. JSON decoded off MQTT by a
                # decoupled tracking agent that never touches YOLO/Ultralytics).
                # Expected shape per detection: [x1, y1, x2, y2, conf, cls],
                # with conf/cls optional (defaulted if the array is narrower).
                raw = np.asarray(yolo_boxes, dtype=float)
                if raw.ndim == 1:
                    raw = raw.reshape(1, -1)
                if raw.shape[1] < 4:
                    raise ValueError(
                        f"Raw detections need at least 4 columns [x1,y1,x2,y2]; got shape {raw.shape}."
                    )
                boxes_data = raw[:, 0:4]
                confs_data = raw[:, 4] if raw.shape[1] > 4 else np.ones(len(raw))
                cls_data = raw[:, 5] if raw.shape[1] > 5 else np.zeros(len(raw))

            for i, box in enumerate(boxes_data):
                current_centroids.append(get_centroid(box))
                current_bboxes.append(box)
                current_confs.append(float(confs_data[i]))
                current_classes.append(int(cls_data[i]))

        # 3. Matching Router (ByteTrack: two-stage IoU + Hungarian assignment)
        detection_to_id, unmatched_detections = self._match_bytetrack(
            current_centroids, current_bboxes, current_confs, cam_dx, cam_dy
        )
        
        # 4. Lifecycle Management: Update Matched Tracks (O(1) Reverse Lookup)
        matched_tracks_set = set()
        
        for det_idx, track_id in detection_to_id.items():
            track_state = self.active_tracks[track_id]
            
            track_state["centroid"] = current_centroids[det_idx]
            track_state["bbox"] = current_bboxes[det_idx]
            track_state["confidence"] = current_confs[det_idx]
            track_state["class_id"] = current_classes[det_idx]
            track_state["missed_frames"] = 0
            track_state["age"] += 1
            
            # O(1) ring buffer append
            track_state["history"].append(current_centroids[det_idx])
            
            matched_tracks_set.add(track_id)
            
        # 4b. Lifecycle Management: Update Missed Tracks
        for track_id, track_state in self.active_tracks.items():
            if track_id not in matched_tracks_set:
                track_state["missed_frames"] += 1

        # 5. Lifecycle Management: Target Acquisition
        for i in unmatched_detections:
            new_id = self.next_id
            self.next_id += 1
            
            # Initialize history with a deque maxlen to prevent memory leaks
            history_deque = deque([current_centroids[i]], maxlen=self.max_history)
            
            self.active_tracks[new_id] = {
                "centroid": current_centroids[i],
                "bbox": current_bboxes[i],
                "confidence": current_confs[i],
                "class_id": current_classes[i],
                "missed_frames": 0,
                "age": 1,
                "history": history_deque,
                "velocity_px_sec": (0.0, 0.0) 
            }
            detection_to_id[i] = new_id

        # 6. Lifecycle Management: Target Eviction
        dead_tracks = [tid for tid, state in self.active_tracks.items() if state["missed_frames"] > self.max_lost]
        for tid in dead_tracks:
            del self.active_tracks[tid]

        # 7. Build Standardized Payload
        payload = []
        for i, bbox in enumerate(current_bboxes):
            assigned_id = detection_to_id.get(i)
            if assigned_id is None:
                continue
                
            track_state = self.active_tracks[assigned_id]
            history_list = list(track_state["history"]) # Convert deque to list for downstream JSON serialization
            
            vx, vy, speed, heading = compute_kinematics(
                history=history_list, 
                fps=self.frame_rate, 
                old_velocity=track_state["velocity_px_sec"],
                alpha=self.ema_alpha
            )
            
            track_state["velocity_px_sec"] = (vx, vy)
            
            payload.append({
                "track_id": assigned_id,
                "class_id": track_state["class_id"],
                "confidence": round(track_state["confidence"], 2),
                "bbox": [int(x) for x in bbox],
                "bbox_area": int(get_bbox_area(bbox)),
                "centroid": current_centroids[i],
                "velocity_px_sec": (round(vx, 1), round(vy, 1)),
                "speed": round(speed, 1),
                "heading_deg": round(heading, 1),
                "age_frames": track_state["age"],
                "history": history_list
            })
            
        return payload

def draw_tracking_data(frame, tracks):
    # [Unchanged: Visualization logic]
    for track in tracks:
        tid = track["track_id"]
        x1, y1, x2, y2 = track["bbox"]
        age = track["age_frames"]
        conf = track["confidence"]
        history = track["history"]
        speed = track.get("speed", 0)
        heading = track.get("heading_deg", 0)
        
        # Hardcoding the threshold visualization fallback if config is unavailable in UI space
        if speed < 5.0: 
            label_kinematics = "Stationary"
        else:
            label_kinematics = f"{int(speed)} px/s @ {int(heading)}deg"
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        label_id = f"ID: {tid} | Conf: {conf}"
        label_age = f"Age: {age}f"
        
        cv2.putText(frame, label_id, (x1, y1 - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(frame, label_age, (x1, y1 - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(frame, label_kinematics, (x1, y1 - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        
        if len(history) > 1:
            for i in range(1, len(history)):
                pt1 = (int(history[i - 1][0]), int(history[i - 1][1]))
                pt2 = (int(history[i][0]), int(history[i][1]))
                thickness = int(np.sqrt(64 / float(len(history) - i + 1)) * 3)
                cv2.line(frame, pt1, pt2, (0, 0, 255), thickness)
                
    return frame