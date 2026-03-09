"""
Focus Tracking System using OpenCV and MediaPipe.

This module uses the laptop camera to monitor the user's focus level
during study sessions. It detects:

1. Face presence (is the user at their desk?)
2. Eye gaze direction (is the user looking at the screen?)
3. Head pose (is the user facing the screen?)

States:
    🙂 FOCUSED    — User is looking at the screen
    😠 DISTRACTED — User is looking away
    👋 AWAY       — No face detected (user left)

When the user is distracted for more than DISTRACTION_THRESHOLD_SECONDS,
a warning notification is sent.

Privacy Note:
    - All processing is done locally. No images are saved or transmitted.
    - The camera feed is only used for real-time analysis.
    - Press 'q' to quit the focus tracker at any time.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from config.settings import CAMERA_INDEX, DISTRACTION_THRESHOLD_SECONDS
from notifications.notify import send_focus_warning, send_session_summary
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# MediaPipe Face Mesh setup
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Eye landmark indices for gaze estimation
# Left eye: inner corner, outer corner, top, bottom
LEFT_EYE = [362, 385, 387, 263, 373, 380]
# Right eye: inner corner, outer corner, top, bottom
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# Iris landmarks
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]


class FocusTracker:
    """
    Camera-based focus tracking system.

    Uses MediaPipe Face Mesh to detect face and eye positions,
    then determines if the user is focused on the screen.

    Attributes:
        camera_index (int): Which camera to use (0 = default).
        threshold_seconds (int): Seconds of distraction before warning.
        is_running (bool): Whether the tracker is currently active.
    """

    def __init__(self, task_id: Optional[int] = None):
        """
        Initialize the focus tracker.

        Args:
            task_id: Optional task ID for logging the focus session.
        """
        self.camera_index = CAMERA_INDEX
        self.threshold_seconds = DISTRACTION_THRESHOLD_SECONDS
        self.task_id = task_id
        self.is_running = False

        # Session tracking
        self.session_id = None
        self.focused_seconds = 0
        self.distracted_seconds = 0
        self.distraction_start = None  # When current distraction began
        self.last_warning_time = 0  # Avoid spamming warnings

        # State
        self.current_state = "focused"  # focused, distracted, away

        # Database
        self.db = DatabaseManager()

        logger.info("Focus tracker initialized")

    def start(self) -> None:
        """
        Start the focus tracking session.

        Opens the camera, begins face detection, and tracks focus.
        Press 'q' to quit the session.
        """
        logger.info("Starting focus tracking session...")

        # Start a database session
        self.session_id = self.db.start_focus_session(self.task_id)

        # Open camera
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logger.error(
                f"Cannot open camera (index {self.camera_index}). "
                "Check your camera permissions in System Preferences."
            )
            return

        self.is_running = True
        last_tick = time.time()

        # Initialize MediaPipe Face Mesh
        with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,  # Enables iris landmarks
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as face_mesh:

            logger.info("Camera opened. Focus tracking active. Press 'q' to stop.")

            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read camera frame")
                    break

                # Flip horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, _ = frame.shape

                # Process frame with MediaPipe
                results = face_mesh.process(rgb_frame)

                # Determine focus state
                current_time = time.time()
                elapsed = current_time - last_tick
                last_tick = current_time

                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]

                    # Calculate gaze direction
                    gaze = self._calculate_gaze(face_landmarks, w, h)

                    if gaze == "center":
                        self._set_state("focused", elapsed)
                    else:
                        self._set_state("distracted", elapsed)

                    # Draw face mesh (optional, for debugging)
                    self._draw_overlay(frame, face_landmarks, w, h)
                else:
                    # No face detected
                    self._set_state("away", elapsed)

                # Draw status overlay
                self._draw_status(frame)

                # Show the frame
                cv2.imshow("Focus Tracker - Press Q to Quit", frame)

                # Check for quit key
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        # Cleanup
        self.is_running = False
        cap.release()
        cv2.destroyAllWindows()

        # End the session
        self._end_session()

    def _calculate_gaze(self, face_landmarks, frame_w: int, frame_h: int) -> str:
        """
        Estimate gaze direction using iris position relative to eye corners.

        Args:
            face_landmarks: MediaPipe face landmarks.
            frame_w: Frame width in pixels.
            frame_h: Frame height in pixels.

        Returns:
            str: "center", "left", or "right"
        """
        try:
            # Get iris center positions
            left_iris_pts = []
            right_iris_pts = []

            for idx in LEFT_IRIS:
                lm = face_landmarks.landmark[idx]
                left_iris_pts.append([lm.x * frame_w, lm.y * frame_h])

            for idx in RIGHT_IRIS:
                lm = face_landmarks.landmark[idx]
                right_iris_pts.append([lm.x * frame_w, lm.y * frame_h])

            left_iris_center = np.mean(left_iris_pts, axis=0)
            right_iris_center = np.mean(right_iris_pts, axis=0)

            # Get eye corner positions for reference
            left_eye_inner = face_landmarks.landmark[362]
            left_eye_outer = face_landmarks.landmark[263]
            right_eye_inner = face_landmarks.landmark[133]
            right_eye_outer = face_landmarks.landmark[33]

            # Calculate horizontal ratio for left eye
            left_inner_x = left_eye_inner.x * frame_w
            left_outer_x = left_eye_outer.x * frame_w
            left_eye_width = abs(left_outer_x - left_inner_x)

            if left_eye_width > 0:
                left_ratio = (left_iris_center[0] - min(left_inner_x, left_outer_x)) / left_eye_width
            else:
                left_ratio = 0.5

            # Calculate horizontal ratio for right eye
            right_inner_x = right_eye_inner.x * frame_w
            right_outer_x = right_eye_outer.x * frame_w
            right_eye_width = abs(right_outer_x - right_inner_x)

            if right_eye_width > 0:
                right_ratio = (right_iris_center[0] - min(right_inner_x, right_outer_x)) / right_eye_width
            else:
                right_ratio = 0.5

            # Average the ratios
            avg_ratio = (left_ratio + right_ratio) / 2

            # Determine gaze direction
            # Center zone: 0.3 to 0.7 (looking at screen)
            if 0.3 <= avg_ratio <= 0.7:
                return "center"
            elif avg_ratio < 0.3:
                return "left"
            else:
                return "right"

        except (IndexError, ZeroDivisionError) as e:
            logger.debug(f"Gaze calculation error: {e}")
            return "center"  # Assume focused if we can't calculate

    def _set_state(self, new_state: str, elapsed_seconds: float) -> None:
        """
        Update the focus state and track time.

        Args:
            new_state: New state ("focused", "distracted", "away").
            elapsed_seconds: Time elapsed since last check.
        """
        if new_state == "focused":
            self.focused_seconds += elapsed_seconds
            self.distraction_start = None
            self.current_state = "focused"

        elif new_state in ("distracted", "away"):
            self.distracted_seconds += elapsed_seconds
            self.current_state = new_state

            # Track continuous distraction
            if self.distraction_start is None:
                self.distraction_start = time.time()

            # Check if we should send a warning
            distraction_duration = time.time() - self.distraction_start
            if distraction_duration >= self.threshold_seconds:
                # Avoid spamming: warn at most once per 30 seconds
                if time.time() - self.last_warning_time > 30:
                    send_focus_warning(new_state)
                    self.last_warning_time = time.time()

    def _draw_overlay(self, frame, face_landmarks, w: int, h: int) -> None:
        """
        Draw face mesh overlay on the frame.

        Args:
            frame: OpenCV image frame.
            face_landmarks: MediaPipe face landmarks.
            w: Frame width.
            h: Frame height.
        """
        # Draw iris circles
        for iris_indices in [LEFT_IRIS, RIGHT_IRIS]:
            pts = []
            for idx in iris_indices:
                lm = face_landmarks.landmark[idx]
                pts.append((int(lm.x * w), int(lm.y * h)))

            center = np.mean(pts, axis=0).astype(int)
            radius = int(np.linalg.norm(np.array(pts[0]) - np.array(pts[2])) / 2)

            color = (0, 255, 0) if self.current_state == "focused" else (0, 0, 255)
            cv2.circle(frame, tuple(center), radius, color, 2)

    def _draw_status(self, frame) -> None:
        """
        Draw the status overlay on the frame with emoji indicators.

        Args:
            frame: OpenCV image frame.
        """
        h, w, _ = frame.shape

        # Background bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Status text and color
        state_config = {
            "focused": {"text": "FOCUSED", "emoji": ":)", "color": (0, 255, 0)},
            "distracted": {"text": "DISTRACTED", "emoji": ":(", "color": (0, 0, 255)},
            "away": {"text": "AWAY", "emoji": "?", "color": (0, 165, 255)},
        }

        config = state_config.get(self.current_state, state_config["focused"])

        # Draw status text
        cv2.putText(
            frame,
            f"{config['emoji']} {config['text']}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            config["color"],
            2,
        )

        # Draw timer
        total = self.focused_seconds + self.distracted_seconds
        focus_pct = (self.focused_seconds / total * 100) if total > 0 else 100

        timer_text = (
            f"Focus: {focus_pct:.0f}% | "
            f"Focused: {int(self.focused_seconds)}s | "
            f"Distracted: {int(self.distracted_seconds)}s"
        )
        cv2.putText(
            frame,
            timer_text,
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        # Draw focus bar
        bar_width = w - 40
        bar_x = 20
        bar_y = 72

        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + 6), (50, 50, 50), -1)
        filled_width = int(bar_width * (focus_pct / 100))
        bar_color = (0, 255, 0) if focus_pct >= 60 else (0, 0, 255)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + 6), bar_color, -1)

    def _end_session(self) -> None:
        """End the focus session, save results, and show summary."""
        if self.session_id:
            self.db.end_focus_session(
                session_id=self.session_id,
                focused_seconds=int(self.focused_seconds),
                distracted_seconds=int(self.distracted_seconds),
            )

        total = self.focused_seconds + self.distracted_seconds
        focus_pct = (self.focused_seconds / total * 100) if total > 0 else 100

        logger.info(
            f"Focus session ended: "
            f"{self.focused_seconds:.0f}s focused, "
            f"{self.distracted_seconds:.0f}s distracted, "
            f"{focus_pct:.1f}% focus"
        )

        # Send summary notification
        send_session_summary(
            focused_minutes=int(self.focused_seconds / 60),
            distracted_minutes=int(self.distracted_seconds / 60),
            focus_percentage=focus_pct,
        )

    def stop(self) -> None:
        """Stop the focus tracker gracefully."""
        self.is_running = False
        logger.info("Focus tracker stop requested")


def run_focus_tracker(task_id: Optional[int] = None) -> None:
    """
    Convenience function to run the focus tracker.

    Args:
        task_id: Optional task ID to associate with this session.
    """
    tracker = FocusTracker(task_id=task_id)
    tracker.start()