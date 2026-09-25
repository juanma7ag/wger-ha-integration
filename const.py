"""Constants for the Wger integration."""

from datetime import timedelta

DOMAIN = "wger"

#
# Configuration
#

CONF_URL = "url"
CONF_TOKEN = "token"
CONF_WEEKLY_GOAL = "weekly_goal"
DEFAULT_WEEKLY_GOAL = 3

#
# Update interval
#

DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)

#
# HA Platforms
#

PLATFORMS = [
    "sensor",
    "binary_sensor",
    "button",
]

#
# API
#

API_VERSION = "/api/v2"

#
# Core
#

ENDPOINT_PROFILE = "/userprofile/"

#
# Routines
#

ENDPOINT_ROUTINES = "/routine/"

#
# Workout
#

ENDPOINT_WORKOUT_SESSIONS = "/workoutsession/"
ENDPOINT_WORKOUT_LOGS = "/workoutlog/"

#
# Body metrics
#

ENDPOINT_WEIGHT_ENTRIES = "/weightentry/"
ENDPOINT_MEASUREMENTS = "/measurement/"

#
# Exercise database
#

ENDPOINT_EXERCISE_INFO = "/exerciseinfo/"

#
# Sensors
#

SENSOR_ACTIVE_ROUTINE = "active_routine"
SENSOR_LAST_SESSION = "last_session"
SENSOR_TRAININGS_THIS_WEEK = "trainings_this_week"
SENSOR_WEEKLY_VOLUME = "weekly_volume"
SENSOR_CURRENT_WEIGHT = "current_weight"

#
# Binary sensors
#

BINARY_TRAINING_TODAY = "training_today"
BINARY_TRAINING_PENDING = "training_pending"

#
# Defaults
#

DEFAULT_PAGE_LIMIT = 100
DEFAULT_LOG_LIMIT = 500