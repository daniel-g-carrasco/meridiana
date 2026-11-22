"""Italian connection cutoffs shared by the profile's checks and report rules, in kW.

Values and comparisons are unchanged; this module only owns their definitions.
"""

SPI_KW = 11.08       # CEI 0-21:2026 8.6.2: dedicated interface protection above this power
BACKUP_KW = 20.0     # CEI 0-21:2026 8.2.2.4: backup to the interface device above this power
LV_KW = 100.0        # CEI 0-21:2026 6.3 Table 5: low voltage up to this power
# Also the existing MV_KW alias: CEI 0-16:2026-07 6.3, Table 4, p. 43.
