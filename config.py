"""Central configuration. Edit values here; modules import them."""

# --- Data mode --------------------------------------------------------------
# "simulated" = generate defect_rate from weather (Phase A default).
# "real"      = use the defect_rate column from the uploaded spreadsheet.
DATA_MODE = "simulated"

# --- Bloom / fruit-development window ----------------------------------------
# Strawberry fruit develops ~25-35 days from bloom. We pull weather for the
# window ending WINDOW_END_DAYS before harvest and starting WINDOW_START_DAYS
# before harvest (i.e. the bloom/fruit-set period that drives cat-face).
WINDOW_START_DAYS = 45  # days before harvest the window opens (earliest bloom)
WINDOW_END_DAYS = 10    # days before harvest the window closes

# --- NASA POWER --------------------------------------------------------------
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMS = ["T2M_MIN", "T2M_MAX", "T2M", "PRECTOTCORR", "RH2M", "WS2M"]
NASA_COMMUNITY = "AG"

# --- Agronomic thresholds (feature builder) ----------------------------------
COLD_NIGHT_C = 7.0       # nights with T2M_MIN below this disrupt pollination
HEAT_SPIKE_C = 30.0      # days with T2M_MAX above this stress fruit set
RAIN_DAY_MM = 2.0        # days with precip above this count as "rain during bloom"
GDD_BASE_C = 10.0        # base temperature for growing-degree-days

# --- Simulator (injected ground-truth relationship) --------------------------
# defect_rate = BASELINE + sum(coef * feature) + noise, clamped to [0, 1].
# The analysis MUST recover that cold_nights and bloom_rain are the strong
# positive drivers. Keep these as the known truth the pipeline test checks.
SIM_BASELINE = 0.05
SIM_COEFS = {
    "cold_nights": 0.020,   # strong positive driver
    "bloom_rain_days": 0.015,  # strong positive driver
    "heat_spike_days": 0.004,  # weak driver
    "gdd": 0.0,             # no effect (analysis should rank it low)
}
SIM_GROWER_EFFECT_SD = 0.01  # faint per-grower offset to exercise confounders
SIM_NOISE_SD = 0.02
SIM_SEED = 42

# --- Cache / server ----------------------------------------------------------
WEATHER_CACHE_DIR = "weather_cache"
PORT = 8000
